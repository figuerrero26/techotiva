"""
Router de dispositivos: CRUD y estadísticas.
"""

from datetime import datetime, timedelta, timezone
from sqlalchemy import or_
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from database import get_db
from app.models.models import (
    Usuario, Dispositivo, Beneficiario, Actividad,
    Seguimiento, Prescriptor, PrimerContacto, Inscripcion,
)
from app.models.models import Estados, EstadoRegistro
from app.schemas.schemas import (
    DispositivoOut, DispositivoUpdate, DispositivoEstadisticas,
    BeneficiarioResumen, ActividadOut,
)
from app.routers._deps import get_current_user, require_role
from app.services.estado_service import EstadoService

router = APIRouter(prefix="/dispositivos", tags=["Dispositivos"])


# ────────────────────────── LISTAR TODOS ──────────────────────────
@router.get("/", response_model=list[DispositivoOut])
def listar_dispositivos(db: Session = Depends(get_db)):
    """Lista todos los dispositivos (público)."""
    disps = db.query(Dispositivo).all()
    result = []
    for d in disps:
        r = DispositivoOut.model_validate(d)
        r.activo = d.usuario.activo if d.usuario else True
        result.append(r)
    return result


# ────────────────────────── MI PERFIL (DISPOSITIVO) ──────────────────────────
@router.get("/me", response_model=DispositivoOut)
def mi_perfil_dispositivo(
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    if current_user.rol != "dispositivo":
        raise HTTPException(status_code=403, detail="Requiere rol dispositivo")
    
    disp = db.query(Dispositivo).filter(Dispositivo.usuario_id == current_user.id).first()
    if not disp:
        raise HTTPException(status_code=404, detail="Perfil de dispositivo no encontrado")
    
    r = DispositivoOut.model_validate(disp)
    r.activo = disp.usuario.activo if disp.usuario else True
    return r

# ────────────────────────── DETALLE ──────────────────────────
@router.get("/{dispositivo_id}", response_model=DispositivoOut)
def detalle_dispositivo(dispositivo_id: int, db: Session = Depends(get_db)):
    disp = db.query(Dispositivo).filter(Dispositivo.id == dispositivo_id).first()
    if not disp:
        raise HTTPException(status_code=404, detail="Dispositivo no encontrado")
    r = DispositivoOut.model_validate(disp)
    r.activo = disp.usuario.activo if disp.usuario else True
    return r


# ────────────────────────── EDITAR PERFIL ──────────────────────────
@router.put("/{dispositivo_id}", response_model=DispositivoOut)
def editar_dispositivo(
    dispositivo_id: int,
    data: DispositivoUpdate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    disp = db.query(Dispositivo).filter(Dispositivo.id == dispositivo_id).first()
    if not disp:
        raise HTTPException(status_code=404, detail="Dispositivo no encontrado")

    # Solo el propio dispositivo o admin pueden editar
    if current_user.rol != "admin" and disp.usuario_id != current_user.id:
        raise HTTPException(status_code=403, detail="No tienes permiso para editar este dispositivo")

    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(disp, field, value)

    db.commit()
    db.refresh(disp)
    r = DispositivoOut.model_validate(disp)
    r.activo = disp.usuario.activo if disp.usuario else True
    return r


# ────────────────────────── BENEFICIARIOS DEL DISPOSITIVO ──────────────────────────
@router.get("/{dispositivo_id}/beneficiarios", response_model=list[BeneficiarioResumen])
def beneficiarios_dispositivo(
    dispositivo_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    disp = db.query(Dispositivo).filter(Dispositivo.id == dispositivo_id).first()
    if not disp:
        raise HTTPException(status_code=404, detail="Dispositivo no encontrado")

    benefs = (
        db.query(Beneficiario)
        .filter(Beneficiario.dispositivo_id == dispositivo_id)
        .all()
    )
    return [BeneficiarioResumen.model_validate(b) for b in benefs]
# ────────────────────────── ESTADÍSTICAS ──────────────────────────
@router.get("/{dispositivo_id}/estadisticas", response_model=DispositivoEstadisticas)
def estadisticas_dispositivo(
    dispositivo_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    disp = db.query(Dispositivo).filter(Dispositivo.id == dispositivo_id).first()
    if not disp:
        raise HTTPException(status_code=404, detail="Dispositivo no encontrado")

    # Beneficiarios activos (inscritos + primer contacto)
    benef_ids = set()
    insc = (
        db.query(Inscripcion.beneficiario_id)
        .join(Actividad, Actividad.id == Inscripcion.actividad_id)
        .filter(Actividad.dispositivo_id == dispositivo_id)
        .distinct()
        .all()
    )
    benef_ids.update(b[0] for b in insc)
    pc = (
        db.query(PrimerContacto.beneficiario_id)
        .filter(PrimerContacto.dispositivo_id == dispositivo_id)
        .distinct()
        .all()
    )
    benef_ids.update(b[0] for b in pc)

    # Prescriptores del dispositivo → sus beneficiarios
    presc_ids = [p.id for p in disp.prescriptores]
    if presc_ids:
        seg = (
            db.query(Seguimiento.beneficiario_id)
            .filter(Seguimiento.prescriptor_id.in_(presc_ids))
            .distinct()
            .all()
        )
        benef_ids.update(b[0] for b in seg)

    # Actividades registradas
    num_actividades = db.query(Actividad).filter(
        Actividad.dispositivo_id == dispositivo_id
    ).count()

    # Seguimientos de la última semana
    semana = datetime.now(timezone.utc) - timedelta(days=7)
    seg_semana = 0
    if presc_ids:
        seg_semana = db.query(Seguimiento).filter(
            Seguimiento.prescriptor_id.in_(presc_ids),
            Seguimiento.fecha >= semana,
        ).count()

    return DispositivoEstadisticas(
        beneficiarios_activos=len(benef_ids),
        actividades_registradas=num_actividades,
        seguimientos_semana=seg_semana,
    )


# ────────────────────────── APROBAR PRESCRIPTOR (POR DISPOSITIVO) 
# 
# ──────────────────────────

@router.get("/{dispositivo_id}/prescriptores/pendientes")
def listar_prescriptores_pendientes(
    dispositivo_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    disp = db.query(Dispositivo).filter(Dispositivo.id == dispositivo_id).first()
    if not disp:
        raise HTTPException(status_code=404, detail="Dispositivo no encontrado")

    # Solo admin o propietario del dispositivo pueden ver pendientes
    if current_user.rol != "admin" and disp.usuario_id != current_user.id:
        raise HTTPException(status_code=403, detail="No tienes permiso para ver prescriptores pendientes")

    prescs = (
    db.query(Prescriptor)
    .filter(
        Prescriptor.dispositivo_id == dispositivo_id,
            or_(
                Prescriptor.estado_actual_id == None,
                Prescriptor.estado_actual.has(EstadoRegistro.estado == Estados.PENDIENTE)
            )
        )
        .all()  # 
    )

    result = []
    for p in prescs:
        result.append({
            "id": p.id,
            "nombre_completo": p.nombre_completo,
            "telefono": p.telefono,
            "usuario_id": p.usuario_id,
            "estado": p.estado,
        })

    return result


@router.post("/{dispositivo_id}/prescriptores/{prescriptor_id}/aprobar")
def aprobar_prescriptor(
    dispositivo_id: int,
    prescriptor_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    disp = db.query(Dispositivo).filter(Dispositivo.id == dispositivo_id).first()
    if not disp:
        raise HTTPException(status_code=404, detail="Dispositivo no encontrado")

    # Solo el admin o el propietario del dispositivo pueden aprobar
    if current_user.rol != "admin" and disp.usuario_id != current_user.id:
        raise HTTPException(status_code=403, detail="No tienes permiso para aprobar prescriptores de este dispositivo")

    presc = db.query(Prescriptor).filter(Prescriptor.id == prescriptor_id).first()
    if not presc:
        raise HTTPException(status_code=404, detail="Prescriptor no encontrado")

    if presc.dispositivo_id != dispositivo_id:
        raise HTTPException(status_code=400, detail="El prescriptor no está asignado a este dispositivo")

    service = EstadoService(db)

    # Activar usuario y perfil del prescriptor
    if presc.usuario:
        service.cambiar_estado(entidad_obj=presc.usuario, nuevo_estado=Estados.ACTIVO, admin_id=current_user.id, motivo="Aprobado por dispositivo")

    service.cambiar_estado(entidad_obj=presc, nuevo_estado=Estados.ACTIVO, admin_id=current_user.id, motivo="Aprobado por dispositivo")

    return {"msg": "Prescriptor aprobado"}


