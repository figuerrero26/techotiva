"""
Router de administración: estadísticas globales, gestión de usuarios y alertas.
"""

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from app.core.security import hash_password
from app.models.models import (
    Usuario, Dispositivo, Prescriptor, Beneficiario,
    Actividad, Seguimiento, PrimerContacto, Inscripcion,
)
from app.schemas.schemas import (
    AdminStats, UsuarioAdmin, CambiarEstado, AlertaOut,
    AdminDispositivoOut, AdminDispositivoCreate,
)
from app.routers._deps import get_current_user, require_role

router = APIRouter(prefix="/admin", tags=["Administración"])

admin_only = require_role("admin")


# ────────────────────────── STATS GLOBALES ──────────────────────────
@router.get("/stats", response_model=AdminStats)
def admin_stats(
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(admin_only),
):
    total_disp = db.query(Dispositivo).count()
    total_users = db.query(Usuario).count()
    total_presc = db.query(Prescriptor).count()
    total_benef = db.query(Beneficiario).count()

    # Alertas: dispositivos sin actividad en los últimos 14 días
    umbral = datetime.now(timezone.utc) - timedelta(days=14)
    dispositivos = db.query(Dispositivo).all()
    alertas = 0
    for d in dispositivos:
        ultima_act = (
            db.query(Actividad)
            .filter(Actividad.dispositivo_id == d.id)
            .first()
        )
        if not ultima_act:
            alertas += 1
            continue
        # Verificar si tiene seguimientos recientes (como proxy de actividad)
        presc_ids = [p.id for p in d.prescriptores]
        if presc_ids:
            ultimo_seg = (
                db.query(Seguimiento)
                .filter(
                    Seguimiento.prescriptor_id.in_(presc_ids),
                    Seguimiento.fecha >= umbral,
                )
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
    users = db.query(Usuario).order_by(Usuario.fecha_registro.desc()).all()
    result = []
    for u in users:
        nombre = u.email
        if u.rol == "dispositivo" and u.dispositivo:
            nombre = u.dispositivo.nombre
        elif u.rol == "prescriptor" and u.prescriptor:
            nombre = u.prescriptor.nombre_completo
        elif u.rol == "beneficiario" and u.beneficiario:
            nombre = u.beneficiario.nombre_apodo
        elif u.rol == "admin":
            nombre = "Admin"

        result.append(UsuarioAdmin(
            id=u.id,
            email=u.email,
            rol=u.rol,
            activo=u.activo,
            fecha_registro=u.fecha_registro,
            nombre=nombre,
        ))
    return result


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

    user.activo = data.activo
    db.commit()
    db.refresh(user)

    nombre = user.email
    if user.rol == "dispositivo" and user.dispositivo:
        nombre = user.dispositivo.nombre
    elif user.rol == "prescriptor" and user.prescriptor:
        nombre = user.prescriptor.nombre_completo
    elif user.rol == "beneficiario" and user.beneficiario:
        nombre = user.beneficiario.nombre_apodo

    return UsuarioAdmin(
        id=user.id,
        email=user.email,
        rol=user.rol,
        activo=user.activo,
        fecha_registro=user.fecha_registro,
        nombre=nombre,
    )


# ────────────────────────── ALERTAS ──────────────────────────
@router.get("/alertas", response_model=list[AlertaOut])
def alertas_sistema(
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(admin_only),
):
    umbral = datetime.now(timezone.utc) - timedelta(days=14)
    dispositivos = db.query(Dispositivo).all()
    alertas = []

    for d in dispositivos:
        # Verificar si tiene seguimientos/actividad reciente
        tiene_actividad_reciente = False
        presc_ids = [p.id for p in d.prescriptores]
        if presc_ids:
            ultimo_seg = (
                db.query(Seguimiento)
                .filter(
                    Seguimiento.prescriptor_id.in_(presc_ids),
                    Seguimiento.fecha >= umbral,
                )
                .first()
            )
            if ultimo_seg:
                tiene_actividad_reciente = True

        if not tiene_actividad_reciente:
            # Calcular días sin actividad
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

    user = Usuario(
        email=data.email,
        password_hash=hash_password(data.password),
        rol="dispositivo",
    )
    db.add(user)
    db.flush()

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
    db.commit()
    db.refresh(disp)

    return AdminDispositivoOut(
        id=disp.id,
        nombre=disp.nombre,
        tipo_servicio=disp.tipo_servicio,
        num_beneficiarios=0,
        prescriptor=None,
        activo=True,
    )


# ────────────────────────── TABLA DE DISPOSITIVOS ──────────────────────────
@router.get("/dispositivos", response_model=list[AdminDispositivoOut])
def admin_listar_dispositivos(
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(admin_only),
):
    dispositivos = db.query(Dispositivo).all()
    result = []
    for d in dispositivos:
        # Contar beneficiarios
        benef_ids = set()
        insc = (
            db.query(Inscripcion.beneficiario_id)
            .join(Actividad, Actividad.id == Inscripcion.actividad_id)
            .filter(Actividad.dispositivo_id == d.id)
            .distinct()
            .all()
        )
        benef_ids.update(b[0] for b in insc)
        pc = (
            db.query(PrimerContacto.beneficiario_id)
            .filter(PrimerContacto.dispositivo_id == d.id)
            .distinct()
            .all()
        )
        benef_ids.update(b[0] for b in pc)

        presc_ids = [p.id for p in d.prescriptores]
        if presc_ids:
            seg = (
                db.query(Seguimiento.beneficiario_id)
                .filter(Seguimiento.prescriptor_id.in_(presc_ids))
                .distinct()
                .all()
            )
            benef_ids.update(b[0] for b in seg)

        # Nombre del prescriptor principal
        presc_name = None
        if d.prescriptores:
            presc_name = d.prescriptores[0].nombre_completo

        result.append(AdminDispositivoOut(
            id=d.id,
            nombre=d.nombre,
            tipo_servicio=d.tipo_servicio,
            num_beneficiarios=len(benef_ids),
            prescriptor=presc_name,
            activo=d.usuario.activo if d.usuario else True,
        ))

    return result
