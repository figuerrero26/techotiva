"""
Router de administración: estadísticas globales, gestión de usuarios y alertas.
"""

import csv
import io
import json
import secrets
import string
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel as _BM
from sqlalchemy import case, func
from sqlalchemy.orm import Session
from app.services.email_service import (
    enviar_correo_bienvenida_dispositivo, enviar_correo_recuperacion, generar_token,
)
from app.core.config import settings

from database import get_db
from app.core.security import hash_password
from app.models.models import (
    Usuario, Estados, EstadoRegistro, Dispositivo, Prescriptor, Beneficiario,
    Actividad, Seguimiento, PrimerContacto, Inscripcion,
)
from app.schemas.schemas import (
    AdminStats, UsuarioAdmin, CambiarEstado, AlertaOut,
    AdminDispositivoOut, AdminDispositivoCreate, CambiarRolRequest,
    BeneficiarioResumen,
)
from app.routers._deps import get_current_user, require_role
from app.services.estado_service import EstadoService

router = APIRouter(prefix="/admin", tags=["Administración"])
admin_only = require_role("admin")


# ─── Helper interno ──────────────────────────────────────────────────────────
def _build_usuario_admin(u: Usuario) -> UsuarioAdmin:
    """Construye UsuarioAdmin resolviendo el nombre y campos de perfil según el rol."""
    nombre = u.email
    fecha_nacimiento = None
    localidad = None
    telefono = None
    descripcion = None
    genero = None
    prescriptor_nombre = None
    dispositivo_nombre = None
    prescriptor_id_val = None
    dispositivo_id_val = None
    beneficiario_id_val = None

    if u.rol == "dispositivo" and u.dispositivo:
        nombre = u.dispositivo.nombre
        telefono = u.dispositivo.telefono
        descripcion = u.dispositivo.descripcion
        dispositivo_id_val = u.dispositivo.id
        dispositivo_nombre = u.dispositivo.nombre
    elif u.rol == "prescriptor" and u.prescriptor:
        nombre = u.prescriptor.nombre_completo
        telefono = u.prescriptor.telefono
        prescriptor_id_val = u.prescriptor.id
        descripcion = u.prescriptor.perfil_disciplina
        if u.prescriptor.dispositivo_id and u.prescriptor.dispositivo:
            dispositivo_nombre = u.prescriptor.dispositivo.nombre
    elif u.rol == "beneficiario" and u.beneficiario:
        nombre = u.beneficiario.nombre_apodo
        fecha_nacimiento = u.beneficiario.fecha_nacimiento
        localidad = u.beneficiario.localidad
        telefono = u.beneficiario.telefono
        descripcion = u.beneficiario.descripcion
        genero = u.beneficiario.genero
        beneficiario_id_val = u.beneficiario.id
        if u.beneficiario.prescriptor_id and u.beneficiario.prescriptor:
            prescriptor_nombre = u.beneficiario.prescriptor.nombre_completo
        if u.beneficiario.dispositivo_id and u.beneficiario.dispositivo:
            dispositivo_nombre = u.beneficiario.dispositivo.nombre
            dispositivo_id_val = u.beneficiario.dispositivo_id
    elif u.rol == "admin":
        nombre = "Admin"

    proceso_finalizado = (
        u.beneficiario is not None and u.beneficiario.estado == Estados.FINALIZADO
    )

    return UsuarioAdmin(
        id=u.id,
        email=u.email,
        rol=u.rol,
        status=u.estado,
        fecha_registro=u.fecha_registro,
        nombre=nombre,
        fecha_nacimiento=fecha_nacimiento,
        localidad=localidad,
        telefono=telefono,
        descripcion=descripcion,
        genero=genero,
        prescriptor_nombre=prescriptor_nombre,
        dispositivo_nombre=dispositivo_nombre,
        prescriptor_id=prescriptor_id_val,
        dispositivo_id=dispositivo_id_val,
        beneficiario_id=beneficiario_id_val,
        perfil_disciplina=u.prescriptor.perfil_disciplina if u.rol == "prescriptor" and u.prescriptor else None,
        politica_privacidad_at=u.politica_privacidad_at,
        proceso_finalizado=proceso_finalizado,
    )


# ────────────────────────── STATS GLOBALES ──────────────────────────
@router.get("/stats", response_model=AdminStats)
def admin_stats(
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(admin_only),
):
    total_disp = (
        db.query(Dispositivo)
        .join(Usuario, Usuario.id == Dispositivo.usuario_id)
        .join(Usuario.estado_actual)
        .filter(EstadoRegistro.estado == Estados.ACTIVO)
        .count()
    )
    total_users = db.query(Usuario).filter(Usuario.rol != "admin").count()
    total_presc = (
        db.query(Prescriptor)
        .join(Usuario, Usuario.id == Prescriptor.usuario_id)
        .join(Usuario.estado_actual)
        .filter(EstadoRegistro.estado == Estados.ACTIVO)
        .count()
    )
    total_benef = (
        db.query(Beneficiario)
        .join(Usuario, Usuario.id == Beneficiario.usuario_id)
        .join(Usuario.estado_actual)
        .filter(EstadoRegistro.estado == Estados.ACTIVO)
        .count()
    )

    umbral = datetime.now(timezone.utc) - timedelta(days=14)
    dispositivos_activos = (
        db.query(Dispositivo)
        .join(Usuario, Usuario.id == Dispositivo.usuario_id)
        .join(Usuario.estado_actual)
        .filter(EstadoRegistro.estado == Estados.ACTIVO)
        .all()
    )
    alertas = 0
    for d in dispositivos_activos:
        presc_ids = [p.id for p in d.prescriptores]
        if not presc_ids:
            alertas += 1
            continue
        ultimo_seg = (
            db.query(Seguimiento)
            .filter(Seguimiento.prescriptor_id.in_(presc_ids), Seguimiento.fecha >= umbral)
            .first()
        )
        if not ultimo_seg:
            alertas += 1

    total_acts = db.query(Actividad).count()

    return AdminStats(
        total_dispositivos=total_disp,
        total_usuarios=total_users,
        total_prescriptores=total_presc,
        total_beneficiarios=total_benef,
        alertas_pendientes=alertas,
        total_actividades=total_acts,
    )


# ────────────────────────── USUARIOS ──────────────────────────
@router.get("/usuarios", response_model=list[UsuarioAdmin])
def listar_usuarios(
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(admin_only),
):
    users = (
        db.query(Usuario)
        .outerjoin(EstadoRegistro, Usuario.estado_actual_id == EstadoRegistro.id)
        .filter(Usuario.rol != "admin")
        .order_by(
            case(
                (EstadoRegistro.estado == Estados.PENDIENTE, 0),
                (EstadoRegistro.estado == Estados.ACTIVO,    1),
                (EstadoRegistro.estado == Estados.INACTIVO,  2),
                else_=3,
            ),
            Usuario.fecha_registro.desc(),
        )
        .all()
    )
    return [_build_usuario_admin(u) for u in users]


# ────────────────────────── CAMBIAR ESTADO ──────────────────────────
@router.put("/usuarios/{usuario_id}/estado", response_model=UsuarioAdmin)
def cambiar_estado_usuario(
    usuario_id: int,
    data: CambiarEstado,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(admin_only),
):
    user = db.query(Usuario).filter(Usuario.id == usuario_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    if user.id == current_user.id:
        raise HTTPException(status_code=400, detail="No puedes cambiar tu propio estado")

    service = EstadoService(db)
    service.cambiar_estado(entidad_obj=user, nuevo_estado=data.status, admin_id=current_user.id, motivo="Cambio de estado desde panel administrativo")

    if user.dispositivo:
        service.cambiar_estado(entidad_obj=user.dispositivo, nuevo_estado=data.status, admin_id=current_user.id, motivo="Cambio de estado desde panel administrativo")
    elif user.prescriptor:
        service.cambiar_estado(entidad_obj=user.prescriptor, nuevo_estado=data.status, admin_id=current_user.id, motivo="Cambio de estado desde panel administrativo")
    elif user.beneficiario:
        service.cambiar_estado(entidad_obj=user.beneficiario, nuevo_estado=data.status, admin_id=current_user.id, motivo="Cambio de estado desde panel administrativo")

    db.refresh(user)
    return _build_usuario_admin(user)


# ────────────────────────── CAMBIAR ROL ──────────────────────────
@router.put("/usuarios/{usuario_id}/rol", response_model=UsuarioAdmin)
def cambiar_rol_usuario(
    usuario_id: int,
    data: CambiarRolRequest,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(admin_only),
):
    user = db.query(Usuario).filter(Usuario.id == usuario_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    if user.id == current_user.id:
        raise HTTPException(status_code=400, detail="No puedes cambiar tu propio rol")

    rol_anterior = user.rol
    user.rol = data.rol

    # Registrar el cambio en EstadoRegistro con motivo
    service = EstadoService(db)
    service.cambiar_estado(
        entidad_obj=user,
        nuevo_estado=user.estado,
        admin_id=current_user.id,
        motivo=f"Cambio de rol: {rol_anterior} → {data.rol}"
    )

    db.commit()
    db.refresh(user)
    return _build_usuario_admin(user)


# ────────────────────────── CREAR PERFIL DISPOSITIVO PARA USUARIO EXISTENTE ──────────────────────────
@router.post("/usuarios/{usuario_id}/crear-dispositivo", response_model=UsuarioAdmin)
def crear_perfil_dispositivo(
    usuario_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(admin_only),
):
    user = db.query(Usuario).filter(Usuario.id == usuario_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    if user.rol != "dispositivo":
        raise HTTPException(status_code=400, detail="El usuario no tiene rol de dispositivo")
    if user.dispositivo:
        raise HTTPException(status_code=409, detail="Ya tiene un perfil de dispositivo")

    disp = Dispositivo(
        usuario_id=user.id,
        nombre=user.email,
    )
    db.add(disp)
    db.flush()

    service = EstadoService(db)
    service.cambiar_estado(entidad_obj=disp, nuevo_estado=Estados.ACTIVO, admin_id=current_user.id, motivo="Perfil creado desde admin")

    db.commit()
    db.refresh(user)
    return _build_usuario_admin(user)


# ────────────────────────── ELIMINAR USUARIO ──────────────────────────
@router.delete("/usuarios/{usuario_id}", status_code=204)
def eliminar_usuario(
    usuario_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(admin_only),
):
    user = db.query(Usuario).filter(Usuario.id == usuario_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    if user.id == current_user.id:
        raise HTTPException(status_code=400, detail="No puedes eliminar tu propia cuenta")

    try:
        # Limpiar FK estado_actual del usuario
        user.estado_actual_id = None
        db.flush()

        # ── Beneficiario (puede existir aunque el rol actual sea otro) ──
        benef = db.query(Beneficiario).filter(Beneficiario.usuario_id == user.id).first()
        if benef:
            benef.estado_actual_id = None
            db.flush()
            db.query(Seguimiento).filter(Seguimiento.beneficiario_id == benef.id).delete(synchronize_session="fetch")
            db.flush()
            db.query(PrimerContacto).filter(PrimerContacto.beneficiario_id == benef.id).delete(synchronize_session="fetch")
            db.flush()
            db.query(Inscripcion).filter(Inscripcion.beneficiario_id == benef.id).delete(synchronize_session="fetch")
            db.flush()
            db.query(EstadoRegistro).filter(
                EstadoRegistro.entidad_tipo.in_(["beneficiarios", "beneficiario"]),
                EstadoRegistro.entidad_id == benef.id,
            ).delete(synchronize_session="fetch")
            db.flush()
            db.delete(benef)
            db.flush()

        # ── Prescriptor ──
        presc = db.query(Prescriptor).filter(Prescriptor.usuario_id == user.id).first()
        if presc:
            presc.estado_actual_id = None
            db.flush()
            db.query(Beneficiario).filter(Beneficiario.prescriptor_id == presc.id).update(
                {"prescriptor_id": None}, synchronize_session="fetch"
            )
            db.flush()
            db.query(Seguimiento).filter(Seguimiento.prescriptor_id == presc.id).delete(synchronize_session="fetch")
            db.flush()
            db.query(PrimerContacto).filter(PrimerContacto.prescriptor_id == presc.id).delete(synchronize_session="fetch")
            db.flush()
            db.query(EstadoRegistro).filter(
                EstadoRegistro.entidad_tipo.in_(["prescriptores", "prescriptor"]),
                EstadoRegistro.entidad_id == presc.id,
            ).delete(synchronize_session="fetch")
            db.flush()
            db.delete(presc)
            db.flush()

        # ── Dispositivo ──
        disp = db.query(Dispositivo).filter(Dispositivo.usuario_id == user.id).first()
        if disp:
            disp.estado_actual_id = None
            db.flush()
            db.query(Prescriptor).filter(Prescriptor.dispositivo_id == disp.id).update(
                {"dispositivo_id": None}, synchronize_session="fetch"
            )
            db.flush()
            db.query(EstadoRegistro).filter(
                EstadoRegistro.entidad_tipo.in_(["dispositivos", "dispositivo"]),
                EstadoRegistro.entidad_id == disp.id,
            ).delete(synchronize_session="fetch")
            db.flush()
            db.delete(disp)
            db.flush()

        # ── Estados del usuario ──
        db.query(EstadoRegistro).filter(
            EstadoRegistro.entidad_tipo.in_(["usuarios", "usuario"]),
            EstadoRegistro.entidad_id == user.id,
        ).delete(synchronize_session=False)

        db.delete(user)
        db.commit()

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error al eliminar: {str(e)}")


# ────────────────────────── RESTABLECER CONTRASEÑA ──────────────────────────
@router.post("/usuarios/{usuario_id}/restablecer-password")
def admin_restablecer_password(
    usuario_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(admin_only),
):
    user = db.query(Usuario).filter(Usuario.id == usuario_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    if not user.email or user.email.endswith("@sin-cuenta.mascate"):
        raise HTTPException(status_code=400, detail="Este usuario no tiene un correo real registrado")

    token = generar_token()
    user.password_reset_token = token
    user.password_reset_token_expiry = datetime.now(timezone.utc) + timedelta(hours=24)
    db.commit()

    background_tasks.add_task(
        enviar_correo_recuperacion,
        email=user.email,
        token=token,
        base_url=settings.app_base_url,
    )
    return {"message": f"Correo de restablecimiento enviado a {user.email}"}


# ────────────────────────── ALERTAS ──────────────────────────
@router.get("/alertas", response_model=list[AlertaOut])
def alertas_sistema(
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(admin_only),
):
    umbral = datetime.now(timezone.utc) - timedelta(days=14)
    dispositivos = (
        db.query(Dispositivo)
        .join(Usuario, Usuario.id == Dispositivo.usuario_id)
        .join(Usuario.estado_actual)
        .filter(EstadoRegistro.estado == Estados.ACTIVO)
        .all()
    )
    alertas = []
    for d in dispositivos:
        tiene_actividad_reciente = False
        presc_ids = [p.id for p in d.prescriptores]
        if presc_ids:
            ultimo_seg = (
                db.query(Seguimiento)
                .filter(Seguimiento.prescriptor_id.in_(presc_ids), Seguimiento.fecha >= umbral)
                .first()
            )
            if ultimo_seg:
                tiene_actividad_reciente = True

        if not tiene_actividad_reciente:
            ultima_fecha = (
                db.query(func.max(Seguimiento.fecha))
                .filter(Seguimiento.prescriptor_id.in_(presc_ids) if presc_ids else False)
                .scalar()
            )
            if ultima_fecha:
                if ultima_fecha.tzinfo is None:
                    ultima_fecha = ultima_fecha.replace(tzinfo=timezone.utc)
                dias = (datetime.now(timezone.utc) - ultima_fecha).days
            else:
                dias = 999

            alertas.append(AlertaOut(
                dispositivo_id=d.id,
                dispositivo=d.nombre,
                mensaje=f"Sin reporte en {dias} días" if dias < 999 else "Sin reportes registrados",
                dias_sin_actividad=dias,
            ))

    return alertas


# ────────────────────────── CREAR DISPOSITIVO (ADMIN) ──────────────────────────
@router.post("/dispositivos", response_model=AdminDispositivoOut, status_code=201)
def admin_crear_dispositivo(
    data: AdminDispositivoCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(admin_only),
):
    if db.query(Usuario).filter(Usuario.email == data.email).first():
        raise HTTPException(status_code=409, detail="Ya existe una cuenta con ese correo")

    # Generar password temporal
    alphabet = string.ascii_letters + string.digits
    password_temporal = ''.join(secrets.choice(alphabet) for _ in range(12))

    user = Usuario(
        email=data.email,
        password_hash=hash_password(password_temporal),
        rol="dispositivo",
        email_verificado=True,
    )
    db.add(user)
    db.flush()

    service_estado = EstadoService(db)
    service_estado.cambiar_estado(entidad_obj=user, nuevo_estado=Estados.ACTIVO, admin_id=current_user.id, motivo="Dispositivo creado directamente por el administrador")

    disp = Dispositivo(
        usuario_id=user.id,
        nombre=data.nombre,
        lugar_actividades=data.lugar_actividades,
        ubicacion=data.ubicacion,
        tipo_servicio=data.tipo_servicio,
        dia_actividad=data.dia_actividad,
        hora_actividad=data.hora_actividad,
        telefono=data.telefono,
        redes_sociales=data.redes_sociales,
    )
    db.add(disp)
    db.flush()

    service_estado.cambiar_estado(entidad_obj=disp, nuevo_estado=Estados.ACTIVO, admin_id=current_user.id, motivo="Dispositivo creado directamente por el administrador")

    db.commit()
    db.refresh(disp)

    background_tasks.add_task(
        enviar_correo_bienvenida_dispositivo,
        email=data.email,
        password=password_temporal,
        base_url=settings.app_base_url,
    )

    return AdminDispositivoOut(
        id=disp.id,
        nombre=disp.nombre,
        tipo_servicio=disp.tipo_servicio,
        num_beneficiarios=0,
        prescriptores=[],
        activo=True,
        email=data.email,
        fecha_registro=user.fecha_registro,
        num_actividades=0,
        asistencia_pct=None,
    )


# ────────────────────────── LISTAR DISPOSITIVOS ──────────────────────────
@router.get("/dispositivos", response_model=list[AdminDispositivoOut])
def admin_listar_dispositivos(
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(admin_only),
):
    dispositivos = db.query(Dispositivo).all()
    result = []
    for d in dispositivos:
        benef_ids = set()
        insc = (
            db.query(Inscripcion.beneficiario_id)
            .join(Actividad, Actividad.id == Inscripcion.actividad_id)
            .filter(Actividad.dispositivo_id == d.id)
            .distinct().all()
        )
        benef_ids.update(b[0] for b in insc)
        pc = (
            db.query(PrimerContacto.beneficiario_id)
            .filter(PrimerContacto.dispositivo_id == d.id)
            .distinct().all()
        )
        benef_ids.update(b[0] for b in pc)

        presc_ids = [p.id for p in d.prescriptores]
        if presc_ids:
            seg = (
                db.query(Seguimiento.beneficiario_id)
                .filter(Seguimiento.prescriptor_id.in_(presc_ids))
                .distinct().all()
            )
            benef_ids.update(b[0] for b in seg)

        num_actividades = db.query(Actividad).filter(Actividad.dispositivo_id == d.id).count()
        presc_names = [p.nombre_completo for p in d.prescriptores] if d.prescriptores else []
        email_disp = d.usuario.email if d.usuario else None
        fecha_registro = d.usuario.fecha_registro if d.usuario else None

        result.append(AdminDispositivoOut(
            id=d.id,
            nombre=d.nombre,
            tipo_servicio=d.tipo_servicio,
            num_beneficiarios=len(benef_ids),
            prescriptores=presc_names,
            activo=d.usuario.estado == Estados.ACTIVO if d.usuario else False,
            email=email_disp,
            fecha_registro=fecha_registro,
            num_actividades=num_actividades,
            asistencia_pct=None,
            lugar_actividades=d.lugar_actividades,
            ubicacion=d.ubicacion,
            dia_actividad=d.dia_actividad,
            hora_actividad=d.hora_actividad,
            telefono=d.telefono,
            redes_sociales=d.redes_sociales,
        ))

    return result


# ────────────────────────── ELIMINAR DISPOSITIVO ──────────────────────────
@router.delete("/dispositivos/{dispositivo_id}", status_code=204)
def admin_eliminar_dispositivo(
    dispositivo_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(admin_only),
):
    disp = db.query(Dispositivo).filter(Dispositivo.id == dispositivo_id).first()
    if not disp:
        raise HTTPException(status_code=404, detail="Dispositivo no encontrado")

    tiene_actividades = db.query(Actividad).filter(Actividad.dispositivo_id == dispositivo_id).count() > 0
    tiene_prescriptores = len(disp.prescriptores) > 0
    tiene_pc = db.query(PrimerContacto).filter(PrimerContacto.dispositivo_id == dispositivo_id).count() > 0

    if tiene_actividades or tiene_prescriptores or tiene_pc:
        raise HTTPException(status_code=409, detail="No se puede eliminar: el dispositivo tiene datos asociados")

    usuario = db.query(Usuario).filter(Usuario.id == disp.usuario_id).first()
    db.delete(disp)
    db.flush()
    if usuario:
        db.query(EstadoRegistro).filter(
            EstadoRegistro.entidad_tipo == "usuario",
            EstadoRegistro.entidad_id == usuario.id,
        ).delete(synchronize_session="fetch")
        db.flush()
        db.delete(usuario)
    db.commit()


# ────────────────────────── EXPORTAR DISPOSITIVOS ──────────────────────────
@router.get("/dispositivos/exportar")
def exportar_dispositivos(
    formato: str = Query(default="csv", pattern="^(csv|json)$"),
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(admin_only),
):
    dispositivos = db.query(Dispositivo).all()
    data = []

    for d in dispositivos:
        benef_ids = set()
        insc = (
            db.query(Inscripcion.beneficiario_id)
            .join(Actividad, Actividad.id == Inscripcion.actividad_id)
            .filter(Actividad.dispositivo_id == d.id)
            .distinct().all()
        )
        benef_ids.update(b[0] for b in insc)
        pc = (
            db.query(PrimerContacto.beneficiario_id)
            .filter(PrimerContacto.dispositivo_id == d.id)
            .distinct().all()
        )
        benef_ids.update(b[0] for b in pc)

        num_actividades = db.query(Actividad).filter(Actividad.dispositivo_id == d.id).count()
        activo = d.usuario.estado == Estados.ACTIVO if d.usuario else False
        fecha_registro = d.usuario.fecha_registro.strftime("%Y-%m-%d") if d.usuario and d.usuario.fecha_registro else None

        data.append({
            "nombre": d.nombre,
            "tipo_servicio": d.tipo_servicio or "",
            "ubicacion": d.ubicacion or "",
            "telefono": d.telefono or "",
            "num_beneficiarios": len(benef_ids),
            "num_actividades": num_actividades,
            "estado": "activo" if activo else "inactivo",
            "fecha_registro": fecha_registro or "",
        })

    if formato == "json":
        return StreamingResponse(
            io.BytesIO(json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8")),
            media_type="application/json",
            headers={"Content-Disposition": "attachment; filename=dispositivos.json"},
        )

    # CSV por defecto
    output = io.StringIO()
    campos = ["nombre", "tipo_servicio", "ubicacion", "telefono", "num_beneficiarios", "num_actividades", "estado", "fecha_registro"]
    writer = csv.DictWriter(output, fieldnames=campos)
    writer.writeheader()
    writer.writerows(data)

    return StreamingResponse(
        io.BytesIO(output.getvalue().encode("utf-8")),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=dispositivos.csv"},
    )


# ────────────────────────── LISTAR BENEFICIARIOS (para formularios) ──────────
@router.get("/beneficiarios", response_model=list[BeneficiarioResumen])
def admin_listar_beneficiarios(
    admin_actual: Usuario = Depends(admin_only),
    db: Session = Depends(get_db),
):
    benefs = db.query(Beneficiario).all()
    result = []
    for b in benefs:
        email = b.usuario.email if b.usuario else None
        status = b.estado
        result.append(BeneficiarioResumen(
            id=b.id,
            nombre_apodo=b.nombre_apodo,
            email=email,
            genero=b.genero,
            fecha_nacimiento=b.fecha_nacimiento,
            localidad=b.localidad,
            telefono=b.telefono,
            status=status,
        ))
    return result


# ────────────────────────── APROBAR USUARIO ──────────────────────────
@router.post("/usuarios/{usuario_id}/aprobar")
def aprobar_usuario(
    usuario_id: int,
    admin_actual: Usuario = Depends(admin_only),
    db: Session = Depends(get_db)
):
    usuario = db.query(Usuario).filter(Usuario.id == usuario_id).first()
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    service = EstadoService(db)
    service.cambiar_estado(entidad_obj=usuario, nuevo_estado=Estados.ACTIVO, admin_id=admin_actual.id, motivo="Documentación verificada correctamente")

    if usuario.dispositivo:
        service.cambiar_estado(entidad_obj=usuario.dispositivo, nuevo_estado=Estados.ACTIVO, admin_id=admin_actual.id, motivo="Documentación verificada correctamente")
    elif usuario.prescriptor:
        service.cambiar_estado(entidad_obj=usuario.prescriptor, nuevo_estado=Estados.ACTIVO, admin_id=admin_actual.id, motivo="Documentación verificada correctamente")
    elif usuario.beneficiario:
        service.cambiar_estado(entidad_obj=usuario.beneficiario, nuevo_estado=Estados.ACTIVO, admin_id=admin_actual.id, motivo="Documentación verificada correctamente")

    return {"msg": "Usuario aprobado"}


# ────────────────────────── SOLICITUDES DE PRESCRIPTORES ──────────────────────────
@router.get("/solicitudes-prescriptor")
def listar_solicitudes_prescriptor(
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(admin_only),
):
    """Retorna todos los prescriptores con solicitud de unión pendiente a algún dispositivo."""
    prescs = (
        db.query(Prescriptor)
        .filter(Prescriptor.solicitud_dispositivo_id.isnot(None))
        .all()
    )
    result = []
    for p in prescs:
        disp_sol = db.query(Dispositivo).filter(Dispositivo.id == p.solicitud_dispositivo_id).first()
        disp_actual = db.query(Dispositivo).filter(Dispositivo.id == p.dispositivo_id).first() if p.dispositivo_id else None
        result.append({
            "prescriptor_id":           p.id,
            "nombre_completo":          p.nombre_completo,
            "email":                    p.usuario.email if p.usuario else "",
            "dispositivo_id_actual":    p.dispositivo_id,
            "dispositivo_nombre_actual": disp_actual.nombre if disp_actual else None,
            "solicitud_dispositivo_id": p.solicitud_dispositivo_id,
            "solicitud_nombre":         disp_sol.nombre if disp_sol else None,
        })
    return result


@router.post("/prescriptores/{prescriptor_id}/aprobar-solicitud")
def admin_aprobar_solicitud(
    prescriptor_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(admin_only),
):
    presc = db.query(Prescriptor).filter(Prescriptor.id == prescriptor_id).first()
    if not presc:
        raise HTTPException(status_code=404, detail="Prescriptor no encontrado")
    if not presc.solicitud_dispositivo_id:
        raise HTTPException(status_code=400, detail="No tiene solicitud pendiente")

    presc.dispositivo_id = presc.solicitud_dispositivo_id
    presc.solicitud_dispositivo_id = None

    service = EstadoService(db)
    if presc.usuario:
        service.cambiar_estado(entidad_obj=presc.usuario, nuevo_estado=Estados.ACTIVO, admin_id=current_user.id, motivo="Solicitud aprobada por admin")
    service.cambiar_estado(entidad_obj=presc, nuevo_estado=Estados.ACTIVO, admin_id=current_user.id, motivo="Solicitud aprobada por admin")

    return {"msg": "Solicitud aprobada"}


@router.post("/prescriptores/{prescriptor_id}/rechazar-solicitud")
def admin_rechazar_solicitud(
    prescriptor_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(admin_only),
):
    presc = db.query(Prescriptor).filter(Prescriptor.id == prescriptor_id).first()
    if not presc:
        raise HTTPException(status_code=404, detail="Prescriptor no encontrado")
    presc.solicitud_dispositivo_id = None
    db.commit()
    return {"msg": "Solicitud rechazada"}


# ────────────────────────── ASIGNAR / DESASOCIAR DISPOSITIVO ──────────────────────────
class AsignarDispositivoRequest(_BM):
    dispositivo_id: int | None = None


@router.put("/prescriptores/{prescriptor_id}/dispositivo")
def admin_asignar_dispositivo(
    prescriptor_id: int,
    data: AsignarDispositivoRequest,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(admin_only),
):
    """Asigna o quita el dispositivo de un prescriptor directamente (sin solicitud)."""
    presc = db.query(Prescriptor).filter(Prescriptor.id == prescriptor_id).first()
    if not presc:
        raise HTTPException(status_code=404, detail="Prescriptor no encontrado")

    if data.dispositivo_id is not None:
        disp = db.query(Dispositivo).filter(Dispositivo.id == data.dispositivo_id).first()
        if not disp:
            raise HTTPException(status_code=404, detail="Dispositivo no encontrado")

    # Si cambia de dispositivo, desasignar todos sus beneficiarios
    if presc.dispositivo_id != data.dispositivo_id:
        db.query(Beneficiario).filter(Beneficiario.prescriptor_id == presc.id).update(
            {Beneficiario.prescriptor_id: None}
        )

    presc.dispositivo_id = data.dispositivo_id
    presc.solicitud_dispositivo_id = None
    db.commit()

    if data.dispositivo_id is not None:
        service = EstadoService(db)
        if presc.usuario and presc.usuario.estado != Estados.ACTIVO:
            service.cambiar_estado(entidad_obj=presc.usuario, nuevo_estado=Estados.ACTIVO, admin_id=current_user.id, motivo="Asignado a dispositivo por admin")
        if presc.estado != Estados.ACTIVO:
            service.cambiar_estado(entidad_obj=presc, nuevo_estado=Estados.ACTIVO, admin_id=current_user.id, motivo="Asignado a dispositivo por admin")

    return {"msg": "Dispositivo actualizado", "dispositivo_nombre": disp.nombre if data.dispositivo_id else None}


@router.put("/beneficiarios/{beneficiario_id}/dispositivo")
def admin_asignar_dispositivo_beneficiario(
    beneficiario_id: int,
    data: AsignarDispositivoRequest,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(admin_only),
):
    benef = db.query(Beneficiario).filter(Beneficiario.id == beneficiario_id).first()
    if not benef:
        raise HTTPException(status_code=404, detail="Beneficiario no encontrado")

    if data.dispositivo_id is not None:
        disp = db.query(Dispositivo).filter(Dispositivo.id == data.dispositivo_id).first()
        if not disp:
            raise HTTPException(status_code=404, detail="Dispositivo no encontrado")

    benef.dispositivo_id = data.dispositivo_id
    if data.dispositivo_id is None:
        benef.prescriptor_id = None
    db.commit()

    return {"msg": "Dispositivo actualizado", "dispositivo_nombre": disp.nombre if data.dispositivo_id else None}