import time

import pytest

from app import crear_app
from buscador.db import DB
from buscador.fuentes import osm


@pytest.fixture
def cliente(cfg, monkeypatch):
    db = DB(cfg.ruta_db)
    monkeypatch.setattr(osm, "buscar", lambda sector, ciudad, session=None: [
        {"nombre": "Bar Pepe", "telefono": "612345678", "email": None, "web": None, "fuente": "osm",
         "lat": 40.4, "lon": -3.7, "redes": [], "maps_url": "https://osm.org/node/1"},
        {"nombre": "Café Luna", "telefono": "912345678", "email": "luna@gmail.com", "web": None, "fuente": "osm",
         "lat": 40.41, "lon": -3.71, "redes": []},
    ])
    import buscador.verificador as v
    monkeypatch.setattr(v, "responde", lambda url, session, timeout=8: (False, ""))
    app = crear_app(cfg, db)
    return app.test_client(), db


def _esperar(c):
    for _ in range(50):
        if not c.get("/api/trabajo").get_json()["activo"]:
            return
        time.sleep(0.1)
    raise AssertionError("el trabajo no terminó")


def test_flujo_completo(cliente):
    c, db = cliente
    assert c.post("/api/buscar", json={"sector": "bares", "ciudad": "madrid", "fuentes": ["osm"]}).status_code == 200
    _esperar(c)
    negocios = db.listar(estado_web="sin_web")
    assert {n["nombre"] for n in negocios} == {"Bar Pepe", "Café Luna"}
    assert all(n["ciudad"] == "Madrid" for n in negocios)
    html = c.get("/").get_data(as_text=True)
    assert "Bar Pepe" in html and "Café Luna" in html

    pepe = next(n for n in negocios if n["nombre"] == "Bar Pepe")
    m = c.get(f"/api/negocio/{pepe['id']}/mensaje").get_json()
    assert m["canal"] == "whatsapp"
    r = c.post(f"/api/negocio/{pepe['id']}/registrar", json={"canal": "whatsapp", "texto": m["texto"]}).get_json()
    assert r["enlace"].startswith("https://wa.me/34612345678?text=")
    assert db.obtener(pepe["id"])["estado"] == "contactado"

    luna = next(n for n in negocios if n["nombre"] == "Café Luna")
    m = c.get(f"/api/negocio/{luna['id']}/mensaje").get_json()
    assert m["canal"] == "email" and m["smtp"] is False
    r = c.post(f"/api/negocio/{luna['id']}/registrar",
               json={"canal": "email", "asunto": m["asunto"], "texto": m["texto"]}).get_json()
    assert r["enlace"].startswith("mailto:luna@gmail.com?subject=")

    # Límite diario (2 en el test)
    r = c.post(f"/api/negocio/{luna['id']}/registrar", json={"canal": "email", "texto": "x"})
    assert r.status_code == 429

    # Volver a buscar no pisa el estado
    c.post("/api/buscar", json={"sector": "bares", "ciudad": "Madrid", "fuentes": ["osm"]})
    _esperar(c)
    assert db.obtener(pepe["id"])["estado"] == "contactado"

    assert "Bar Pepe" in c.get("/exportar.csv").get_data(as_text=True)


def test_no_contactar(cliente):
    c, db = cliente
    c.post("/api/buscar", json={"sector": "bares", "ciudad": "Madrid", "fuentes": ["osm"]})
    _esperar(c)
    n = db.listar()[0]
    assert c.post(f"/api/negocio/{n['id']}/estado", json={"estado": "no_contactar"}).status_code == 200
    r = c.post(f"/api/negocio/{n['id']}/registrar", json={"canal": "whatsapp", "texto": "x"})
    assert r.status_code == 403
    assert c.post(f"/api/negocio/{n['id']}/estado", json={"estado": "inventado"}).status_code == 400


def test_validaciones(cliente):
    c, _ = cliente
    assert c.post("/api/buscar", json={"sector": "", "ciudad": "Madrid", "fuentes": ["osm"]}).status_code == 400
    assert c.get("/api/negocio/nada/mensaje").status_code == 404
