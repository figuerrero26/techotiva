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
    Actividad, Inscripcion, PrimerContacto, Estados, EstadoRegistro,
)
from app.schemas.schemas import (
    AsignadoOut, SeguimientoCreate, SeguimientoOut,
    PrescriptorMe, PrescriptorUpdate,
)
from app.routers._deps import get_current_user


def _nombre_autor_seguimiento(db: Session, prescriptor_id: int) -> str | None:
    """Devuelve el nombre de quien hizo el seguimiento según su rol real."""
    presc = db.query(Prescriptor).filter(Prescriptor.id == prescriptor_id).first()
    if not presc:
        return None
    usuario = db.query(Usuario).filter(Usuario.id == presc.usuario_id).first()
    if not usuario:
        return presc.nombre_completo
    if usuario.rol == "admin":
        return "Administrador"
    if usuario.rol == "dispositivo":
        disp = db.query(Dispositivo).filter(Dispositivo.usuario_id == usuario.id).first()
        return disp.nombre if disp else usuario.email
    return presc.nombre_completo

router = APIRouter(prefix="/prescriptores", tags=["Prescriptores"])


def _get_prescriptor(db: Session, user: Usuario) -> Prescriptor:
    """Obtiene el perfil de prescriptor. Si no existe, lo crea automáticamente."""
    presc = db.query(Prescriptor).filter(Prescriptor.usuario_id == user.id).first()
    if not presc:
        presc = Prescriptor(usuario_id=user.id, nombre_completo=user.email)
        db.add(presc)
        db.flush()
        est = EstadoRegistro(
            entidad_tipo="prescriptores", entidad_id=presc.id,
            estado=Estados.ACTIVO, cambiado_por=None, motivo="Perfil autocreado",
        )
        db.add(est)
        db.flush()
        presc.estado_actual_id = est.id
        db.commit()
        db.refresh(presc)
    return presc


def _benef_accesible(db: Session, presc: Prescriptor, benef: Beneficiario) -> bool:
    """Mismo criterio que "mis asignados": de mi dispositivo, asignado a mí o ya atendido por mí."""
    if presc.dispositivo_id and benef.dispositivo_id == presc.dispositivo_id:
        return True
    if benef.prescriptor_id == presc.id:
        return True
    return db.query(Seguimiento.id).filter(
        Seguimiento.prescriptor_id == presc.id, Seguimiento.beneficiario_id == benef.id
    ).first() is not None


# Semáforo de seguimiento (días desde el último seguimiento)
DIAS_REVISAR = 7    # desde 7 días → amarillo
DIAS_URGENTE = 14   # desde 14 días → rojo


def calcular_estado(dias: Optional[int]) -> str:
    """Al día < 7 días · Por revisar 7–13 días · Urgente 14+ días o sin ningún seguimiento."""
    if dias is None:
        return "urgente"
    if dias < DIAS_REVISAR:
        return "al_dia"
    if dias < DIAS_URGENTE:
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

    benef_ids = set()

    # 1. Asignación directa (FK prescriptor_id en beneficiarios)
    directos = (
        db.query(Beneficiario.id)
        .filter(Beneficiario.prescriptor_id == presc.id)
        .all()
    )
    benef_ids.update(b[0] for b in directos)

    # 2. Beneficiarios con seguimiento previo de este prescriptor
    seg_ids = (
        db.query(Seguimiento.beneficiario_id)
        .filter(Seguimiento.prescriptor_id == presc.id)
        .distinct()
        .all()
    )
    benef_ids.update(b[0] for b in seg_ids)

    # 3. Siempre incluir todos los beneficiarios del dispositivo
    if presc.dispositivo_id:
        directo = (
            db.query(Beneficiario.id)
            .filter(Beneficiario.dispositivo_id == presc.dispositivo_id)
            .all()
        )
        benef_ids.update(b[0] for b in directo)
        insc = (
            db.query(Inscripcion.beneficiario_id)
            .join(Actividad, Actividad.id == Inscripcion.actividad_id)
            .filter(Actividad.dispositivo_id == presc.dispositivo_id)
            .distinct()
            .all()
        )
        benef_ids.update(b[0] for b in insc)
        pc = (
            db.query(PrimerContacto.beneficiario_id)
            .filter(PrimerContacto.dispositivo_id == presc.dispositivo_id)
            .distinct()
            .all()
        )
        benef_ids.update(b[0] for b in pc)

    benef_ids = list(benef_ids)

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

        usuario = db.query(Usuario).filter(Usuario.id == benef.usuario_id).first()
        if benef.estado == Estados.FINALIZADO:
            estado = "finalizado"
        elif benef.prescriptor_id is None:
            estado = "desvinculado"
        else:
            estado = calcular_estado(dias_sin)
        result.append(AsignadoOut(
            id=benef.id,
            nombre_apodo=benef.nombre_apodo,
            ultima_sesion=ultima,
            dias_sin_sesion=dias_sin,
            estado=estado,
            email=usuario.email if usuario else None,
            telefono=benef.telefono,
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

    if current_user.rol != "admin" and not _benef_accesible(db, presc, benef):
        raise HTTPException(status_code=403, detail="No tienes acceso a este beneficiario")

    if benef.estado == Estados.FINALIZADO and current_user.rol != "admin":
        raise HTTPException(status_code=403, detail="El proceso de este beneficiario está finalizado. Un administrador debe reactivarlo primero.")

    seg = Seguimiento(
        prescriptor_id=presc.id,
        beneficiario_id=data.beneficiario_id,
        tipo_registro=data.tipo_registro,
        observaciones=data.observaciones,
    )
    db.add(seg)

    if data.tipo_registro == "Cierre de proceso":
        estado_fin = EstadoRegistro(
            entidad_tipo=benef.__tablename__,
            entidad_id=benef.id,
            estado=Estados.FINALIZADO,
            cambiado_por=current_user.id,
            motivo="Cierre de proceso registrado",
        )
        db.add(estado_fin)
        db.flush()
        benef.estado_actual_id = estado_fin.id

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
        nombre_prescriptor=_nombre_autor_seguimiento(db, seg.prescriptor_id),
    )


# ────────────────────────── LISTAR SEGUIMIENTOS ──────────────────────────
@router.get("/seguimientos", response_model=list[SeguimientoOut])
def listar_seguimientos(
    beneficiario_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    if current_user.rol not in ("prescriptor", "admin", "dispositivo"):
        raise HTTPException(status_code=403, detail="Requiere rol prescriptor")

    if current_user.rol == "admin":
        q = db.query(Seguimiento)
        if beneficiario_id:
            q = q.filter(Seguimiento.beneficiario_id == beneficiario_id)
    elif current_user.rol == "dispositivo":
        # Solo seguimientos de beneficiarios de su dispositivo
        disp = db.query(Dispositivo).filter(Dispositivo.usuario_id == current_user.id).first()
        q = (db.query(Seguimiento)
             .join(Beneficiario, Beneficiario.id == Seguimiento.beneficiario_id)
             .filter(Beneficiario.dispositivo_id == (disp.id if disp else -1)))
        if beneficiario_id:
            q = q.filter(Seguimiento.beneficiario_id == beneficiario_id)
    else:
        presc = _get_prescriptor(db, current_user)
        if beneficiario_id:
            # Ver ficha de un beneficiario: todos sus seguimientos, si es accesible para mí
            benef = db.query(Beneficiario).filter(Beneficiario.id == beneficiario_id).first()
            if not benef or not _benef_accesible(db, presc, benef):
                raise HTTPException(status_code=403, detail="No tienes acceso a este beneficiario")
            q = db.query(Seguimiento).filter(Seguimiento.beneficiario_id == beneficiario_id)
        else:
            # Sin filtro de beneficiario: solo los propios del prescriptor
            q = db.query(Seguimiento).filter(Seguimiento.prescriptor_id == presc.id)

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
            nombre_prescriptor=_nombre_autor_seguimiento(db, s.prescriptor_id),
        ))
    return result


# ────────────────────────── ELIMINAR SEGUIMIENTO ──────────────────────────
@router.delete("/seguimientos/{seguimiento_id}", status_code=204)
def eliminar_seguimiento(
    seguimiento_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    if current_user.rol not in ("prescriptor", "admin"):
        raise HTTPException(status_code=403, detail="Requiere rol prescriptor")

    seg = db.query(Seguimiento).filter(Seguimiento.id == seguimiento_id).first()
    if not seg:
        raise HTTPException(status_code=404, detail="Seguimiento no encontrado")
    # El admin borra cualquiera; el prescriptor solo los suyos.
    # (No usar _get_prescriptor aquí: crearía un perfil de prescriptor para el admin.)
    if current_user.rol != "admin":
        presc = _get_prescriptor(db, current_user)
        if seg.prescriptor_id != presc.id:
            raise HTTPException(status_code=403, detail="No tienes permiso para eliminar este seguimiento")

    db.delete(seg)
    db.commit()


# ────────────────────────── GET /me ──────────────────────────
@router.get("/me", response_model=PrescriptorMe)
def mi_perfil_prescriptor(
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    if current_user.rol != "prescriptor":
        raise HTTPException(status_code=403, detail="Requiere rol prescriptor")
    presc = _get_prescriptor(db, current_user)

    dispositivo_nombre = None
    if presc.dispositivo_id:
        disp = db.query(Dispositivo).filter(Dispositivo.id == presc.dispositivo_id).first()
        dispositivo_nombre = disp.nombre if disp else None

    return PrescriptorMe(
        id=presc.id,
        nombre_completo=presc.nombre_completo,
        perfil_disciplina=presc.perfil_disciplina,
        telefono=presc.telefono,
        email=current_user.email,
        dispositivo_id=presc.dispositivo_id,
        dispositivo_nombre=dispositivo_nombre,
        fecha_registro=current_user.fecha_registro,
    )


# ────────────────────────── PUT /me ──────────────────────────
@router.put("/me", response_model=PrescriptorMe)
def editar_perfil_prescriptor(
    data: PrescriptorUpdate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    if current_user.rol != "prescriptor":
        raise HTTPException(status_code=403, detail="Requiere rol prescriptor")
    presc = _get_prescriptor(db, current_user)

    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(presc, field, value)

    db.commit()
    db.refresh(presc)

    dispositivo_nombre = None
    if presc.dispositivo_id:
        disp = db.query(Dispositivo).filter(Dispositivo.id == presc.dispositivo_id).first()
        dispositivo_nombre = disp.nombre if disp else None

    return PrescriptorMe(
        id=presc.id,
        nombre_completo=presc.nombre_completo,
        perfil_disciplina=presc.perfil_disciplina,
        telefono=presc.telefono,
        email=current_user.email,
        dispositivo_id=presc.dispositivo_id,
        dispositivo_nombre=dispositivo_nombre,
        fecha_registro=current_user.fecha_registro,
    )
