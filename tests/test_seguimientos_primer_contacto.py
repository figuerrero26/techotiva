"""Seguimientos, cierre de proceso, hoja de primer contacto y traslados."""
import uuid

from conftest import ADMIN, PRESC_FRANKIN, PRESC_ANA, DISP_FONTIBON, DISP_ENGATIVA, BENEF_LAURA


def _disp_id(db, email):
    from app.models.models import Dispositivo, Usuario
    return db.query(Dispositivo).join(Usuario, Usuario.id == Dispositivo.usuario_id).filter(Usuario.email == email).first().id


def _crear_benef_pc(client, h, disp_id, **extra):
    datos = {"dispositivo_id": disp_id, "nombre_apodo": f"QA {uuid.uuid4().hex[:6]}", "fecha_contacto": "2026-11-01",
             "politica_privacidad": "Sí", "emociones": "Miedo - Terror", "barrio": "Kennedy"}
    datos.update(extra)
    r = client.post("/primer-contacto/sin-cuenta", headers=h, json=datos)
    assert r.status_code == 201, r.text
    return r.json()


# ── Primer contacto ──────────────────────────────────────────────────────────
def test_pc_sin_privacidad_rechazado(client, login, db):
    r = client.post("/primer-contacto/sin-cuenta", headers=login(PRESC_FRANKIN),
                    json={"dispositivo_id": _disp_id(db, DISP_FONTIBON), "nombre_apodo": "X", "politica_privacidad": "No"})
    assert r.status_code == 422


def test_pc_a_nombre_de_otro_dispositivo_rechazado(client, login, db):
    r = client.post("/primer-contacto/sin-cuenta", headers=login(PRESC_FRANKIN),
                    json={"dispositivo_id": _disp_id(db, DISP_ENGATIVA), "nombre_apodo": "X", "politica_privacidad": "Sí"})
    assert r.status_code == 403


def test_pc_correo_ya_registrado(client, login, db):
    r = client.post("/primer-contacto/sin-cuenta", headers=login(PRESC_FRANKIN),
                    json={"dispositivo_id": _disp_id(db, DISP_FONTIBON), "nombre_apodo": "X",
                          "politica_privacidad": "Sí", "email": BENEF_LAURA})
    assert r.status_code == 409


def test_pc_html_rechazado(client, login, db):
    r = client.post("/primer-contacto/sin-cuenta", headers=login(PRESC_FRANKIN),
                    json={"dispositivo_id": _disp_id(db, DISP_FONTIBON), "nombre_apodo": "<b>X</b>", "politica_privacidad": "Sí"})
    assert r.status_code == 422


def test_pc_otro_dispositivo_no_lo_ve(client, login, db):
    pc = _crear_benef_pc(client, login(PRESC_FRANKIN), _disp_id(db, DISP_FONTIBON))
    assert client.get(f"/primer-contacto/{pc['id']}", headers=login(PRESC_ANA)).status_code == 403
    assert client.put(f"/primer-contacto/{pc['id']}", headers=login(PRESC_ANA), json={"emociones": None}).status_code == 403


def test_pc_edicion_borra_y_respeta_campos_bloqueados(client, login, db):
    h = login(PRESC_FRANKIN); pc = _crear_benef_pc(client, h, _disp_id(db, DISP_FONTIBON))
    r = client.put(f"/primer-contacto/{pc['id']}", headers=h, json={"emociones": None, "barrio": "HACK", "fecha_contacto": "2020-01-01"})
    d = r.json()
    assert r.status_code == 200 and d["emociones"] is None
    assert d["barrio"] == "Kennedy" and d["fecha_contacto"] == "2026-11-01"


def test_pc_inexistente(client, login):
    assert client.get("/primer-contacto/999999", headers=login(ADMIN)).status_code == 404


# ── Seguimientos ─────────────────────────────────────────────────────────────
def test_seguimiento_crear_y_listar(client, login, db):
    h = login(PRESC_FRANKIN); pc = _crear_benef_pc(client, h, _disp_id(db, DISP_FONTIBON))
    r = client.post("/prescriptores/seguimientos", headers=h, json={"beneficiario_id": pc["beneficiario_id"],
                                                                   "tipo_registro": "Visita", "observaciones": "Todo bien 😊 ñ"})
    assert r.status_code == 201
    lista = client.get(f"/prescriptores/seguimientos?beneficiario_id={pc['beneficiario_id']}", headers=h).json()
    assert any(s["observaciones"] == "Todo bien 😊 ñ" for s in lista)


def test_seguimiento_tipo_vacio_rechazado(client, login, db):
    h = login(PRESC_FRANKIN); pc = _crear_benef_pc(client, h, _disp_id(db, DISP_FONTIBON))
    r = client.post("/prescriptores/seguimientos", headers=h, json={"beneficiario_id": pc["beneficiario_id"], "tipo_registro": ""})
    assert r.status_code == 422


def test_seguimiento_beneficiario_inexistente(client, login):
    r = client.post("/prescriptores/seguimientos", headers=login(PRESC_FRANKIN), json={"beneficiario_id": 999999, "tipo_registro": "Visita"})
    assert r.status_code == 404


def test_cierre_de_proceso_bloquea_y_admin_reactiva(client, login, db):
    h = login(PRESC_FRANKIN); pc = _crear_benef_pc(client, h, _disp_id(db, DISP_FONTIBON)); bid = pc["beneficiario_id"]
    assert client.post("/prescriptores/seguimientos", headers=h, json={"beneficiario_id": bid, "tipo_registro": "Cierre de proceso"}).status_code == 201
    assert client.post("/prescriptores/seguimientos", headers=h, json={"beneficiario_id": bid, "tipo_registro": "Visita"}).status_code == 403
    from app.models.models import Beneficiario
    uid = db.query(Beneficiario).get(bid).usuario_id
    assert client.put(f"/admin/usuarios/{uid}/estado", headers=login(ADMIN), json={"status": "activo"}).status_code == 200
    assert client.post("/prescriptores/seguimientos", headers=h, json={"beneficiario_id": bid, "tipo_registro": "Visita"}).status_code == 201


def test_prescriptor_no_borra_seguimiento_ajeno(client, login, db):
    h = login(PRESC_FRANKIN); pc = _crear_benef_pc(client, h, _disp_id(db, DISP_FONTIBON))
    s = client.post("/prescriptores/seguimientos", headers=h, json={"beneficiario_id": pc["beneficiario_id"], "tipo_registro": "Visita"}).json()
    assert client.delete(f"/prescriptores/seguimientos/{s['id']}", headers=login(PRESC_ANA)).status_code == 403


# ── Traslado entre dispositivos ──────────────────────────────────────────────
def test_traslado_conserva_historial_y_quita_acceso_anterior(client, login, db):
    h = login(PRESC_FRANKIN); pc = _crear_benef_pc(client, h, _disp_id(db, DISP_FONTIBON)); bid = pc["beneficiario_id"]
    client.post("/prescriptores/seguimientos", headers=h, json={"beneficiario_id": bid, "tipo_registro": "Visita", "observaciones": "antes"})
    r = client.put(f"/admin/beneficiarios/{bid}/dispositivo", headers=login(ADMIN), json={"dispositivo_id": _disp_id(db, DISP_ENGATIVA)})
    assert r.status_code == 200
    assert client.post("/prescriptores/seguimientos", headers=h, json={"beneficiario_id": bid, "tipo_registro": "Visita"}).status_code == 403
    segs = client.get(f"/prescriptores/seguimientos?beneficiario_id={bid}", headers=login(PRESC_ANA)).json()
    assert any(s["observaciones"] == "antes" for s in segs)


# ── Integridad al eliminar ───────────────────────────────────────────────────
def test_eliminar_prescriptor_no_borra_historial_de_beneficiarios(client, login, db):
    """Eliminar la cuenta de un prescriptor no debe borrar los seguimientos que hizo a los beneficiarios."""
    from app.models.models import Seguimiento, Usuario
    e = f"presc_{uuid.uuid4().hex[:6]}@test.com"
    client.post("/auth/register", json={"rol": "prescriptor", "email": e, "password": "Abcdefg1",
                                        "nombre_completo": "Presc QA", "dispositivo_id": _disp_id(db, DISP_FONTIBON)})
    u = db.query(Usuario).filter(Usuario.email == e).first()
    ha = login(ADMIN)
    client.post(f"/admin/usuarios/{u.id}/aprobar", headers=ha)
    u.email_verificado = True; db.commit()
    hp = login(e, "Abcdefg1")
    pc = _crear_benef_pc(client, hp, _disp_id(db, DISP_FONTIBON))
    s = client.post("/prescriptores/seguimientos", headers=hp, json={"beneficiario_id": pc["beneficiario_id"], "tipo_registro": "Visita"}).json()
    r = client.delete(f"/admin/usuarios/{u.id}", headers=ha)
    db.expire_all()
    # o se impide la eliminación, o el historial queda intacto
    assert r.status_code == 409 or db.query(Seguimiento).get(s["id"]) is not None


def test_eliminar_cuenta_de_dispositivo_con_datos_no_deja_huerfanos(client, login, db):
    from app.models.models import Usuario
    disp_user = db.query(Usuario).filter(Usuario.email == DISP_ENGATIVA).first()
    r = client.delete(f"/admin/usuarios/{disp_user.id}", headers=login(ADMIN))
    assert r.status_code == 409   # tiene prescriptores, beneficiarios y registros asociados


def test_eliminar_prescriptor_sin_historial_si_se_permite(client, login, db):
    from app.models.models import Usuario
    e = f"presc_{uuid.uuid4().hex[:6]}@test.com"
    client.post("/auth/register", json={"rol": "prescriptor", "email": e, "password": "Abcdefg1",
                                        "nombre_completo": "Presc QA2", "dispositivo_id": _disp_id(db, DISP_FONTIBON)})
    u = db.query(Usuario).filter(Usuario.email == e).first()
    assert client.delete(f"/admin/usuarios/{u.id}", headers=login(ADMIN)).status_code == 204


def test_admin_eliminar_dispositivo_con_beneficiarios_rechazado(client, login, db):
    assert client.delete(f"/admin/dispositivos/{_disp_id(db, DISP_ENGATIVA)}", headers=login(ADMIN)).status_code == 409


def test_hoja_de_primer_contacto_no_se_puede_borrar(client, login, db):
    """La opción de borrar hojas se retiró de todos los perfiles; tampoco existe por API."""
    h = login(PRESC_FRANKIN); pc = _crear_benef_pc(client, h, _disp_id(db, DISP_FONTIBON))
    assert client.delete(f"/primer-contacto/{pc['id']}", headers=h).status_code == 405
    assert client.get(f"/primer-contacto/{pc['id']}", headers=h).status_code == 200
