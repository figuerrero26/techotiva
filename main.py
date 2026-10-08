from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, RedirectResponse
from datetime import datetime, timezone
from sqlalchemy import text
from sqlalchemy.orm import Session
from database import get_db, Base, engine, SessionLocal, run_migrations

from app.core.config import settings
from app.core.security import hash_password


# ─── Seed: crear admin por defecto si no existe ───────────────────────────────
def seed_admin():
    from app.models.models import Usuario, EstadoRegistro, Estados
    db = SessionLocal()
    try:
        exists = db.query(Usuario).filter(Usuario.rol == "admin").first()
        if not exists:
            admin = Usuario(
                email=settings.admin_email,
                password_hash=hash_password(settings.admin_password),
                rol="admin",
                email_verificado=True,
            )
            db.add(admin)
            db.flush()

            estado = EstadoRegistro(
                entidad_tipo="usuarios",
                entidad_id=admin.id,
                estado=Estados.ACTIVO,
                cambiado_por=None,
                motivo="Usuario administrador inicial",
            )
            db.add(estado)
            db.flush()

            admin.estado_actual_id = estado.id
            db.commit()
            print(f" Admin creado: {settings.admin_email}")
        else:
            exists.password_hash = hash_password(settings.admin_password)
            db.commit()
            print(f" Admin sincronizado: {exists.email}")
    finally:
        db.close()

# ─── Seed: datos iniciales (dispositivos, prescriptores, beneficiarios) ───────
def seed_datos():
    from app.models.models import (
        Usuario, Dispositivo, Prescriptor, Beneficiario, EstadoRegistro, Estados
    )

    PASSWORD = "Test1234!"

    dispositivos_data = [
        {"email": "artevivo.fontibon@ctt.org",        "nombre": "Arte Vivo Fontibón",      "tipo_servicio": "Arte y cultura", "lugar_actividades": "Fontibón"},
        {"email": "clubdeportivo.engativa@ctt.org",   "nombre": "Club Deportivo Engativá", "tipo_servicio": "Deporte",        "lugar_actividades": "Engativá"},
    ]
    prescriptores_data = [
        {"email": "frankin.guerrero@ctt.org", "nombre_completo": "Frankin Ivan Guerrero", "perfil_disciplina": "Trabajo social", "disp_email": "artevivo.fontibon@ctt.org"},
        {"email": "ana.martinez@ctt.org",     "nombre_completo": "Ana Sofia Martinez",    "perfil_disciplina": "Psicología",     "disp_email": "clubdeportivo.engativa@ctt.org"},
    ]
    beneficiarios_data = [
        {"email": "laura.omana@correo.com",  "nombre_apodo": "Laura Isabela Omaña",  "disp_email": "artevivo.fontibon@ctt.org"},
        {"email": "karol.cotame@correo.com", "nombre_apodo": "Karol Marcela Cotame", "disp_email": "artevivo.fontibon@ctt.org"},
        {"email": "yeimy.poveda@correo.com", "nombre_apodo": "Yeimy Poveda",         "disp_email": "clubdeportivo.engativa@ctt.org"},
    ]

    db = SessionLocal()
    try:
        def _make_estado(tipo, entidad_id):
            e = EstadoRegistro(entidad_tipo=tipo, entidad_id=entidad_id,
                               estado=Estados.ACTIVO, motivo="Dato inicial", cambiado_por=None)
            db.add(e)
            db.flush()
            return e

        def _make_usuario(email, rol):
            u = Usuario(email=email, password_hash=hash_password(PASSWORD),
                        rol=rol, email_verificado=True)
            db.add(u)
            db.flush()
            eu = _make_estado("usuario", u.id)
            u.estado_actual_id = eu.id
            return u

        # ── Dispositivos ──────────────────────────────────────────────────────
        disp_ids = {}
        for d in dispositivos_data:
            existing = db.query(Usuario).filter(Usuario.email == d["email"]).first()
            if not existing:
                u = _make_usuario(d["email"], "dispositivo")
                perfil = Dispositivo(usuario_id=u.id, nombre=d["nombre"],
                                     tipo_servicio=d["tipo_servicio"],
                                     lugar_actividades=d["lugar_actividades"])
                db.add(perfil)
                db.flush()
                ep = _make_estado("dispositivo", perfil.id)
                perfil.estado_actual_id = ep.id
                db.flush()
                disp_ids[d["email"]] = perfil.id
                print(f"  Dispositivo creado: {d['nombre']}")
            else:
                p = db.query(Dispositivo).filter(Dispositivo.usuario_id == existing.id).first()
                if p:
                    disp_ids[d["email"]] = p.id
        db.commit()

        # ── Prescriptores ─────────────────────────────────────────────────────
        for d in prescriptores_data:
            existing = db.query(Usuario).filter(Usuario.email == d["email"]).first()
            if not existing:
                u = _make_usuario(d["email"], "prescriptor")
                perfil = Prescriptor(usuario_id=u.id, nombre_completo=d["nombre_completo"],
                                     perfil_disciplina=d["perfil_disciplina"],
                                     dispositivo_id=disp_ids.get(d["disp_email"]))
                db.add(perfil)
                db.flush()
                ep = _make_estado("prescriptor", perfil.id)
                perfil.estado_actual_id = ep.id
                db.flush()
                print(f"  Prescriptor creado: {d['nombre_completo']}")
        db.commit()

        # ── Beneficiarios ─────────────────────────────────────────────────────
        for d in beneficiarios_data:
            existing = db.query(Usuario).filter(Usuario.email == d["email"]).first()
            if not existing:
                u = _make_usuario(d["email"], "beneficiario")
                perfil = Beneficiario(usuario_id=u.id, nombre_apodo=d["nombre_apodo"],
                                      dispositivo_id=disp_ids.get(d["disp_email"]))
                db.add(perfil)
                db.flush()
                ep = _make_estado("beneficiario", perfil.id)
                perfil.estado_actual_id = ep.id
                db.flush()
                print(f"  Beneficiario creado: {d['nombre_apodo']}")
        db.commit()

    finally:
        db.close()


# ─── Lifespan ─────────────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    run_migrations()
    seed_admin()
    seed_datos()
    yield


# ─── App ──────────────────────────────────────────────────────────────────────
app = FastAPI(
    title="MASCATE API",
    description=(
        "API del sistema MASCATE para gestión de Dispositivos CBC, "
        "Prescriptxres y Beneficiarixs. Autenticación JWT + roles."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# ─── CORS ─────────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


from fastapi.staticfiles import StaticFiles

# Sirve los archivos HTML como estáticos
app.mount("/static", StaticFiles(directory="templates/static"), name="static")
# ─── Routers ──────────────────────────────────────────────────────────────────
from app.routers import auth, admin, dispositivos, prescriptores, beneficiarios, actividades, primer_contacto

app.include_router(auth.router)
app.include_router(admin.router)
app.include_router(dispositivos.router)
app.include_router(prescriptores.router)
app.include_router(beneficiarios.router)
app.include_router(actividades.router)
app.include_router(primer_contacto.router)

@app.get("/login",          include_in_schema=False)
def login_page():           return FileResponse("templates/mascate-auth-final.html")

@app.get("/dashboard",      include_in_schema=False)
def dashboard_page():       return FileResponse("templates/mascate-dashboards-final.html")

@app.get("/usuarios",       include_in_schema=False)
def usuarios_page():        return FileResponse("templates/usuarios.html")

@app.get("/actividades",    include_in_schema=False)
def actividades_page():     return FileResponse("templates/actividades.html")

@app.get("/reportes",       include_in_schema=False)
def reportes_page():        return FileResponse("templates/reportes.html")

@app.get("/perfil",         include_in_schema=False)
def perfil_page():          return FileResponse("templates/perfil.html")

@app.get("/notificaciones", include_in_schema=False)
def notificaciones_page():  return FileResponse("templates/notificaciones.html")

@app.get("/configuracion",  include_in_schema=False)
def configuracion_page():   return FileResponse("templates/configuracion.html")

@app.get("/mis-actividades", include_in_schema=False)
def mis_actividades_page():
    return FileResponse("templates/mis-actividades.html")

@app.get("/mapa", include_in_schema=False)
def mapa_page():
    return FileResponse("templates/mapa.html")

@app.get("/reportar-info", include_in_schema=False)
def reportar_info_page():
    return FileResponse("templates/reportar-info.html")

@app.get("/roles", include_in_schema=False)
def roles_page():
    return FileResponse("templates/roles.html")

@app.get("/", include_in_schema=False)
def root():
    return RedirectResponse(url="/login")

@app.get("/dispositivos-admin", include_in_schema=False)
def dispositivos_admin_page():
    return FileResponse("templates/dispositivos-admin.html")

@app.get("/mis-prescriptores", include_in_schema=False)
def mis_prescriptores_page():
    return FileResponse("templates/mis-prescriptores.html")

@app.get("/mi-dispositivo", include_in_schema=False)
def mi_dispositivo_page():
    return FileResponse("templates/mi-dispositivo.html")

@app.get("/mis-seguimientos", include_in_schema=False)
def mis_seguimientos_page():
    return FileResponse("templates/mis-seguimientos.html")

@app.get("/health", tags=["Health"])
def health_check(db: Session = Depends(get_db)):
    try:
        db.execute(text("SELECT 1"))
        db_status = "ok"
    except Exception:
        db_status = "error"
    
    return {
        "status": "healthy",
        "api": {
            "name": "MASCATE API",
            "version": "1.0.0",
            "status": "ok"
        },
        "database": {
            "status": db_status,
            "engine": "sqlite" if settings.database_url.startswith("sqlite") else "postgresql",
        },
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
