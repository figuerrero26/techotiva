"""
Datos ficticios para ver el panel central con información.

Uso (desde la raíz del proyecto):
    python scripts/seed_demo.py                        # crea 40 beneficiarios demo
    python scripts/seed_demo.py --cantidad 6 --spa 4   # crea 6, de los cuales 4 consumen SPA
    python scripts/seed_demo.py --borrar               # elimina todo lo creado por este script

Cada beneficiario queda con la hoja de primer contacto y la ficha completas, asignado
a un dispositivo (se reparten por igual) y al prescriptor de ese dispositivo.

Todos los registros demo usan correos que terminan en @demo.ctt, así se pueden
identificar y borrar sin tocar los datos reales.
"""

import random
import sys
from datetime import date, time, timedelta
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


def _arg(nombre, defecto):
    """Lee --nombre N de la línea de comandos."""
    if nombre in sys.argv:
        return int(sys.argv[sys.argv.index(nombre) + 1])
    return defecto


def _tel(rnd, prefijo="3"):
    return f"{prefijo}{rnd.randint(0, 2)}{rnd.randint(0, 9)} {rnd.randint(100, 999)} {rnd.randint(1000, 9999)}"


def crear(db, cantidad=CANTIDAD, con_spa=None):
    if db.query(Usuario).filter(Usuario.email.like("%" + DOMINIO)).first():
        print("Ya existen datos demo. Bórralos primero con --borrar.")
        return

    disps = db.query(Dispositivo).order_by(Dispositivo.id).all()
    if not disps:
        print("No hay dispositivos creados; arranca el servidor una vez para que se creen.")
        return
    presc_por_disp = {}
    for p in db.query(Prescriptor).order_by(Prescriptor.id).all():
        if p.dispositivo_id and p.usuario and p.usuario.rol == "prescriptor":
            presc_por_disp.setdefault(p.dispositivo_id, []).append(p)

    rnd = random.Random(2026)
    hoy = date.today()
    # Quiénes consumen SPA: los primeros `con_spa`; al alternar dispositivos quedan repartidos
    if con_spa is None:
        consume = [rnd.random() < 0.35 for _ in range(cantidad)]
    else:
        consume = [i < con_spa for i in range(cantidad)]

    for i in range(cantidad):
        disp = disps[i % len(disps)]
        lista = presc_por_disp.get(disp.id) or []
        presc = lista[(i // len(disps)) % len(lista)] if lista else None   # se reparten entre los del dispositivo
        nombre = f"{rnd.choice(NOMBRES)} {rnd.choice(APELLIDOS)}"

        u = Usuario(email=f"demo{i + 1:02d}{DOMINIO}", password_hash="!no-login!",
                    rol="beneficiario", email_verificado=False)
        db.add(u)
        db.flush()
        _estado(db, u, "Dato demo")

        edad = rnd.choice([rnd.randint(14, 17), rnd.randint(18, 28), rnd.randint(18, 28),
                           rnd.randint(29, 59), rnd.randint(29, 59), rnd.randint(60, 78)])
        fnac = hoy - timedelta(days=edad * 365 + rnd.randint(0, 300))
        tiene_apoyo = True                     # hoja completa: todos tienen persona de apoyo
        etnico = i % 3 == 0                    # uno de cada tres pertenece a un grupo étnico
        actor = rnd.choice(["Junta de acción comunal", "Parroquia del barrio", "Colectivo juvenil"])

        # Ficha del beneficiario (datos personales, red de apoyo, educación y recreación)
        b = Beneficiario(
            usuario_id=u.id, nombre_apodo=nombre, dispositivo_id=disp.id,
            prescriptor_id=presc.id if presc else None,
            genero=rnd.choice(GENEROS), fecha_nacimiento=fnac, localidad=rnd.choice(LOCALIDADES),
            telefono=_tel(rnd), descripcion="Beneficiario ficticio para mostrar el panel.",
            estado_civil=rnd.choice(["Soltero(a)", "Unión libre", "Casado(a)", "Divorciado(a)", "Viudo(a)"]),
            num_hijos=rnd.choice([0, 0, 1, 2, 3]),
            pertenencia_etnica="Sí" if etnico else "No",
            etnia=rnd.choice(["Afrocolombiano", "Indígena", "Raizal"]) if etnico else None,
            religion=rnd.choice(["Católica", "Cristiana", "Evangélica", "Ninguna", "Sin respuesta"]),
            con_quien_vive=rnd.choice(["Padres (papá y/o mamá)", "Otros familiares (familia extensa)",
                                       "Vive solo(a)", "Vive con hijos(as)", "Vive con la pareja"]),
            direccion=f"Calle {rnd.randint(1, 80)} # {rnd.randint(10, 120)}-{rnd.randint(1, 99)}",
            escolaridad=rnd.choice(["Primaria completa", "Secundaria incompleta", "Secundaria completa",
                                    "Técnica completa", "Profesional incompleta"]),
            ocupacion=rnd.choice(["Estudiantes", "Trabajo informal", "No tiene", "Trabajo formal", "Emprendimiento"]),
            sabe_leer_escribir=rnd.random() < 0.9, sabe_usar_computador=rnd.random() < 0.6,
            tiene_persona_apoyo=tiene_apoyo,
            nombre_persona_apoyo=f"{rnd.choice(NOMBRES)} {rnd.choice(APELLIDOS)}" if tiene_apoyo else None,
            telefono_persona_apoyo=_tel(rnd) if tiene_apoyo else None,
            vinculo_persona_apoyo=rnd.choice(["Madre", "Hermana", "Amigo", "Tía"]) if tiene_apoyo else None,
            tipo_vinculo_codigo=rnd.choice(["Madre", "Hermánx", "Amistad", "Tix"]) if tiene_apoyo else "Sin respuesta",
            genero_apoyo=rnd.choice(["Femenino", "Masculino"]) if tiene_apoyo else "Sin respuesta",
            apoyo_familiar=rnd.random() < 0.6, apoyo_comunitario=rnd.random() < 0.4,
            apoyo_institucional=rnd.random() < 0.5, apoyo_otro_actor=True,
            apoyo_actor_social=actor, cual_actor_social=actor,
            practica_deporte=rnd.random() < 0.4, tiene_tiempo_recreacion=rnd.random() < 0.6,
            cuanto_tiempo_recreacion=rnd.choice(["1 hora al día", "Fines de semana", "2 horas a la semana"]),
            conoce_espacios=rnd.choice(["Sí", "No", "Tal vez"]),
            ha_participado=rnd.choice(["Sí", "No", "Tal vez"]),
        )
        db.add(b)
        db.flush()
        _estado(db, b, "Dato demo")

        sits = rnd.sample(SITUACIONES, rnd.randint(1, 3))
        if consume[i]:
            sits += rnd.sample(SPA, rnd.choice([1, 1, 2]))

        # Emociones con algo más de peso en las negativas (población vulnerable)
        pesos = [3, 2, 2, 2, 3, 4, 2, 2]
        emos = set()
        for _ in range(rnd.randint(1, 3)):
            emos.add(rnd.choices(EMOCIONES, weights=pesos)[0])

        # Hoja de primer contacto completa (todas las secciones)
        db.add(PrimerContacto(
            beneficiario_id=b.id, dispositivo_id=disp.id, prescriptor_id=presc.id if presc else None,
            fecha_contacto=hoy - timedelta(days=rnd.randint(1, 60)),
            hora_contacto=time(rnd.randint(8, 17), rnd.choice([0, 15, 30, 45])),
            numero_caso=f"DEMO-{i + 1:03d}",
            forma_contacto=rnd.choice(["En la calle", "Institución", "Junta de acción comunal", "Referencia"]),
            tipo_contacto=rnd.choice(["Presencial", "Presencial", "Telefónico"]),
            lugar_contacto=rnd.choice(["Espacio público", "Vivienda", "Sede del dispositivo", "Salón comunal"]),
            upz=rnd.choice(["80-Corabastos", "47-Kennedy Central", "44-Américas", "82-Patio Bonito"]),
            barrio=rnd.choice(["Patio Bonito", "Timiza", "Castilla", "Las Margaritas", "El Tintal"]),
            convenio_515=rnd.choice(["Nuevo", "Antiguo", "Pionero"]),
            tipo_dbc=disp.nombre, politica_privacidad="Sí",
            info_por_beneficiario="No",
            nombre_fuente=f"{rnd.choice(NOMBRES)} {rnd.choice(APELLIDOS)}",
            telefono_fuente=_tel(rnd),
            genero_fuente=rnd.choice(["Femenino", "Masculino"]),
            vinculo_fuente=rnd.choice(["Familiar", "Conocido(a)", "Amigo(a)", "Integrante de una institución"]),
            edad_benef=edad,
            clase_via=rnd.choice(["Calle", "Carrera", "Diagonal", "Transversal"]),
            numero_via_principal=str(rnd.randint(1, 80)), letra_via_principal=rnd.choice(["A", "B", "C"]),
            identificador_sector="Sur", numero_via_generadora=str(rnd.randint(10, 120)),
            letra_via_generadora=rnd.choice(["A", "B", "C"]), numero_predio=str(rnd.randint(1, 99)),
            otras_caracteristicas_dir=rnd.choice(["Casa", "Apartamento 201", "Interior 3"]),
            poblaciones_especiales=" | ".join(rnd.sample(POBLACIONES, rnd.choice([1, 1, 2]))),
            procesos_previos=rnd.randint(0, 2),
            apoyo_personas_cercanas=rnd.choice(["Ninguna", "1-2", "3-5"]),
            apoyo_interes_otros=rnd.choice(["Poco", "Incierto", "Algo", "Mucho"]),
            apoyo_ayuda_vecinos=rnd.choice(["Difícil", "Posible", "Fácil"]),
            alimentacion=rnd.choice(["Consume 3 o más comidas al día", "Consume 2 o menos comidas al día"]),
            emociones=" | ".join(
                f"{e} - {rnd.choices(NIVELES[e], weights=[3, 4, 2])[0]}" for e in EMOCIONES if e in emos
            ),
            situaciones_presentes=" | ".join(sits),
            peticiones=" | ".join(rnd.sample(PETICIONES, rnd.randint(1, 3))),
            descripcion_caso="Registro ficticio para mostrar el panel. "
                             + ("Refiere consumo de sustancias psicoactivas. " if consume[i] else "")
                             + "Se acuerda seguimiento con el prescriptor del dispositivo.",
            rol_registrador="Prescriptor",
            nombre_registrador=presc.nombre_completo if presc else disp.nombre,
            telefono_registrador=(presc.telefono if presc and presc.telefono else _tel(rnd)),
        ))

    db.commit()
    print(f"Creados {cantidad} beneficiarios demo ({sum(consume)} con consumo de SPA) "
          f"repartidos en {len(disps)} dispositivo(s).")


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
        if "--borrar" in sys.argv:
            borrar(db)
        else:
            spa = _arg("--spa", -1)
            crear(db, _arg("--cantidad", CANTIDAD), None if spa < 0 else spa)
    finally:
        db.close()
