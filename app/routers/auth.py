"""
Router de autenticación: login y registro.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from database import get_db
from app.core.security import hash_password, verify_password, create_access_token
from app.models.models import Usuario, Dispositivo, Prescriptor, Beneficiario
from app.schemas.schemas import (
    LoginRequest, LoginResponse,
    RegisterRequest, RegisterResponse,
)

router = APIRouter(prefix="/auth", tags=["Autenticación"])


# ────────────────────────── LOGIN ──────────────────────────
@router.post("/login", response_model=LoginResponse)
def login(req: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(Usuario).filter(Usuario.email == req.email).first()
    if not user or not verify_password(req.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Credenciales incorrectas")
    if not user.activo:
        raise HTTPException(status_code=403, detail="Cuenta desactivada")

    # Obtener nombre según el rol
    nombre = user.email
    if user.rol == "dispositivo" and user.dispositivo:
        nombre = user.dispositivo.nombre
    elif user.rol == "prescriptor" and user.prescriptor:
        nombre = user.prescriptor.nombre_completo
    elif user.rol == "beneficiario" and user.beneficiario:
        nombre = user.beneficiario.nombre_apodo
    elif user.rol == "admin":
        nombre = "Admin MASCATE"

    token = create_access_token({"sub": str(user.id), "rol": user.rol})
    return LoginResponse(
        access_token=token,
        rol=user.rol,
        nombre=nombre,
    )


# ────────────────────────── REGISTRO ──────────────────────────
@router.post("/register", response_model=RegisterResponse, status_code=201)
def register(req: RegisterRequest, db: Session = Depends(get_db)):
    # Validar rol
    if req.rol not in ("dispositivo", "prescriptor", "beneficiario"):
        raise HTTPException(status_code=400, detail="Rol no válido para registro")

    # Verificar email único
    if db.query(Usuario).filter(Usuario.email == req.email).first():
        raise HTTPException(status_code=409, detail="Ya existe una cuenta con ese correo")

    # Crear usuario base
    user = Usuario(
        email=req.email,
        password_hash=hash_password(req.password),
        rol=req.rol,
    )
    db.add(user)
    db.flush()  # para obtener user.id

    # Crear perfil según rol
    if req.rol == "dispositivo":
        if not req.nombre:
            raise HTTPException(status_code=400, detail="El nombre del dispositivo es obligatorio")
        disp = Dispositivo(
            usuario_id=user.id,
            nombre=req.nombre,
            lugar_actividades=req.lugar_actividades,
            ubicacion=req.ubicacion,
            tipo_servicio=req.tipo_servicio,
            dia_actividad=req.dia_actividad,
            hora_actividad=req.hora_actividad,
            telefono=req.telefono,
            redes_sociales=req.redes_sociales,
        )
        db.add(disp)

    elif req.rol == "prescriptor":
        if not req.nombre_completo:
            raise HTTPException(status_code=400, detail="El nombre completo es obligatorio")
        presc = Prescriptor(
            usuario_id=user.id,
            nombre_completo=req.nombre_completo,
            perfil_disciplina=req.perfil_disciplina,
            telefono=req.telefono,
            dispositivo_id=req.dispositivo_id,
        )
        db.add(presc)

    elif req.rol == "beneficiario":
        if not req.nombre_apodo:
            raise HTTPException(status_code=400, detail="El nombre o apodo es obligatorio")
        benef = Beneficiario(
            usuario_id=user.id,
            nombre_apodo=req.nombre_apodo,
        )
        db.add(benef)

    db.commit()
    db.refresh(user)

    return RegisterResponse(
        message="Cuenta creada exitosamente",
        usuario_id=user.id,
        rol=user.rol,
    )
