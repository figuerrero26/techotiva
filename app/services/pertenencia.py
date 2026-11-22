"""
A qué dispositivo pertenece hoy un beneficiario.

Un beneficiario pertenece a UN solo dispositivo a la vez:
  - el que tiene asignado (Beneficiario.dispositivo_id), o
  - si aún no tiene ninguno asignado, los dispositivos con los que tiene relación
    (se inscribió a una actividad suya, o le hicieron primer contacto o seguimiento ahí).

Al trasladarlo a otro dispositivo, el anterior deja de verlo como propio.
Su historial (seguimientos y primer contacto) nunca se borra.
"""
from typing import Optional

from sqlalchemy.orm import Session

from app.models.models import (
    Actividad, Beneficiario, Inscripcion, Prescriptor, PrimerContacto, Seguimiento,
)


def ids_beneficiarios_de_dispositivo(db: Session, dispositivo_id: Optional[int]) -> set:
    """Ids de los beneficiarios que hoy pertenecen al dispositivo."""
    if not dispositivo_id:
        return set()

    asignados = {
        b[0] for b in db.query(Beneficiario.id).filter(Beneficiario.dispositivo_id == dispositivo_id).all()
    }

    # Relación con el dispositivo (solo cuenta para quien no tiene dispositivo asignado)
    relacion = set()
    relacion.update(b[0] for b in (
        db.query(Inscripcion.beneficiario_id)
        .join(Actividad, Actividad.id == Inscripcion.actividad_id)
        .filter(Actividad.dispositivo_id == dispositivo_id).distinct().all()
    ))
    relacion.update(b[0] for b in (
        db.query(PrimerContacto.beneficiario_id)
        .filter(PrimerContacto.dispositivo_id == dispositivo_id).distinct().all()
    ))
    presc_ids = [p[0] for p in db.query(Prescriptor.id).filter(Prescriptor.dispositivo_id == dispositivo_id).all()]
    if presc_ids:
        relacion.update(b[0] for b in (
            db.query(Seguimiento.beneficiario_id)
            .filter(Seguimiento.prescriptor_id.in_(presc_ids)).distinct().all()
        ))

    sin_asignar = set()
    if relacion:
        sin_asignar = {
            b[0] for b in db.query(Beneficiario.id)
            .filter(Beneficiario.id.in_(relacion), Beneficiario.dispositivo_id.is_(None)).all()
        }
    return asignados | sin_asignar


def pertenece_a(benef: Beneficiario, dispositivo_id: Optional[int], dispositivo_relacionado: Optional[int] = None) -> bool:
    """
    ¿El beneficiario es hoy de ese dispositivo?
    `dispositivo_relacionado`: dispositivo de un registro concreto (p. ej. el de su primer contacto),
    que solo cuenta si el beneficiario aún no tiene dispositivo asignado.
    """
    if not dispositivo_id or benef is None:
        return False
    if benef.dispositivo_id is not None:
        return benef.dispositivo_id == dispositivo_id
    return dispositivo_relacionado == dispositivo_id
