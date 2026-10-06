"""
Router de beneficiarios: perfil propio, edición y actividades.
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from datetime import date as date_type
from database import get_db
from app.models.models import Usuario, Beneficiario, Inscripcion, Actividad, Dispositivo, Prescriptor, Seguimiento
from app.schemas.schemas import (
    BeneficiarioMe, BeneficiarioUpdate,
    ActividadOut, InscripcionRequest, InscripcionResponse, SeguimientoOut,
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

    prescriptor_nombre = None
    if benef.prescriptor_id:
        presc = db.query(Prescriptor).filter(Prescriptor.id == benef.prescriptor_id).first()
        prescriptor_nombre = presc.nombre_completo if presc else None

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
        prescriptor_id=benef.prescriptor_id,
        prescriptor_nombre=prescriptor_nombre,
        estado_civil=benef.estado_civil,
        num_hijos=benef.num_hijos,
        etnia=benef.etnia,
        con_quien_vive=benef.con_quien_vive,
        direccion=benef.direccion,
        escolaridad=benef.escolaridad,
        ocupacion=benef.ocupacion,
        sabe_leer_escribir=benef.sabe_leer_escribir,
        sabe_usar_computador=benef.sabe_usar_computador,
        nombre_persona_apoyo=benef.nombre_persona_apoyo,
        telefono_persona_apoyo=benef.telefono_persona_apoyo,
        vinculo_persona_apoyo=benef.vinculo_persona_apoyo,
        apoyo_familiar=benef.apoyo_familiar,
        apoyo_comunitario=benef.apoyo_comunitario,
        apoyo_institucional=benef.apoyo_institucional,
        apoyo_actor_social=benef.apoyo_actor_social,
        practica_deporte=benef.practica_deporte,
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
    hoy = date_type.today()
    result = []
    for a in actividades:
        out = ActividadOut.model_validate(a)
        out.total_inscritos = len(a.inscripciones)
        out.dispositivo_nombre = a.dispositivo.nombre if a.dispositivo else None
        if a.fecha_inicio and a.fecha_inicio < hoy:
            out.activa = False
        result.append(out)
    return result


# ────────────────────────── MIS SEGUIMIENTOS ──────────────────────────
@router.get("/mis-seguimientos", response_model=list[SeguimientoOut])
def mis_seguimientos(
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    if current_user.rol != "beneficiario":
        raise HTTPException(status_code=403, detail="Requiere rol beneficiario")
    benef = _get_beneficiario(db, current_user)
    segs = (
        db.query(Seguimiento)
        .filter(Seguimiento.beneficiario_id == benef.id)
        .order_by(Seguimiento.fecha.desc())
        .all()
    )
    result = []
    for s in segs:
        result.append(SeguimientoOut(
            id=s.id,
            prescriptor_id=s.prescriptor_id,
            beneficiario_id=s.beneficiario_id,
            tipo_registro=s.tipo_registro,
            observaciones=s.observaciones,
            fecha=s.fecha,
            nombre_beneficiario=benef.nombre_apodo,
        ))
    return result


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


class AsignarPrescriptorRequest(BaseModel):
    prescriptor_id: int | None = None


# ────────────────────────── PUT /asignar-prescriptor ──────────────────────────
@router.put("/{beneficiario_id}/asignar-prescriptor")
def asignar_prescriptor(
    beneficiario_id: int,
    data: AsignarPrescriptorRequest,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    if current_user.rol not in ("admin", "dispositivo"):
        raise HTTPException(status_code=403, detail="Solo admin o dispositivo pueden asignar prescriptores")

    benef = db.query(Beneficiario).filter(Beneficiario.id == beneficiario_id).first()
    if not benef:
        raise HTTPException(status_code=404, detail="Beneficiario no encontrado")

    prescriptor_id = data.prescriptor_id
    if prescriptor_id:
        presc = db.query(Prescriptor).filter(Prescriptor.id == prescriptor_id).first()
        if not presc:
            raise HTTPException(status_code=404, detail="Prescriptor no encontrado")
        # Verificar que el prescriptor pertenece al mismo dispositivo que el beneficiario
        if current_user.rol == "dispositivo":
            disp = db.query(Dispositivo).filter(Dispositivo.usuario_id == current_user.id).first()
            if disp and presc.dispositivo_id != disp.id:
                raise HTTPException(status_code=403, detail="El prescriptor no pertenece a tu dispositivo")

    benef.prescriptor_id = prescriptor_id
    db.commit()
    return {"mensaje": "Prescriptor asignado correctamente", "beneficiario_id": beneficiario_id, "prescriptor_id": prescriptor_id}


# ────────────────────────── POST /solicitar-dispositivo ──────────────────────────
@router.post("/solicitar-dispositivo/{dispositivo_id}")
def solicitar_dispositivo(
    dispositivo_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    if current_user.rol != "beneficiario":
        raise HTTPException(status_code=403, detail="Solo beneficiarios pueden solicitar unirse")

    benef = _get_beneficiario(db, current_user)

    disp = db.query(Dispositivo).filter(Dispositivo.id == dispositivo_id).first()
    if not disp:
        raise HTTPException(status_code=404, detail="Dispositivo no encontrado")

    if benef.dispositivo_id == dispositivo_id:
        raise HTTPException(status_code=400, detail="Ya perteneces a este dispositivo")

    benef.dispositivo_id = dispositivo_id
    db.commit()
    return {"msg": f"Te has unido a {disp.nombre} correctamente."}


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

    actividad = db.query(Actividad).filter(Actividad.id == actividad_id).first()
    if actividad and actividad.fecha_inicio and actividad.fecha_inicio < date_type.today():
        raise HTTPException(status_code=400, detail="No puedes desinscribirte de una actividad que ya culminó")

    db.delete(inscripcion)
    db.commit()
    return {"mensaje": "Desinscripción exitosa"}