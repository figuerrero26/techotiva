"""
Script de datos de prueba para Cuida Tu Techo.
Ejecutar desde la raíz del proyecto:
    python seed_test_data.py

Crea:
  - 2 dispositivos (activos, email verificado)
  - 2 prescriptores (activos, uno por dispositivo)
  - 4 beneficiarios (2 por dispositivo, con todos los campos)
  - 4 primeros contactos (uno por beneficiario)
  - 2 seguimientos de ejemplo

Contraseña de todos: Test1234!
"""

import sys
import os
from datetime import date, time, datetime, timezone

sys.path.insert(0, os.path.dirname(__file__))

from database import SessionLocal, engine
from app.models.models import (
    Base, Usuario, EstadoRegistro, Estados,
    Dispositivo, Prescriptor, Beneficiario,
    PrimerContacto, Seguimiento,
)
from app.core.security import hash_password

# ── helpers ──────────────────────────────────────────────────────────────────

def _estado(db, tipo, entidad_id, estado, motivo="Seed de prueba"):
    er = EstadoRegistro(
        entidad_tipo=tipo,
        entidad_id=entidad_id,
        estado=estado,
        motivo=motivo,
        cambiado_por=None,
    )
    db.add(er)
    db.flush()
    return er


def _usuario(db, email, rol):
    u = Usuario(
        email=email,
        password_hash=hash_password("Test1234!"),
        rol=rol,
        email_verificado=True,
        politica_privacidad_at=datetime.now(timezone.utc),
        fecha_registro=datetime.now(timezone.utc),
    )
    db.add(u)
    db.flush()
    er = _estado(db, "usuario", u.id, Estados.ACTIVO)
    u.estado_actual_id = er.id
    db.flush()
    return u


# ── main ─────────────────────────────────────────────────────────────────────

def seed():
    db = SessionLocal()
    try:
        # Verificar si ya hay datos de prueba
        if db.query(Dispositivo).filter(Dispositivo.nombre == "Arte Vivo Fontibón").first():
            print("Ya existen datos de prueba. Abortando para no duplicar.")
            return

        print("Creando dispositivos...")

        # ── Dispositivo 1 ──────────────────────────────────────────────────
        u_d1 = _usuario(db, "artevivo.fontibon@ctt.org", "dispositivo")
        d1 = Dispositivo(
            usuario_id=u_d1.id,
            nombre="Arte Vivo Fontibón",
            tipo_servicio="Artístico",
            lugar_actividades="Parque",
            ubicacion="Parque El Edén, Cra 99 # 17A-51, Fontibón, Bogotá",
            dia_actividad="Lunes y Miércoles",
            hora_actividad="15:00",
            telefono="+57 310 234 5678",
            redes_sociales="@artevivofont",
        )
        db.add(d1)
        db.flush()
        er_d1 = _estado(db, "dispositivo", d1.id, Estados.ACTIVO)
        d1.estado_actual_id = er_d1.id
        db.flush()

        # ── Dispositivo 2 ──────────────────────────────────────────────────
        u_d2 = _usuario(db, "clubdeportivo.engativa@ctt.org", "dispositivo")
        d2 = Dispositivo(
            usuario_id=u_d2.id,
            nombre="Club Deportivo Engativá",
            tipo_servicio="Deportivo",
            lugar_actividades="Sede propia",
            ubicacion="Cll 63B # 96-40, Engativá, Bogotá",
            dia_actividad="Martes y Viernes",
            hora_actividad="08:00",
            telefono="+57 320 876 5432",
            redes_sociales="@clubdep.eng",
        )
        db.add(d2)
        db.flush()
        er_d2 = _estado(db, "dispositivo", d2.id, Estados.ACTIVO)
        d2.estado_actual_id = er_d2.id
        db.flush()

        print("Creando prescriptores...")

        # ── Prescriptor 1 (Arte Vivo) ──────────────────────────────────────
        u_p1 = _usuario(db, "laura.gomez@ctt.org", "prescriptor")
        p1 = Prescriptor(
            usuario_id=u_p1.id,
            nombre_completo="Laura Gómez Ríos",
            perfil_disciplina="Psicología",
            telefono="+57 311 111 2222",
            dispositivo_id=d1.id,
        )
        db.add(p1)
        db.flush()
        er_p1 = _estado(db, "prescriptor", p1.id, Estados.ACTIVO)
        p1.estado_actual_id = er_p1.id
        db.flush()

        # ── Prescriptor 2 (Club Deportivo) ─────────────────────────────────
        u_p2 = _usuario(db, "carlos.andrade@ctt.org", "prescriptor")
        p2 = Prescriptor(
            usuario_id=u_p2.id,
            nombre_completo="Carlos Andrade Peña",
            perfil_disciplina="Trabajo Social",
            telefono="+57 322 333 4444",
            dispositivo_id=d2.id,
        )
        db.add(p2)
        db.flush()
        er_p2 = _estado(db, "prescriptor", p2.id, Estados.ACTIVO)
        p2.estado_actual_id = er_p2.id
        db.flush()

        print("Creando beneficiarios...")

        # ── Beneficiario 1 — Rosa Medina (Arte Vivo, Laura) ────────────────
        u_b1 = _usuario(db, "rosa.medina@correo.com", "beneficiario")
        b1 = Beneficiario(
            usuario_id=u_b1.id,
            nombre_apodo="Rosa",
            dispositivo_id=d1.id,
            prescriptor_id=p1.id,
            fecha_nacimiento=date(1975, 3, 12),
            localidad="Fontibón",
            telefono="+57 300 111 2233",
            genero="Femenino",
            estado_civil="Separada",
            num_hijos=2,
            etnia="Mestiza",
            con_quien_vive="Hijos",
            direccion="Cra 101 # 22-15, Fontibón",
            escolaridad="Bachillerato completo",
            ocupacion="Artesana",
            sabe_leer_escribir=True,
            sabe_usar_computador=True,
            nombre_persona_apoyo="Marta Medina",
            telefono_persona_apoyo="+57 300 444 5566",
            vinculo_persona_apoyo="Hermana",
            apoyo_familiar=True,
            apoyo_comunitario=True,
            apoyo_institucional=False,
            apoyo_actor_social=None,
            practica_deporte=True,
            tiene_tiempo_recreacion=True,
            cuanto_tiempo_recreacion="2-3 horas a la semana",
            conoce_espacios="Sí",
            ha_participado="Sí",
            religion="Católica",
            tiene_persona_apoyo=True,
            tipo_vinculo_codigo="Hermánx",
            genero_apoyo="Femenino",
            apoyo_otro_actor=False,
            cual_actor_social=None,
        )
        db.add(b1)
        db.flush()
        er_b1 = _estado(db, "beneficiario", b1.id, Estados.ACTIVO)
        b1.estado_actual_id = er_b1.id
        db.flush()

        # ── Beneficiario 2 — Miguel Torres (Arte Vivo, Laura) ─────────────
        u_b2 = _usuario(db, "miguel.torres@correo.com", "beneficiario")
        b2 = Beneficiario(
            usuario_id=u_b2.id,
            nombre_apodo="Miguel",
            dispositivo_id=d1.id,
            prescriptor_id=p1.id,
            fecha_nacimiento=date(1988, 7, 25),
            localidad="Fontibón",
            telefono="+57 301 222 3344",
            genero="Masculino",
            estado_civil="Soltero",
            num_hijos=0,
            etnia="Afrodescendiente",
            con_quien_vive="Solo",
            direccion="Cll 20 # 97-10 Apto 302, Fontibón",
            escolaridad="Técnico completo",
            ocupacion="Músico independiente",
            sabe_leer_escribir=True,
            sabe_usar_computador=True,
            nombre_persona_apoyo="Jorge Torres",
            telefono_persona_apoyo="+57 301 555 6677",
            vinculo_persona_apoyo="Padre",
            apoyo_familiar=True,
            apoyo_comunitario=False,
            apoyo_institucional=True,
            apoyo_actor_social="Fundación Créeme",
            practica_deporte=False,
            tiene_tiempo_recreacion=True,
            cuanto_tiempo_recreacion="Fines de semana",
            conoce_espacios="Tal vez",
            ha_participado="No",
            religion="Ninguna",
            tiene_persona_apoyo=True,
            tipo_vinculo_codigo="Padre",
            genero_apoyo="Masculino",
            apoyo_otro_actor=True,
            cual_actor_social="Fundación Créeme",
        )
        db.add(b2)
        db.flush()
        er_b2 = _estado(db, "beneficiario", b2.id, Estados.ACTIVO)
        b2.estado_actual_id = er_b2.id
        db.flush()

        # ── Beneficiario 3 — Carmen Ruiz (Club Deportivo, Carlos) ──────────
        u_b3 = _usuario(db, "carmen.ruiz@correo.com", "beneficiario")
        b3 = Beneficiario(
            usuario_id=u_b3.id,
            nombre_apodo="Carmen",
            dispositivo_id=d2.id,
            prescriptor_id=p2.id,
            fecha_nacimiento=date(1962, 11, 5),
            localidad="Engativá",
            telefono="+57 302 333 4455",
            genero="Femenino",
            estado_civil="Viuda",
            num_hijos=3,
            etnia="Mestiza",
            con_quien_vive="Nietos",
            direccion="Cll 64 # 93A-22, Engativá",
            escolaridad="Primaria completa",
            ocupacion="Ama de casa",
            sabe_leer_escribir=True,
            sabe_usar_computador=False,
            nombre_persona_apoyo="Luis Ruiz",
            telefono_persona_apoyo="+57 302 666 7788",
            vinculo_persona_apoyo="Hijo",
            apoyo_familiar=True,
            apoyo_comunitario=True,
            apoyo_institucional=True,
            apoyo_actor_social="Junta de acción comunal",
            practica_deporte=True,
            tiene_tiempo_recreacion=True,
            cuanto_tiempo_recreacion="Todos los días",
            conoce_espacios="Sí",
            ha_participado="Sí",
            religion="Cristiana",
            tiene_persona_apoyo=True,
            tipo_vinculo_codigo="Hijx",
            genero_apoyo="Masculino",
            apoyo_otro_actor=True,
            cual_actor_social="Junta de acción comunal Engativá",
        )
        db.add(b3)
        db.flush()
        er_b3 = _estado(db, "beneficiario", b3.id, Estados.ACTIVO)
        b3.estado_actual_id = er_b3.id
        db.flush()

        # ── Beneficiario 4 — Julio Vargas (Club Deportivo, Carlos) ─────────
        u_b4 = _usuario(db, "julio.vargas@correo.com", "beneficiario")
        b4 = Beneficiario(
            usuario_id=u_b4.id,
            nombre_apodo="Julio",
            dispositivo_id=d2.id,
            prescriptor_id=p2.id,
            fecha_nacimiento=date(1995, 4, 18),
            localidad="Engativá",
            telefono="+57 303 444 5566",
            genero="Masculino",
            estado_civil="Casado",
            num_hijos=1,
            etnia="Indígena",
            con_quien_vive="Pareja e hijo",
            direccion="Transv 96 # 62-50, Engativá",
            escolaridad="Universitario incompleto",
            ocupacion="Auxiliar de bodega",
            sabe_leer_escribir=True,
            sabe_usar_computador=True,
            nombre_persona_apoyo="Ana Vargas",
            telefono_persona_apoyo="+57 303 777 8899",
            vinculo_persona_apoyo="Cónyuge",
            apoyo_familiar=True,
            apoyo_comunitario=False,
            apoyo_institucional=False,
            apoyo_actor_social=None,
            practica_deporte=True,
            tiene_tiempo_recreacion=True,
            cuanto_tiempo_recreacion="Sábados",
            conoce_espacios="No",
            ha_participado="No",
            religion="Ninguna",
            tiene_persona_apoyo=True,
            tipo_vinculo_codigo="Cónyuge",
            genero_apoyo="Femenino",
            apoyo_otro_actor=False,
            cual_actor_social=None,
        )
        db.add(b4)
        db.flush()
        er_b4 = _estado(db, "beneficiario", b4.id, Estados.ACTIVO)
        b4.estado_actual_id = er_b4.id
        db.flush()

        print("Creando primeros contactos...")

        # ── Primer Contacto B1 — Rosa ──────────────────────────────────────
        pc1 = PrimerContacto(
            beneficiario_id=b1.id,
            dispositivo_id=d1.id,
            prescriptor_id=p1.id,
            convenio_515="Sí",
            tipo_dbc="Base Comunitaria",
            politica_privacidad="Sí",
            numero_caso="CTT-2026-001",
            fecha_contacto=date(2026, 6, 10),
            hora_contacto=time(15, 30),
            upz="UPZ 76 – Fontibón",
            barrio="Versalles",
            forma_contacto="Remisión institucional",
            nombre_fuente="Secretaría Local de Integración",
            telefono_fuente="+57 1 369 1234",
            genero_fuente="Femenino",
            vinculo_fuente="Institucional",
            edad_benef=51,
            clase_via="Calle",
            numero_via_principal="22",
            letra_via_principal="",
            identificador_sector="",
            numero_via_generadora="101",
            letra_via_generadora="",
            numero_predio="15",
            otras_caracteristicas_dir="Casa esquinera, portón azul",
            situaciones_presentes="Aislamiento social, duelo no elaborado por separación",
            peticiones="Desea participar en actividades artísticas y reconectar con su comunidad",
            descripcion_caso="Rosa fue derivada por la secretaría local tras perder su empleo. Presenta estado emocional estable pero manifiesta soledad y falta de motivación.",
            procesos_previos=0,
            rol_registrador="Psicóloga",
            nombre_registrador="Laura Gómez Ríos",
            telefono_registrador="+57 311 111 2222",
        )
        db.add(pc1)

        # ── Primer Contacto B2 — Miguel ────────────────────────────────────
        pc2 = PrimerContacto(
            beneficiario_id=b2.id,
            dispositivo_id=d1.id,
            prescriptor_id=p1.id,
            convenio_515="No",
            tipo_dbc="Club de vida",
            politica_privacidad="Sí",
            numero_caso="CTT-2026-002",
            fecha_contacto=date(2026, 7, 3),
            hora_contacto=time(16, 0),
            upz="UPZ 76 – Fontibón",
            barrio="La Cabaña",
            forma_contacto="Voluntario",
            nombre_fuente="",
            telefono_fuente="",
            genero_fuente="",
            vinculo_fuente="",
            edad_benef=37,
            clase_via="Calle",
            numero_via_principal="20",
            letra_via_principal="",
            identificador_sector="",
            numero_via_generadora="97",
            letra_via_generadora="",
            numero_predio="10",
            otras_caracteristicas_dir="Apto 302, edificio Fontana",
            situaciones_presentes="Inestabilidad laboral, consumo esporádico de alcohol",
            peticiones="Quiere retomar estudios y encontrar una red de apoyo",
            descripcion_caso="Miguel llegó por cuenta propia al dispositivo. Músico desempleado con historial de consumo leve. Motivado a participar en talleres creativos.",
            procesos_previos=1,
            rol_registrador="Psicóloga",
            nombre_registrador="Laura Gómez Ríos",
            telefono_registrador="+57 311 111 2222",
        )
        db.add(pc2)

        # ── Primer Contacto B3 — Carmen ────────────────────────────────────
        pc3 = PrimerContacto(
            beneficiario_id=b3.id,
            dispositivo_id=d2.id,
            prescriptor_id=p2.id,
            convenio_515="Sí",
            tipo_dbc="Base Comunitaria",
            politica_privacidad="Sí",
            numero_caso="CTT-2026-003",
            fecha_contacto=date(2026, 7, 15),
            hora_contacto=time(9, 0),
            upz="UPZ 74 – Engativá",
            barrio="Boyacá Real",
            forma_contacto="Remisión familiar",
            nombre_fuente="Luis Ruiz",
            telefono_fuente="+57 302 666 7788",
            genero_fuente="Masculino",
            vinculo_fuente="Hijo",
            edad_benef=63,
            clase_via="Calle",
            numero_via_principal="64",
            letra_via_principal="",
            identificador_sector="",
            numero_via_generadora="93A",
            letra_via_generadora="",
            numero_predio="22",
            otras_caracteristicas_dir="Casa de un piso, reja negra",
            situaciones_presentes="Dolor crónico, movilidad reducida, depresión leve",
            peticiones="Busca actividad física adaptada y compañía",
            descripcion_caso="Carmen es remitida por su hijo. Viuda hace 3 años, con dificultades de movilidad leve. Muestra interés en actividades grupales de bajo impacto físico.",
            procesos_previos=0,
            rol_registrador="Trabajador Social",
            nombre_registrador="Carlos Andrade Peña",
            telefono_registrador="+57 322 333 4444",
        )
        db.add(pc3)

        # ── Primer Contacto B4 — Julio ─────────────────────────────────────
        pc4 = PrimerContacto(
            beneficiario_id=b4.id,
            dispositivo_id=d2.id,
            prescriptor_id=p2.id,
            convenio_515="No",
            tipo_dbc="Club de vida",
            politica_privacidad="Sí",
            numero_caso="CTT-2026-004",
            fecha_contacto=date(2026, 8, 20),
            hora_contacto=time(8, 30),
            upz="UPZ 74 – Engativá",
            barrio="Las Ferias",
            forma_contacto="Referido por vecino",
            nombre_fuente="Pedro Salamanca",
            telefono_fuente="+57 315 200 1111",
            genero_fuente="Masculino",
            vinculo_fuente="Vecino",
            edad_benef=31,
            clase_via="Transversal",
            numero_via_principal="96",
            letra_via_principal="",
            identificador_sector="",
            numero_via_generadora="62",
            letra_via_generadora="",
            numero_predio="50",
            otras_caracteristicas_dir="Segundo piso, escalera exterior",
            situaciones_presentes="Estrés laboral, conflictos familiares, sedentarismo",
            peticiones="Interés en actividad física y manejo del estrés",
            descripcion_caso="Julio fue referido por un vecino que participa en el club. Trabaja turnos largos y reporta dificultad para manejar el estrés. Pareja también expresa preocupación.",
            procesos_previos=0,
            rol_registrador="Trabajador Social",
            nombre_registrador="Carlos Andrade Peña",
            telefono_registrador="+57 322 333 4444",
        )
        db.add(pc4)

        print("Creando seguimientos de ejemplo...")

        seg1 = Seguimiento(
            prescriptor_id=p1.id,
            beneficiario_id=b1.id,
            tipo_registro="Sesión individual",
            observaciones="Rosa asistió puntualmente. Muestra mejoría en su estado anímico. Participó en el taller de pintura y socializó con otros participantes. Se planea continuar con sesiones grupales.",
            fecha=datetime(2026, 7, 5, 15, 45, tzinfo=timezone.utc),
        )
        db.add(seg1)

        seg2 = Seguimiento(
            prescriptor_id=p2.id,
            beneficiario_id=b3.id,
            tipo_registro="Visita domiciliaria",
            observaciones="Carmen recibió visita en casa. Condiciones de habitabilidad adecuadas. Expresa mejoría desde inicio de actividades. Se evaluó adaptación de ejercicios a su condición física. Próxima cita en dispositivo.",
            fecha=datetime(2026, 8, 2, 9, 30, tzinfo=timezone.utc),
        )
        db.add(seg2)

        db.commit()

        print("")
        print("Datos de prueba creados exitosamente.")
        print("")
        print("Dispositivos:")
        print("  artevivo.fontibon@ctt.org     — Arte Vivo Fontibón")
        print("  clubdeportivo.engativa@ctt.org — Club Deportivo Engativá")
        print("")
        print("Prescriptores:")
        print("  laura.gomez@ctt.org   — Laura Gómez Ríos (Psicología, Arte Vivo)")
        print("  carlos.andrade@ctt.org — Carlos Andrade Peña (T. Social, Club Dep.)")
        print("")
        print("Beneficiarios:")
        print("  rosa.medina@correo.com   — Rosa Medina    (Arte Vivo / Laura)")
        print("  miguel.torres@correo.com — Miguel Torres  (Arte Vivo / Laura)")
        print("  carmen.ruiz@correo.com   — Carmen Ruiz    (Club Dep. / Carlos)")
        print("  julio.vargas@correo.com  — Julio Vargas   (Club Dep. / Carlos)")
        print("")
        print("Contraseña de todos los usuarios: Test1234!")

    except Exception as e:
        db.rollback()
        print(f"ERROR: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed()
