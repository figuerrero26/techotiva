"""
Datos ficticios para ver el panel central con información.

Uso (desde la raíz del proyecto):
    python scripts/seed_demo.py           # crea 40 beneficiarios demo con su primer contacto
    python scripts/seed_demo.py --borrar  # elimina todo lo creado por este script

Todos los registros demo usan correos que terminan en @demo.ctt, así se pueden
identificar y borrar sin tocar los datos reales.
"""

import random
import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from database import SessionLocal, engine, Base, run_migrations  # noqa: E402
from app.models.models import (  # noqa: E402
    Usuario, Dispositivo, Prescriptor, Beneficiario, PrimerContacto,
    EstadoRegistro, Estados, Seguimiento, Inscripcion,
)

DOMINIO = "@demo.ctt"
CANTIDAD = 40

NOMBRES = [
    "María Fernanda", "Juan Camilo", "Luisa", "Andrés Felipe", "Paula Andrea", "Santiago",
    "Diana Marcela", "Kevin", "Valentina", "Jhon Alexander", "Natalia", "Brayan", "Camila",
    "Óscar", "Yuliana", "Cristian", "Sandra", "Miguel Ángel", "Daniela", "Wilson",
]
APELLIDOS = [
    "Rodríguez", "Gómez", "Martínez", "López", "Hernández", "Díaz", "Moreno", "Rojas",
    "Vargas", "Castro", "Ramírez", "Torres", "Suárez", "Pineda", "Cárdenas", "Ortiz",
]
GENEROS = ["Femenino"] * 5 + ["Masculino"] * 4 + ["No binario", "Transgénero", "No responde"]
LOCALIDADES = ["Kennedy", "Fontibón", "Engativá", "Bosa", "Suba", "Ciudad Bolívar"]

SPA = [
    "Uso de sustancias psicoactivas legales",
    "Uso de sustancias psicoactivas ilegales",
    "Uso de sustancias vía intravenosa",
]
SITUACIONES = [
    "Crisis psicológica", "Condición psiquiátrica", "Enfermedades", "Discapacidad", "VIH",
    "Ansiedad / Depresión", "Trastorno de estrés postraumático",
    "Violencia intrafamiliar", "Violencia comunitaria", "Problemas de convivencia en el entorno",
    "Habita la calle de forma permanente", "Discriminación", "Problemas con la justicia",
    "Malos resultados o deserción escolar", "Víctima del conflicto", "Población migrante",
    "Sin empleo u ocupación", "Dificultades económicas", "Pobreza extrema", "Hambre",
]
EMOCIONES = ["Alegría", "Confianza", "Anticipación", "Sorpresa", "Miedo", "Tristeza", "Disgusto", "Ira"]
NIVELES = {
    "Alegría": ["Serenidad", "Alegría", "Éxtasis"],
    "Confianza": ["Aceptación", "Confianza", "Admiración"],
    "Anticipación": ["Interés", "Anticipación", "Vigilancia"],
    "Sorpresa": ["Distracción", "Sorpresa", "Asombro"],
    "Miedo": ["Aprensión", "Miedo", "Terror"],
    "Tristeza": ["Pensativo", "Tristeza", "Pena"],
    "Disgusto": ["Aburrimiento", "Disgusto", "Aversión"],
    "Ira": ["Molestia", "Ira", "Furia"],
}
PETICIONES = [
    "Apoyo psicosocial", "Atención médica", "Alimentación", "Kit de higiene", "Ropa",
    "Formación técnica", "Apoyo para conseguir empleo", "Apoyo escolar", "Asesoría legal",
    "Documentación",
]
POBLACIONES = ["Migración", "Discapacidad", "Adulto mayor", "Infancia", "Adolescencia", "LGBTIQ+"]


def _estado(db, obj, motivo):
    e = EstadoRegistro(entidad_tipo=obj.__tablename__, entidad_id=obj.id,
                       estado=Estados.ACTIVO, motivo=motivo, cambiado_por=None)
    db.add(e)
    db.flush()
    obj.estado_actual_id = e.id


def crear(db):
    if db.query(Usuario).filter(Usuario.email.like("%" + DOMINIO)).first():
        print("Ya existen datos demo. Bórralos primero con --borrar.")
        return

    disps = db.query(Dispositivo).all()
    if not disps:
        print("No hay dispositivos creados; arranca el servidor una vez para que se creen.")
        return
    presc_por_disp = {}
    for p in db.query(Prescriptor).all():
        presc_por_disp.setdefault(p.dispositivo_id, p.id)

    rnd = random.Random(2026)
    hoy = date.today()

    for i in range(CANTIDAD):
        disp = disps[i % len(disps)]
        nombre = f"{rnd.choice(NOMBRES)} {rnd.choice(APELLIDOS)}"

        u = Usuario(email=f"demo{i + 1:02d}{DOMINIO}", password_hash="!no-login!",
                    rol="beneficiario", email_verificado=False)
        db.add(u)
        db.flush()
        _estado(db, u, "Dato demo")

        edad = rnd.choice([rnd.randint(14, 17), rnd.randint(18, 28), rnd.randint(18, 28),
                           rnd.randint(29, 59), rnd.randint(29, 59), rnd.randint(60, 78)])
        fnac = hoy - timedelta(days=edad * 365 + rnd.randint(0, 300))

        b = Beneficiario(
            usuario_id=u.id, nombre_apodo=nombre, dispositivo_id=disp.id,
            prescriptor_id=presc_por_disp.get(disp.id),
            genero=rnd.choice(GENEROS), fecha_nacimiento=fnac,
            localidad=rnd.choice(LOCALIDADES),
        )
        db.add(b)
        db.flush()
        _estado(db, b, "Dato demo")

        # ~35 % consume alguna sustancia
        sits = rnd.sample(SITUACIONES, rnd.randint(1, 4))
        if rnd.random() < 0.35:
            sits += rnd.sample(SPA, rnd.choice([1, 1, 2]))

        # Emociones con algo más de peso en las negativas (población vulnerable)
        pesos = [3, 2, 2, 2, 3, 4, 2, 2]
        emos = set()
        for _ in range(rnd.randint(1, 3)):
            emos.add(rnd.choices(EMOCIONES, weights=pesos)[0])

        pobl = rnd.sample(POBLACIONES, rnd.choice([0, 0, 1, 1, 2]))

        db.add(PrimerContacto(
            beneficiario_id=b.id, dispositivo_id=disp.id,
            prescriptor_id=presc_por_disp.get(disp.id),
            fecha_contacto=hoy - timedelta(days=rnd.randint(1, 90)),
            politica_privacidad="Sí", tipo_dbc=disp.nombre,
            tipo_contacto=rnd.choice(["Presencial", "Presencial", "Telefónico"]),
            info_por_beneficiario="Sí", edad_benef=edad,
            situaciones_presentes=" | ".join(sits),
            emociones=" | ".join(
                f"{e} - {rnd.choices(NIVELES[e], weights=[3, 4, 2])[0]}" for e in EMOCIONES if e in emos
            ),
            peticiones=" | ".join(rnd.sample(PETICIONES, rnd.randint(1, 3))),
            poblaciones_especiales=" | ".join(pobl) or None,
            alimentacion=rnd.choice(["Consume 3 o más comidas al día", "Consume 2 o menos comidas al día"]),
            descripcion_caso="Registro ficticio para pruebas del panel.",
        ))

    db.commit()
    print(f"Creados {CANTIDAD} beneficiarios demo repartidos en {len(disps)} dispositivo(s).")


def borrar(db):
    usuarios = db.query(Usuario).filter(Usuario.email.like("%" + DOMINIO)).all()
    if not usuarios:
        print("No hay datos demo para borrar.")
        return
    uids = [u.id for u in usuarios]
    benefs = db.query(Beneficiario).filter(Beneficiario.usuario_id.in_(uids)).all()
    bids = [b.id for b in benefs]

    if bids:
        db.query(PrimerContacto).filter(PrimerContacto.beneficiario_id.in_(bids)).delete(synchronize_session=False)
        db.query(Seguimiento).filter(Seguimiento.beneficiario_id.in_(bids)).delete(synchronize_session=False)
        db.query(Inscripcion).filter(Inscripcion.beneficiario_id.in_(bids)).delete(synchronize_session=False)
        db.query(EstadoRegistro).filter(
            EstadoRegistro.entidad_tipo == Beneficiario.__tablename__,
            EstadoRegistro.entidad_id.in_(bids),
            EstadoRegistro.motivo == "Dato demo",
        ).delete(synchronize_session=False)
        db.query(Beneficiario).filter(Beneficiario.id.in_(bids)).delete(synchronize_session=False)
    db.query(EstadoRegistro).filter(
        EstadoRegistro.entidad_tipo == Usuario.__tablename__,
        EstadoRegistro.entidad_id.in_(uids),
        EstadoRegistro.motivo == "Dato demo",
    ).delete(synchronize_session=False)
    db.query(Usuario).filter(Usuario.id.in_(uids)).delete(synchronize_session=False)
    db.commit()
    print(f"Borrados {len(bids)} beneficiarios demo.")


if __name__ == "__main__":
    Base.metadata.create_all(bind=engine)
    run_migrations()
    db = SessionLocal()
    try:
        borrar(db) if "--borrar" in sys.argv else crear(db)
    finally:
        db.close()
