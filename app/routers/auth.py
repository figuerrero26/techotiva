from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException, Request, status, BackgroundTasks
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr, field_validator
from typing import Optional
import hashlib
import hmac
import re
import secrets

from app.services.email_service import (
    generar_token, enviar_correo_verificacion, enviar_correo_recuperacion, enviar_codigo_2fa,
    notificar_nuevo_registro,
)
from app.core.config import settings
from database import get_db
from app.models.models import Usuario, Estados, EstadoRegistro, Dispositivo, Prescriptor, Beneficiario
from app.core.security import hash_password, verify_password, create_access_token
from app.core.rate_limit import (
    ip_cliente, limite_login, limite_login_ip, limite_2fa_ip, limite_recuperar_ip,
)
from app.routers._deps import get_current_user
from app.schemas.schemas import CambiarPasswordRequest

router = APIRouter(prefix="/auth", tags=["Autenticación"])


def _token_para(usuario: Usuario) -> str:
    """Token de sesión; lleva la versión de sesión vigente del usuario."""
    return create_access_token({"sub": str(usuario.id), "rol": usuario.rol, "sv": usuario.sesion_version or 0})


def _cerrar_sesiones(usuario: Usuario) -> None:
    """Invalida todos los tokens emitidos hasta ahora para este usuario."""
    usuario.sesion_version = (usuario.sesion_version or 0) + 1


# ─── Schemas locales ──────────────────────────────────────────────────────────
def _minusculas(v):
    return v.strip().lower() if isinstance(v, str) else v


class LoginRequest(BaseModel):
    email: EmailStr
    password: str

    _email_min = field_validator("email", mode="before")(_minusculas)


class RegisterRequest(BaseModel):
    rol: str
    email: EmailStr
    password: str

    _email_min = field_validator("email", mode="before")(_minusculas)

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


# ─── Verificación en dos pasos (admin) ───────────────────────────────────────
DOSFA_MINUTOS     = 10   # vigencia del código
DOSFA_INTENTOS    = 5    # códigos errados permitidos antes de invalidarlo
DOSFA_REENVIO_SEG = 60   # espera mínima entre envíos

# Hash para comparar cuando el correo no existe: así el login tarda lo mismo
# exista o no la cuenta, y no se puede adivinar qué correos están registrados.
_HASH_FALSO = hash_password(secrets.token_urlsafe(16))


def _sha(valor: str) -> str:
    return hashlib.sha256(valor.encode()).hexdigest()


def _hmac_codigo(codigo: str) -> str:
    return hmac.new(settings.secret_key.encode(), codigo.encode(), hashlib.sha256).hexdigest()


def _enmascarar(email: str) -> str:
    usuario, _, dominio = email.partition("@")
    return (usuario[:2] + "***@" + dominio) if dominio else "***"


def _limpiar_2fa(usuario: Usuario) -> None:
    usuario.dosfa_desafio = None
    usuario.dosfa_codigo = None
    usuario.dosfa_expira = None
    usuario.dosfa_intentos = 0


def _respuesta_sesion(db: Session, usuario: Usuario) -> dict:
    return {
        "access_token": _token_para(usuario),
        "token_type": "bearer",
        "rol": usuario.rol,
        "nombre": _get_nombre(db, usuario),
        "user_id": usuario.id,
    }


async def _enviar_nuevo_codigo(db: Session, usuario: Usuario) -> None:
    """Genera un código nuevo, guarda solo su hash y lo envía por correo."""
    codigo = f"{secrets.randbelow(10**6):06d}"
    ahora = datetime.utcnow()
    usuario.dosfa_codigo = _hmac_codigo(codigo)
    usuario.dosfa_expira = ahora + timedelta(minutes=DOSFA_MINUTOS)
    usuario.dosfa_enviado = ahora
    usuario.dosfa_intentos = 0
    db.commit()
    try:
        await enviar_codigo_2fa(usuario.email, codigo, DOSFA_MINUTOS)
    except Exception:
        _limpiar_2fa(usuario)
        db.commit()
        raise HTTPException(
            status_code=503,
            detail="No se pudo enviar el código de verificación al correo. Revisa la configuración de correo del servidor.",
        )


# ─── Activar / desactivar 2FA (Configuración del admin) ─────────────────────
class Config2FARequest(BaseModel):
    activo: bool
    password: Optional[str] = None


@router.get("/2fa", summary="Estado de la verificación en dos pasos del admin")
def estado_2fa(current_user: Usuario = Depends(get_current_user)):
    if current_user.rol != "admin":
        raise HTTPException(status_code=403, detail="Solo para el administrador")
    return {
        "activo": current_user.dosfa_activo is not False,
        # Si ADMIN_2FA=false en el .env, la verificación está apagada para todos
        "habilitado_servidor": settings.admin_2fa,
    }


@router.put("/2fa", summary="Activar o desactivar la verificación en dos pasos del admin")
def cambiar_2fa(
    data: Config2FARequest,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    if current_user.rol != "admin":
        raise HTTPException(status_code=403, detail="Solo para el administrador")
    # Desactivar exige la contraseña: una sesión abierta no basta para quitar la protección
    if not data.activo:
        clave = "2fa-off:" + str(current_user.id)
        limite_login.verificar(clave)
        if not data.password or not verify_password(data.password, current_user.password_hash):
            limite_login.fallo(clave)
            raise HTTPException(status_code=400, detail="Contraseña incorrecta")
        limite_login.limpiar(clave)
    current_user.dosfa_activo = data.activo
    db.commit()
    return {"activo": data.activo}


# ─── Login ────────────────────────────────────────────────────────────────────
@router.post("/login", summary="Iniciar sesión")
async def login(data: LoginRequest, request: Request, db: Session = Depends(get_db)):
    clave_email = "login:" + data.email.lower()
    clave_ip = "login-ip:" + ip_cliente(request)
    limite_login.verificar(clave_email)
    limite_login_ip.verificar(clave_ip)

    usuario = db.query(Usuario).filter(Usuario.email == data.email).first()

    if not usuario:
        verify_password(data.password, _HASH_FALSO)
    if not usuario or not verify_password(data.password, usuario.password_hash):
        limite_login.fallo(clave_email)
        limite_login_ip.fallo(clave_ip)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Credenciales incorrectas")

    limite_login.limpiar(clave_email)

    if not usuario.estado_actual:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Error de configuración de cuenta. Contacta soporte.")

    if usuario.estado_actual.estado == Estados.PENDIENTE:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tu cuenta está en revisión. Te avisaremos por correo cuando sea aprobada.")

    if usuario.estado_actual.estado == Estados.INACTIVO:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tu cuenta ha sido desactivada")

    if usuario.estado_actual.estado != Estados.ACTIVO:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tu cuenta no está activa")

    if not usuario.email_verificado:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Debes verificar tu correo antes de iniciar sesión. Revisa el enlace que te enviamos.")

    # Admin: la contraseña sola no basta, se pide un código enviado al correo
    if usuario.rol == "admin" and settings.admin_2fa and usuario.dosfa_activo is not False:
        if usuario.dosfa_enviado and (datetime.utcnow() - usuario.dosfa_enviado).total_seconds() < 30:
            raise HTTPException(status_code=429, detail="Espera unos segundos antes de pedir otro código.")
        desafio = secrets.token_urlsafe(32)
        usuario.dosfa_desafio = _sha(desafio)
        await _enviar_nuevo_codigo(db, usuario)
        return {
            "requiere_2fa": True,
            "desafio": desafio,
            "correo": _enmascarar(usuario.email),
            "minutos": DOSFA_MINUTOS,
        }

    return _respuesta_sesion(db, usuario)


class Verificar2FARequest(BaseModel):
    desafio: str
    codigo: str


class Reenviar2FARequest(BaseModel):
    desafio: str


def _usuario_por_desafio(db: Session, desafio: str) -> Usuario:
    usuario = None
    if desafio and desafio.strip():
        usuario = db.query(Usuario).filter(Usuario.dosfa_desafio == _sha(desafio.strip())).first()
    if not usuario or not usuario.dosfa_codigo or not usuario.dosfa_expira:
        raise HTTPException(status_code=400, detail="El código ya no es válido. Inicia sesión de nuevo.")
    if datetime.utcnow() > usuario.dosfa_expira:
        _limpiar_2fa(usuario)
        db.commit()
        raise HTTPException(status_code=400, detail="El código venció. Inicia sesión de nuevo para recibir otro.")
    return usuario


@router.post("/verificar-2fa", summary="Segundo paso del login del administrador")
def verificar_2fa(data: Verificar2FARequest, request: Request, db: Session = Depends(get_db)):
    clave_ip = "2fa-ip:" + ip_cliente(request)
    limite_2fa_ip.verificar(clave_ip)

    usuario = _usuario_por_desafio(db, data.desafio)

    codigo = re.sub(r"\D", "", data.codigo or "")
    if not hmac.compare_digest(usuario.dosfa_codigo, _hmac_codigo(codigo)):
        limite_2fa_ip.fallo(clave_ip)
        usuario.dosfa_intentos = (usuario.dosfa_intentos or 0) + 1
        restantes = DOSFA_INTENTOS - usuario.dosfa_intentos
        if restantes <= 0:
            _limpiar_2fa(usuario)
            db.commit()
            raise HTTPException(status_code=400, detail="Demasiados intentos con este código. Inicia sesión de nuevo.")
        db.commit()
        raise HTTPException(status_code=400, detail=f"Código incorrecto. Te quedan {restantes} intento(s).")

    # Revalidar que la cuenta siga activa y siendo admin
    if usuario.rol != "admin" or not usuario.estado_actual or usuario.estado_actual.estado != Estados.ACTIVO:
        _limpiar_2fa(usuario)
        db.commit()
        raise HTTPException(status_code=403, detail="Tu cuenta no está activa")

    _limpiar_2fa(usuario)
    db.commit()
    limite_2fa_ip.limpiar(clave_ip)
    return _respuesta_sesion(db, usuario)


@router.post("/reenviar-2fa", summary="Reenviar el código de verificación del administrador")
async def reenviar_2fa(data: Reenviar2FARequest, db: Session = Depends(get_db)):
    usuario = _usuario_por_desafio(db, data.desafio)
    if usuario.dosfa_enviado:
        espera = DOSFA_REENVIO_SEG - (datetime.utcnow() - usuario.dosfa_enviado).total_seconds()
        if espera > 0:
            raise HTTPException(status_code=429, detail=f"Espera {int(espera) + 1} segundos para pedir otro código.")
    await _enviar_nuevo_codigo(db, usuario)
    return {"mensaje": f"Te enviamos un código nuevo a {_enmascarar(usuario.email)}.", "minutos": DOSFA_MINUTOS}


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
        mensaje = "Solicitud enviada. Cuando el administrador apruebe tu cuenta te llegará un correo para activarla."

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
        mensaje = "Solicitud enviada. Cuando el dispositivo apruebe tu cuenta te llegará un correo para activarla."

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

    # Beneficiario: verifica su correo de una vez.
    # Prescriptor y dispositivo: no se les escribe hasta que los aprueben; el correo
    # de aprobación trae el enlace para verificar (ver notificar_aprobacion).
    if data.rol == "beneficiario":
        token_verificacion = generar_token()
        usuario.email_token = token_verificacion
        db.commit()
        background_tasks.add_task(
            enviar_correo_verificacion,
            email=data.email,
            token=token_verificacion,
            base_url=settings.app_base_url,
        )
    else:
        db.commit()

    # Aviso a quien debe revisar el registro (dispositivo y/o admin)
    nombre_registro = data.nombre_completo if data.rol == "prescriptor" else (
        data.nombre if data.rol == "dispositivo" else data.nombre_apodo)
    notificar_nuevo_registro(
        background_tasks, db, usuario, nombre_registro,
        dispositivo=disp if data.rol == "prescriptor" else None,
    )

    return {
        "message": mensaje,
        "user_id": usuario.id,
        "status": estado_valor,
    }


# ─── Verificar email ──────────────────────────────────────────────────────────
@router.get("/verificar-email")
def verificar_email(token: str, db: Session = Depends(get_db)):
    """Enlace del correo: verifica y vuelve al login con un mensaje para la persona."""
    usuario = db.query(Usuario).filter(Usuario.email_token == token).first() if token else None
    if not usuario:
        return RedirectResponse(url="/login?verificado=invalido", status_code=303)
    usuario.email_verificado = True
    usuario.email_token = None
    db.commit()
    pendiente = usuario.estado == Estados.PENDIENTE
    return RedirectResponse(url="/login?verificado=" + ("revision" if pendiente else "ok"), status_code=303)


# ─── Recuperar contraseña ────────────────────────────────────────────────────
class RecuperarPasswordRequest(BaseModel):
    email: EmailStr

    _email_min = field_validator("email", mode="before")(_minusculas)


@router.post("/recuperar-password", summary="Solicitar recuperación de contraseña")
def recuperar_password(
    data: RecuperarPasswordRequest,
    request: Request,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    clave_ip = "recuperar-ip:" + ip_cliente(request)
    limite_recuperar_ip.verificar(clave_ip)
    limite_recuperar_ip.fallo(clave_ip)   # cuenta cada solicitud, exista o no el correo

    usuario = db.query(Usuario).filter(Usuario.email == data.email).first()
    # No reenviar si ya se mandó un enlace hace menos de un minuto (evita llenar el buzón)
    reciente = False
    if usuario and usuario.password_reset_token_expiry:
        exp = usuario.password_reset_token_expiry
        if exp.tzinfo is None:
            exp = exp.replace(tzinfo=timezone.utc)
        reciente = exp - datetime.now(timezone.utc) > timedelta(minutes=9)
    if usuario and not reciente:
        token = generar_token()
        usuario.password_reset_token = token
        usuario.password_reset_token_expiry = datetime.now(timezone.utc) + timedelta(minutes=10)
        db.commit()
        background_tasks.add_task(
            enviar_correo_recuperacion,
            email=usuario.email,
            token=token,
            base_url=settings.app_base_url,
        )
    # Siempre responder igual para no revelar si el email existe
    return {"message": "Si ese correo está registrado, recibirás un enlace para restablecer tu contraseña."}


class ResetearPasswordRequest(BaseModel):
    token: str
    nueva_password: str


@router.post("/resetear-password", summary="Establecer nueva contraseña con token")
def resetear_password(
    data: ResetearPasswordRequest,
    db: Session = Depends(get_db),
):
    token = data.token.strip()
    nueva = data.nueva_password.strip()
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
    _cerrar_sesiones(usuario)   # cierra las sesiones abiertas
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
    _cerrar_sesiones(current_user)   # cierra las demás sesiones
    db.commit()

    nuevo = _token_para(current_user)
    return {"mensaje": "Contraseña actualizada correctamente", "access_token": nuevo}


# ── Sesiones activas ──────────────────────────────────────────────────────────
@router.post("/ping")
def ping(current_user: Usuario = Depends(get_current_user)):
    """Pulso del navegador; get_current_user ya registra la última actividad."""
    return {"ok": True}


@router.post("/logout")
def logout(
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    """Marca al usuario como desconectado (el token lo borra el navegador)."""
    current_user.ultima_actividad = None
    _cerrar_sesiones(current_user)
    db.commit()
    return {"ok": True}