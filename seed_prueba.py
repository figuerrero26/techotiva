"""
Script de datos de prueba para MASCATE.
Crea un dispositivo, un prescriptor y un beneficiario asociados entre sí.
Ejecutar desde la raíz del proyecto:
    python seed_prueba.py
"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from database import SessionLocal
from app.core.security import hash_password
from app.models.models import (
    Usuario, Dispositivo, Prescriptor, Beneficiario,
    EstadoRegistro, Estados,
)
from datetime import date

CLAVE = "123456789"

def crear_estado(db, tipo, entidad_id, estado=Estados.ACTIVO, motivo="Seed prueba"):
    est = EstadoRegistro(
        entidad_tipo=tipo,
        entidad_id=entidad_id,
        estado=estado,
        cambiado_por=None,
        motivo=motivo,
    )
    db.add(est)
    db.flush()
    return est

def seed():
    db = SessionLocal()
    try:
        # ── 1. DISPOSITIVO ─────────────────────────────────────────────────
        email_disp = "dispositivo.prueba@test.com"
        if db.query(Usuario).filter(Usuario.email == email_disp).first():
            print(f"[!] Ya existe {email_disp}, omitiendo dispositivo.")
            disp_user = db.query(Usuario).filter(Usuario.email == email_disp).first()
            disp_entity = disp_user.dispositivo
        else:
            disp_user = Usuario(
                email=email_disp,
                password_hash=hash_password(CLAVE),
                rol="dispositivo",
                email_verificado=True,
            )
            db.add(disp_user)
            db.flush()

            est_u = crear_estado(db, "usuarios", disp_user.id)
            disp_user.estado_actual_id = est_u.id
            db.flush()

            disp_entity = Dispositivo(
                usuario_id=disp_user.id,
                nombre="Dispositivo de Prueba Centro",
                lugar_actividades="Centro Comunitario La Esperanza",
                ubicacion="Calle Principal 123, Barrio Centro",
                tipo_servicio="Atención social integral",
                dia_actividad="Lunes y Miércoles",
                hora_actividad="09:00",
                telefono="3001234567",
            )
            db.add(disp_entity)
            db.flush()

            est_d = crear_estado(db, "dispositivos", disp_entity.id)
            disp_entity.estado_actual_id = est_d.id
            db.flush()
            print(f"[+] Dispositivo creado: {email_disp}")

        # ── 2. PRESCRIPTOR ─────────────────────────────────────────────────
        email_presc = "prescriptor.prueba@test.com"
        if db.query(Usuario).filter(Usuario.email == email_presc).first():
            print(f"[!] Ya existe {email_presc}, omitiendo prescriptor.")
            presc_user = db.query(Usuario).filter(Usuario.email == email_presc).first()
            presc_entity = presc_user.prescriptor
        else:
            presc_user = Usuario(
                email=email_presc,
                password_hash=hash_password(CLAVE),
                rol="prescriptor",
                email_verificado=True,
            )
            db.add(presc_user)
            db.flush()

            est_u2 = crear_estado(db, "usuarios", presc_user.id)
            presc_user.estado_actual_id = est_u2.id
            db.flush()

            presc_entity = Prescriptor(
                usuario_id=presc_user.id,
                nombre_completo="Prescriptor de Prueba",
                perfil_disciplina="Trabajo Social",
                telefono="3009876543",
                dispositivo_id=disp_entity.id,
            )
            db.add(presc_entity)
            db.flush()

            est_p = crear_estado(db, "prescriptores", presc_entity.id)
            presc_entity.estado_actual_id = est_p.id
            db.flush()
            print(f"[+] Prescriptor creado: {email_presc} -> dispositivo '{disp_entity.nombre}'")

        # ── 3. BENEFICIARIO ────────────────────────────────────────────────
        email_benef = "beneficiario.prueba@test.com"
        if db.query(Usuario).filter(Usuario.email == email_benef).first():
            print(f"[!] Ya existe {email_benef}, omitiendo beneficiario.")
        else:
            benef_user = Usuario(
                email=email_benef,
                password_hash=hash_password(CLAVE),
                rol="beneficiario",
                email_verificado=True,
            )
            db.add(benef_user)
            db.flush()

            est_u3 = crear_estado(db, "usuarios", benef_user.id)
            benef_user.estado_actual_id = est_u3.id
            db.flush()

            benef_entity = Beneficiario(
                usuario_id=benef_user.id,
                nombre_apodo="Beneficiario de Prueba",
                dispositivo_id=disp_entity.id,
                prescriptor_id=presc_entity.id,
                fecha_nacimiento=date(1985, 6, 15),
                genero="femenino",
                telefono="3101112233",
                localidad="Barrio Centro",
                estado_civil="soltero/a",
                escolaridad="secundaria",
                ocupacion="Independiente",
                sabe_leer_escribir=True,
                sabe_usar_computador=False,
            )
            db.add(benef_entity)
            db.flush()

            est_b = crear_estado(db, "beneficiarios", benef_entity.id)
            benef_entity.estado_actual_id = est_b.id
            db.flush()
            print(f"[+] Beneficiario creado: {email_benef} -> prescriptor '{presc_entity.nombre_completo}'")

        db.commit()
        print("\n[OK] Datos de prueba creados exitosamente.")
        print("-" * 50)
        print(f"  Dispositivo : {email_disp}")
        print(f"  Prescriptor : {email_presc}")
        print(f"  Beneficiario: {email_benef}")
        print(f"  Clave todos : {CLAVE}")
        print("-" * 50)

    except Exception as e:
        db.rollback()
        print(f"[ERROR] {e}")
        raise
    finally:
        db.close()

if __name__ == "__main__":
    seed()
