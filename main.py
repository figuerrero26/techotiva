"""
MASCATE — Mesa Autónoma de SPA y Cannábica Techotiva
Punto de entrada de la API FastAPI.

Ejecutar con:
    python -m uvicorn main:app --reload --port 8080
"""

from contextlib import asynccontextmanager
from datetime import datetime, timezone, timedelta

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, RedirectResponse

from database import engine, SessionLocal, Base
from app.models.models import (
    Usuario, Dispositivo, Prescriptor, Beneficiario,
    Actividad, Seguimiento, PrimerContacto, Inscripcion,
)
from app.core.security import hash_password

# Importar routers
from app.routers import auth, dispositivos, actividades, prescriptores, beneficiarios, admin


# ════════════════════════════════════════════════════════════
#  SEED — datos de ejemplo si la BD está vacía
# ════════════════════════════════════════════════════════════
def seed_database():
    """Pobla la base de datos con datos de ejemplo si está vacía."""
    db = SessionLocal()
    try:
        if db.query(Usuario).count() > 0:
            return  # ya hay datos

        now = datetime.now(timezone.utc)

        # ── 1. Admin ──
        admin_user = Usuario(
            email="admin@mascate.org",
            password_hash=hash_password("admin123"),
            rol="admin",
            fecha_registro=now - timedelta(days=60),
        )
        db.add(admin_user)
        db.flush()

        # ── 2. Dispositivo 1: Arte Vivo Techotiva ──
        disp1_user = Usuario(
            email="artevivo@mascate.org",
            password_hash=hash_password("artevivo123"),
            rol="dispositivo",
            fecha_registro=now - timedelta(days=45),
        )
        db.add(disp1_user)
        db.flush()

        disp1 = Dispositivo(
            usuario_id=disp1_user.id,
            nombre="Arte Vivo Techotiva",
            lugar_actividades="Parque",
            ubicacion="Parque El Tintal, Bogotá",
            tipo_servicio="Artístico",
            dia_actividad="Lunes, Miércoles, Viernes",
            hora_actividad="14:00",
            telefono="+57 310 000 0001",
            redes_sociales="@artevivo_tec",
        )
        db.add(disp1)
        db.flush()

        # ── 3. Dispositivo 2: Red Deportiva Sur ──
        disp2_user = Usuario(
            email="deportivasur@mascate.org",
            password_hash=hash_password("deportiva123"),
            rol="dispositivo",
            fecha_registro=now - timedelta(days=40),
        )
        db.add(disp2_user)
        db.flush()

        disp2 = Dispositivo(
            usuario_id=disp2_user.id,
            nombre="Red Deportiva Sur",
            lugar_actividades="Salón comunal",
            ubicacion="Cancha Municipal Sur, Bogotá",
            tipo_servicio="Deportivo",
            dia_actividad="Martes, Jueves, Sábado",
            hora_actividad="16:00",
            telefono="+57 310 000 0002",
            redes_sociales="@redsur_dep",
        )
        db.add(disp2)
        db.flush()

        # ── 4. Prescriptor 1: María P. (Arte Vivo) ──
        presc1_user = Usuario(
            email="maria@mascate.org",
            password_hash=hash_password("maria123"),
            rol="prescriptor",
            fecha_registro=now - timedelta(days=35),
        )
        db.add(presc1_user)
        db.flush()

        presc1 = Prescriptor(
            usuario_id=presc1_user.id,
            nombre_completo="María Pérez",
            perfil_disciplina="Arte y cultura",
            telefono="+57 320 111 2222",
            dispositivo_id=disp1.id,
        )
        db.add(presc1)
        db.flush()

        # ── 5. Prescriptor 2: Carlos R. (Red Deportiva) ──
        presc2_user = Usuario(
            email="carlos@mascate.org",
            password_hash=hash_password("carlos123"),
            rol="prescriptor",
            fecha_registro=now - timedelta(days=30),
        )
        db.add(presc2_user)
        db.flush()

        presc2 = Prescriptor(
            usuario_id=presc2_user.id,
            nombre_completo="Carlos Ramírez",
            perfil_disciplina="Deporte",
            telefono="+57 320 333 4444",
            dispositivo_id=disp2.id,
        )
        db.add(presc2)
        db.flush()

        # ── 6. Beneficiarios (4) ──
        benef_data = [
            ("skate@mail.com", "Skate", 25),
            ("sofi@mail.com", "Sofía G.", 20),
            ("julian@mail.com", "Julián M.", 18),
            ("laura@mail.com", "Laura R.", 15),
        ]
        beneficiarios = []
        for email, apodo, days_ago in benef_data:
            u = Usuario(
                email=email,
                password_hash=hash_password("benef123"),
                rol="beneficiario",
                fecha_registro=now - timedelta(days=days_ago),
            )
            db.add(u)
            db.flush()
            b = Beneficiario(usuario_id=u.id, nombre_apodo=apodo)
            db.add(b)
            db.flush()
            beneficiarios.append(b)

        # ── 7. Actividades (6) ──
        actividades_data = [
            (disp1.id, "Taller de grafiti", "Artístico", "Parque El Tintal", "Lunes", "15:00", "🎨"),
            (disp1.id, "Círculo musical", "Cultural", "Salón comunal", "Viernes", "17:00", "🎵"),
            (disp1.id, "Huerta urbana", "Ambiental", "Reserva natural", "Sábado", "09:00", "🌿"),
            (disp2.id, "Fútbol comunitario", "Deportivo", "Cancha Municipal", "Miércoles", "16:00", "⚽"),
            (disp2.id, "Centro de escucha", "Escucha", "Sede propia", "Jueves", "14:00", "💬"),
            (disp2.id, "Taller de lectura", "Educativo", "Salón comunal", "Martes", "16:00", "📚"),
        ]
        actividades = []
        for did, nombre, tipo, lugar, dia, hora, emoji in actividades_data:
            a = Actividad(
                dispositivo_id=did,
                nombre=nombre,
                tipo=tipo,
                lugar=lugar,
                dia_semana=dia,
                hora=hora,
                emoji=emoji,
            )
            db.add(a)
            db.flush()
            actividades.append(a)

        # ── 8. Inscripciones (beneficiarios en actividades) ──
        inscripciones = [
            (beneficiarios[0].id, actividades[0].id),
            (beneficiarios[0].id, actividades[3].id),
            (beneficiarios[1].id, actividades[0].id),
            (beneficiarios[1].id, actividades[1].id),
            (beneficiarios[2].id, actividades[3].id),
            (beneficiarios[2].id, actividades[4].id),
            (beneficiarios[3].id, actividades[1].id),
            (beneficiarios[3].id, actividades[5].id),
        ]
        for bid, aid in inscripciones:
            db.add(Inscripcion(beneficiario_id=bid, actividad_id=aid))

        # ── 9. Primer contacto ──
        for i, b in enumerate(beneficiarios[:3]):
            db.add(PrimerContacto(
                beneficiario_id=b.id,
                dispositivo_id=disp1.id if i < 2 else disp2.id,
                fecha_contacto=(now - timedelta(days=10 + i)).date(),
                notas=f"Primer acercamiento de {b.nombre_apodo} al dispositivo.",
            ))

        # ── 10. Seguimientos ──
        seguimientos_data = [
            (presc1.id, beneficiarios[0].id, "Sesión grupal", "Participó activamente en el taller.", now - timedelta(days=1)),
            (presc1.id, beneficiarios[1].id, "Seguimiento individual", "Muestra interés en música.", now - timedelta(days=2)),
            (presc1.id, beneficiarios[2].id, "Sesión grupal", "Asistió al taller de grafiti.", now - timedelta(days=5)),
            (presc1.id, beneficiarios[3].id, "Actividad especial", "No asiste desde hace días.", now - timedelta(days=10)),
            (presc2.id, beneficiarios[2].id, "Sesión grupal", "Buen rendimiento en fútbol.", now - timedelta(days=1)),
            (presc2.id, beneficiarios[3].id, "Seguimiento individual", "Retomó actividades deportivas.", now - timedelta(days=4)),
        ]
        for pid, bid, tipo, obs, fecha in seguimientos_data:
            db.add(Seguimiento(
                prescriptor_id=pid,
                beneficiario_id=bid,
                tipo_registro=tipo,
                observaciones=obs,
                fecha=fecha,
            ))

        db.commit()
        print("[OK] Base de datos poblada con datos de ejemplo.")

    except Exception as e:
        db.rollback()
        print(f"[ERROR] Error al poblar la base de datos: {e}")
        raise
    finally:
        db.close()


# ════════════════════════════════════════════════════════════
#  APP
# ════════════════════════════════════════════════════════════
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Crea tablas y pobla datos de ejemplo al iniciar."""
    Base.metadata.create_all(bind=engine)
    seed_database()
    yield


app = FastAPI(
    title="MASCATE API",
    description="Mesa Autónoma de SPA y Cannábica Techotiva — API de registro comunitario",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS — permitir peticiones desde los HTML locales
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Registrar routers
app.include_router(auth.router)
app.include_router(dispositivos.router)
app.include_router(actividades.router)
app.include_router(prescriptores.router)
app.include_router(beneficiarios.router)
app.include_router(admin.router)


# ════════════════════════════════════════════════════════════
#  FRONTEND — servir páginas HTML
# ════════════════════════════════════════════════════════════
@app.get("/login", include_in_schema=False)
def login_page():
    return FileResponse("templates/mascate-auth-final.html")

@app.get("/dashboard", include_in_schema=False)
def dashboard_page():
    return FileResponse("templates/mascate-dashboards-final.html")

@app.get("/", include_in_schema=False)
def root():
    return RedirectResponse(url="/login")