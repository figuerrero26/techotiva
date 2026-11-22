"""Funciones del admin, exportación, entradas extremas y seguridad general."""
import io
import uuid

from conftest import ADMIN, PRESC_ANA, BENEF_LAURA, DISP_FONTIBON


def test_stats_e_indicadores(client, login):
    h = login(ADMIN)
    assert client.get("/admin/stats", headers=h).json()["total_prescriptores"] >= 2
    ind = client.get("/admin/indicadores", headers=h).json()
    assert {"total_beneficiarios", "spa", "emociones", "cobertura"} <= ind.keys()


def test_exportar_excel_sin_secretos(client, login):
    from openpyxl import load_workbook
    r = client.get("/admin/exportar-todo", headers=login(ADMIN))
    assert r.status_code == 200
    wb = load_workbook(io.BytesIO(r.content))
    texto = " ".join(str(c.value) for ws in wb.worksheets for row in ws.iter_rows() for c in row if c.value)
    assert "$2b$" not in texto and "password" not in texto.lower()
    assert "Primer contacto" in wb.sheetnames


def test_rechazar_solo_pendientes(client, login, db):
    from app.models.models import Usuario
    activo = db.query(Usuario).filter(Usuario.email == PRESC_ANA).first()
    assert client.post(f"/admin/usuarios/{activo.id}/rechazar", headers=login(ADMIN)).status_code == 400


def test_admin_no_se_cambia_su_propio_estado(client, login, db):
    from app.models.models import Usuario
    adm = db.query(Usuario).filter(Usuario.email == ADMIN).first()
    assert client.put(f"/admin/usuarios/{adm.id}/estado", headers=login(ADMIN), json={"status": "inactivo"}).status_code == 400


def test_admin_no_se_elimina_a_si_mismo(client, login, db):
    from app.models.models import Usuario
    adm = db.query(Usuario).filter(Usuario.email == ADMIN).first()
    assert client.delete(f"/admin/usuarios/{adm.id}", headers=login(ADMIN)).status_code == 400


def test_cambio_de_rol_crea_el_perfil(client, login, db):
    """Al pasar un beneficiario a prescriptor se crea su perfil con su nombre y su dispositivo."""
    from app.models.models import Usuario, Prescriptor, Beneficiario
    e = f"rol_{uuid.uuid4().hex[:6]}@test.com"
    client.post("/auth/register", json={"rol": "beneficiario", "email": e, "password": "Abcdefg1",
                                        "nombre_apodo": "QA Rol", "politica_privacidad": True})
    u = db.query(Usuario).filter(Usuario.email == e).first()
    b = db.query(Beneficiario).filter(Beneficiario.usuario_id == u.id).first(); b.dispositivo_id = 1; db.commit()
    r = client.put(f"/admin/usuarios/{u.id}/rol", headers=login(ADMIN), json={"rol": "prescriptor"})
    assert r.status_code == 200 and r.json()["rol"] == "prescriptor"
    db.expire_all()
    p = db.query(Prescriptor).filter(Prescriptor.usuario_id == u.id).first()
    assert p and p.nombre_completo == "QA Rol" and p.dispositivo_id == 1 and p.estado == "activo"
    # sin proceso, su perfil de beneficiario se retira (ya no cuenta como beneficiario)
    assert db.query(Beneficiario).filter(Beneficiario.usuario_id == u.id).first() is None


def test_beneficiario_con_proceso_no_cambia_de_rol(client, login, db):
    """Si ya tiene hoja de primer contacto o seguimientos, no puede pasar a otro rol."""
    from app.models.models import Usuario, Beneficiario
    e = f"rol_{uuid.uuid4().hex[:6]}@test.com"
    r = client.post("/primer-contacto/sin-cuenta", headers=login(ADMIN),
                    json={"dispositivo_id": 1, "nombre_apodo": "QA Proceso", "politica_privacidad": "Sí", "email": e})
    assert r.status_code == 201, r.text
    u = db.query(Usuario).filter(Usuario.email == e).first()
    r = client.put(f"/admin/usuarios/{u.id}/rol", headers=login(ADMIN), json={"rol": "prescriptor"})
    assert r.status_code == 400 and "primer contacto" in r.json()["detail"]
    db.expire_all()
    assert db.query(Usuario).get(u.id).rol == "beneficiario"
    assert db.query(Beneficiario).filter(Beneficiario.usuario_id == u.id).first() is not None


def test_prescriptor_con_avances_no_cambia_de_rol(client, login, db):
    from app.models.models import Usuario
    from conftest import PRESC_FRANKIN
    h = login(PRESC_FRANKIN)
    r = client.post("/primer-contacto/sin-cuenta", headers=h,
                    json={"dispositivo_id": 1, "nombre_apodo": "QA Avance", "politica_privacidad": "Sí"})
    assert r.status_code == 201, r.text
    u = db.query(Usuario).filter(Usuario.email == PRESC_FRANKIN).first()
    r = client.put(f"/admin/usuarios/{u.id}/rol", headers=login(ADMIN), json={"rol": "beneficiario"})
    assert r.status_code == 400 and "prescriptor" in r.json()["detail"]


def test_dispositivo_con_datos_no_cambia_de_rol(client, login, db):
    from app.models.models import Usuario
    from conftest import DISP_ENGATIVA
    u = db.query(Usuario).filter(Usuario.email == DISP_ENGATIVA).first()
    r = client.put(f"/admin/usuarios/{u.id}/rol", headers=login(ADMIN), json={"rol": "prescriptor"})
    assert r.status_code == 400 and "dispositivo" in r.json()["detail"]


def test_prescriptor_sin_avances_si_cambia_de_rol(client, login, db):
    from app.models.models import Usuario, Prescriptor, Beneficiario
    e = f"presc_{uuid.uuid4().hex[:6]}@test.com"
    client.post("/auth/register", json={"rol": "prescriptor", "email": e, "password": "Abcdefg1",
                                        "nombre_completo": "Presc Nuevo", "dispositivo_id": 1})
    u = db.query(Usuario).filter(Usuario.email == e).first()
    r = client.put(f"/admin/usuarios/{u.id}/rol", headers=login(ADMIN), json={"rol": "beneficiario"})
    assert r.status_code == 200
    db.expire_all()
    assert db.query(Prescriptor).filter(Prescriptor.usuario_id == u.id).first() is None
    b = db.query(Beneficiario).filter(Beneficiario.usuario_id == u.id).first()
    assert b and b.nombre_apodo == "Presc Nuevo" and b.dispositivo_id == 1


def test_rol_admin_no_se_asigna_ni_se_quita(client, login, db):
    from app.models.models import Usuario
    e = f"rol_{uuid.uuid4().hex[:6]}@test.com"
    client.post("/auth/register", json={"rol": "beneficiario", "email": e, "password": "Abcdefg1",
                                        "nombre_apodo": "QA Admin", "politica_privacidad": True})
    u = db.query(Usuario).filter(Usuario.email == e).first()
    r = client.put(f"/admin/usuarios/{u.id}/rol", headers=login(ADMIN), json={"rol": "admin"})
    assert r.status_code == 400 and "administrador" in r.json()["detail"]
    # un segundo admin (creado a mano) tampoco pierde el rol desde la plataforma
    u.rol = "admin"; db.commit()
    r = client.put(f"/admin/usuarios/{u.id}/rol", headers=login(ADMIN), json={"rol": "beneficiario"})
    assert r.status_code == 400


def test_usuario_inexistente(client, login):
    assert client.put("/admin/usuarios/999999/estado", headers=login(ADMIN), json={"status": "activo"}).status_code == 404


def test_estado_invalido(client, login, db):
    from app.models.models import Usuario
    u = db.query(Usuario).filter(Usuario.email == PRESC_ANA).first()
    assert client.put(f"/admin/usuarios/{u.id}/estado", headers=login(ADMIN), json={"status": "hackeado"}).status_code == 422


# ── Entradas extremas ────────────────────────────────────────────────────────
def test_texto_muy_largo_rechazado_o_controlado(client, login):
    """Un texto enorme no debe tumbar el servidor (500)."""
    r = client.put("/beneficiarios/me", headers=login(BENEF_LAURA), json={"descripcion": "a" * 200_000})
    assert r.status_code in (200, 413, 422)


def test_caracteres_especiales_y_emojis_se_guardan(client, login):
    h = login(BENEF_LAURA)
    txt = "Ñandú 🚀 José — «hola» 'comillas' \"dobles\" & %"
    r = client.put("/beneficiarios/me", headers=h, json={"descripcion": txt})
    assert r.status_code == 200
    assert client.get("/beneficiarios/me", headers=h).json()["descripcion"] == txt


def test_tipos_de_dato_incorrectos(client, login):
    r = client.post("/beneficiarios/inscribirse", headers=login(BENEF_LAURA), json={"actividad_id": "abc"})
    assert r.status_code == 422


def test_ids_negativos(client, login):
    assert client.get("/primer-contacto/-1", headers=login(ADMIN)).status_code == 404


def test_html_en_cualquier_campo_rechazado(client, login):
    r = client.put("/prescriptores/me", headers=login(PRESC_ANA), json={"nombre_completo": "x\" onmouseover=\"alert(1)\" <i>"})
    assert r.status_code == 422


def test_inyeccion_sql_en_busqueda_no_afecta(client, login):
    r = client.get("/actividades/?tipo=' OR '1'='1")
    assert r.status_code == 200 and r.json() == []


def test_error_interno_no_expone_trazas(client):
    r = client.get("/ruta-que-no-existe")
    assert r.status_code == 404 and "Traceback" not in r.text


def test_encabezados_de_seguridad(client):
    r = client.get("/login")
    assert r.headers["x-frame-options"] == "DENY" and r.headers["x-content-type-options"] == "nosniff"


def test_paginas_cargan(client):
    for p in ["/login", "/dashboard", "/usuarios", "/actividades", "/reportes", "/perfil", "/notificaciones",
              "/configuracion", "/mis-actividades", "/mapa", "/reportar-info", "/roles", "/dispositivos-admin",
              "/mis-prescriptores", "/mis-seguimientos"]:
        assert client.get(p).status_code == 200, p
