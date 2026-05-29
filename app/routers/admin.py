"""
Router de administración: estadísticas globales, gestión de usuarios y alertas.
"""

import csv
import io
import json
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from database import get_db
from app.core.security import hash_password
from app.models.models import (
    Usuario, Estados, EstadoRegistro, Dispositivo, Prescriptor, Beneficiario,
    Actividad, Seguimiento, PrimerContacto, Inscripcion,
)
from app.schemas.schemas import (
    AdminStats, UsuarioAdmin, CambiarEstado, AlertaOut,
    AdminDispositivoOut, AdminDispositivoCreate, CambiarRolRequest,
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

    if u.rol == "dispositivo" and u.dispositivo:
        nombre = u.dispositivo.nombre
        telefono = u.dispositivo.telefono
        descripcion = u.dispositivo.descripcion
    elif u.rol == "prescriptor" and u.prescriptor:
        nombre = u.prescriptor.nombre_completo
        telefono = u.prescriptor.telefono
    elif u.rol == "beneficiario" and u.beneficiario:
        nombre = u.beneficiario.nombre_apodo
        fecha_nacimiento = u.beneficiario.fecha_nacimiento
        localidad = u.beneficiario.localidad
        telefono = u.beneficiario.telefono
        descripcion = u.beneficiario.descripcion
        genero = u.beneficiario.genero
    elif u.rol == "admin":
        nombre = "Admin"

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

    return AdminStats(
        total_dispositivos=total_disp,
        total_usuarios=total_users,
        total_prescriptores=total_presc,
        total_beneficiarios=total_benef,
        alertas_pendientes=alertas,
    )


# ────────────────────────── USUARIOS ──────────────────────────
@router.get("/usuarios", response_model=list[UsuarioAdmin])
def listar_usuarios(
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(admin_only),
):
    from sqlalchemy import case
    users = (
        db.query(Usuario)
        .outerjoin(EstadoRegistro, Usuario.estado_actual_id == EstadoRegistro.id)
        .filter(Usuario.rol != "admin")
        .filter(Usuario.rol != "prescriptor")
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
            from sqlalchemy import func
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
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(admin_only),
):
    if db.query(Usuario).filter(Usuario.email == data.email).first():
        raise HTTPException(status_code=409, detail="Ya existe una cuenta con ese correo")

    # Generar password temporal
    import secrets, string
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

    return AdminDispositivoOut(
        id=disp.id,
        nombre=disp.nombre,
        tipo_servicio=disp.tipo_servicio,
        num_beneficiarios=0,
        prescriptor=None,
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
        presc_name = d.prescriptores[0].nombre_completo if d.prescriptores else None
        email_disp = d.usuario.email if d.usuario else None
        fecha_registro = d.usuario.fecha_registro if d.usuario else None

        result.append(AdminDispositivoOut(
            id=d.id,
            nombre=d.nombre,
            tipo_servicio=d.tipo_servicio,
            num_beneficiarios=len(benef_ids),
            prescriptor=presc_name,
            activo=d.usuario.estado == Estados.ACTIVO if d.usuario else False,
            email=email_disp,
            fecha_registro=fecha_registro,
            num_actividades=num_actividades,
            asistencia_pct=None,
        ))

    return result


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