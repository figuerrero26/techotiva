"""
Repositorio para EstadoRegistro.
Toda la lógica de cambio de estado pasa por aquí.
"""

from datetime import datetime, timezone
from typing import Optional, List

from sqlalchemy.orm import Session

from app.models.models import EstadoRegistro, Estados


class EstadoRepository:

    def __init__(self, db: Session):
        self.db = db

    def registrar_cambio(
        self,
        entidad_tipo: str,
        entidad_id: int,
        nuevo_estado: str,
        cambiado_por: int,
        motivo: Optional[str] = None,
    ) -> EstadoRegistro:
        """
        Crea un nuevo registro en el historial y devuelve el objeto.
        El caller es responsable de actualizar estado_actual_id en la entidad.
        """
        registro = EstadoRegistro(
            entidad_tipo=entidad_tipo,
            entidad_id=entidad_id,
            estado=nuevo_estado,
            cambiado_por=cambiado_por,
            motivo=motivo,
            fecha=datetime.now(timezone.utc),
        )
        self.db.add(registro)
        self.db.flush()   # obtiene el id sin hacer commit todavía
        return registro

    def historial(
        self,
        entidad_tipo: str,
        entidad_id: int,
    ) -> List[EstadoRegistro]:
        """Devuelve el historial completo de estados, del más reciente al más antiguo."""
        return (
            self.db.query(EstadoRegistro)
            .filter(
                EstadoRegistro.entidad_tipo == entidad_tipo,
                EstadoRegistro.entidad_id == entidad_id,
            )
            .order_by(EstadoRegistro.fecha.desc())
            .all()
        )

    def estado_actual(
        self,
        entidad_tipo: str,
        entidad_id: int,
    ) -> Optional[str]:
        """Consulta rápida sin cargar la entidad completa."""
        ultimo = (
            self.db.query(EstadoRegistro)
            .filter(
                EstadoRegistro.entidad_tipo == entidad_tipo,
                EstadoRegistro.entidad_id == entidad_id,
            )
            .order_by(EstadoRegistro.fecha.desc())
            .first()
        )
        return ultimo.estado if ultimo else Estados.PENDIENTE