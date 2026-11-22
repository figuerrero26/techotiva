"""
Configuración de las pruebas automáticas.

- Cada sesión de pruebas usa una base de datos NUEVA en una carpeta temporal:
  nunca toca mascate.db ni el servidor publicado.
- Los correos no se envían: se capturan en `correos` para poder revisarlos.
- Los límites de intentos (fuerza bruta) se reinician antes de cada prueba.

Ejecutar desde la raíz del proyecto:   python -m pytest tests -q
"""
import os
import sys
import tempfile
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parent.parent
_TMP = tempfile.mkdtemp(prefix="cuidatutecho_tests_")
os.environ["DATABASE_URL"] = "sqlite:///" + str(Path(_TMP) / "pruebas.db").replace("\\", "/")
os.environ["APP_ENV"] = "development"     # crea los usuarios de prueba (clave Test1234!)
os.environ["ADMIN_2FA"] = "true"
os.environ["ADMIN_PASSWORD"] = "Test1234!"
sys.path.insert(0, str(RAIZ))
os.chdir(RAIZ)                             # las páginas se sirven con rutas relativas

CLAVE = "Test1234!"
ADMIN = "techotivasite@gmail.com"
DISP_FONTIBON = "artevivo.fontibon@ctt.org"
DISP_ENGATIVA = "clubdeportivo.engativa@ctt.org"
PRESC_FRANKIN = "frankin.guerrero@ctt.org"      # Arte Vivo Fontibón (seed)
PRESC_ANA = "ana.martinez@ctt.org"              # Club Deportivo Engativá (seed)
BENEF_LAURA = "laura.omana@correo.com"          # Arte Vivo Fontibón (seed)
BENEF_YEIMY = "yeimy.poveda@correo.com"         # Club Deportivo Engativá (seed)

correos = []   # (tipo, destinatario, datos)


def _capturar(tipo):
    async def falso(*args, **kwargs):
        destino = kwargs.get("email") or kwargs.get("email_destino") or (args[0] if args else None)
        correos.append((tipo, destino, {"args": args, **kwargs}))
    return falso


@pytest.fixture(scope="session")
def app():
    import app.services.email_service as E
    import app.routers.auth as A
    import app.routers.admin as AD
    import app.routers.primer_contacto as PC
    for nombre in ["enviar_correo_verificacion", "enviar_correo_recuperacion", "enviar_codigo_2fa",
                   "enviar_correo_aprobacion", "enviar_aviso_registro",
                   "enviar_correo_bienvenida_beneficiario", "enviar_correo_bienvenida_dispositivo"]:
        falso = _capturar(nombre)
        for mod in (E, A, AD, PC):
            if hasattr(mod, nombre):
                setattr(mod, nombre, falso)
    import main
    return main.app


@pytest.fixture(scope="session")
def client(app):
    from fastapi.testclient import TestClient
    with TestClient(app) as c:
        yield c


@pytest.fixture(autouse=True)
def limpiar_limites():
    from app.core import rate_limit
    for lim in (rate_limit.limite_login, rate_limit.limite_login_ip,
                rate_limit.limite_2fa_ip, rate_limit.limite_recuperar_ip):
        lim._fallos.clear()
    yield


@pytest.fixture
def db():
    from database import SessionLocal
    s = SessionLocal()
    yield s
    s.close()


def ultimo_correo(tipo):
    for t, dest, datos in reversed(correos):
        if t == tipo:
            return dest, datos
    return None, None


@pytest.fixture(scope="session")
def login(client):
    """login(email) → encabezados con el token (resuelve la verificación en dos pasos del admin)."""
    cache = {}

    def _login(email, clave=CLAVE, nuevo=False):
        if email in cache and not nuevo:
            return cache[email]
        from database import SessionLocal
        from app.models.models import Usuario
        s = SessionLocal()
        u = s.query(Usuario).filter(Usuario.email == email).first()
        if u:
            u.dosfa_enviado = None   # evita la espera de 30 s entre códigos
            s.commit()
        s.close()
        r = client.post("/auth/login", json={"email": email, "password": clave})
        assert r.status_code == 200, (email, r.status_code, r.text)
        d = r.json()
        if d.get("requiere_2fa"):
            _, datos = ultimo_correo("enviar_codigo_2fa")
            codigo = datos.get("codigo") or datos["args"][1]
            r = client.post("/auth/verificar-2fa", json={"desafio": d["desafio"], "codigo": codigo})
            assert r.status_code == 200, r.text
            d = r.json()
        h = {"Authorization": "Bearer " + d["access_token"]}
        cache[email] = h
        return h
    return _login
