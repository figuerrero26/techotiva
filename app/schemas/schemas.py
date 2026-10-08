"""
Schemas Pydantic para request / response de la API MASCATE.
"""

from datetime import datetime, date, time
from typing import Optional, List, Literal
from pydantic import BaseModel, EmailStr


# ════════════════════ AUTH ════════════════════

class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    rol: str
    nombre: str
    user_id: int


class RegisterResponse(BaseModel):
    message: str
    user_id: int
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
    email: Optional[str] = None
    genero: Optional[str] = None
    fecha_nacimiento: Optional[date] = None
    localidad: Optional[str] = None
    telefono: Optional[str] = None
    status: Optional[str] = None

    class Config:
        from_attributes = True


# ════════════════════ BENEFICIARIO ════════════════════

class BeneficiarioMe(BaseModel):
    id: int
    nombre_apodo: str
    email: str
    fecha_registro: datetime
    fecha_nacimiento: Optional[date] = None
    localidad: Optional[str] = None
    telefono: Optional[str] = None
    descripcion: Optional[str] = None
    genero: Optional[str] = None
    dispositivo_id: Optional[int] = None
    dispositivo_nombre: Optional[str] = None
    prescriptor_id: Optional[int] = None
    prescriptor_nombre: Optional[str] = None
    # Perfil sociodemográfico
    estado_civil: Optional[str] = None
    num_hijos: Optional[int] = None
    etnia: Optional[str] = None
    con_quien_vive: Optional[str] = None
    direccion: Optional[str] = None
    escolaridad: Optional[str] = None
    ocupacion: Optional[str] = None
    sabe_leer_escribir: Optional[bool] = None
    sabe_usar_computador: Optional[bool] = None
    nombre_persona_apoyo: Optional[str] = None
    telefono_persona_apoyo: Optional[str] = None
    vinculo_persona_apoyo: Optional[str] = None
    apoyo_familiar: Optional[bool] = None
    apoyo_comunitario: Optional[bool] = None
    apoyo_institucional: Optional[bool] = None
    apoyo_actor_social: Optional[str] = None
    practica_deporte: Optional[bool] = None

    class Config:
        from_attributes = True


class BeneficiarioUpdate(BaseModel):
    nombre_apodo: Optional[str] = None
    telefono: Optional[str] = None
    localidad: Optional[str] = None
    fecha_nacimiento: Optional[date] = None
    genero: Optional[str] = None
    descripcion: Optional[str] = None
    dispositivo_id: Optional[int] = None
    # Perfil sociodemográfico
    estado_civil: Optional[str] = None
    num_hijos: Optional[int] = None
    etnia: Optional[str] = None
    con_quien_vive: Optional[str] = None
    direccion: Optional[str] = None
    escolaridad: Optional[str] = None
    ocupacion: Optional[str] = None
    sabe_leer_escribir: Optional[bool] = None
    sabe_usar_computador: Optional[bool] = None
    nombre_persona_apoyo: Optional[str] = None
    telefono_persona_apoyo: Optional[str] = None
    vinculo_persona_apoyo: Optional[str] = None
    apoyo_familiar: Optional[bool] = None
    apoyo_comunitario: Optional[bool] = None
    apoyo_institucional: Optional[bool] = None
    apoyo_actor_social: Optional[str] = None
    practica_deporte: Optional[bool] = None


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
    dispositivo_nombre: Optional[str] = None
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
    total_inscritos: int = 0

    class Config:
        from_attributes = True


# ════════════════════ PRESCRIPTOR / SEGUIMIENTOS ════════════════════

class AsignadoOut(BaseModel):
    id: int
    nombre_apodo: str
    ultima_sesion: Optional[datetime] = None
    dias_sin_sesion: Optional[int] = None
    estado: str
    email: Optional[str] = None
    telefono: Optional[str] = None


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
    nombre_prescriptor: Optional[str] = None

    class Config:
        from_attributes = True


class PrescriptorMe(BaseModel):
    id: int
    nombre_completo: str
    perfil_disciplina: Optional[str] = None
    telefono: Optional[str] = None
    email: str
    dispositivo_id: Optional[int] = None
    dispositivo_nombre: Optional[str] = None
    solicitud_dispositivo_id: Optional[int] = None
    solicitud_dispositivo_nombre: Optional[str] = None
    fecha_registro: datetime

    class Config:
        from_attributes = True


class PrescriptorUpdate(BaseModel):
    nombre_completo: Optional[str] = None
    perfil_disciplina: Optional[str] = None
    telefono: Optional[str] = None


class PrescriptorResumen(BaseModel):
    id: int
    nombre_completo: str
    perfil_disciplina: Optional[str] = None
    telefono: Optional[str] = None
    email: str
    status: str

    class Config:
        from_attributes = True


# ════════════════════ ADMIN ════════════════════

class AdminStats(BaseModel):
    total_dispositivos: int
    total_usuarios: int
    total_prescriptores: int
    total_beneficiarios: int
    alertas_pendientes: int
    total_actividades: int = 0


class UsuarioAdmin(BaseModel):
    id: int
    email: str
    rol: str
    status: str
    fecha_registro: datetime
    nombre: Optional[str] = None
    fecha_nacimiento: Optional[date] = None
    localidad: Optional[str] = None
    telefono: Optional[str] = None
    descripcion: Optional[str] = None
    genero: Optional[str] = None
    prescriptor_nombre: Optional[str] = None
    dispositivo_nombre: Optional[str] = None
    prescriptor_id: Optional[int] = None
    dispositivo_id: Optional[int] = None
    beneficiario_id: Optional[int] = None
    perfil_disciplina: Optional[str] = None
    politica_privacidad_at: Optional[datetime] = None
    proceso_finalizado: bool = False

    class Config:
        from_attributes = True


class CambiarEstado(BaseModel):
    status: Literal["pendiente", "activo", "inactivo", "rechazado"]


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
    prescriptores: List[str] = []
    activo: bool
    email: Optional[str] = None
    fecha_registro: Optional[datetime] = None
    num_actividades: Optional[int] = None
    asistencia_pct: Optional[float] = None
    lugar_actividades: Optional[str] = None
    ubicacion: Optional[str] = None
    dia_actividad: Optional[str] = None
    hora_actividad: Optional[str] = None
    telefono: Optional[str] = None
    redes_sociales: Optional[str] = None

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


# ════════════════════ PRIMER CONTACTO ════════════════════

# Campos compartidos entre Create y SinCuenta
class _PCBase(BaseModel):
    dispositivo_id:      int
    # Convenio
    convenio_515:        Optional[str] = None
    tipo_dbc:            Optional[str] = None
    politica_privacidad: Optional[str] = None
    numero_caso:         Optional[str] = None
    # Evento
    fecha_contacto:      Optional[date] = None
    hora_contacto:       Optional[str]  = None
    upz:                 Optional[str]  = None
    barrio:              Optional[str]  = None
    forma_contacto:      Optional[str]  = None
    # Fuente
    nombre_fuente:       Optional[str]  = None
    telefono_fuente:     Optional[str]  = None
    genero_fuente:       Optional[str]  = None
    vinculo_fuente:      Optional[str]  = None
    # Edad
    edad_benef:          Optional[int]  = None
    # Dirección
    clase_via:                Optional[str] = None
    numero_via_principal:     Optional[str] = None
    letra_via_principal:      Optional[str] = None
    identificador_sector:     Optional[str] = None
    numero_via_generadora:    Optional[str] = None
    letra_via_generadora:     Optional[str] = None
    numero_predio:            Optional[str] = None
    otras_caracteristicas_dir: Optional[str] = None
    # Situación
    situaciones_presentes: Optional[str] = None
    peticiones:            Optional[str] = None
    descripcion_caso:      Optional[str] = None
    procesos_previos:      Optional[int] = 0
    # Registrador
    rol_registrador:      Optional[str] = None
    nombre_registrador:   Optional[str] = None
    telefono_registrador: Optional[str] = None
    # Datos demográficos del beneficiario (actualizan el registro Beneficiario)
    genero:                   Optional[str]  = None
    telefono:                 Optional[str]  = None
    fecha_nacimiento:         Optional[str]  = None
    localidad:                Optional[str]  = None
    estado_civil:             Optional[str]  = None
    num_hijos:                Optional[int]  = None
    etnia:                    Optional[str]  = None
    pertenencia_etnica:       Optional[str]  = None
    religion:                 Optional[str]  = None
    con_quien_vive:           Optional[str]  = None
    sabe_leer_escribir:       Optional[bool] = None
    sabe_usar_computador:     Optional[bool] = None
    escolaridad:              Optional[str]  = None
    ocupacion:                Optional[str]  = None
    apoyo_familiar:           Optional[bool] = None
    apoyo_comunitario:        Optional[bool] = None
    apoyo_institucional:      Optional[bool] = None
    apoyo_otro_actor:         Optional[bool] = None
    cual_actor_social:        Optional[str]  = None
    practica_deporte:         Optional[bool] = None
    tiene_tiempo_recreacion:  Optional[bool] = None
    cuanto_tiempo_recreacion: Optional[str]  = None
    conoce_espacios:          Optional[str]  = None
    ha_participado:           Optional[str]  = None
    tiene_persona_apoyo:      Optional[bool] = None
    nombre_persona_apoyo:     Optional[str]  = None
    telefono_persona_apoyo:   Optional[str]  = None
    vinculo_persona_apoyo:    Optional[str]  = None
    tipo_vinculo_codigo:      Optional[str]  = None
    genero_apoyo:             Optional[str]  = None


class PrimerContactoCreate(_PCBase):
    beneficiario_id: int


class PrimerContactoOut(BaseModel):
    id: int
    beneficiario_id: int
    dispositivo_id: int
    prescriptor_id: Optional[int] = None
    created_at:      Optional[datetime] = None
    # Convenio
    convenio_515:        Optional[str]  = None
    tipo_dbc:            Optional[str]  = None
    politica_privacidad: Optional[str]  = None
    numero_caso:         Optional[str]  = None
    # Evento
    fecha_contacto:  Optional[date] = None
    hora_contacto:   Optional[str]  = None
    upz:             Optional[str]  = None
    barrio:          Optional[str]  = None
    forma_contacto:  Optional[str]  = None
    # Fuente
    nombre_fuente:   Optional[str]  = None
    telefono_fuente: Optional[str]  = None
    genero_fuente:   Optional[str]  = None
    vinculo_fuente:  Optional[str]  = None
    edad_benef:      Optional[int]  = None
    # Dirección
    clase_via:                 Optional[str] = None
    numero_via_principal:      Optional[str] = None
    letra_via_principal:       Optional[str] = None
    identificador_sector:      Optional[str] = None
    numero_via_generadora:     Optional[str] = None
    letra_via_generadora:      Optional[str] = None
    numero_predio:             Optional[str] = None
    otras_caracteristicas_dir: Optional[str] = None
    # Situación
    situaciones_presentes: Optional[str] = None
    peticiones:            Optional[str] = None
    descripcion_caso:      Optional[str] = None
    procesos_previos:      Optional[int] = None
    # Registrador
    rol_registrador:      Optional[str] = None
    nombre_registrador:   Optional[str] = None
    telefono_registrador: Optional[str] = None
    # Beneficiario (denormalizado)
    nombre_beneficiario:      Optional[str]  = None
    fecha_nacimiento:         Optional[date] = None
    genero:                   Optional[str]  = None
    telefono:                 Optional[str]  = None
    localidad:                Optional[str]  = None
    estado_civil:             Optional[str]  = None
    num_hijos:                Optional[int]  = None
    etnia:                    Optional[str]  = None
    pertenencia_etnica:       Optional[str]  = None
    religion:                 Optional[str]  = None
    con_quien_vive:           Optional[str]  = None
    sabe_leer_escribir:       Optional[bool] = None
    sabe_usar_computador:     Optional[bool] = None
    escolaridad:              Optional[str]  = None
    ocupacion:                Optional[str]  = None
    apoyo_familiar:           Optional[bool] = None
    apoyo_comunitario:        Optional[bool] = None
    apoyo_institucional:      Optional[bool] = None
    apoyo_otro_actor:         Optional[bool] = None
    cual_actor_social:        Optional[str]  = None
    practica_deporte:         Optional[bool] = None
    tiene_tiempo_recreacion:  Optional[bool] = None
    cuanto_tiempo_recreacion: Optional[str]  = None
    conoce_espacios:          Optional[str]  = None
    ha_participado:           Optional[str]  = None
    tiene_persona_apoyo:      Optional[bool] = None
    nombre_persona_apoyo:     Optional[str]  = None
    telefono_persona_apoyo:   Optional[str]  = None
    vinculo_persona_apoyo:    Optional[str]  = None
    tipo_vinculo_codigo:      Optional[str]  = None
    genero_apoyo:             Optional[str]  = None

    class Config:
        from_attributes = True


# ════════════════════ AUTH EXTRA ════════════════════

class CambiarPasswordRequest(BaseModel):
    password_actual: str
    password_nueva: str


class CambiarRolRequest(BaseModel):
    rol: Literal["beneficiario", "prescriptor", "dispositivo", "admin"]


# ════════════════════ INSCRIPCIONES ════════════════════

class InscripcionRequest(BaseModel):
    actividad_id: int


class InscripcionResponse(BaseModel):
    mensaje: str
    actividad_id: int
