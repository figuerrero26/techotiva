from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, RedirectResponse
from datetime import datetime, timezone
from sqlalchemy import text
from sqlalchemy.orm import Session
from database import get_db

from app.core.config import settings
from app.core.security import hash_password
from database import Base, engine, SessionLocal, run_migrations


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

            # El admin se activa a sí mismo en el historial
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
            print(f" Admin ya existe: {exists.email}")
    finally:
        db.close()

# ─── Lifespan ─────────────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    run_migrations()
    seed_admin()
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
    from fastapi.responses import RedirectResponse
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
            "engine": "postgresql"
        },
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
