from sqlalchemy.orm import Session
from app.models.models import EstadoRegistro
from app.repositories.estado_repository import EstadoRepository # Ajusta la ruta según tu proyecto

class EstadoService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = EstadoRepository(db)

    def cambiar_estado(self, entidad_obj, nuevo_estado: str, admin_id: int, motivo: str = None):
        """
        Orquestador para cambiar el estado de cualquier entidad 
        y mantener la integridad de la auditoría.
        """
        # 1. Registrar en la tabla de auditoría
        # Usamos __tablename__ para identificar el tipo de entidad dinámicamente
        registro = self.repo.registrar_cambio(
            entidad_tipo=entidad_obj.__tablename__,
            entidad_id=entidad_obj.id,
            nuevo_estado=nuevo_estado,
            cambiado_por=admin_id,
            motivo=motivo
        )

        # 2. Actualizar el puntero en la entidad principal
        entidad_obj.estado_actual_id = registro.id
        
        self.db.add(entidad_obj)
        self.db.commit()
        self.db.refresh(entidad_obj)
        
        return entidad_obj