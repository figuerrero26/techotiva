"""
Router de beneficiarios: perfil propio, edición y actividades.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
from app.models.models import Usuario, Beneficiario, Inscripcion, Actividad, Dispositivo
from app.schemas.schemas import (
    BeneficiarioMe, BeneficiarioUpdate,
    ActividadOut, InscripcionRequest, InscripcionResponse,
)
from app.routers._deps import get_current_user

router = APIRouter(prefix="/beneficiarios", tags=["Beneficiarios"])


def _get_beneficiario(db: Session, user: Usuario) -> Beneficiario:
    benef = db.query(Beneficiario).filter(Beneficiario.usuario_id == user.id).first()
    if not benef:
        raise HTTPException(status_code=404, detail="Perfil de beneficiario no encontrado")
    return benef


def _build_beneficiario_me(benef: Beneficiario, user: Usuario, db: Session) -> BeneficiarioMe:
    dispositivo_nombre = None
    if benef.dispositivo_id:
        disp = db.query(Dispositivo).filter(Dispositivo.id == benef.dispositivo_id).first()
        dispositivo_nombre = disp.nombre if disp else None

    return BeneficiarioMe(
        id=benef.id,
        nombre_apodo=benef.nombre_apodo,
        email=user.email,
        fecha_registro=user.fecha_registro,
        fecha_nacimiento=benef.fecha_nacimiento,
        localidad=benef.localidad,
        telefono=benef.telefono,
        descripcion=benef.descripcion,
        genero=benef.genero,
        dispositivo_id=benef.dispositivo_id,
        dispositivo_nombre=dispositivo_nombre,
    )


# ────────────────────────── GET /me ──────────────────────────
@router.get("/me", response_model=BeneficiarioMe)
def mi_perfil(
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    if current_user.rol != "beneficiario":
        raise HTTPException(status_code=403, detail="Requiere rol beneficiario")
    benef = _get_beneficiario(db, current_user)
    return _build_beneficiario_me(benef, current_user, db)


# ────────────────────────── PUT /me ──────────────────────────
@router.put("/me", response_model=BeneficiarioMe)
def editar_perfil(
    data: BeneficiarioUpdate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    if current_user.rol != "beneficiario":
        raise HTTPException(status_code=403, detail="Requiere rol beneficiario")
    benef = _get_beneficiario(db, current_user)

    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(benef, field, value)

    db.commit()
    db.refresh(benef)
    return _build_beneficiario_me(benef, current_user, db)


# ────────────────────────── MIS ACTIVIDADES ──────────────────────────
@router.get("/mis-actividades", response_model=list[ActividadOut])
def mis_actividades(
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    if current_user.rol != "beneficiario":
        raise HTTPException(status_code=403, detail="Requiere rol beneficiario")
    benef = _get_beneficiario(db, current_user)

    actividades = (
        db.query(Actividad)
        .join(Inscripcion, Inscripcion.actividad_id == Actividad.id)
        .filter(Inscripcion.beneficiario_id == benef.id)
        .all()
    )
    return [ActividadOut.model_validate(a) for a in actividades]


# ────────────────────────── POST /inscribirse ──────────────────────────
@router.post("/inscribirse", response_model=InscripcionResponse, status_code=201)
def inscribirse(
    data: InscripcionRequest,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    if current_user.rol != "beneficiario":
        raise HTTPException(status_code=403, detail="Requiere rol beneficiario")
    benef = _get_beneficiario(db, current_user)

    actividad = db.query(Actividad).filter(Actividad.id == data.actividad_id).first()
    if not actividad:
        raise HTTPException(status_code=404, detail="Actividad no encontrada")

    ya_inscrito = db.query(Inscripcion).filter(
        Inscripcion.beneficiario_id == benef.id,
        Inscripcion.actividad_id == data.actividad_id,
    ).first()
    if ya_inscrito:
        raise HTTPException(status_code=400, detail="Ya estás inscrito en esta actividad")

    if actividad.cupo_maximo is not None:
        inscritos = db.query(Inscripcion).filter(
            Inscripcion.actividad_id == data.actividad_id
        ).count()
        if inscritos >= actividad.cupo_maximo:
            raise HTTPException(status_code=403, detail="La actividad no tiene cupo disponible")

    nueva = Inscripcion(beneficiario_id=benef.id, actividad_id=data.actividad_id)
    db.add(nueva)
    db.commit()

    return InscripcionResponse(mensaje="Inscripción exitosa", actividad_id=data.actividad_id)


# ────────────────────────── DELETE /desinscribirse/{actividad_id} ──────────────────────────
@router.delete("/desinscribirse/{actividad_id}")
def desinscribirse(
    actividad_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    if current_user.rol != "beneficiario":
        raise HTTPException(status_code=403, detail="Requiere rol beneficiario")
    benef = _get_beneficiario(db, current_user)

    inscripcion = db.query(Inscripcion).filter(
        Inscripcion.beneficiario_id == benef.id,
        Inscripcion.actividad_id == actividad_id,
    ).first()
    if not inscripcion:
        raise HTTPException(status_code=404, detail="No estás inscrito en esta actividad")

    db.delete(inscripcion)
    db.commit()
    return {"mensaje": "Desinscripción exitosa"}