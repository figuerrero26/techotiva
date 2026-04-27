"""
Router de actividades: CRUD con filtros.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional

from database import get_db
from app.models.models import Usuario, Dispositivo, Actividad
from app.schemas.schemas import ActividadCreate, ActividadUpdate, ActividadOut
from app.routers._deps import get_current_user

router = APIRouter(prefix="/actividades", tags=["Actividades"])


# ────────────────────────── LISTAR ──────────────────────────
@router.get("/", response_model=list[ActividadOut])
def listar_actividades(
    tipo: Optional[str] = Query(None),
    dispositivo_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
):
    """Lista actividades con filtros opcionales (público)."""
    q = db.query(Actividad)
    if tipo:
        q = q.filter(Actividad.tipo == tipo)
    if dispositivo_id:
        q = q.filter(Actividad.dispositivo_id == dispositivo_id)
    return [ActividadOut.model_validate(a) for a in q.all()]


# ────────────────────────── CREAR ──────────────────────────
@router.post("/", response_model=ActividadOut, status_code=201)
def crear_actividad(
    data: ActividadCreate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    # Solo dispositivo o admin pueden crear
    if current_user.rol not in ("dispositivo", "admin"):
        raise HTTPException(status_code=403, detail="Solo dispositivos pueden crear actividades")

    # Determinar el dispositivo_id
    if current_user.rol == "dispositivo":
        disp = db.query(Dispositivo).filter(Dispositivo.usuario_id == current_user.id).first()
        if not disp:
            raise HTTPException(status_code=404, detail="Perfil de dispositivo no encontrado")
        disp_id = disp.id
    else:
        # Admin debe enviar dispositivo_id
        if not data.dispositivo_id:
            raise HTTPException(status_code=400, detail="Admin debe indicar dispositivo_id")
        disp_id = data.dispositivo_id

    act = Actividad(
        dispositivo_id=disp_id,
        nombre=data.nombre,
        tipo=data.tipo,
        lugar=data.lugar,
        dia_semana=data.dia_semana,
        hora=data.hora,
        emoji=data.emoji or "📋",
    )
    db.add(act)
    db.commit()
    db.refresh(act)
    return ActividadOut.model_validate(act)


# ────────────────────────── EDITAR ──────────────────────────
@router.put("/{actividad_id}", response_model=ActividadOut)
def editar_actividad(
    actividad_id: int,
    data: ActividadUpdate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    act = db.query(Actividad).filter(Actividad.id == actividad_id).first()
    if not act:
        raise HTTPException(status_code=404, detail="Actividad no encontrada")

    # Verificar ownership
    if current_user.rol == "dispositivo":
        disp = db.query(Dispositivo).filter(Dispositivo.usuario_id == current_user.id).first()
        if not disp or act.dispositivo_id != disp.id:
            raise HTTPException(status_code=403, detail="No puedes editar esta actividad")
    elif current_user.rol != "admin":
        raise HTTPException(status_code=403, detail="Sin permisos para editar actividades")

    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(act, field, value)

    db.commit()
    db.refresh(act)
    return ActividadOut.model_validate(act)


# ────────────────────────── ELIMINAR ──────────────────────────
@router.delete("/{actividad_id}")
def eliminar_actividad(
    actividad_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    act = db.query(Actividad).filter(Actividad.id == actividad_id).first()
    if not act:
        raise HTTPException(status_code=404, detail="Actividad no encontrada")

    if current_user.rol == "dispositivo":
        disp = db.query(Dispositivo).filter(Dispositivo.usuario_id == current_user.id).first()
        if not disp or act.dispositivo_id != disp.id:
            raise HTTPException(status_code=403, detail="No puedes eliminar esta actividad")
    elif current_user.rol != "admin":
        raise HTTPException(status_code=403, detail="Sin permisos")

    db.delete(act)
    db.commit()
    return {"message": "Actividad eliminada"}
