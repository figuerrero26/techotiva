"""
Schemas Pydantic para request / response de la API MASCATE.
"""

from datetime import datetime, date
from typing import Optional, List
from pydantic import BaseModel, EmailStr


# ════════════════════ AUTH ════════════════════

class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    rol: str
    nombre: str


class RegisterRequest(BaseModel):
    rol: str
    email: EmailStr
    password: str
    # dispositivo
    nombre: Optional[str] = None
    lugar_actividades: Optional[str] = None
    ubicacion: Optional[str] = None
    tipo_servicio: Optional[str] = None
    dia_actividad: Optional[str] = None
    hora_actividad: Optional[str] = None
    telefono: Optional[str] = None
    redes_sociales: Optional[str] = None
    # prescriptor
    nombre_completo: Optional[str] = None
    perfil_disciplina: Optional[str] = None
    dispositivo_id: Optional[int] = None
    # beneficiario
    nombre_apodo: Optional[str] = None


class RegisterResponse(BaseModel):
    message: str
    usuario_id: int
    rol: str


# ════════════════════ DISPOSITIVO ════════════════════

class DispositivoOut(BaseModel):
    id: int
    nombre: str
    lugar_actividades: Optional[str] = None
    ubicacion: Optional[str] = None
    tipo_servicio: Optional[str] = None
    dia_actividad: Optional[str] = None
    hora_actividad: Optional[str] = None
    telefono: Optional[str] = None
    redes_sociales: Optional[str] = None
    activo: bool = True

    class Config:
        from_attributes = True


class DispositivoUpdate(BaseModel):
    nombre: Optional[str] = None
    lugar_actividades: Optional[str] = None
    ubicacion: Optional[str] = None
    tipo_servicio: Optional[str] = None
    dia_actividad: Optional[str] = None
    hora_actividad: Optional[str] = None
    telefono: Optional[str] = None
    redes_sociales: Optional[str] = None


class DispositivoEstadisticas(BaseModel):
    beneficiarios_activos: int
    actividades_registradas: int
    seguimientos_semana: int


class BeneficiarioResumen(BaseModel):
    id: int
    nombre_apodo: str

    class Config:
        from_attributes = True


# ════════════════════ ACTIVIDAD ════════════════════

class ActividadCreate(BaseModel):
    nombre: str
    tipo: Optional[str] = None
    lugar: Optional[str] = None
    dia_semana: Optional[str] = None
    hora: Optional[str] = None
    emoji: Optional[str] = "📋"
    dispositivo_id: Optional[int] = None  # se toma del token si no se envía


class ActividadUpdate(BaseModel):
    nombre: Optional[str] = None
    tipo: Optional[str] = None
    lugar: Optional[str] = None
    dia_semana: Optional[str] = None
    hora: Optional[str] = None
    emoji: Optional[str] = None
    activa: Optional[bool] = None


class ActividadOut(BaseModel):
    id: int
    dispositivo_id: int
    nombre: str
    tipo: Optional[str] = None
    lugar: Optional[str] = None
    dia_semana: Optional[str] = None
    hora: Optional[str] = None
    emoji: Optional[str] = None
    activa: bool = True

    class Config:
        from_attributes = True


# ════════════════════ PRESCRIPTOR / SEGUIMIENTOS ════════════════════

class AsignadoOut(BaseModel):
    id: int
    nombre_apodo: str
    ultima_sesion: Optional[datetime] = None
    dias_sin_sesion: Optional[int] = None
    estado: str  # al_dia | revisar | urgente


class SeguimientoCreate(BaseModel):
    beneficiario_id: int
    tipo_registro: str   # sesión grupal / seguimiento individual / actividad especial
    observaciones: Optional[str] = None


class SeguimientoOut(BaseModel):
    id: int
    prescriptor_id: int
    beneficiario_id: int
    tipo_registro: Optional[str] = None
    observaciones: Optional[str] = None
    fecha: datetime
    nombre_beneficiario: Optional[str] = None

    class Config:
        from_attributes = True


# ════════════════════ BENEFICIARIO ════════════════════

class BeneficiarioMe(BaseModel):
    id: int
    nombre_apodo: str
    email: str
    fecha_registro: datetime

    class Config:
        from_attributes = True


# ════════════════════ ADMIN ════════════════════

class AdminStats(BaseModel):
    total_dispositivos: int
    total_usuarios: int
    total_prescriptores: int
    total_beneficiarios: int
    alertas_pendientes: int


class UsuarioAdmin(BaseModel):
    id: int
    email: str
    rol: str
    activo: bool
    fecha_registro: datetime
    nombre: Optional[str] = None

    class Config:
        from_attributes = True


class CambiarEstado(BaseModel):
    activo: bool


class AlertaOut(BaseModel):
    dispositivo_id: int
    dispositivo: str
    mensaje: str
    dias_sin_actividad: int


class AdminDispositivoOut(BaseModel):
    id: int
    nombre: str
    tipo_servicio: Optional[str] = None
    num_beneficiarios: int
    prescriptor: Optional[str] = None
    activo: bool


class AdminDispositivoCreate(BaseModel):
    email: EmailStr
    password: str
    nombre: str
    lugar_actividades: Optional[str] = None
    ubicacion: Optional[str] = None
    tipo_servicio: Optional[str] = None
    dia_actividad: Optional[str] = None
    hora_actividad: Optional[str] = None
    telefono: Optional[str] = None
    redes_sociales: Optional[str] = None
