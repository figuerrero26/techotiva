"""
Router para Hoja de Primer Contacto.
"""

from datetime import datetime, timedelta, timezone, date as ddate, time as dtime
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session

from database import get_db
from app.core.config import settings
from app.core.security import hash_password
from app.models.models import (
    Usuario, Prescriptor, Beneficiario, PrimerContacto, Dispositivo,
    Estados, EstadoRegistro,
)
from app.schemas.schemas import PrimerContactoCreate, PrimerContactoOut, _PCBase
from app.routers._deps import get_current_user
from app.services.estado_service import EstadoService
from app.services.email_service import generar_token, enviar_correo_bienvenida_beneficiario


# ── Campos demográficos que viven en Beneficiario ────────────────────────────
_BENEF_FIELDS = (
    "genero", "telefono", "localidad",
    "estado_civil", "num_hijos", "etnia", "pertenencia_etnica", "religion", "con_quien_vive",
    "sabe_leer_escribir", "sabe_usar_computador", "escolaridad", "ocupacion",
    "apoyo_familiar", "apoyo_comunitario", "apoyo_institucional",
    "apoyo_otro_actor", "cual_actor_social", "practica_deporte",
    "tiene_tiempo_recreacion", "cuanto_tiempo_recreacion",
    "conoce_espacios", "ha_participado",
    "tiene_persona_apoyo", "nombre_persona_apoyo", "telefono_persona_apoyo",
    "vinculo_persona_apoyo", "tipo_vinculo_codigo", "genero_apoyo",
)

# ── Campos del evento PrimerContacto ─────────────────────────────────────────
_PC_FIELDS = (
    "convenio_515", "tipo_dbc", "politica_privacidad", "numero_caso",
    "upz", "barrio", "forma_contacto",
    "nombre_fuente", "telefono_fuente", "genero_fuente", "vinculo_fuente",
    "edad_benef",
    "clase_via", "numero_via_principal", "letra_via_principal",
    "identificador_sector", "numero_via_generadora", "letra_via_generadora",
    "numero_predio", "otras_caracteristicas_dir",
    "situaciones_presentes", "peticiones", "descripcion_caso",
    "procesos_previos",
    "rol_registrador", "nombre_registrador", "telefono_registrador",
)


class PrimerContactoSinCuenta(_PCBase):
    """Crea un beneficiario + primer contacto sin cuenta existente."""
    nombre_apodo: str
    email: Optional[EmailStr] = None


router = APIRouter(prefix="/primer-contacto", tags=["Primer Contacto"])


def _get_prescriptor_opt(db: Session, user: Usuario) -> Optional[Prescriptor]:
    return db.query(Prescriptor).filter(Prescriptor.usuario_id == user.id).first()


def _marcar_privacidad(db: Session, usuario: Usuario) -> None:
    if usuario and not usuario.politica_privacidad_at:
        usuario.politica_privacidad_at = datetime.now(timezone.utc)


def _parse_fecha(s: Optional[str]) -> Optional[ddate]:
    if not s:
        return None
    try:
        return ddate.fromisoformat(s)
    except Exception:
        return None


def _parse_hora(s: Optional[str]) -> Optional[dtime]:
    if not s:
        return None
    try:
        h, m = s.split(":")
        return dtime(int(h), int(m))
    except Exception:
        return None


def _apply_benef_fields(benef: Beneficiario, data: _PCBase) -> None:
    """Actualiza los campos demográficos de Beneficiario desde el payload."""
    if data.fecha_nacimiento is not None:
        benef.fecha_nacimiento = _parse_fecha(str(data.fecha_nacimiento))
    for field in _BENEF_FIELDS:
        val = getattr(data, field, None)
        if val is not None:
            setattr(benef, field, val)


def _apply_pc_fields(pc: PrimerContacto, data: _PCBase) -> None:
    for field in _PC_FIELDS:
        val = getattr(data, field, None)
        if val is not None:
            setattr(pc, field, val)


def _to_out(pc: PrimerContacto, benef: Optional[Beneficiario]) -> PrimerContactoOut:
    hora_str = pc.hora_contacto.strftime("%H:%M") if pc.hora_contacto else None
    return PrimerContactoOut(
        id=pc.id,
        beneficiario_id=pc.beneficiario_id,
        dispositivo_id=pc.dispositivo_id,
        prescriptor_id=pc.prescriptor_id,
        created_at=pc.created_at,
        # Convenio
        convenio_515=pc.convenio_515,
        tipo_dbc=pc.tipo_dbc,
        politica_privacidad=pc.politica_privacidad,
        numero_caso=pc.numero_caso,
        # Evento
        fecha_contacto=pc.fecha_contacto,
        hora_contacto=hora_str,
        upz=pc.upz,
        barrio=pc.barrio,
        forma_contacto=pc.forma_contacto,
        # Fuente
        nombre_fuente=pc.nombre_fuente,
        telefono_fuente=pc.telefono_fuente,
        genero_fuente=pc.genero_fuente,
        vinculo_fuente=pc.vinculo_fuente,
        edad_benef=pc.edad_benef,
        # Dirección
        clase_via=pc.clase_via,
        numero_via_principal=pc.numero_via_principal,
        letra_via_principal=pc.letra_via_principal,
        identificador_sector=pc.identificador_sector,
        numero_via_generadora=pc.numero_via_generadora,
        letra_via_generadora=pc.letra_via_generadora,
        numero_predio=pc.numero_predio,
        otras_caracteristicas_dir=pc.otras_caracteristicas_dir,
        # Situación
        situaciones_presentes=pc.situaciones_presentes,
        peticiones=pc.peticiones,
        descripcion_caso=pc.descripcion_caso,
        procesos_previos=pc.procesos_previos,
        # Registrador
        rol_registrador=pc.rol_registrador,
        nombre_registrador=pc.nombre_registrador,
        telefono_registrador=pc.telefono_registrador,
        # Beneficiario
        nombre_beneficiario=benef.nombre_apodo if benef else None,
        fecha_nacimiento=benef.fecha_nacimiento if benef else None,
        genero=benef.genero if benef else None,
        telefono=benef.telefono if benef else None,
        localidad=benef.localidad if benef else None,
        estado_civil=benef.estado_civil if benef else None,
        num_hijos=benef.num_hijos if benef else None,
        etnia=benef.etnia if benef else None,
        pertenencia_etnica=benef.pertenencia_etnica if benef else None,
        religion=benef.religion if benef else None,
        con_quien_vive=benef.con_quien_vive if benef else None,
        sabe_leer_escribir=benef.sabe_leer_escribir if benef else None,
        sabe_usar_computador=benef.sabe_usar_computador if benef else None,
        escolaridad=benef.escolaridad if benef else None,
        ocupacion=benef.ocupacion if benef else None,
        apoyo_familiar=benef.apoyo_familiar if benef else None,
        apoyo_comunitario=benef.apoyo_comunitario if benef else None,
        apoyo_institucional=benef.apoyo_institucional if benef else None,
        apoyo_otro_actor=benef.apoyo_otro_actor if benef else None,
        cual_actor_social=benef.cual_actor_social if benef else None,
        practica_deporte=benef.practica_deporte if benef else None,
        tiene_tiempo_recreacion=benef.tiene_tiempo_recreacion if benef else None,
        cuanto_tiempo_recreacion=benef.cuanto_tiempo_recreacion if benef else None,
        conoce_espacios=benef.conoce_espacios if benef else None,
        ha_participado=benef.ha_participado if benef else None,
        tiene_persona_apoyo=benef.tiene_persona_apoyo if benef else None,
        nombre_persona_apoyo=benef.nombre_persona_apoyo if benef else None,
        telefono_persona_apoyo=benef.telefono_persona_apoyo if benef else None,
        vinculo_persona_apoyo=benef.vinculo_persona_apoyo if benef else None,
        tipo_vinculo_codigo=benef.tipo_vinculo_codigo if benef else None,
        genero_apoyo=benef.genero_apoyo if benef else None,
    )


# ── POST ──────────────────────────────────────────────────────────────────────
@router.post("/", response_model=PrimerContactoOut, status_code=201)
def crear_primer_contacto(
    data: PrimerContactoCreate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    if current_user.rol not in ("prescriptor", "dispositivo", "admin"):
        raise HTTPException(status_code=403, detail="Sin permiso para registrar primer contacto")

    benef = db.query(Beneficiario).filter(Beneficiario.id == data.beneficiario_id).first()
    if not benef:
        raise HTTPException(status_code=404, detail="Beneficiario no encontrado")

    disp = db.query(Dispositivo).filter(Dispositivo.id == data.dispositivo_id).first()
    if not disp:
        raise HTTPException(status_code=404, detail="Dispositivo no encontrado")

    presc = _get_prescriptor_opt(db, current_user)

    pc = PrimerContacto(
        beneficiario_id=data.beneficiario_id,
        dispositivo_id=data.dispositivo_id,
        prescriptor_id=presc.id if presc else None,
        fecha_contacto=data.fecha_contacto or ddate.today(),
        hora_contacto=_parse_hora(data.hora_contacto),
    )
    _apply_pc_fields(pc, data)
    _apply_benef_fields(benef, data)

    if data.politica_privacidad == 'Sí' and benef.usuario:
        _marcar_privacidad(db, benef.usuario)

    db.add(pc)
    db.commit()
    db.refresh(pc)
    return _to_out(pc, benef)


# ── POST sin cuenta ───────────────────────────────────────────────────────────
@router.post("/sin-cuenta", response_model=PrimerContactoOut, status_code=201)
def crear_primer_contacto_sin_cuenta(
    data: PrimerContactoSinCuenta,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    if current_user.rol not in ("prescriptor", "dispositivo", "admin"):
        raise HTTPException(status_code=403, detail="Sin permiso para registrar primer contacto")

    disp = db.query(Dispositivo).filter(Dispositivo.id == data.dispositivo_id).first()
    if not disp:
        raise HTTPException(status_code=404, detail="Dispositivo no encontrado")

    if data.email:
        if db.query(Usuario).filter(Usuario.email == data.email).first():
            raise HTTPException(status_code=409, detail="Ya existe una cuenta con ese correo electrónico")

    import secrets as _sec
    tiene_email_real = bool(data.email)
    if tiene_email_real:
        email_usuario = data.email
        pwd_hash = hash_password(_sec.token_urlsafe(32))
    else:
        token_anonimo = _sec.token_hex(8)
        email_usuario = f"anonimo_{token_anonimo}@sin-cuenta.mascate"
        pwd_hash = "!no-login!"

    usuario_anonimo = Usuario(
        email=email_usuario,
        password_hash=pwd_hash,
        rol="beneficiario",
        email_verificado=False,
    )
    db.add(usuario_anonimo)
    db.flush()

    service = EstadoService(db)
    service.cambiar_estado(
        entidad_obj=usuario_anonimo,
        nuevo_estado=Estados.ACTIVO,
        admin_id=current_user.id,
        motivo="Beneficiario registrado en primer contacto sin cuenta",
    )

    benef = Beneficiario(
        usuario_id=usuario_anonimo.id,
        nombre_apodo=data.nombre_apodo,
        dispositivo_id=data.dispositivo_id,
    )
    _apply_benef_fields(benef, data)
    db.add(benef)
    db.flush()

    estado_benef = EstadoRegistro(
        entidad_tipo="beneficiarios",
        entidad_id=benef.id,
        estado=Estados.ACTIVO,
        cambiado_por=current_user.id,
        motivo="Registro en primer contacto",
    )
    db.add(estado_benef)
    db.flush()
    benef.estado_actual_id = estado_benef.id

    presc = _get_prescriptor_opt(db, current_user)

    pc = PrimerContacto(
        beneficiario_id=benef.id,
        dispositivo_id=data.dispositivo_id,
        prescriptor_id=presc.id if presc else None,
        fecha_contacto=data.fecha_contacto or ddate.today(),
        hora_contacto=_parse_hora(data.hora_contacto),
    )
    _apply_pc_fields(pc, data)

    if data.politica_privacidad == 'Sí':
        _marcar_privacidad(db, usuario_anonimo)

    db.add(pc)
    db.commit()
    db.refresh(pc)

    if tiene_email_real:
        reset_token = generar_token()
        usuario_anonimo.password_reset_token = reset_token
        usuario_anonimo.password_reset_token_expiry = datetime.now(timezone.utc) + timedelta(hours=24)
        db.commit()
        background_tasks.add_task(
            enviar_correo_bienvenida_beneficiario,
            email=email_usuario,
            token=reset_token,
            base_url=settings.app_base_url,
        )

    return _to_out(pc, benef)


# ── GET lista ─────────────────────────────────────────────────────────────────
@router.get("/", response_model=list[PrimerContactoOut])
def listar_primer_contacto(
    beneficiario_id: Optional[int] = Query(None),
    dispositivo_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    if current_user.rol not in ("prescriptor", "dispositivo", "admin"):
        raise HTTPException(status_code=403, detail="Sin permiso")

    q = db.query(PrimerContacto)

    if current_user.rol == "prescriptor":
        presc = _get_prescriptor_opt(db, current_user)
        # When loading a specific beneficiario's ficha, skip the dispositivo filter
        # so prescriptors can see primer contactos regardless of which dispositivo created them
        if presc and presc.dispositivo_id and not beneficiario_id:
            q = q.filter(PrimerContacto.dispositivo_id == presc.dispositivo_id)
    elif current_user.rol == "dispositivo":
        disp = db.query(Dispositivo).filter(Dispositivo.usuario_id == current_user.id).first()
        if disp:
            q = q.filter(PrimerContacto.dispositivo_id == disp.id)

    if beneficiario_id:
        q = q.filter(PrimerContacto.beneficiario_id == beneficiario_id)
    if dispositivo_id and current_user.rol == "admin":
        q = q.filter(PrimerContacto.dispositivo_id == dispositivo_id)

    pcs = q.order_by(PrimerContacto.fecha_contacto.desc()).all()
    result = []
    for pc in pcs:
        benef = db.query(Beneficiario).filter(Beneficiario.id == pc.beneficiario_id).first()
        result.append(_to_out(pc, benef))
    return result


# ── GET uno ───────────────────────────────────────────────────────────────────
@router.get("/{pc_id}", response_model=PrimerContactoOut)
def obtener_primer_contacto(
    pc_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    if current_user.rol not in ("prescriptor", "dispositivo", "admin"):
        raise HTTPException(status_code=403, detail="Sin permiso")

    pc = db.query(PrimerContacto).filter(PrimerContacto.id == pc_id).first()
    if not pc:
        raise HTTPException(status_code=404, detail="Registro no encontrado")

    benef = db.query(Beneficiario).filter(Beneficiario.id == pc.beneficiario_id).first()
    return _to_out(pc, benef)


# ── PUT ───────────────────────────────────────────────────────────────────────
class PrimerContactoUpdate(_PCBase):
    dispositivo_id: Optional[int] = None  # override to optional for updates


@router.put("/{pc_id}", response_model=PrimerContactoOut)
def actualizar_primer_contacto(
    pc_id: int,
    data: PrimerContactoUpdate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    if current_user.rol not in ("prescriptor", "dispositivo", "admin"):
        raise HTTPException(status_code=403, detail="Sin permiso")

    pc = db.query(PrimerContacto).filter(PrimerContacto.id == pc_id).first()
    if not pc:
        raise HTTPException(status_code=404, detail="Registro no encontrado")

    if data.fecha_contacto is not None:
        pc.fecha_contacto = data.fecha_contacto
    if data.hora_contacto is not None:
        pc.hora_contacto = _parse_hora(data.hora_contacto)

    _apply_pc_fields(pc, data)

    benef = db.query(Beneficiario).filter(Beneficiario.id == pc.beneficiario_id).first()
    if benef:
        _apply_benef_fields(benef, data)
        if data.politica_privacidad == 'Sí' and benef.usuario:
            _marcar_privacidad(db, benef.usuario)

    db.commit()
    db.refresh(pc)
    return _to_out(pc, benef)


# ── DELETE ────────────────────────────────────────────────────────────────────
@router.delete("/{pc_id}", status_code=204)
def eliminar_primer_contacto(
    pc_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    if current_user.rol not in ("prescriptor", "dispositivo", "admin"):
        raise HTTPException(status_code=403, detail="Sin permiso")

    pc = db.query(PrimerContacto).filter(PrimerContacto.id == pc_id).first()
    if not pc:
        raise HTTPException(status_code=404, detail="Registro no encontrado")

    if current_user.rol != "admin":
        presc = _get_prescriptor_opt(db, current_user)
        if not presc or pc.prescriptor_id != presc.id:
            raise HTTPException(status_code=403, detail="No tienes permiso para eliminar este registro")

    db.delete(pc)
    db.commit()
