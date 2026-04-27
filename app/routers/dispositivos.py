"""
Router de dispositivos: CRUD y estadísticas.
"""

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from database import get_db
from app.models.models import (
    Usuario, Dispositivo, Beneficiario, Actividad,
    Seguimiento, Prescriptor, PrimerContacto, Inscripcion,
)
from app.schemas.schemas import (
    DispositivoOut, DispositivoUpdate, DispositivoEstadisticas,
    BeneficiarioResumen, ActividadOut,
)
from app.routers._deps import get_current_user, require_role

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

    # Beneficiarios inscritos en actividades de este dispositivo
    benef_ids = (
        db.query(Inscripcion.beneficiario_id)
        .join(Actividad, Actividad.id == Inscripcion.actividad_id)
        .filter(Actividad.dispositivo_id == dispositivo_id)
        .distinct()
        .all()
    )
    ids = [b[0] for b in benef_ids]

    # También beneficiarios con primer contacto en este dispositivo
    pc_ids = (
        db.query(PrimerContacto.beneficiario_id)
        .filter(PrimerContacto.dispositivo_id == dispositivo_id)
        .distinct()
        .all()
    )
    ids.extend([b[0] for b in pc_ids])

    # También beneficiarios con seguimiento de prescriptores de este dispositivo
    presc_ids = [p.id for p in disp.prescriptores]
    if presc_ids:
        seg_ids = (
            db.query(Seguimiento.beneficiario_id)
            .filter(Seguimiento.prescriptor_id.in_(presc_ids))
            .distinct()
            .all()
        )
        ids.extend([b[0] for b in seg_ids])

    unique_ids = list(set(ids))
    if not unique_ids:
        return []

    benefs = db.query(Beneficiario).filter(Beneficiario.id.in_(unique_ids)).all()
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
