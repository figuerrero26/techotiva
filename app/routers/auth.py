from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr, field_validator
from typing import Optional
import re

from app.services.email_service import generar_token, enviar_correo_verificacion, enviar_correo_recuperacion
from app.core.config import settings
from database import get_db
from app.models.models import Usuario, Estados, EstadoRegistro, Dispositivo, Prescriptor, Beneficiario
from app.core.security import hash_password, verify_password, create_access_token
from app.routers._deps import get_current_user
from app.schemas.schemas import CambiarPasswordRequest

router = APIRouter(prefix="/auth", tags=["Autenticación"])


# ─── Schemas locales ──────────────────────────────────────────────────────────
class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class RegisterRequest(BaseModel):
    rol: str
    email: EmailStr
    password: str

    # Dispositivo CBC
    nombre: Optional[str] = None
    lugar_actividades: Optional[str] = None
    ubicacion: Optional[str] = None
    tipo_servicio: Optional[str] = None
    dia_actividad: Optional[str] = None
    hora_actividad: Optional[str] = None
    telefono: Optional[str] = None
    redes_sociales: Optional[str] = None

    # Prescriptxr
    nombre_completo: Optional[str] = None
    perfil_disciplina: Optional[str] = None
    dispositivo_id: Optional[int] = None

    # Beneficiarix
    nombre_apodo: Optional[str] = None

    politica_privacidad: bool = False

    @field_validator("password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("La contraseña debe tener al menos 8 caracteres")
        return v

    @field_validator("rol")
    @classmethod
    def rol_valido(cls, v: str) -> str:
        allowed = {"dispositivo", "prescriptor", "beneficiario"}
        if v not in allowed:
            raise ValueError(f"Rol inválido. Permitidos: {allowed}")
        return v


# ─── Helpers ──────────────────────────────────────────────────────────────────
def _get_nombre(db: Session, usuario: Usuario) -> str:
    if usuario.rol == "dispositivo":
        d = db.query(Dispositivo).filter(Dispositivo.usuario_id == usuario.id).first()
        return d.nombre if d else usuario.email
    elif usuario.rol == "prescriptor":
        p = db.query(Prescriptor).filter(Prescriptor.usuario_id == usuario.id).first()
        return p.nombre_completo if p else usuario.email
    elif usuario.rol == "beneficiario":
        b = db.query(Beneficiario).filter(Beneficiario.usuario_id == usuario.id).first()
        return b.nombre_apodo if b else usuario.email
    return "Administrador MASCATE"


def _validar_password_nueva(password: str) -> bool:
    """Mínimo 8 caracteres, al menos una mayúscula y un número."""
    if len(password) < 8:
        return False
    if not re.search(r"[A-Z]", password):
        return False
    if not re.search(r"\d", password):
        return False
    return True


# ─── Login ────────────────────────────────────────────────────────────────────
@router.post("/login", summary="Iniciar sesión")
def login(data: LoginRequest, db: Session = Depends(get_db)):
    usuario = db.query(Usuario).filter(Usuario.email == data.email).first()

    if not usuario or not verify_password(data.password, usuario.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Credenciales incorrectas")

    if not usuario.estado_actual:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Error de configuración de cuenta. Contacta soporte.")

    if usuario.estado_actual.estado == Estados.PENDIENTE:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tu cuenta está pendiente de aprobación")

    if usuario.estado_actual.estado == Estados.INACTIVO:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tu cuenta ha sido desactivada")

    if not usuario.email_verificado:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Debes verificar tu correo electrónico antes de iniciar sesión")

    nombre = _get_nombre(db, usuario)
    token = create_access_token({"sub": str(usuario.id), "rol": usuario.rol})

    return {
        "access_token": token,
        "token_type": "bearer",
        "rol": usuario.rol,
        "nombre": nombre,
        "user_id": usuario.id,
    }


# ─── Register ─────────────────────────────────────────────────────────────────
@router.post("/register", status_code=201, summary="Registrar nuevo usuario")
def register(data: RegisterRequest, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    if db.query(Usuario).filter(Usuario.email == data.email).first():
        raise HTTPException(status_code=409, detail="Este correo ya está registrado")

    usuario = Usuario(
        email=data.email,
        password_hash=hash_password(data.password),
        rol=data.rol,
        email_verificado=False,
        politica_privacidad_at=datetime.now(timezone.utc) if data.politica_privacidad else None,
    )
    db.add(usuario)
    db.flush()

    estado_valor = Estados.ACTIVO if data.rol == "beneficiario" else Estados.PENDIENTE
    estado_inicial = EstadoRegistro(
        entidad_tipo="usuario",
        entidad_id=usuario.id,
        estado=estado_valor,
        motivo="Registro inicial de usuario a través de la plataforma",
        cambiado_por=None
    )
    db.add(estado_inicial)
    db.flush()
    usuario.estado_actual_id = estado_inicial.id

    if data.rol == "dispositivo":
        if not data.nombre:
            raise HTTPException(400, detail="El nombre del dispositivo es obligatorio")
        perfil = Dispositivo(
            usuario_id=usuario.id,
            nombre=data.nombre,
            lugar_actividades=data.lugar_actividades,
            ubicacion=data.ubicacion,
            tipo_servicio=data.tipo_servicio,
            dia_actividad=data.dia_actividad,
            hora_actividad=data.hora_actividad,
            telefono=data.telefono,
            redes_sociales=data.redes_sociales,
        )
        db.add(perfil)
        db.flush()
        estado_disp = EstadoRegistro(entidad_tipo="dispositivo", entidad_id=perfil.id, estado=Estados.PENDIENTE, motivo="Solicitud de registro como dispositivo", cambiado_por=None)
        db.add(estado_disp)
        db.flush()
        perfil.estado_actual_id = estado_disp.id
        mensaje = "Solicitud enviada. Verifica tu correo y luego un administrador debe aprobarte."

    elif data.rol == "prescriptor":
        if not data.nombre_completo:
            raise HTTPException(400, detail="El nombre completo es obligatorio")
        if not data.dispositivo_id:
            raise HTTPException(400, detail="Debes seleccionar un Dispositivo CBC")
        disp = db.query(Dispositivo).filter(Dispositivo.id == data.dispositivo_id).first()
        if not disp:
            raise HTTPException(400, detail="El dispositivo seleccionado no es válido")
        disp_usuario = db.query(Usuario).filter(Usuario.id == disp.usuario_id).first()
        if not disp_usuario or not disp_usuario.estado_actual or disp_usuario.estado_actual.estado != Estados.ACTIVO:
            raise HTTPException(400, detail="El dispositivo seleccionado no está activo")
        perfil = Prescriptor(
            usuario_id=usuario.id,
            nombre_completo=data.nombre_completo,
            perfil_disciplina=data.perfil_disciplina,
            telefono=data.telefono,
            dispositivo_id=data.dispositivo_id,
        )
        db.add(perfil)
        db.flush()
        estado_presc = EstadoRegistro(entidad_tipo="prescriptor", entidad_id=perfil.id, estado=Estados.PENDIENTE, motivo="Solicitud de registro como prescriptor", cambiado_por=None)
        db.add(estado_presc)
        db.flush()
        perfil.estado_actual_id = estado_presc.id
        mensaje = "Solicitud enviada. Verifica tu correo y luego el Dispositivo CBC debe aprobarte."

    elif data.rol == "beneficiario":
        if not data.nombre_apodo:
            raise HTTPException(400, detail="El nombre o apodo es obligatorio")
        perfil = Beneficiario(
            usuario_id=usuario.id,
            nombre_apodo=data.nombre_apodo,
            dispositivo_id=data.dispositivo_id,  # ← NUEVO
        )
        db.add(perfil)
        db.flush()
        estado_benef = EstadoRegistro(entidad_tipo="beneficiario", entidad_id=perfil.id, estado=Estados.ACTIVO, motivo="Registro de beneficiario", cambiado_por=None)
        db.add(estado_benef)
        db.flush()
        perfil.estado_actual_id = estado_benef.id
        mensaje = "Registro completado. Verifica tu correo para iniciar sesión."

    token_verificacion = generar_token()
    usuario.email_token = token_verificacion

    db.commit()

    background_tasks.add_task(
        enviar_correo_verificacion,
        email=data.email,
        token=token_verificacion,
        base_url=settings.app_base_url
    )

    return {
        "message": mensaje,
        "user_id": usuario.id,
        "status": estado_valor,
    }


# ─── Verificar email ──────────────────────────────────────────────────────────
@router.get("/verificar-email")
def verificar_email(token: str, db: Session = Depends(get_db)):
    usuario = db.query(Usuario).filter(Usuario.email_token == token).first()
    if not usuario:
        raise HTTPException(400, detail="Token inválido o expirado")
    if usuario.email_verificado:
        return {"message": "Correo ya verificado"}
    usuario.email_verificado = True
    usuario.email_token = None
    db.commit()
    return {"message": "¡Correo verificado! Tu solicitud será revisada pronto."}


# ─── Recuperar contraseña ────────────────────────────────────────────────────
class RecuperarPasswordRequest(BaseModel):
    email: EmailStr


@router.post("/recuperar-password", summary="Solicitar recuperación de contraseña")
def recuperar_password(
    data: RecuperarPasswordRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    usuario = db.query(Usuario).filter(Usuario.email == data.email).first()
    if usuario:
        token = generar_token()
        usuario.password_reset_token = token
        usuario.password_reset_token_expiry = datetime.now(timezone.utc) + timedelta(hours=24)
        db.commit()
        background_tasks.add_task(
            enviar_correo_recuperacion,
            email=usuario.email,
            token=token,
            base_url=settings.app_base_url,
        )
    # Siempre responder igual para no revelar si el email existe
    return {"message": "Si ese correo está registrado, recibirás un enlace para restablecer tu contraseña."}


@router.post("/resetear-password", summary="Establecer nueva contraseña con token")
def resetear_password(
    data: dict,
    db: Session = Depends(get_db),
):
    token = data.get("token", "").strip()
    nueva = data.get("nueva_password", "").strip()
    if not token or not nueva:
        raise HTTPException(400, detail="Token y contraseña son requeridos")
    if not _validar_password_nueva(nueva):
        raise HTTPException(422, detail="La contraseña debe tener al menos 8 caracteres, una mayúscula y un número")
    usuario = db.query(Usuario).filter(Usuario.password_reset_token == token).first()
    if not usuario:
        raise HTTPException(400, detail="El enlace no es válido o ya fue utilizado")
    # Verificar expiración
    if usuario.password_reset_token_expiry:
        expiry = usuario.password_reset_token_expiry
        if expiry.tzinfo is None:
            expiry = expiry.replace(tzinfo=timezone.utc)
        if expiry < datetime.now(timezone.utc):
            raise HTTPException(400, detail="El enlace ha expirado. Solicita uno nuevo desde el formulario de inicio de sesión.")
    usuario.password_hash = hash_password(nueva)
    usuario.password_reset_token = None
    usuario.password_reset_token_expiry = None
    usuario.email_verificado = True
    db.commit()
    return {"message": "Contraseña actualizada correctamente. Ya puedes iniciar sesión."}


# ─── Cambiar contraseña ───────────────────────────────────────────────────────
@router.post("/cambiar-password", summary="Cambiar contraseña del usuario logueado")
def cambiar_password(
    data: CambiarPasswordRequest,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    # Verificar que la contraseña actual es correcta
    if not verify_password(data.password_actual, current_user.password_hash):
        raise HTTPException(status_code=400, detail="La contraseña actual es incorrecta")

    # Validar requisitos de la nueva contraseña
    if not _validar_password_nueva(data.password_nueva):
        raise HTTPException(
            status_code=422,
            detail="La nueva contraseña debe tener al menos 8 caracteres, una mayúscula y un número"
        )

    current_user.password_hash = hash_password(data.password_nueva)
    db.commit()

    return {"mensaje": "Contraseña actualizada correctamente"}