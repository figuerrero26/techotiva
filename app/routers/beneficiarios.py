"""
Router de beneficiarios: perfil propio y actividades inscritas.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from app.models.models import Usuario, Beneficiario, Inscripcion, Actividad
from app.schemas.schemas import BeneficiarioMe, ActividadOut
from app.routers._deps import get_current_user

router = APIRouter(prefix="/beneficiarios", tags=["Beneficiarios"])


# ────────────────────────── MI PERFIL ──────────────────────────
@router.get("/me", response_model=BeneficiarioMe)
def mi_perfil(
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    if current_user.rol != "beneficiario":
        raise HTTPException(status_code=403, detail="Requiere rol beneficiario")

    benef = db.query(Beneficiario).filter(Beneficiario.usuario_id == current_user.id).first()
    if not benef:
        raise HTTPException(status_code=404, detail="Perfil no encontrado")

    return BeneficiarioMe(
        id=benef.id,
        nombre_apodo=benef.nombre_apodo,
        email=current_user.email,
        fecha_registro=current_user.fecha_registro,
    )


# ────────────────────────── MIS ACTIVIDADES ──────────────────────────
@router.get("/mis-actividades", response_model=list[ActividadOut])
def mis_actividades(
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    if current_user.rol != "beneficiario":
        raise HTTPException(status_code=403, detail="Requiere rol beneficiario")

    benef = db.query(Beneficiario).filter(Beneficiario.usuario_id == current_user.id).first()
    if not benef:
        raise HTTPException(status_code=404, detail="Perfil no encontrado")

    inscripciones = (
        db.query(Actividad)
        .join(Inscripcion, Inscripcion.actividad_id == Actividad.id)
        .filter(Inscripcion.beneficiario_id == benef.id)
        .all()
    )
    return [ActividadOut.model_validate(a) for a in inscripciones]
