"""
Borrado completo de una cuenta y todo lo que depende de ella.
Lo usan "Eliminar usuario" (admin) y "Rechazar" una solicitud pendiente.
"""
from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.models import (
    Usuario, Beneficiario, Prescriptor, Dispositivo,
    Seguimiento, PrimerContacto, Inscripcion, EstadoRegistro,
)


def borrar_usuario_completo(db: Session, user: Usuario) -> None:
    try:
        # Limpiar FK estado_actual del usuario
        user.estado_actual_id = None
        db.flush()

        # ── Beneficiario (puede existir aunque el rol actual sea otro) ──
        benef = db.query(Beneficiario).filter(Beneficiario.usuario_id == user.id).first()
        if benef:
            benef.estado_actual_id = None
            db.flush()
            db.query(Seguimiento).filter(Seguimiento.beneficiario_id == benef.id).delete(synchronize_session="fetch")
            db.flush()
            db.query(PrimerContacto).filter(PrimerContacto.beneficiario_id == benef.id).delete(synchronize_session="fetch")
            db.flush()
            db.query(Inscripcion).filter(Inscripcion.beneficiario_id == benef.id).delete(synchronize_session="fetch")
            db.flush()
            db.query(EstadoRegistro).filter(
                EstadoRegistro.entidad_tipo.in_(["beneficiarios", "beneficiario"]),
                EstadoRegistro.entidad_id == benef.id,
            ).delete(synchronize_session="fetch")
            db.flush()
            db.delete(benef)
            db.flush()

        # ── Prescriptor ──
        presc = db.query(Prescriptor).filter(Prescriptor.usuario_id == user.id).first()
        if presc:
            presc.estado_actual_id = None
            db.flush()
            db.query(Beneficiario).filter(Beneficiario.prescriptor_id == presc.id).update(
                {"prescriptor_id": None}, synchronize_session="fetch"
            )
            db.flush()
            db.query(Seguimiento).filter(Seguimiento.prescriptor_id == presc.id).delete(synchronize_session="fetch")
            db.flush()
            db.query(PrimerContacto).filter(PrimerContacto.prescriptor_id == presc.id).delete(synchronize_session="fetch")
            db.flush()
            db.query(EstadoRegistro).filter(
                EstadoRegistro.entidad_tipo.in_(["prescriptores", "prescriptor"]),
                EstadoRegistro.entidad_id == presc.id,
            ).delete(synchronize_session="fetch")
            db.flush()
            db.delete(presc)
            db.flush()

        # ── Dispositivo ──
        disp = db.query(Dispositivo).filter(Dispositivo.usuario_id == user.id).first()
        if disp:
            disp.estado_actual_id = None
            db.flush()
            db.query(Prescriptor).filter(Prescriptor.dispositivo_id == disp.id).update(
                {"dispositivo_id": None}, synchronize_session="fetch"
            )
            db.flush()
            db.query(EstadoRegistro).filter(
                EstadoRegistro.entidad_tipo.in_(["dispositivos", "dispositivo"]),
                EstadoRegistro.entidad_id == disp.id,
            ).delete(synchronize_session="fetch")
            db.flush()
            db.delete(disp)
            db.flush()

        # ── Estados del usuario ──
        db.query(EstadoRegistro).filter(
            EstadoRegistro.entidad_tipo.in_(["usuarios", "usuario"]),
            EstadoRegistro.entidad_id == user.id,
        ).delete(synchronize_session=False)

        db.delete(user)
        db.commit()

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error al eliminar: {str(e)}")
