"""Actividades, inscripciones y perfil del beneficiario."""
import threading
from datetime import date, timedelta

from conftest import DISP_FONTIBON, DISP_ENGATIVA, BENEF_LAURA, BENEF_YEIMY, ADMIN


def _crear_actividad(client, h, **extra):
    datos = {"nombre": "QA Taller", "tipo": "Deportivo", "lugar": "Parque", "hora": "10:00",
             "fecha_inicio": (date.today() + timedelta(days=7)).isoformat(),
             "descripcion": "Traer agua", "cupo_maximo": 10}
    datos.update(extra)
    r = client.post("/actividades/", headers=h, json=datos)
    assert r.status_code == 201, r.text
    return r.json()


# ── CRUD de actividades ──────────────────────────────────────────────────────
def test_crear_actividad_guarda_todos_los_campos(client, login):
    a = _crear_actividad(client, login(DISP_FONTIBON))
    assert a["fecha_inicio"] and a["descripcion"] == "Traer agua" and a["cupo_maximo"] == 10


def test_editar_actividad_propia(client, login):
    h = login(DISP_FONTIBON); a = _crear_actividad(client, h)
    r = client.put(f"/actividades/{a['id']}", headers=h, json={"lugar": "Salón comunal"})
    assert r.status_code == 200 and r.json()["lugar"] == "Salón comunal"


def test_no_edita_actividad_de_otro_dispositivo(client, login):
    a = _crear_actividad(client, login(DISP_FONTIBON))
    assert client.put(f"/actividades/{a['id']}", headers=login(DISP_ENGATIVA), json={"lugar": "x"}).status_code == 403


def test_actividad_cupo_negativo_rechazado(client, login):
    r = client.post("/actividades/", headers=login(DISP_FONTIBON), json={"nombre": "X", "cupo_maximo": -5})
    assert r.status_code == 422


def test_eliminar_actividad_con_inscritos_borra_inscripciones(client, login, db):
    from app.models.models import Inscripcion
    h = login(DISP_FONTIBON); a = _crear_actividad(client, h)
    assert client.post("/beneficiarios/inscribirse", headers=login(BENEF_LAURA), json={"actividad_id": a["id"]}).status_code == 201
    assert client.delete(f"/actividades/{a['id']}", headers=h).status_code in (200, 204)
    db.expire_all()
    assert db.query(Inscripcion).filter(Inscripcion.actividad_id == a["id"]).count() == 0


def test_actividad_inexistente(client, login):
    assert client.put("/actividades/999999", headers=login(DISP_FONTIBON), json={"lugar": "x"}).status_code == 404


# ── Inscripciones ────────────────────────────────────────────────────────────
def test_inscribirse_y_desinscribirse(client, login):
    a = _crear_actividad(client, login(DISP_FONTIBON)); h = login(BENEF_LAURA)
    assert client.post("/beneficiarios/inscribirse", headers=h, json={"actividad_id": a["id"]}).status_code == 201
    assert a["id"] in [x["id"] for x in client.get("/beneficiarios/mis-actividades", headers=h).json()]
    assert client.delete(f"/beneficiarios/desinscribirse/{a['id']}", headers=h).status_code == 200


def test_inscripcion_duplicada(client, login):
    a = _crear_actividad(client, login(DISP_FONTIBON)); h = login(BENEF_LAURA)
    client.post("/beneficiarios/inscribirse", headers=h, json={"actividad_id": a["id"]})
    assert client.post("/beneficiarios/inscribirse", headers=h, json={"actividad_id": a["id"]}).status_code == 400


def test_inscripcion_doble_clic_simultaneo(client, login, db):
    """Dos solicitudes al mismo tiempo (doble clic) no deben crear dos inscripciones."""
    from app.models.models import Inscripcion
    a = _crear_actividad(client, login(DISP_FONTIBON)); h = login(BENEF_YEIMY)
    hilos = [threading.Thread(target=lambda: client.post("/beneficiarios/inscribirse", headers=h,
                                                          json={"actividad_id": a["id"]})) for _ in range(6)]
    [t.start() for t in hilos]; [t.join() for t in hilos]
    db.expire_all()
    assert db.query(Inscripcion).filter(Inscripcion.actividad_id == a["id"]).count() == 1


def test_inscripcion_sin_cupo(client, login):
    a = _crear_actividad(client, login(DISP_FONTIBON), cupo_maximo=1)
    assert client.post("/beneficiarios/inscribirse", headers=login(BENEF_LAURA), json={"actividad_id": a["id"]}).status_code == 201
    assert client.post("/beneficiarios/inscribirse", headers=login(BENEF_YEIMY), json={"actividad_id": a["id"]}).status_code == 403


def test_no_se_inscribe_a_actividad_pasada(client, login):
    a = _crear_actividad(client, login(DISP_FONTIBON), fecha_inicio=(date.today() - timedelta(days=2)).isoformat())
    assert client.post("/beneficiarios/inscribirse", headers=login(BENEF_LAURA), json={"actividad_id": a["id"]}).status_code == 400


def test_no_se_inscribe_a_actividad_desactivada(client, login):
    hd = login(DISP_FONTIBON); a = _crear_actividad(client, hd)
    client.put(f"/actividades/{a['id']}", headers=hd, json={"activa": False})
    assert client.post("/beneficiarios/inscribirse", headers=login(BENEF_LAURA), json={"actividad_id": a["id"]}).status_code == 400


def test_inscribirse_a_actividad_inexistente(client, login):
    assert client.post("/beneficiarios/inscribirse", headers=login(BENEF_LAURA), json={"actividad_id": 999999}).status_code == 404


def test_desinscribirse_sin_estar_inscrito(client, login):
    assert client.delete("/beneficiarios/desinscribirse/999999", headers=login(BENEF_LAURA)).status_code == 404


# ── Perfil del beneficiario ──────────────────────────────────────────────────
def test_beneficiario_edita_su_perfil(client, login):
    h = login(BENEF_LAURA)
    r = client.put("/beneficiarios/me", headers=h, json={"telefono": "300 111 2233"})
    assert r.status_code == 200 and r.json()["telefono"] == "300 111 2233"


def test_beneficiario_no_puede_cambiarse_de_dispositivo(client, login, db):
    """El dispositivo lo asigna el admin; el beneficiario no debe poder cambiarlo desde su perfil."""
    from app.models.models import Beneficiario, Usuario
    b = db.query(Beneficiario).join(Usuario).filter(Usuario.email == BENEF_LAURA).first()
    original = b.dispositivo_id
    otro = 2 if original != 2 else 1
    client.put("/beneficiarios/me", headers=login(BENEF_LAURA), json={"dispositivo_id": otro})
    db.expire_all()
    assert db.query(Beneficiario).get(b.id).dispositivo_id == original
