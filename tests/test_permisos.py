"""Control de acceso: cada rol solo puede hacer lo que le corresponde."""
import pytest

from conftest import ADMIN, PRESC_ANA, PRESC_FRANKIN, BENEF_LAURA, DISP_FONTIBON, DISP_ENGATIVA

ENDPOINTS_ADMIN = [
    ("get", "/admin/stats"), ("get", "/admin/usuarios"), ("get", "/admin/alertas"),
    ("get", "/admin/dispositivos"), ("get", "/admin/indicadores"), ("get", "/admin/indicadores/spa"),
    ("get", "/admin/exportar-todo"), ("get", "/admin/sesiones-activas"), ("get", "/admin/beneficiarios"),
]


@pytest.mark.parametrize("rol_email", [PRESC_ANA, BENEF_LAURA, DISP_FONTIBON])
@pytest.mark.parametrize("metodo,ruta", ENDPOINTS_ADMIN)
def test_no_admin_no_accede_a_endpoints_de_admin(client, login, rol_email, metodo, ruta):
    r = getattr(client, metodo)(ruta, headers=login(rol_email))
    assert r.status_code == 403


@pytest.mark.parametrize("metodo,ruta", ENDPOINTS_ADMIN)
def test_admin_accede(client, login, metodo, ruta):
    assert getattr(client, metodo)(ruta, headers=login(ADMIN)).status_code == 200


def test_beneficiario_no_crea_seguimientos(client, login):
    r = client.post("/prescriptores/seguimientos", headers=login(BENEF_LAURA),
                    json={"beneficiario_id": 1, "tipo_registro": "Visita"})
    assert r.status_code == 403


def test_beneficiario_no_crea_actividades(client, login):
    r = client.post("/actividades/", headers=login(BENEF_LAURA), json={"nombre": "X"})
    assert r.status_code == 403


def test_prescriptor_no_crea_actividades(client, login):
    r = client.post("/actividades/", headers=login(PRESC_ANA), json={"nombre": "X"})
    assert r.status_code == 403


def test_beneficiario_no_ve_primer_contacto(client, login):
    assert client.get("/primer-contacto/", headers=login(BENEF_LAURA)).status_code == 403


def test_dispositivo_no_edita_otro_dispositivo(client, login, db):
    from app.models.models import Dispositivo, Usuario
    otro = db.query(Dispositivo).join(Usuario, Usuario.id == Dispositivo.usuario_id).filter(Usuario.email == DISP_ENGATIVA).first()
    r = client.put(f"/dispositivos/{otro.id}", headers=login(DISP_FONTIBON), json={"nombre": "Hackeado"})
    assert r.status_code == 403


def test_dispositivo_no_lista_beneficiarios_de_otro(client, login, db):
    from app.models.models import Dispositivo, Usuario
    otro = db.query(Dispositivo).join(Usuario, Usuario.id == Dispositivo.usuario_id).filter(Usuario.email == DISP_ENGATIVA).first()
    assert client.get(f"/dispositivos/{otro.id}/beneficiarios-detalle", headers=login(DISP_FONTIBON)).status_code == 403


def test_estadisticas_de_dispositivo_no_visibles_para_otros(client, login, db):
    """Un beneficiario no debería poder consultar las estadísticas internas de cualquier dispositivo."""
    from app.models.models import Dispositivo, Usuario
    otro = db.query(Dispositivo).join(Usuario, Usuario.id == Dispositivo.usuario_id).filter(Usuario.email == DISP_ENGATIVA).first()
    assert client.get(f"/dispositivos/{otro.id}/estadisticas", headers=login(BENEF_LAURA)).status_code == 403


def test_dispositivo_no_aprueba_prescriptores_de_otro(client, login, db):
    from app.models.models import Dispositivo, Usuario
    otro = db.query(Dispositivo).join(Usuario, Usuario.id == Dispositivo.usuario_id).filter(Usuario.email == DISP_ENGATIVA).first()
    r = client.post(f"/dispositivos/{otro.id}/prescriptores/1/aprobar", headers=login(DISP_FONTIBON))
    assert r.status_code == 403


def test_prescriptor_no_ve_inscritos(client, login):
    assert client.get("/actividades/1/inscritos", headers=login(PRESC_FRANKIN)).status_code in (403, 404)


def test_2fa_solo_admin(client, login):
    assert client.get("/auth/2fa", headers=login(PRESC_ANA)).status_code == 403
