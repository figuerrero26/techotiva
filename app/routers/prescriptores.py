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
    PrescriptorMe, PrescriptorUpdate, BeneficiarioResumen, DispositivoOut,
)
from app.routers._deps import get_current_user

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

    # 3. Si aún no hay nadie asignado, mostrar los del dispositivo como fallback
    if not benef_ids and presc.dispositivo_id:
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
        estado = "desvinculado" if benef.prescriptor_id is None else _calcular_estado(dias_sin)
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
    if current_user.rol not in ("prescriptor", "admin", "dispositivo"):
        raise HTTPException(status_code=403, detail="Requiere rol prescriptor")

    if current_user.rol in ("admin", "dispositivo"):
        q = db.query(Seguimiento)
        if beneficiario_id:
            q = q.filter(Seguimiento.beneficiario_id == beneficiario_id)
    else:
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


# ────────────────────────── ELIMINAR SEGUIMIENTO ──────────────────────────
@router.delete("/seguimientos/{seguimiento_id}", status_code=204)
def eliminar_seguimiento(
    seguimiento_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    if current_user.rol not in ("prescriptor", "admin"):
        raise HTTPException(status_code=403, detail="Requiere rol prescriptor")

    presc = _get_prescriptor(db, current_user)
    seg = db.query(Seguimiento).filter(Seguimiento.id == seguimiento_id).first()
    if not seg:
        raise HTTPException(status_code=404, detail="Seguimiento no encontrado")
    if seg.prescriptor_id != presc.id and current_user.rol != "admin":
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

    solicitud_dispositivo_nombre = None
    if presc.solicitud_dispositivo_id:
        d_sol = db.query(Dispositivo).filter(Dispositivo.id == presc.solicitud_dispositivo_id).first()
        solicitud_dispositivo_nombre = d_sol.nombre if d_sol else None

    return PrescriptorMe(
        id=presc.id,
        nombre_completo=presc.nombre_completo,
        perfil_disciplina=presc.perfil_disciplina,
        telefono=presc.telefono,
        email=current_user.email,
        dispositivo_id=presc.dispositivo_id,
        dispositivo_nombre=dispositivo_nombre,
        solicitud_dispositivo_id=presc.solicitud_dispositivo_id,
        solicitud_dispositivo_nombre=solicitud_dispositivo_nombre,
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

    solicitud_dispositivo_nombre_put = None
    if presc.solicitud_dispositivo_id:
        d_sol = db.query(Dispositivo).filter(Dispositivo.id == presc.solicitud_dispositivo_id).first()
        solicitud_dispositivo_nombre_put = d_sol.nombre if d_sol else None

    return PrescriptorMe(
        id=presc.id,
        nombre_completo=presc.nombre_completo,
        perfil_disciplina=presc.perfil_disciplina,
        telefono=presc.telefono,
        email=current_user.email,
        dispositivo_id=presc.dispositivo_id,
        dispositivo_nombre=dispositivo_nombre,
        solicitud_dispositivo_id=presc.solicitud_dispositivo_id,
        solicitud_dispositivo_nombre=solicitud_dispositivo_nombre_put,
        fecha_registro=current_user.fecha_registro,
    )


# ────────────────────────── BENEFICIARIOS DEL DISPOSITIVO (prescriptor ve todos) ──────────
@router.get("/beneficiarios-dispositivo", response_model=list[BeneficiarioResumen])
def beneficiarios_de_mi_dispositivo(
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    if current_user.rol != "prescriptor":
        raise HTTPException(status_code=403, detail="Requiere rol prescriptor")

    presc = _get_prescriptor(db, current_user)
    if not presc.dispositivo_id:
        return []

    dispositivo_id = presc.dispositivo_id
    benef_ids: set = set()

    insc = (
        db.query(Inscripcion.beneficiario_id)
        .join(Actividad, Actividad.id == Inscripcion.actividad_id)
        .filter(Actividad.dispositivo_id == dispositivo_id)
        .all()
    )
    benef_ids.update(b[0] for b in insc)

    pc = (
        db.query(PrimerContacto.beneficiario_id)
        .filter(PrimerContacto.dispositivo_id == dispositivo_id)
        .all()
    )
    benef_ids.update(b[0] for b in pc)

    disp = db.query(Dispositivo).filter(Dispositivo.id == dispositivo_id).first()
    if disp:
        presc_ids = [p.id for p in disp.prescriptores]
        if presc_ids:
            seg = (
                db.query(Seguimiento.beneficiario_id)
                .filter(Seguimiento.prescriptor_id.in_(presc_ids))
                .all()
            )
            benef_ids.update(b[0] for b in seg)

    directo = (
        db.query(Beneficiario.id)
        .filter(Beneficiario.dispositivo_id == dispositivo_id)
        .all()
    )
    benef_ids.update(b[0] for b in directo)

    if not benef_ids:
        return []

    benefs = db.query(Beneficiario).filter(Beneficiario.id.in_(benef_ids)).all()
    result = []
    for b in benefs:
        email = b.usuario.email if b.usuario else None
        result.append(BeneficiarioResumen(
            id=b.id,
            nombre_apodo=b.nombre_apodo,
            email=email,
            genero=b.genero,
            fecha_nacimiento=b.fecha_nacimiento,
            localidad=b.localidad,
            telefono=b.telefono,
            status=b.estado,
        ))
    return result


# ────────────────────────── DISPOSITIVOS DISPONIBLES ──────────────────────────
@router.get("/dispositivos-disponibles", response_model=list[DispositivoOut])
def dispositivos_disponibles(
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    if current_user.rol != "prescriptor":
        raise HTTPException(status_code=403, detail="Requiere rol prescriptor")

    disps = (
        db.query(Dispositivo)
        .join(Usuario, Usuario.id == Dispositivo.usuario_id)
        .join(Usuario.estado_actual)
        .filter(EstadoRegistro.estado == Estados.ACTIVO)
        .all()
    )
    result = []
    for d in disps:
        r = DispositivoOut.model_validate(d)
        r.activo = True
        result.append(r)
    return result


# ────────────────────────── SOLICITAR UNIRSE A DISPOSITIVO ──────────────────────────
@router.post("/solicitar-dispositivo/{dispositivo_id}")
def solicitar_dispositivo(
    dispositivo_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    if current_user.rol != "prescriptor":
        raise HTTPException(status_code=403, detail="Requiere rol prescriptor")

    presc = _get_prescriptor(db, current_user)
    disp = db.query(Dispositivo).filter(Dispositivo.id == dispositivo_id).first()
    if not disp:
        raise HTTPException(status_code=404, detail="Dispositivo no encontrado")
    if presc.dispositivo_id == dispositivo_id:
        raise HTTPException(status_code=400, detail="Ya perteneces a este dispositivo")

    presc.solicitud_dispositivo_id = dispositivo_id
    db.commit()
    return {"msg": f"Solicitud enviada a {disp.nombre}. Esperando aprobación."}


# ────────────────────────── CANCELAR SOLICITUD ──────────────────────────
@router.delete("/cancelar-solicitud")
def cancelar_solicitud(
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    if current_user.rol != "prescriptor":
        raise HTTPException(status_code=403, detail="Requiere rol prescriptor")

    presc = _get_prescriptor(db, current_user)
    presc.solicitud_dispositivo_id = None
    db.commit()
    return {"msg": "Solicitud cancelada"}