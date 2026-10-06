"""
Router de dispositivos: CRUD y estadísticas.
"""

from datetime import datetime, timedelta, timezone
from sqlalchemy import or_, func
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
    BeneficiarioResumen, PrescriptorResumen, AsignadoOut,
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

    benef_ids = set()

    # Por inscripciones en actividades del dispositivo
    insc = (
        db.query(Inscripcion.beneficiario_id)
        .join(Actividad, Actividad.id == Inscripcion.actividad_id)
        .filter(Actividad.dispositivo_id == dispositivo_id)
        .all()
    )
    benef_ids.update(b[0] for b in insc)

    # Por primer contacto
    pc = (
        db.query(PrimerContacto.beneficiario_id)
        .filter(PrimerContacto.dispositivo_id == dispositivo_id)
        .all()
    )
    benef_ids.update(b[0] for b in pc)

    # Por seguimientos de prescriptores del dispositivo
    presc_ids = [p.id for p in disp.prescriptores]
    if presc_ids:
        seg = (
            db.query(Seguimiento.beneficiario_id)
            .filter(Seguimiento.prescriptor_id.in_(presc_ids))
            .all()
        )
        benef_ids.update(b[0] for b in seg)

    # Por dispositivo_id directo en el perfil del beneficiario
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


# ────────────────────────── BENEFICIARIOS CON SEGUIMIENTO ──────────────────────────
@router.get("/{dispositivo_id}/beneficiarios-detalle", response_model=list[AsignadoOut])
def beneficiarios_dispositivo_detalle(
    dispositivo_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    if current_user.rol not in ("dispositivo", "admin"):
        raise HTTPException(status_code=403, detail="Requiere rol dispositivo")

    disp = db.query(Dispositivo).filter(Dispositivo.id == dispositivo_id).first()
    if not disp:
        raise HTTPException(status_code=404, detail="Dispositivo no encontrado")

    benef_ids = set()

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

    now = datetime.now(timezone.utc)
    result = []
    for bid in benef_ids:
        benef = db.query(Beneficiario).filter(Beneficiario.id == bid).first()
        if not benef:
            continue

        ultima = (
            db.query(func.max(Seguimiento.fecha))
            .filter(Seguimiento.beneficiario_id == bid)
            .scalar()
        )

        dias_sin = None
        if ultima:
            if ultima.tzinfo is None:
                ultima = ultima.replace(tzinfo=timezone.utc)
            dias_sin = (now - ultima).days

        def _estado(dias):
            if dias is None:
                return "urgente"
            if dias < 3:
                return "al_dia"
            if dias <= 7:
                return "revisar"
            return "urgente"

        usuario = db.query(Usuario).filter(Usuario.id == benef.usuario_id).first() if hasattr(benef, 'usuario_id') else None
        result.append(AsignadoOut(
            id=benef.id,
            nombre_apodo=benef.nombre_apodo,
            ultima_sesion=ultima,
            dias_sin_sesion=dias_sin,
            estado=_estado(dias_sin),
            email=usuario.email if usuario else None,
            telefono=benef.telefono if hasattr(benef, 'telefono') else None,
        ))

    return result


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

# ────────────────────────── PRESCRIPTORES ACTIVOS DEL DISPOSITIVO ──────────────────────────
@router.get("/{dispositivo_id}/prescriptores", response_model=list[PrescriptorResumen])
def listar_prescriptores_dispositivo(
    dispositivo_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    disp = db.query(Dispositivo).filter(Dispositivo.id == dispositivo_id).first()
    if not disp:
        raise HTTPException(status_code=404, detail="Dispositivo no encontrado")

    if current_user.rol != "admin" and disp.usuario_id != current_user.id:
        raise HTTPException(status_code=403, detail="No tienes permiso")

    prescs = (
        db.query(Prescriptor)
        .filter(
            Prescriptor.dispositivo_id == dispositivo_id,
            Prescriptor.estado_actual.has(EstadoRegistro.estado == Estados.ACTIVO)
        )
        .all()
    )

    result = []
    for p in prescs:
        result.append(PrescriptorResumen(
            id=p.id,
            nombre_completo=p.nombre_completo,
            perfil_disciplina=p.perfil_disciplina,
            telefono=p.telefono,
            email=p.usuario.email if p.usuario else "",
            status=p.estado,
        ))
    return result

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


# ────────────────────────── RECHAZAR PRESCRIPTOR (POR DISPOSITIVO) ──────────────────────────
@router.put("/{dispositivo_id}/prescriptores/{prescriptor_id}/rechazar")
def rechazar_prescriptor(
    dispositivo_id: int,
    prescriptor_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    disp = db.query(Dispositivo).filter(Dispositivo.id == dispositivo_id).first()
    if not disp:
        raise HTTPException(status_code=404, detail="Dispositivo no encontrado")

    if current_user.rol != "admin" and disp.usuario_id != current_user.id:
        raise HTTPException(status_code=403, detail="No tienes permiso para rechazar prescriptores de este dispositivo")

    presc = db.query(Prescriptor).filter(Prescriptor.id == prescriptor_id).first()
    if not presc:
        raise HTTPException(status_code=404, detail="Prescriptor no encontrado")

    if presc.dispositivo_id != dispositivo_id:
        raise HTTPException(status_code=403, detail="El prescriptor no pertenece a este dispositivo")

    service = EstadoService(db)

    service.cambiar_estado(
        entidad_obj=presc,
        nuevo_estado=Estados.RECHAZADO,
        admin_id=current_user.id,
        motivo="Rechazado por el dispositivo"
    )

    if presc.usuario:
        service.cambiar_estado(
            entidad_obj=presc.usuario,
            nuevo_estado=Estados.RECHAZADO,
            admin_id=current_user.id,
            motivo="Rechazado por el dispositivo"
        )

    return {"mensaje": "Prescriptxr rechazado"}


# ────────────────────────── SOLICITUDES DE UNIÓN ──────────────────────────
@router.get("/{dispositivo_id}/solicitudes")
def listar_solicitudes(
    dispositivo_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    disp = db.query(Dispositivo).filter(Dispositivo.id == dispositivo_id).first()
    if not disp:
        raise HTTPException(status_code=404, detail="Dispositivo no encontrado")
    if current_user.rol != "admin" and disp.usuario_id != current_user.id:
        raise HTTPException(status_code=403, detail="Sin permiso")

    prescs = (
        db.query(Prescriptor)
        .filter(Prescriptor.solicitud_dispositivo_id == dispositivo_id)
        .all()
    )
    return [
        {
            "id": p.id,
            "nombre_completo": p.nombre_completo,
            "perfil_disciplina": p.perfil_disciplina,
            "telefono": p.telefono,
            "email": p.usuario.email if p.usuario else "",
            "dispositivo_actual": p.dispositivo.nombre if (p.dispositivo_id and p.dispositivo) else None,
        }
        for p in prescs
    ]


@router.post("/{dispositivo_id}/solicitudes/{prescriptor_id}/aprobar")
def aprobar_solicitud(
    dispositivo_id: int,
    prescriptor_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    disp = db.query(Dispositivo).filter(Dispositivo.id == dispositivo_id).first()
    if not disp:
        raise HTTPException(status_code=404, detail="Dispositivo no encontrado")
    if current_user.rol != "admin" and disp.usuario_id != current_user.id:
        raise HTTPException(status_code=403, detail="Sin permiso")

    presc = db.query(Prescriptor).filter(Prescriptor.id == prescriptor_id).first()
    if not presc:
        raise HTTPException(status_code=404, detail="Prescriptor no encontrado")
    if presc.solicitud_dispositivo_id != dispositivo_id:
        raise HTTPException(status_code=400, detail="Este prescriptor no tiene solicitud pendiente para este dispositivo")

    presc.dispositivo_id = dispositivo_id
    presc.solicitud_dispositivo_id = None

    service = EstadoService(db)
    if presc.usuario:
        service.cambiar_estado(entidad_obj=presc.usuario, nuevo_estado=Estados.ACTIVO, admin_id=current_user.id, motivo="Solicitud de unión aprobada")
    service.cambiar_estado(entidad_obj=presc, nuevo_estado=Estados.ACTIVO, admin_id=current_user.id, motivo="Solicitud de unión aprobada")

    return {"msg": "Solicitud aprobada. Prescriptor vinculado al dispositivo."}


@router.post("/{dispositivo_id}/solicitudes/{prescriptor_id}/rechazar")
def rechazar_solicitud(
    dispositivo_id: int,
    prescriptor_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    disp = db.query(Dispositivo).filter(Dispositivo.id == dispositivo_id).first()
    if not disp:
        raise HTTPException(status_code=404, detail="Dispositivo no encontrado")
    if current_user.rol != "admin" and disp.usuario_id != current_user.id:
        raise HTTPException(status_code=403, detail="Sin permiso")

    presc = db.query(Prescriptor).filter(Prescriptor.id == prescriptor_id).first()
    if not presc:
        raise HTTPException(status_code=404, detail="Prescriptor no encontrado")
    if presc.solicitud_dispositivo_id != dispositivo_id:
        raise HTTPException(status_code=400, detail="Este prescriptor no tiene solicitud pendiente para este dispositivo")

    presc.solicitud_dispositivo_id = None
    db.commit()
    return {"msg": "Solicitud rechazada"}