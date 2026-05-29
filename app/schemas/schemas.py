"""
Schemas Pydantic para request / response de la API MASCATE.
"""

from datetime import datetime, date
from typing import Optional, List, Literal
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
    usuario_id: Optional[int] = None
    nombre: str
    lugar_actividades: Optional[str] = None
    ubicacion: Optional[str] = None
    tipo_servicio: Optional[str] = None
    dia_actividad: Optional[str] = None
    hora_actividad: Optional[str] = None
    telefono: Optional[str] = None
    redes_sociales: Optional[str] = None
    descripcion: Optional[str] = None
    capacidad: Optional[int] = None
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
    descripcion: Optional[str] = None
    capacidad: Optional[int] = None


class DispositivoEstadisticas(BaseModel):
    beneficiarios_activos: int
    actividades_registradas: int
    seguimientos_semana: int


class BeneficiarioResumen(BaseModel):
    id: int
    nombre_apodo: str

    class Config:
        from_attributes = True


# ════════════════════ BENEFICIARIO ════════════════════

class BeneficiarioMe(BaseModel):
    id: int
    nombre_apodo: str
    email: str
    fecha_registro: datetime
    fecha_nacimiento: Optional[date] = None
    localidad:        Optional[str] = None
    telefono:         Optional[str] = None
    descripcion:      Optional[str] = None
    genero:           Optional[str] = None
    dispositivo_id:     Optional[int] = None   # ← agregar
    dispositivo_nombre: Optional[str] = None   # ← agregar

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
    dispositivo_id: Optional[int] = None
    descripcion: Optional[str] = None
    cupo_maximo: Optional[int] = None
    fecha_inicio: Optional[date] = None


class ActividadUpdate(BaseModel):
    nombre: Optional[str] = None
    tipo: Optional[str] = None
    lugar: Optional[str] = None
    dia_semana: Optional[str] = None
    hora: Optional[str] = None
    emoji: Optional[str] = None
    activa: Optional[bool] = None
    descripcion: Optional[str] = None
    cupo_maximo: Optional[int] = None
    fecha_inicio: Optional[date] = None


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
    descripcion: Optional[str] = None
    cupo_maximo: Optional[int] = None
    fecha_inicio: Optional[date] = None

    class Config:
        from_attributes = True


# ════════════════════ PRESCRIPTOR / SEGUIMIENTOS ════════════════════

class AsignadoOut(BaseModel):
    id: int
    nombre_apodo: str
    ultima_sesion: Optional[datetime] = None
    dias_sin_sesion: Optional[int] = None
    estado: str
    localidad:        Optional[str] = None
    telefono:         Optional[str] = None
    fecha_nacimiento: Optional[date] = None
    dispositivo_id:   Optional[int] = None


class SeguimientoCreate(BaseModel):
    beneficiario_id: int
    tipo_registro: str
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
    status: str
    fecha_registro: datetime
    nombre: Optional[str] = None
    fecha_nacimiento: Optional[date] = None
    localidad:        Optional[str] = None
    telefono:         Optional[str] = None
    descripcion:      Optional[str] = None
    genero:           Optional[str] = None

    class Config:
        from_attributes = True


class CambiarEstado(BaseModel):
    status: Literal["pendiente", "activo", "inactivo"]


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
    email: Optional[str] = None
    fecha_registro: Optional[datetime] = None
    num_actividades: Optional[int] = None
    asistencia_pct: Optional[float] = None

    class Config:
        from_attributes = True


class AdminDispositivoCreate(BaseModel):
    email: EmailStr
    nombre: str
    lugar_actividades: Optional[str] = None
    ubicacion: Optional[str] = None
    tipo_servicio: Optional[str] = None
    dia_actividad: Optional[str] = None
    hora_actividad: Optional[str] = None
    telefono: Optional[str] = None
    redes_sociales: Optional[str] = None

# ════════════════════ PRESCRIPTOR ME ════════════════════

class PrescriptorMe(BaseModel):
    id: int
    nombre_completo: str
    perfil_disciplina: Optional[str] = None
    telefono: Optional[str] = None
    email: str
    dispositivo_id: Optional[int] = None
    dispositivo_nombre: Optional[str] = None
    fecha_registro: datetime

    class Config:
        from_attributes = True


class PrescriptorUpdate(BaseModel):
    nombre_completo: Optional[str] = None
    perfil_disciplina: Optional[str] = None
    telefono: Optional[str] = None


class BeneficiarioUpdate(BaseModel):
    nombre_apodo: Optional[str] = None
    telefono: Optional[str] = None
    localidad: Optional[str] = None
    fecha_nacimiento: Optional[date] = None
    genero: Optional[str] = None
    descripcion: Optional[str] = None


class InscripcionRequest(BaseModel):
    actividad_id: int


class InscripcionResponse(BaseModel):
    mensaje: str
    actividad_id: int
# ════════════════════ AUTH EXTRA ════════════════════

class CambiarPasswordRequest(BaseModel):
    password_actual: str
    password_nueva: str


class CambiarRolRequest(BaseModel):
    rol: Literal["beneficiario", "prescriptor", "dispositivo", "admin"]