from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user, require_roles
from app.models.user import User, UserRole
from app.repositories.user_repo import UserRepository
from app.schemas.user import UserOut, DispositivoPublic
from database import get_db

router = APIRouter(tags=["Usuarios"])


# ─── Público: lista de dispositivos activos (para el select de registro) ──────
@router.get(
    "/dispositivos/",
    response_model=List[DispositivoPublic],
    summary="Listar Dispositivos CBC activos",
    description="Retorna todos los Dispositivos CBC aprobados. Sin autenticación.",
)
def list_dispositivos(db: Session = Depends(get_db)):
    repo = UserRepository(db)
    return repo.get_all_dispositivos_activos()


# ─── Perfil del usuario autenticado ──────────────────────────────────────────
@router.get(
    "/users/me",
    response_model=UserOut,
    summary="Mi perfil",
)
def get_me(current_user: User = Depends(get_current_user)):
    return current_user


# ─── Admin: ver pendientes de aprobación ─────────────────────────────────────
@router.get(
    "/admin/pendientes",
    response_model=List[UserOut],
    summary="Ver Dispositivos CBC pendientes (solo Admin)",
)
def get_pendientes_admin(
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(UserRole.ADMIN)),
):
    repo = UserRepository(db)
    return repo.get_pending_by_role(UserRole.DISPOSITIVO)


# ─── Dispositivo: ver prescriptores pendientes ───────────────────────────────
@router.get(
    "/dispositivo/pendientes",
    response_model=List[UserOut],
    summary="Ver Prescriptxres pendientes (solo Dispositivo CBC)",
)
def get_pendientes_dispositivo(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.DISPOSITIVO)),
):
    repo = UserRepository(db)
    # Solo los que eligieron este dispositivo
    pendientes = repo.get_pending_by_role(UserRole.PRESCRIPTOR)
    return [p for p in pendientes if p.dispositivo_id == current_user.id]


# ─── Prescriptor: ver beneficiarixs pendientes ───────────────────────────────
@router.get(
    "/prescriptor/pendientes",
    response_model=List[UserOut],
    summary="Ver Beneficiarixs pendientes (solo Prescriptxr)",
)
def get_pendientes_prescriptor(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.PRESCRIPTOR)),
):
    repo = UserRepository(db)
    pendientes = repo.get_pending_by_role(UserRole.BENEFICIARIO)
    # Filtra los que están en el mismo dispositivo que este prescriptor
    return [p for p in pendientes]


# ─── Aprobar usuario (cualquier aprobador con el rol correcto) ────────────────
@router.patch(
    "/users/{user_id}/aprobar",
    response_model=UserOut,
    summary="Aprobar un usuario pendiente",
)
def aprobar_usuario(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    from app.models.user import UserStatus
    from app.services.auth_service import APPROVAL_RULES

    repo = UserRepository(db)
    target = repo.get_by_id(user_id)

    if not target:
        raise HTTPException(404, detail="Usuario no encontrado")

    if target.status != UserStatus.PENDIENTE:
        raise HTTPException(400, detail="Este usuario no está pendiente")

    # Verificar que el aprobador tenga el rol correcto
    expected_approver_role = APPROVAL_RULES.get(target.rol)
    if current_user.rol != expected_approver_role:
        raise HTTPException(
            403,
            detail=f"Solo un {expected_approver_role.value} puede aprobar este rol",
        )

    return repo.approve(user_id, current_user.id)