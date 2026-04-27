"""
Modelos SQLAlchemy para MASCATE.

Tablas: usuarios, dispositivos, prescriptores, beneficiarios,
        actividades, seguimientos, primer_contacto,
        inscripciones (relación N:M beneficiario ↔ actividad).
"""

from datetime import datetime, timezone

from sqlalchemy import (
    Column, Integer, String, Boolean, Text, DateTime, ForeignKey, Date,
)
from sqlalchemy.orm import relationship

from database import Base


# ────────────────────────── USUARIOS ──────────────────────────
class Usuario(Base):
    __tablename__ = "usuarios"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    rol = Column(String(20), nullable=False)  # dispositivo | prescriptor | beneficiario | admin
    activo = Column(Boolean, default=True)
    fecha_registro = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    # relaciones inversas
    dispositivo = relationship("Dispositivo", back_populates="usuario", uselist=False)
    prescriptor = relationship("Prescriptor", back_populates="usuario", uselist=False)
    beneficiario = relationship("Beneficiario", back_populates="usuario", uselist=False)


# ────────────────────────── DISPOSITIVOS ──────────────────────────
class Dispositivo(Base):
    __tablename__ = "dispositivos"

    id = Column(Integer, primary_key=True, index=True)
    usuario_id = Column(Integer, ForeignKey("usuarios.id"), nullable=False, unique=True)
    nombre = Column(String(200), nullable=False)
    lugar_actividades = Column(String(100))   # parque / salón comunal / sede propia / …
    ubicacion = Column(String(300))
    tipo_servicio = Column(String(100))       # artístico / cultural / deportivo / …
    dia_actividad = Column(String(100))
    hora_actividad = Column(String(20))
    telefono = Column(String(30))
    redes_sociales = Column(String(300))

    usuario = relationship("Usuario", back_populates="dispositivo")
    actividades = relationship("Actividad", back_populates="dispositivo", cascade="all, delete-orphan")
    prescriptores = relationship("Prescriptor", back_populates="dispositivo")
    primeros_contactos = relationship("PrimerContacto", back_populates="dispositivo")


# ────────────────────────── PRESCRIPTORES ──────────────────────────
class Prescriptor(Base):
    __tablename__ = "prescriptores"

    id = Column(Integer, primary_key=True, index=True)
    usuario_id = Column(Integer, ForeignKey("usuarios.id"), nullable=False, unique=True)
    nombre_completo = Column(String(200), nullable=False)
    perfil_disciplina = Column(String(100))
    telefono = Column(String(30))
    dispositivo_id = Column(Integer, ForeignKey("dispositivos.id"), nullable=True)

    usuario = relationship("Usuario", back_populates="prescriptor")
    dispositivo = relationship("Dispositivo", back_populates="prescriptores")
    seguimientos = relationship("Seguimiento", back_populates="prescriptor", cascade="all, delete-orphan")


# ────────────────────────── BENEFICIARIOS ──────────────────────────
class Beneficiario(Base):
    __tablename__ = "beneficiarios"

    id = Column(Integer, primary_key=True, index=True)
    usuario_id = Column(Integer, ForeignKey("usuarios.id"), nullable=False, unique=True)
    nombre_apodo = Column(String(200), nullable=False)

    usuario = relationship("Usuario", back_populates="beneficiario")
    seguimientos = relationship("Seguimiento", back_populates="beneficiario")
    primeros_contactos = relationship("PrimerContacto", back_populates="beneficiario")
    inscripciones = relationship("Inscripcion", back_populates="beneficiario", cascade="all, delete-orphan")


# ────────────────────────── ACTIVIDADES ──────────────────────────
class Actividad(Base):
    __tablename__ = "actividades"

    id = Column(Integer, primary_key=True, index=True)
    dispositivo_id = Column(Integer, ForeignKey("dispositivos.id"), nullable=False)
    nombre = Column(String(200), nullable=False)
    tipo = Column(String(60))    # artístico / deportivo / cultural / …
    lugar = Column(String(200))
    dia_semana = Column(String(30))
    hora = Column(String(20))
    emoji = Column(String(10), default="📋")
    activa = Column(Boolean, default=True)

    dispositivo = relationship("Dispositivo", back_populates="actividades")
    inscripciones = relationship("Inscripcion", back_populates="actividad", cascade="all, delete-orphan")


# ────────────────────────── SEGUIMIENTOS ──────────────────────────
class Seguimiento(Base):
    __tablename__ = "seguimientos"

    id = Column(Integer, primary_key=True, index=True)
    prescriptor_id = Column(Integer, ForeignKey("prescriptores.id"), nullable=False)
    beneficiario_id = Column(Integer, ForeignKey("beneficiarios.id"), nullable=False)
    tipo_registro = Column(String(60))  # sesión grupal / seguimiento individual / actividad especial
    observaciones = Column(Text)
    fecha = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    prescriptor = relationship("Prescriptor", back_populates="seguimientos")
    beneficiario = relationship("Beneficiario", back_populates="seguimientos")


# ────────────────────────── PRIMER CONTACTO ──────────────────────────
class PrimerContacto(Base):
    __tablename__ = "primer_contacto"

    id = Column(Integer, primary_key=True, index=True)
    beneficiario_id = Column(Integer, ForeignKey("beneficiarios.id"), nullable=False)
    dispositivo_id = Column(Integer, ForeignKey("dispositivos.id"), nullable=False)
    fecha_contacto = Column(Date, default=lambda: datetime.now(timezone.utc).date())
    notas = Column(Text)

    beneficiario = relationship("Beneficiario", back_populates="primeros_contactos")
    dispositivo = relationship("Dispositivo", back_populates="primeros_contactos")


# ────────────────────────── INSCRIPCIONES (N:M) ──────────────────────────
class Inscripcion(Base):
    """Relación muchos-a-muchos entre beneficiarios y actividades."""
    __tablename__ = "inscripciones"

    id = Column(Integer, primary_key=True, index=True)
    beneficiario_id = Column(Integer, ForeignKey("beneficiarios.id"), nullable=False)
    actividad_id = Column(Integer, ForeignKey("actividades.id"), nullable=False)
    fecha_inscripcion = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    beneficiario = relationship("Beneficiario", back_populates="inscripciones")
    actividad = relationship("Actividad", back_populates="inscripciones")
