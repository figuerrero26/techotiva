from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.user import UserRole, UserStatus
from app.repositories.user_repo import UserRepository
from app.schemas.auth import LoginRequest, RegisterRequest, TokenResponse, RegisterResponse
from app.core.security import verify_password, hash_password, create_access_token


# ─── Reglas de aprobación ─────────────────────────────────────────────────────
# rol a registrar → quien puede aprobarlo
APPROVAL_RULES = {
    UserRole.DISPOSITIVO:  UserRole.ADMIN,
    UserRole.PRESCRIPTOR:  UserRole.DISPOSITIVO,
    UserRole.BENEFICIARIO: UserRole.PRESCRIPTOR,
}

# Mensajes de estado pendiente por rol
PENDING_MESSAGES = {
    UserRole.DISPOSITIVO:  "Tu solicitud fue enviada. Un administrador debe aprobarte.",
    UserRole.PRESCRIPTOR:  "Tu solicitud fue enviada. El Dispositivo CBC que elegiste debe aprobarte.",
    UserRole.BENEFICIARIO: "Tu solicitud fue enviada. Tu Prescriptxr debe aprobarte.",
}


class AuthService:
    def __init__(self, db: Session):
        self.repo = UserRepository(db)

    # ─── Login ────────────────────────────────────────────────────────────────
    def login(self, data: LoginRequest) -> TokenResponse:
        user = self.repo.get_by_email(data.email)

        # Mensaje genérico para no revelar si el email existe
        if not user or not verify_password(data.password, user.hashed_pwd):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Credenciales incorrectas",
            )

        if user.estado == Estados.PENDIENTE:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Tu cuenta está pendiente de aprobación",
            )

        if user.estado == Estados.INACTIVO:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Tu cuenta ha sido desactivada",
            )

        token = create_access_token({"sub": str(user.id), "rol": user.rol.value})

        return TokenResponse(
            access_token=token,
            rol=user.rol.value,
            status=user.status.value,
            user_id=user.id,
        )

    # ─── Registro ─────────────────────────────────────────────────────────────
    def register(self, data: RegisterRequest) -> RegisterResponse:
        # 1. Email duplicado
        if self.repo.get_by_email(data.email):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Este correo ya está registrado",
            )

        rol = UserRole(data.rol)
        user_data = {
            "email": data.email,
            "hashed_pwd": hash_password(data.password),
            "rol": rol,
            "status": UserStatus.PENDIENTE,
        }

        # 2. Validaciones y campos específicos por rol
        if rol == UserRole.DISPOSITIVO:
            if not data.nombre:
                raise HTTPException(400, detail="El nombre del dispositivo es obligatorio")
            user_data.update({
                "nombre": data.nombre,
                "lugar_actividades": data.lugar_actividades,
                "ubicacion": data.ubicacion,
                "tipo_servicio": data.tipo_servicio,
            })

        elif rol == UserRole.PRESCRIPTOR:
            if not data.nombre_completo:
                raise HTTPException(400, detail="El nombre completo es obligatorio")
            if not data.dispositivo_id:
                raise HTTPException(400, detail="Debes seleccionar un Dispositivo CBC")

            # Verificar que el dispositivo exista y esté activo
            dispositivo = self.repo.get_by_id(data.dispositivo_id)
            if not dispositivo or dispositivo.rol != UserRole.DISPOSITIVO or dispositivo.status != UserStatus.ACTIVO:
                raise HTTPException(400, detail="El dispositivo seleccionado no es válido")

            user_data.update({
                "nombre_completo": data.nombre_completo,
                "perfil_disciplina": data.perfil_disciplina,
                "telefono": data.telefono,
                "dispositivo_id": data.dispositivo_id,
            })

        elif rol == UserRole.BENEFICIARIO:
            if not data.nombre_apodo:
                raise HTTPException(400, detail="El nombre o apodo es obligatorio")
            user_data.update({
                "nombre_apodo": data.nombre_apodo,
            })

        # 3. Crear usuario
        user = self.repo.create(**user_data)

        return RegisterResponse(
            message=PENDING_MESSAGES[rol],
            user_id=user.id,
            status=user.status.value,
        )