from typing import Optional, List
from sqlalchemy.orm import Session

from app.models.models import (
    Usuario, Dispositivo, Prescriptor,
    EstadoRegistro, Estados, TipoEntidad,
)
from app.repositories.estado_repo import EstadoRepository
from app.core.security import hash_password


class UserRepository:

    def __init__(self, db: Session):
        self.db = db
        self._estado_repo = EstadoRepository(db)

    # ── Lecturas ───────────────────────────────────────────────────────────
    def get_by_id(self, user_id: int) -> Optional[Usuario]:
        return self.db.query(Usuario).filter(Usuario.id == user_id).first()

    def get_by_email(self, email: str) -> Optional[Usuario]:
        return self.db.query(Usuario).filter(Usuario.email == email).first()

    def get_all_dispositivos_activos(self) -> List[Usuario]:
        return (
            self.db.query(Usuario)
            .join(EstadoRegistro, Usuario.estado_actual_id == EstadoRegistro.id)
            .filter(
                Usuario.rol == "dispositivo",
                EstadoRegistro.estado == Estados.ACTIVO,
            )
            .all()
        )

    def get_pending_by_role(self, rol: str) -> List[Usuario]:
        """Usuarios sin estado_actual_id (jamás procesados) o con estado pendiente."""
        sin_estado = (
            self.db.query(Usuario)
            .filter(Usuario.rol == rol, Usuario.estado_actual_id.is_(None))
            .all()
        )
        con_pendiente = (
            self.db.query(Usuario)
            .join(EstadoRegistro, Usuario.estado_actual_id == EstadoRegistro.id)
            .filter(Usuario.rol == rol, EstadoRegistro.estado == Estados.PENDIENTE)
            .all()
        )
        return sin_estado + con_pendiente

    # ── Escrituras ─────────────────────────────────────────────────────────
    def create(self, **kwargs) -> Usuario:
        """Crea el usuario. Estado inicial = pendiente (sin estado_actual_id)."""
        kwargs.pop("status", None)   # elimina campo legacy si viene
        kwargs.pop("activo", None)   # elimina campo legacy si viene
        user = Usuario(**kwargs)
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user

    def _cambiar_estado_usuario(
        self,
        user_id: int,
        nuevo_estado: str,
        admin_id: int,
        motivo: Optional[str] = None,
    ) -> Optional[Usuario]:
        user = self.get_by_id(user_id)
        if not user:
            return None
        registro = self._estado_repo.registrar_cambio(
            entidad_tipo=TipoEntidad.USUARIO,
            entidad_id=user_id,
            nuevo_estado=nuevo_estado,
            cambiado_por=admin_id,
            motivo=motivo,
        )
        user.estado_actual_id = registro.id
        self.db.commit()
        self.db.refresh(user)
        return user

    def approve(self, user_id: int, approver_id: int, motivo: str = "Aprobado por admin") -> Optional[Usuario]:
        return self._cambiar_estado_usuario(user_id, Estados.ACTIVO, approver_id, motivo)

    def deactivate(self, user_id: int, admin_id: int, motivo: str = "Desactivado por admin") -> Optional[Usuario]:
        return self._cambiar_estado_usuario(user_id, Estados.INACTIVO, admin_id, motivo)

    def reject(self, user_id: int, admin_id: int, motivo: Optional[str] = None) -> Optional[Usuario]:
        return self._cambiar_estado_usuario(user_id, Estados.RECHAZADO, admin_id, motivo)

    def suspend(self, user_id: int, admin_id: int, motivo: Optional[str] = None) -> Optional[Usuario]:
        return self._cambiar_estado_usuario(user_id, Estados.SUSPENDIDO, admin_id, motivo)

    def historial_estados(self, user_id: int):
        return self._estado_repo.historial(TipoEntidad.USUARIO, user_id)