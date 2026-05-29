from typing import Optional
from datetime import datetime
from pydantic import BaseModel


class UserOut(BaseModel):
    id: int
    email: str
    rol: str
    status: str
    nombre: Optional[str] = None
    nombre_completo: Optional[str] = None
    nombre_apodo: Optional[str] = None
    lugar_actividades: Optional[str] = None
    ubicacion: Optional[str] = None
    tipo_servicio: Optional[str] = None
    perfil_disciplina: Optional[str] = None
    telefono: Optional[str] = None
    dispositivo_id: Optional[int] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class DispositivoPublic(BaseModel):
    """Vista pública de dispositivos para el selector de registro."""
    id: int
    nombre: Optional[str] = None
    ubicacion: Optional[str] = None
    tipo_servicio: Optional[str] = None

    model_config = {"from_attributes": True}