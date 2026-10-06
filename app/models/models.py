from datetime import datetime, timezone
from sqlalchemy import (
    Column, Integer, String, Boolean, Text,
    DateTime, ForeignKey, Date, Time, func,
)
from sqlalchemy.orm import relationship
from database import Base


# ── Valores válidos de estado ──────────────────────────────────────────────
class Estados:
    PENDIENTE  = "pendiente"
    ACTIVO     = "activo"
    INACTIVO   = "inactivo"
    RECHAZADO  = "rechazado"
    SUSPENDIDO = "suspendido"


# ── Tipos de entidad ───────────────────────────────────────────────────────
class TipoEntidad:
    USUARIO      = "usuario"
    DISPOSITIVO  = "dispositivo"
    PRESCRIPTOR  = "prescriptor"
    BENEFICIARIO = "beneficiario"


# ── ESTADO REGISTRO (tabla de auditoría universal) ─────────────────────────
class EstadoRegistro(Base):
    """
    Cada fila representa UN cambio de estado sobre UNA entidad.
    Para saber el estado actual:
        SELECT * FROM estado_registro
        WHERE entidad_tipo = 'usuario' AND entidad_id = X
        ORDER BY fecha DESC LIMIT 1;
    """
    __tablename__ = "estado_registro"

    id           = Column(Integer, primary_key=True, index=True)
    entidad_tipo = Column(String(30), nullable=False, index=True)
    entidad_id   = Column(Integer, nullable=False, index=True)
    estado       = Column(String(20), nullable=False)
    cambiado_por = Column(Integer, ForeignKey("usuarios.id"), nullable=True)
    motivo       = Column(Text, nullable=True)
    fecha        = Column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)

    admin = relationship("Usuario", foreign_keys=[cambiado_por])


# ── USUARIOS ───────────────────────────────────────────────────────────────
class Usuario(Base):
    __tablename__ = "usuarios"

    id               = Column(Integer, primary_key=True, index=True)
    email            = Column(String(255), unique=True, nullable=False, index=True)
    password_hash    = Column(String(255), nullable=False)
    rol              = Column(String(20), nullable=False)
    estado_actual_id = Column(Integer, ForeignKey("estado_registro.id"), nullable=True)
    fecha_registro   = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    email_verificado     = Column(Boolean, default=False)
    email_token          = Column(String(100), nullable=True)
    password_reset_token        = Column(String(100), nullable=True)
    password_reset_token_expiry = Column(DateTime, nullable=True)
    politica_privacidad_at      = Column(DateTime, nullable=True)

    estado_actual = relationship(
        "EstadoRegistro",
        foreign_keys=[estado_actual_id],
        lazy="joined",
    )

    dispositivo  = relationship("Dispositivo",  back_populates="usuario", uselist=False)
    prescriptor  = relationship("Prescriptor",  back_populates="usuario", uselist=False)
    beneficiario = relationship("Beneficiario", back_populates="usuario", uselist=False)

    @property
    def estado(self) -> str:
        if self.estado_actual:
            return self.estado_actual.estado
        return Estados.PENDIENTE

    @property
    def activo(self) -> bool:
        return self.estado == Estados.ACTIVO


# ── DISPOSITIVOS ───────────────────────────────────────────────────────────
class Dispositivo(Base):
    __tablename__ = "dispositivos"

    id                = Column(Integer, primary_key=True, index=True)
    usuario_id        = Column(Integer, ForeignKey("usuarios.id"), nullable=False, unique=True)
    nombre            = Column(String(200), nullable=False)
    lugar_actividades = Column(String(100))
    ubicacion         = Column(String(300))
    tipo_servicio     = Column(String(100))
    dia_actividad     = Column(String(100))
    hora_actividad    = Column(String(20))
    telefono          = Column(String(30))
    redes_sociales    = Column(String(300))
    estado_actual_id  = Column(Integer, ForeignKey("estado_registro.id"), nullable=True)
    descripcion       = Column(Text, nullable=True)
    capacidad         = Column(Integer, nullable=True)

    estado_actual      = relationship("EstadoRegistro", foreign_keys=[estado_actual_id], lazy="joined")
    usuario            = relationship("Usuario", back_populates="dispositivo")
    actividades        = relationship("Actividad", back_populates="dispositivo", cascade="all, delete-orphan")
    prescriptores      = relationship("Prescriptor", foreign_keys="[Prescriptor.dispositivo_id]", back_populates="dispositivo")
    primeros_contactos = relationship("PrimerContacto", back_populates="dispositivo")

    @property
    def estado(self) -> str:
        if self.estado_actual:
            return self.estado_actual.estado
        return Estados.PENDIENTE


# ── PRESCRIPTORES ──────────────────────────────────────────────────────────
class Prescriptor(Base):
    __tablename__ = "prescriptores"

    id                = Column(Integer, primary_key=True, index=True)
    usuario_id        = Column(Integer, ForeignKey("usuarios.id"), nullable=False, unique=True)
    nombre_completo   = Column(String(200), nullable=False)
    perfil_disciplina = Column(String(100))
    telefono          = Column(String(30))
    dispositivo_id           = Column(Integer, ForeignKey("dispositivos.id"), nullable=True)
    solicitud_dispositivo_id = Column(Integer, ForeignKey("dispositivos.id"), nullable=True)
    estado_actual_id         = Column(Integer, ForeignKey("estado_registro.id"), nullable=True)

    estado_actual        = relationship("EstadoRegistro", foreign_keys=[estado_actual_id], lazy="joined")
    usuario              = relationship("Usuario", back_populates="prescriptor")
    dispositivo          = relationship("Dispositivo", foreign_keys=[dispositivo_id], back_populates="prescriptores")
    dispositivo_solicitud = relationship("Dispositivo", foreign_keys=[solicitud_dispositivo_id])
    seguimientos  = relationship("Seguimiento", back_populates="prescriptor", cascade="all, delete-orphan")

    @property
    def estado(self) -> str:
        if self.estado_actual:
            return self.estado_actual.estado
        return Estados.PENDIENTE


# ── BENEFICIARIOS ──────────────────────────────────────────────────────────
class Beneficiario(Base):
    __tablename__ = "beneficiarios"

    id               = Column(Integer, primary_key=True, index=True)
    usuario_id       = Column(Integer, ForeignKey("usuarios.id"), nullable=False, unique=True)
    nombre_apodo     = Column(String(200), nullable=False)
    estado_actual_id = Column(Integer, ForeignKey("estado_registro.id"), nullable=True)
    dispositivo_id   = Column(Integer, ForeignKey("dispositivos.id"), nullable=True)
    prescriptor_id   = Column(Integer, ForeignKey("prescriptores.id"), nullable=True)

    # Datos de contacto y básicos
    fecha_nacimiento = Column(Date, nullable=True)
    localidad        = Column(String(100), nullable=True)
    telefono         = Column(String(30), nullable=True)
    descripcion      = Column(Text, nullable=True)
    genero           = Column(String(30), nullable=True)

    # Perfil sociodemográfico
    estado_civil         = Column(String(40), nullable=True)
    num_hijos            = Column(Integer, nullable=True)
    etnia                = Column(String(60), nullable=True)
    con_quien_vive       = Column(String(100), nullable=True)
    direccion            = Column(Text, nullable=True)
    escolaridad          = Column(String(60), nullable=True)
    ocupacion            = Column(String(100), nullable=True)
    sabe_leer_escribir   = Column(Boolean, nullable=True)
    sabe_usar_computador = Column(Boolean, nullable=True)

    # Red de apoyo
    nombre_persona_apoyo   = Column(String(200), nullable=True)
    telefono_persona_apoyo = Column(String(30), nullable=True)
    vinculo_persona_apoyo  = Column(String(60), nullable=True)
    apoyo_familiar         = Column(Boolean, nullable=True)
    apoyo_comunitario      = Column(Boolean, nullable=True)
    apoyo_institucional    = Column(Boolean, nullable=True)
    apoyo_actor_social     = Column(String(200), nullable=True)

    # Participación y recreación
    practica_deporte         = Column(Boolean, nullable=True)
    tiene_tiempo_recreacion  = Column(Boolean, nullable=True)
    cuanto_tiempo_recreacion = Column(String(50), nullable=True)
    conoce_espacios          = Column(String(20), nullable=True)   # Sí / No / Tal vez
    ha_participado           = Column(String(20), nullable=True)   # Sí / No / Tal vez

    # Identidad y cultura
    religion            = Column(String(60), nullable=True)
    pertenencia_etnica  = Column(String(5),  nullable=True)   # 'Sí' / 'No'

    # Persona de apoyo extendida
    tiene_persona_apoyo = Column(Boolean, nullable=True)
    tipo_vinculo_codigo = Column(String(20), nullable=True)   # MADRE / PADRE / HIJX …
    genero_apoyo        = Column(String(20), nullable=True)   # FEMENINO / MASCULINO / NR

    # Red de apoyo extendida
    apoyo_otro_actor  = Column(Boolean, nullable=True)         # Recibe apoyo de otro actor social
    cual_actor_social = Column(String(200), nullable=True)     # Cuál actor

    estado_actual      = relationship("EstadoRegistro", foreign_keys=[estado_actual_id], lazy="joined")
    usuario            = relationship("Usuario", back_populates="beneficiario")
    dispositivo        = relationship("Dispositivo", foreign_keys=[dispositivo_id])
    prescriptor        = relationship("Prescriptor", foreign_keys=[prescriptor_id])
    seguimientos       = relationship("Seguimiento", back_populates="beneficiario")
    primeros_contactos = relationship("PrimerContacto", back_populates="beneficiario")
    inscripciones      = relationship("Inscripcion", back_populates="beneficiario", cascade="all, delete-orphan")

    @property
    def estado(self) -> str:
        if self.estado_actual:
            return self.estado_actual.estado
        return Estados.PENDIENTE


# ── ACTIVIDADES ────────────────────────────────────────────────────────────
class Actividad(Base):
    __tablename__ = "actividades"

    id             = Column(Integer, primary_key=True, index=True)
    dispositivo_id = Column(Integer, ForeignKey("dispositivos.id"), nullable=False)
    nombre         = Column(String(200), nullable=False)
    tipo           = Column(String(60))
    lugar          = Column(String(200))
    dia_semana     = Column(String(30))
    hora           = Column(String(20))
    emoji          = Column(String(10), default="📋")
    activa         = Column(Boolean, default=True)
    descripcion    = Column(Text, nullable=True)
    cupo_maximo    = Column(Integer, nullable=True)
    fecha_inicio   = Column(Date, nullable=True)

    dispositivo   = relationship("Dispositivo", back_populates="actividades")
    inscripciones = relationship("Inscripcion", back_populates="actividad", cascade="all, delete-orphan")


# ── SEGUIMIENTOS ───────────────────────────────────────────────────────────
class Seguimiento(Base):
    __tablename__ = "seguimientos"

    id              = Column(Integer, primary_key=True, index=True)
    prescriptor_id  = Column(Integer, ForeignKey("prescriptores.id"), nullable=False)
    beneficiario_id = Column(Integer, ForeignKey("beneficiarios.id"), nullable=False)
    tipo_registro   = Column(String(60))
    observaciones   = Column(Text)
    fecha           = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    prescriptor  = relationship("Prescriptor",  back_populates="seguimientos")
    beneficiario = relationship("Beneficiario", back_populates="seguimientos")


# ── PRIMER CONTACTO ────────────────────────────────────────────────────────
class PrimerContacto(Base):
    __tablename__ = "primer_contacto"

    id               = Column(Integer, primary_key=True, index=True)
    beneficiario_id  = Column(Integer, ForeignKey("beneficiarios.id"), nullable=False)
    dispositivo_id   = Column(Integer, ForeignKey("dispositivos.id"), nullable=False)
    prescriptor_id   = Column(Integer, ForeignKey("prescriptores.id"), nullable=True)
    created_at       = Column(DateTime, default=datetime.utcnow, nullable=True)

    # Datos del convenio
    convenio_515        = Column(String(20), nullable=True)
    tipo_dbc            = Column(String(60), nullable=True)
    politica_privacidad = Column(String(20), nullable=True)
    numero_caso         = Column(String(50), nullable=True)

    # Datos del evento de contacto
    fecha_contacto   = Column(Date, default=lambda: datetime.now(timezone.utc).date())
    hora_contacto    = Column(Time, nullable=True)
    upz              = Column(String(100), nullable=True)
    barrio           = Column(String(100), nullable=True)
    forma_contacto   = Column(String(60), nullable=True)

    # Datos de la fuente (quien derivó)
    nombre_fuente    = Column(String(200), nullable=True)
    telefono_fuente  = Column(String(30), nullable=True)
    genero_fuente    = Column(String(30), nullable=True)
    vinculo_fuente   = Column(String(60), nullable=True)

    # Edad del beneficiario (en caso de no tener fecha de nacimiento)
    edad_benef       = Column(Integer, nullable=True)

    # Dirección del beneficiario
    clase_via                 = Column(String(30), nullable=True)
    numero_via_principal      = Column(String(20), nullable=True)
    letra_via_principal       = Column(String(10), nullable=True)
    identificador_sector      = Column(String(20), nullable=True)
    numero_via_generadora     = Column(String(20), nullable=True)
    letra_via_generadora      = Column(String(10), nullable=True)
    numero_predio             = Column(String(20), nullable=True)
    otras_caracteristicas_dir = Column(String(100), nullable=True)

    # Resumen del primer encuentro
    situaciones_presentes = Column(Text, nullable=True)
    peticiones            = Column(Text, nullable=True)
    descripcion_caso      = Column(Text, nullable=True)

    # Procesos previos
    procesos_previos = Column(Integer, default=0, nullable=True)

    # Datos del registrador
    rol_registrador      = Column(String(100), nullable=True)
    nombre_registrador   = Column(String(200), nullable=True)
    telefono_registrador = Column(String(30), nullable=True)

    beneficiario = relationship("Beneficiario", back_populates="primeros_contactos")
    dispositivo  = relationship("Dispositivo",  back_populates="primeros_contactos")
    prescriptor  = relationship("Prescriptor",  foreign_keys=[prescriptor_id])


# ── INSCRIPCIONES (N:M) ────────────────────────────────────────────────────
class Inscripcion(Base):
    __tablename__ = "inscripciones"

    id                = Column(Integer, primary_key=True, index=True)
    beneficiario_id   = Column(Integer, ForeignKey("beneficiarios.id"), nullable=False)
    actividad_id      = Column(Integer, ForeignKey("actividades.id"), nullable=False)
    fecha_inscripcion = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    beneficiario = relationship("Beneficiario", back_populates="inscripciones")
    actividad    = relationship("Actividad",    back_populates="inscripciones")