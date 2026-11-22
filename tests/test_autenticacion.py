"""Autenticación, registro, verificación, recuperación de contraseña, 2FA y sesiones."""
import uuid
from datetime import datetime, timedelta, timezone

from conftest import ADMIN, CLAVE, PRESC_ANA, BENEF_LAURA, DISP_FONTIBON, correos, ultimo_correo


def _email():
    return f"qa_{uuid.uuid4().hex[:8]}@test.com"


# ── Login ────────────────────────────────────────────────────────────────────
def test_login_correcto_entrega_token(client):
    r = client.post("/auth/login", json={"email": PRESC_ANA, "password": CLAVE})
    assert r.status_code == 200 and r.json()["rol"] == "prescriptor" and r.json()["access_token"]


def test_login_clave_errada(client):
    r = client.post("/auth/login", json={"email": PRESC_ANA, "password": "mala"})
    assert r.status_code == 401
    assert r.json()["detail"] == "Credenciales incorrectas"


def test_login_correo_inexistente_mismo_mensaje(client):
    r = client.post("/auth/login", json={"email": "noexiste@test.com", "password": "x"})
    assert r.status_code == 401 and r.json()["detail"] == "Credenciales incorrectas"


def test_login_correo_con_mayusculas(client):
    """El correo no debería distinguir mayúsculas al iniciar sesión."""
    r = client.post("/auth/login", json={"email": PRESC_ANA.upper(), "password": CLAVE})
    assert r.status_code == 200


def test_login_bloqueo_por_fuerza_bruta(client):
    for _ in range(5):
        client.post("/auth/login", json={"email": PRESC_ANA, "password": "mala"})
    r = client.post("/auth/login", json={"email": PRESC_ANA, "password": CLAVE})
    assert r.status_code == 429


def test_login_cuerpo_malformado(client):
    r = client.post("/auth/login", content="{no es json", headers={"Content-Type": "application/json"})
    assert r.status_code == 422


# ── Verificación en dos pasos (admin) ────────────────────────────────────────
def test_admin_requiere_codigo(client, db):
    from app.models.models import Usuario
    u = db.query(Usuario).filter(Usuario.email == ADMIN).first(); u.dosfa_enviado = None; u.dosfa_activo = True; db.commit()
    r = client.post("/auth/login", json={"email": ADMIN, "password": CLAVE})
    assert r.status_code == 200 and r.json().get("requiere_2fa") and "access_token" not in r.json()


def test_2fa_codigo_errado_y_luego_correcto(client, db):
    from app.models.models import Usuario
    u = db.query(Usuario).filter(Usuario.email == ADMIN).first(); u.dosfa_enviado = None; db.commit()
    d = client.post("/auth/login", json={"email": ADMIN, "password": CLAVE}).json()
    _, datos = ultimo_correo("enviar_codigo_2fa"); codigo = datos["args"][1]
    malo = "000000" if codigo != "000000" else "111111"
    assert client.post("/auth/verificar-2fa", json={"desafio": d["desafio"], "codigo": malo}).status_code == 400
    r = client.post("/auth/verificar-2fa", json={"desafio": d["desafio"], "codigo": codigo})
    assert r.status_code == 200 and r.json()["rol"] == "admin"
    # el mismo código no sirve dos veces
    assert client.post("/auth/verificar-2fa", json={"desafio": d["desafio"], "codigo": codigo}).status_code == 400


# ── Registro ─────────────────────────────────────────────────────────────────
def test_registro_beneficiario_envia_verificacion_y_aviso(client):
    e = _email(); n = len(correos)
    r = client.post("/auth/register", json={"rol": "beneficiario", "email": e, "password": "Abcdefg1",
                                            "nombre_apodo": "QA Beni", "politica_privacidad": True})
    assert r.status_code == 201
    tipos = [t for t, _, _ in correos[n:]]
    assert "enviar_correo_verificacion" in tipos and "enviar_aviso_registro" in tipos


def test_registro_rol_admin_prohibido(client):
    r = client.post("/auth/register", json={"rol": "admin", "email": _email(), "password": "Abcdefg1"})
    assert r.status_code == 422


def test_registro_clave_corta(client):
    r = client.post("/auth/register", json={"rol": "beneficiario", "email": _email(), "password": "abc",
                                            "nombre_apodo": "X"})
    assert r.status_code == 422


def test_registro_correo_duplicado(client):
    r = client.post("/auth/register", json={"rol": "beneficiario", "email": BENEF_LAURA, "password": "Abcdefg1",
                                            "nombre_apodo": "X"})
    assert r.status_code == 409


def test_registro_correo_duplicado_con_mayusculas(client):
    """No debería poder crearse una segunda cuenta con el mismo correo en mayúsculas."""
    r = client.post("/auth/register", json={"rol": "beneficiario", "email": BENEF_LAURA.upper(), "password": "Abcdefg1",
                                            "nombre_apodo": "X"})
    assert r.status_code == 409


def test_registro_prescriptor_sin_dispositivo(client):
    r = client.post("/auth/register", json={"rol": "prescriptor", "email": _email(), "password": "Abcdefg1",
                                            "nombre_completo": "X"})
    assert r.status_code == 400


def test_registro_prescriptor_dispositivo_inexistente(client):
    r = client.post("/auth/register", json={"rol": "prescriptor", "email": _email(), "password": "Abcdefg1",
                                            "nombre_completo": "X", "dispositivo_id": 99999})
    assert r.status_code == 400


def test_registro_falla_no_deja_usuario_a_medias(client, db):
    """Si el registro falla por un dato faltante, no debe quedar una cuenta creada."""
    from app.models.models import Usuario
    e = _email()
    r = client.post("/auth/register", json={"rol": "dispositivo", "email": e, "password": "Abcdefg1"})
    assert r.status_code == 400
    db.expire_all()
    assert db.query(Usuario).filter(Usuario.email == e).first() is None


def test_registro_pendiente_no_puede_entrar(client):
    e = _email()
    client.post("/auth/register", json={"rol": "dispositivo", "email": e, "password": "Abcdefg1",
                                        "nombre": "Casa QA", "politica_privacidad": True})
    r = client.post("/auth/login", json={"email": e, "password": "Abcdefg1"})
    assert r.status_code == 403 and "revisión" in r.json()["detail"]


# ── Verificación de correo ───────────────────────────────────────────────────
def test_verificar_email_token_invalido_redirige(client):
    r = client.get("/auth/verificar-email?token=falso", follow_redirects=False)
    assert r.status_code == 303 and "verificado=invalido" in r.headers["location"]


# ── Recuperación de contraseña ───────────────────────────────────────────────
def test_recuperar_respuesta_generica(client):
    a = client.post("/auth/recuperar-password", json={"email": BENEF_LAURA}).json()
    b = client.post("/auth/recuperar-password", json={"email": "noexiste@test.com"}).json()
    assert a == b


def test_resetear_token_vencido(client, db):
    from app.models.models import Usuario
    u = db.query(Usuario).filter(Usuario.email == BENEF_LAURA).first()
    u.password_reset_token = "tok-vencido"
    u.password_reset_token_expiry = datetime.now(timezone.utc) - timedelta(minutes=1)
    db.commit()
    r = client.post("/auth/resetear-password", json={"token": "tok-vencido", "nueva_password": "Nueva1234"})
    assert r.status_code == 400


def test_resetear_clave_debil(client):
    r = client.post("/auth/resetear-password", json={"token": "x", "nueva_password": "debil"})
    assert r.status_code == 422


def test_cambiar_password_actual_errada(client, login):
    h = login(PRESC_ANA)
    r = client.post("/auth/cambiar-password", headers=h, json={"password_actual": "mala", "password_nueva": "Nueva1234"})
    assert r.status_code == 400


# ── Sesiones ─────────────────────────────────────────────────────────────────
def test_sin_token_rechazado(client):
    assert client.get("/prescriptores/me").status_code in (401, 403)


def test_token_alterado_rechazado(client):
    r = client.get("/prescriptores/me", headers={"Authorization": "Bearer abc.def.ghi"})
    assert r.status_code == 401


def test_token_vencido_rechazado(client):
    from app.core.security import create_access_token
    t = create_access_token({"sub": "1", "rol": "admin"}, expires_delta=timedelta(seconds=-10))
    assert client.get("/admin/stats", headers={"Authorization": "Bearer " + t}).status_code == 401


def test_usuario_desactivado_pierde_acceso_con_token_vigente(client, login, db):
    """Si el admin desactiva una cuenta, su sesión abierta debe dejar de funcionar."""
    from app.models.models import Usuario, EstadoRegistro, Estados
    e = _email()
    client.post("/auth/register", json={"rol": "beneficiario", "email": e, "password": "Abcdefg1",
                                        "nombre_apodo": "QA Desactivar", "politica_privacidad": True})
    u = db.query(Usuario).filter(Usuario.email == e).first(); u.email_verificado = True; db.commit()
    h = login(e, "Abcdefg1")
    assert client.get("/beneficiarios/me", headers=h).status_code == 200
    est = EstadoRegistro(entidad_tipo="usuarios", entidad_id=u.id, estado=Estados.INACTIVO, motivo="qa")
    db.add(est); db.flush(); u.estado_actual_id = est.id; db.commit()
    assert client.get("/beneficiarios/me", headers=h).status_code == 403


# ── Regresión de correcciones QA ─────────────────────────────────────────────
def _benef_nuevo(client, db, login):
    from app.models.models import Usuario
    e = _email()
    client.post("/auth/register", json={"rol": "beneficiario", "email": e, "password": "Abcdefg1",
                                        "nombre_apodo": "QA Sesion", "politica_privacidad": True})
    u = db.query(Usuario).filter(Usuario.email == e).first(); u.email_verificado = True; db.commit()
    return e


def test_logout_invalida_el_token(client, login, db):
    e = _benef_nuevo(client, db, login); h = login(e, "Abcdefg1")
    assert client.post("/auth/logout", headers=h).status_code == 200
    assert client.get("/beneficiarios/me", headers=h).status_code == 401
    assert client.get("/beneficiarios/me", headers=login(e, "Abcdefg1", nuevo=True)).status_code == 200


def test_cambiar_password_entrega_token_nuevo(client, login, db):
    e = _benef_nuevo(client, db, login); h = login(e, "Abcdefg1")
    r = client.post("/auth/cambiar-password", headers=h, json={"password_actual": "Abcdefg1", "password_nueva": "Nueva1234"})
    assert r.status_code == 200 and r.json()["access_token"]
    assert client.get("/beneficiarios/me", headers=h).status_code == 401
    assert client.get("/beneficiarios/me", headers={"Authorization": "Bearer " + r.json()["access_token"]}).status_code == 200
