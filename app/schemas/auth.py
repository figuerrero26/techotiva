from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr, field_validator
from typing import Optional
from fastapi import BackgroundTasks
from app.services.email_service import generar_token, enviar_correo_verificacion
from app.core.config import settings
from database import get_db
from app.models.models import Usuario, Dispositivo, Prescriptor, Beneficiario
from app.core.security import hash_password, verify_password, create_access_token

router = APIRouter(prefix="/auth", tags=["Autenticación"])


# ─── Schemas ──────────────────────────────────────────────────────────────────
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
    redes_sociales: Optional[str] = None
    
    # Prescriptxr
    nombre_completo: Optional[str] = None
    perfil_disciplina: Optional[str] = None
    telefono: Optional[str] = None
    dispositivo_id: Optional[int] = None

    # Beneficiarix
    nombre_apodo: Optional[str] = None

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
    """Retorna el nombre visible según el rol del usuario."""
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


# ─── Login ────────────────────────────────────────────────────────────────────
@router.post("/login", summary="Iniciar sesión")
def login(data: LoginRequest, db: Session = Depends(get_db)):
    usuario = db.query(Usuario).filter(Usuario.email == data.email).first()

    if not usuario or not verify_password(data.password, usuario.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales incorrectas",
        )

    if not usuario.activo:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tu cuenta está pendiente de aprobación o ha sido desactivada",
        )

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
@router.post("/register", status_code=201)
def register(data: RegisterRequest, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    # 1. Email duplicado
    if db.query(Usuario).filter(Usuario.email == data.email).first():
        raise HTTPException(status_code=409, detail="Este correo ya está registrado")

    # 2. Crear usuario base (inactivo hasta aprobación)
    usuario = Usuario(
        email=data.email,
        password_hash=hash_password(data.password),
        rol=data.rol,
        activo=False,  # pendiente de aprobación
    )
    db.add(usuario)
    db.flush()  # obtiene el ID sin hacer commit aún

    # 3. Crear perfil según rol
    if data.rol == "dispositivo":
        if not data.nombre:
            raise HTTPException(400, detail="El nombre del dispositivo es obligatorio")
        perfil = Dispositivo(
            usuario_id=usuario.id,
            nombre=data.nombre,
            lugar_actividades=data.lugar_actividades,
            ubicacion=data.ubicacion,
            tipo_servicio=data.tipo_servicio,
        )
        db.add(perfil)
        mensaje = "Solicitud enviada. Un administrador debe aprobarte."

    elif data.rol == "prescriptor":
        if not data.nombre_completo:
            raise HTTPException(400, detail="El nombre completo es obligatorio")
        if not data.dispositivo_id:
            raise HTTPException(400, detail="Debes seleccionar un Dispositivo CBC")

        # Verificar que el dispositivo exista y esté activo
        disp = db.query(Dispositivo).filter(Dispositivo.id == data.dispositivo_id).first()
        if not disp:
            raise HTTPException(400, detail="El dispositivo seleccionado no es válido")
        disp_usuario = db.query(Usuario).filter(Usuario.id == disp.usuario_id).first()
        if not disp_usuario or not disp_usuario.activo:
            raise HTTPException(400, detail="El dispositivo seleccionado no está activo")

        perfil = Prescriptor(
            usuario_id=usuario.id,
            nombre_completo=data.nombre_completo,
            perfil_disciplina=data.perfil_disciplina,
            telefono=data.telefono,
            dispositivo_id=data.dispositivo_id,
        )
        db.add(perfil)
        mensaje = "Solicitud enviada. El Dispositivo CBC que elegiste debe aprobarte."

    elif data.rol == "beneficiario":
        if not data.nombre_apodo:
            raise HTTPException(400, detail="El nombre o apodo es obligatorio")
        perfil = Beneficiario(
            usuario_id=usuario.id,
            nombre_apodo=data.nombre_apodo,
        )
        db.add(perfil)
        mensaje = "Solicitud enviada. Tu Prescriptxr debe aprobarte."
    # Generar token de verificación
    token = generar_token()
    usuario.email_token = token
    usuario.email_verificado = False
    db.commit()

    import asyncio
    try:
        asyncio.get_event_loop().run_until_complete(
            enviar_correo_verificacion(
                email=data.email,
                token=token,
                base_url=settings.app_base_url
            )
        )
        print("✅ Correo enviado")
    except Exception as e:
        print(f"❌ ERROR EMAIL: {e}")

    return {
        "message": mensaje,
        "user_id": usuario.id,
        "status": "pendiente",
    }


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
    
    return {"message": "Correo verificado correctamente. Tu solicitud será revisada pronto."}