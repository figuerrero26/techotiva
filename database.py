from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, DeclarativeBase

from app.core.config import settings


def _make_engine(url: str):
    if url.startswith("sqlite"):
        # SQLite no soporta pool_size/max_overflow
        return create_engine(
            url,
            connect_args={"check_same_thread": False},
            echo=settings.app_env == "development",
        )
    return create_engine(
        url,
        pool_pre_ping=True,
        pool_size=10,
        max_overflow=20,
        echo=settings.app_env == "development",
    )


engine = _make_engine(settings.database_url)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def run_migrations():
    """
    Agrega columnas nuevas a tablas existentes sin perder datos.
    SQLAlchemy create_all solo crea tablas nuevas, no modifica columnas existentes.
    """
    migrations = [
        # Columna de recuperación de contraseña en usuarios
        ("usuarios", "password_reset_token",        "VARCHAR(100)"),
        ("usuarios", "password_reset_token_expiry", "DATETIME"),
        ("usuarios", "politica_privacidad_at",      "DATETIME"),
        # Asignación directa prescriptor→beneficiario
        ("beneficiarios", "prescriptor_id", "INTEGER"),
        # Nuevas columnas en beneficiarios
        ("beneficiarios", "estado_civil",         "VARCHAR(40)"),
        ("beneficiarios", "num_hijos",             "INTEGER"),
        ("beneficiarios", "etnia",                 "VARCHAR(60)"),
        ("beneficiarios", "con_quien_vive",        "VARCHAR(100)"),
        ("beneficiarios", "direccion",             "TEXT"),
        ("beneficiarios", "escolaridad",           "VARCHAR(60)"),
        ("beneficiarios", "ocupacion",             "VARCHAR(100)"),
        ("beneficiarios", "sabe_leer_escribir",    "BOOLEAN"),
        ("beneficiarios", "sabe_usar_computador",  "BOOLEAN"),
        ("beneficiarios", "nombre_persona_apoyo",  "VARCHAR(200)"),
        ("beneficiarios", "telefono_persona_apoyo","VARCHAR(30)"),
        ("beneficiarios", "vinculo_persona_apoyo", "VARCHAR(60)"),
        ("beneficiarios", "apoyo_familiar",        "BOOLEAN"),
        ("beneficiarios", "apoyo_comunitario",     "BOOLEAN"),
        ("beneficiarios", "apoyo_institucional",   "BOOLEAN"),
        ("beneficiarios", "apoyo_actor_social",    "VARCHAR(200)"),
        ("beneficiarios", "practica_deporte",      "BOOLEAN"),
        # Nuevas columnas en primer_contacto
        ("primer_contacto", "prescriptor_id",         "INTEGER"),
        ("primer_contacto", "hora_contacto",           "TIME"),
        ("primer_contacto", "upz",                     "VARCHAR(100)"),
        ("primer_contacto", "barrio",                  "VARCHAR(100)"),
        ("primer_contacto", "forma_contacto",          "VARCHAR(60)"),
        ("primer_contacto", "nombre_fuente",           "VARCHAR(200)"),
        ("primer_contacto", "vinculo_fuente",          "VARCHAR(60)"),
        ("primer_contacto", "situaciones_presentes",   "TEXT"),
        ("primer_contacto", "peticiones",              "TEXT"),
        ("primer_contacto", "descripcion_caso",        "TEXT"),
        ("primer_contacto", "procesos_previos",        "INTEGER DEFAULT 0"),
        # Solicitud de unión de prescriptor a dispositivo (Opción B)
        ("prescriptores", "solicitud_dispositivo_id", "INTEGER"),
        # Beneficiario — identidad/cultura y red de apoyo extendida
        ("beneficiarios", "religion",                 "VARCHAR(60)"),
        ("beneficiarios", "tiene_persona_apoyo",      "BOOLEAN"),
        ("beneficiarios", "tipo_vinculo_codigo",      "VARCHAR(20)"),
        ("beneficiarios", "genero_apoyo",             "VARCHAR(20)"),
        ("beneficiarios", "apoyo_otro_actor",         "BOOLEAN"),
        ("beneficiarios", "cual_actor_social",        "VARCHAR(200)"),
        ("beneficiarios", "tiene_tiempo_recreacion",  "BOOLEAN"),
        ("beneficiarios", "cuanto_tiempo_recreacion", "VARCHAR(50)"),
        ("beneficiarios", "conoce_espacios",          "VARCHAR(20)"),
        ("beneficiarios", "ha_participado",           "VARCHAR(20)"),
        # PrimerContacto — datos del convenio
        ("primer_contacto", "convenio_515",             "VARCHAR(20)"),
        ("primer_contacto", "tipo_dbc",                 "VARCHAR(60)"),
        ("primer_contacto", "politica_privacidad",      "VARCHAR(20)"),
        ("primer_contacto", "numero_caso",              "VARCHAR(50)"),
        # PrimerContacto — fuente extendida
        ("primer_contacto", "telefono_fuente",          "VARCHAR(30)"),
        ("primer_contacto", "genero_fuente",            "VARCHAR(30)"),
        ("primer_contacto", "edad_benef",               "INTEGER"),
        # PrimerContacto — dirección
        ("primer_contacto", "clase_via",                "VARCHAR(30)"),
        ("primer_contacto", "numero_via_principal",     "VARCHAR(20)"),
        ("primer_contacto", "letra_via_principal",      "VARCHAR(10)"),
        ("primer_contacto", "identificador_sector",     "VARCHAR(20)"),
        ("primer_contacto", "numero_via_generadora",    "VARCHAR(20)"),
        ("primer_contacto", "letra_via_generadora",     "VARCHAR(10)"),
        ("primer_contacto", "numero_predio",            "VARCHAR(20)"),
        ("primer_contacto", "otras_caracteristicas_dir","VARCHAR(100)"),
        # PrimerContacto — registrador
        ("primer_contacto", "rol_registrador",          "VARCHAR(100)"),
        ("primer_contacto", "nombre_registrador",       "VARCHAR(200)"),
        ("primer_contacto", "telefono_registrador",     "VARCHAR(30)"),
        # PrimerContacto — marca temporal
        ("primer_contacto", "created_at",               "DATETIME"),
        # Usuario — última actividad (sesiones activas)
        ("usuarios",        "ultima_actividad",         "DATETIME"),
        # Usuario — verificación en dos pasos (admin)
        ("usuarios",        "dosfa_desafio",            "VARCHAR(64)"),
        ("usuarios",        "dosfa_codigo",             "VARCHAR(64)"),
        ("usuarios",        "dosfa_expira",             "DATETIME"),
        ("usuarios",        "dosfa_enviado",            "DATETIME"),
        ("usuarios",        "dosfa_intentos",           "INTEGER DEFAULT 0"),
        ("usuarios",        "dosfa_activo",             "BOOLEAN DEFAULT 1"),
        ("usuarios",        "sesion_version",           "INTEGER DEFAULT 0"),
        # PrimerContacto — campos alineados con formulario malspa
        ("primer_contacto", "tipo_contacto",            "VARCHAR(60)"),
        ("primer_contacto", "lugar_contacto",           "VARCHAR(100)"),
        ("primer_contacto", "info_por_beneficiario",    "VARCHAR(5)"),
        ("primer_contacto", "poblaciones_especiales",   "TEXT"),
        ("primer_contacto", "apoyo_personas_cercanas",  "VARCHAR(30)"),
        ("primer_contacto", "apoyo_interes_otros",      "VARCHAR(30)"),
        ("primer_contacto", "apoyo_ayuda_vecinos",      "VARCHAR(30)"),
        ("primer_contacto", "alimentacion",             "VARCHAR(60)"),
        ("primer_contacto", "emociones",                "TEXT"),
        # Beneficiario — pertenencia étnica
        ("beneficiarios",   "pertenencia_etnica",       "VARCHAR(5)"),
    ]

    is_sqlite = settings.database_url.startswith("sqlite")

    with engine.connect() as conn:
        for tabla, columna, tipo in migrations:
            try:
                if is_sqlite:
                    # SQLite: verificar si la columna existe con PRAGMA
                    cols = conn.execute(text(f"PRAGMA table_info({tabla})")).fetchall()
                    col_names = [c[1] for c in cols]
                    if columna not in col_names:
                        conn.execute(text(f"ALTER TABLE {tabla} ADD COLUMN {columna} {tipo}"))
                else:
                    # PostgreSQL: usar DO $$ para ignorar si ya existe
                    conn.execute(text(f"""
                        DO $$ BEGIN
                            ALTER TABLE {tabla} ADD COLUMN {columna} {tipo};
                        EXCEPTION WHEN duplicate_column THEN NULL;
                        END $$;
                    """))
            except Exception:
                pass
        try:
            conn.execute(text(
                "CREATE UNIQUE INDEX IF NOT EXISTS ux_inscripcion_benef_actividad "
                "ON inscripciones (beneficiario_id, actividad_id)"
            ))
        except Exception as e:   # p. ej. si ya hubiera duplicados en una base antigua
            print(f"[migraciones] No se creó el índice único de inscripciones: {e}")
        conn.commit()
