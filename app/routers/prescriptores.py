"""
Router de prescriptores: asignados y seguimientos.
"""

from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func

from database import get_db
from app.models.models import (
    Usuario, Prescriptor, Beneficiario, Seguimiento, Dispositivo,
)
from app.schemas.schemas import AsignadoOut, SeguimientoCreate, SeguimientoOut
from app.routers._deps import get_current_user

router = APIRouter(prefix="/prescriptores", tags=["Prescriptores"])


def _get_prescriptor(db: Session, user: Usuario) -> Prescriptor:
    """Obtiene el perfil de prescriptor del usuario autenticado."""
    presc = db.query(Prescriptor).filter(Prescriptor.usuario_id == user.id).first()
    if not presc:
        raise HTTPException(status_code=404, detail="Perfil de prescriptor no encontrado")
    return presc


def _calcular_estado(dias: Optional[int]) -> str:
    """Calcula el estado semáforo según días sin sesión."""
    if dias is None:
        return "urgente"
    if dias < 3:
        return "al_dia"
    if dias <= 7:
        return "revisar"
    return "urgente"


# ────────────────────────── MIS ASIGNADOS ──────────────────────────
@router.get("/mis-asignados", response_model=list[AsignadoOut])
def mis_asignados(
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    if current_user.rol not in ("prescriptor", "admin"):
        raise HTTPException(status_code=403, detail="Requiere rol prescriptor")

    presc = _get_prescriptor(db, current_user)

    # Beneficiarios con seguimiento de este prescriptor
    benef_ids = (
        db.query(Seguimiento.beneficiario_id)
        .filter(Seguimiento.prescriptor_id == presc.id)
        .distinct()
        .all()
    )
    benef_ids = [b[0] for b in benef_ids]

    if not benef_ids:
        # Si no tiene seguimientos, buscar beneficiarios del dispositivo
        if presc.dispositivo_id:
            from app.models.models import Actividad, Inscripcion, PrimerContacto
            # Por inscripciones
            insc = (
                db.query(Inscripcion.beneficiario_id)
                .join(Actividad, Actividad.id == Inscripcion.actividad_id)
                .filter(Actividad.dispositivo_id == presc.dispositivo_id)
                .distinct()
                .all()
            )
            benef_ids.extend([b[0] for b in insc])
            # Por primer contacto
            pc = (
                db.query(PrimerContacto.beneficiario_id)
                .filter(PrimerContacto.dispositivo_id == presc.dispositivo_id)
                .distinct()
                .all()
            )
            benef_ids.extend([b[0] for b in pc])
            benef_ids = list(set(benef_ids))

    if not benef_ids:
        return []

    now = datetime.now(timezone.utc)
    result = []
    for bid in benef_ids:
        benef = db.query(Beneficiario).filter(Beneficiario.id == bid).first()
        if not benef:
            continue

        # Última sesión de ESTE prescriptor con ESTE beneficiario
        ultima = (
            db.query(func.max(Seguimiento.fecha))
            .filter(
                Seguimiento.prescriptor_id == presc.id,
                Seguimiento.beneficiario_id == bid,
            )
            .scalar()
        )

        dias_sin = None
        if ultima:
            # Asegurar que ultima tenga tzinfo
            if ultima.tzinfo is None:
                from datetime import timezone as tz
                ultima = ultima.replace(tzinfo=tz.utc)
            dias_sin = (now - ultima).days

        result.append(AsignadoOut(
            id=benef.id,
            nombre_apodo=benef.nombre_apodo,
            ultima_sesion=ultima,
            dias_sin_sesion=dias_sin,
            estado=_calcular_estado(dias_sin),
        ))

    return result


# ────────────────────────── CREAR SEGUIMIENTO ──────────────────────────
@router.post("/seguimientos", response_model=SeguimientoOut, status_code=201)
def crear_seguimiento(
    data: SeguimientoCreate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    if current_user.rol not in ("prescriptor", "admin"):
        raise HTTPException(status_code=403, detail="Requiere rol prescriptor")

    presc = _get_prescriptor(db, current_user)

    # Verificar que el beneficiario existe
    benef = db.query(Beneficiario).filter(Beneficiario.id == data.beneficiario_id).first()
    if not benef:
        raise HTTPException(status_code=404, detail="Beneficiario no encontrado")

    seg = Seguimiento(
        prescriptor_id=presc.id,
        beneficiario_id=data.beneficiario_id,
        tipo_registro=data.tipo_registro,
        observaciones=data.observaciones,
    )
    db.add(seg)
    db.commit()
    db.refresh(seg)

    return SeguimientoOut(
        id=seg.id,
        prescriptor_id=seg.prescriptor_id,
        beneficiario_id=seg.beneficiario_id,
        tipo_registro=seg.tipo_registro,
        observaciones=seg.observaciones,
        fecha=seg.fecha,
        nombre_beneficiario=benef.nombre_apodo,
    )


# ────────────────────────── LISTAR SEGUIMIENTOS ──────────────────────────
@router.get("/seguimientos", response_model=list[SeguimientoOut])
def listar_seguimientos(
    beneficiario_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    if current_user.rol not in ("prescriptor", "admin"):
        raise HTTPException(status_code=403, detail="Requiere rol prescriptor")

    presc = _get_prescriptor(db, current_user)

    q = db.query(Seguimiento).filter(Seguimiento.prescriptor_id == presc.id)
    if beneficiario_id:
        q = q.filter(Seguimiento.beneficiario_id == beneficiario_id)

    segs = q.order_by(Seguimiento.fecha.desc()).all()
    result = []
    for s in segs:
        benef = db.query(Beneficiario).filter(Beneficiario.id == s.beneficiario_id).first()
        result.append(SeguimientoOut(
            id=s.id,
            prescriptor_id=s.prescriptor_id,
            beneficiario_id=s.beneficiario_id,
            tipo_registro=s.tipo_registro,
            observaciones=s.observaciones,
            fecha=s.fecha,
            nombre_beneficiario=benef.nombre_apodo if benef else None,
        ))
    return result
