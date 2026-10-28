from buscador import mensajes, telefonos
from buscador.fuentes import google_places, osm
from buscador.unificar import unificar
from buscador.verificador import coincide_nombre, es_no_propio, verificar
from conftest import Resp, SesionFalsa


def test_telefonos():
    assert telefonos.normalizar("612 34 56 78") == "+34612345678"
    assert telefonos.normalizar("+34 912 345 678") == "+34912345678"
    assert telefonos.normalizar("0034612345678") == "+34612345678"
    assert telefonos.normalizar("612345678; 912345678") == "+34612345678"
    assert telefonos.normalizar("123") is None
    assert telefonos.es_movil("+34612345678") and telefonos.es_movil("+34712345678")
    assert not telefonos.es_movil("+34912345678")
    assert telefonos.enlace_whatsapp("+34612345678", "Hola qué tal").startswith("https://wa.me/34612345678?text=Hola%20qu")


def test_google_normaliza_y_pagina():
    pag1 = {"places": [{"displayName": {"text": "Peluquería Lola"}, "nationalPhoneNumber": "612 34 56 78",
                        "rating": 4.8, "userRatingCount": 52, "businessStatus": "OPERATIONAL"},
                       {"displayName": {"text": "Cerrado"}, "businessStatus": "CLOSED_PERMANENTLY"}],
            "nextPageToken": "abc"}
    pag2 = {"places": [{"displayName": {"text": "Barbería Paco"}, "websiteUri": "https://barberiapaco.es"}]}
    s = SesionFalsa({"places.googleapis.com": [Resp(json_data=pag1), Resp(json_data=pag2)]})
    r = google_places.buscar("peluquerías", "Madrid", "KEY", session=s)
    assert [n["nombre"] for n in r] == ["Peluquería Lola", "Barbería Paco"]
    assert s.llamadas[1][1]["json"]["pageToken"] == "abc"
    assert s.llamadas[0][1]["headers"]["X-Goog-Api-Key"] == "KEY"


def test_osm_normaliza():
    el = {"type": "node", "id": 1, "lat": 40.4, "lon": -3.7,
          "tags": {"name": "Floristería Rosa", "contact:phone": "+34 655 000 111", "email": "Hola@Rosa.es",
                   "addr:street": "Calle Mayor", "addr:housenumber": "3", "contact:instagram": "https://instagram.com/rosa"}}
    n = osm._normalizar(el)
    assert n["telefono"] == "+34 655 000 111" and n["email"] == "Hola@Rosa.es"
    assert n["direccion"] == "Calle Mayor 3" and n["redes"] == ["https://instagram.com/rosa"]


def test_unificar_fusiona_por_telefono_y_nombre():
    g = [{"nombre": "Peluquería Lola", "telefono": "612 34 56 78", "web": None, "rating": 4.8, "fuente": "google",
          "lat": 40.4, "lon": -3.7, "redes": []}]
    o = [{"nombre": "Peluqueria Lola", "telefono": "+34612345678", "email": "LOLA@gmail.com", "web": None,
          "fuente": "osm", "lat": 40.4001, "lon": -3.7001, "redes": ["https://instagram.com/lola"]},
         {"nombre": "Otra", "telefono": None, "fuente": "osm", "lat": 40.5, "lon": -3.6}]
    r = unificar([g, o], sector="peluquerías", ciudad="Madrid")
    assert len(r) == 2
    lola = r[0]
    assert lola["email"] == "lola@gmail.com" and lola["rating"] == 4.8
    assert lola["fuentes"] == "google,osm" and lola["redes"] == ["https://instagram.com/lola"]


def test_no_propios_y_coincidencia():
    assert es_no_propio("https://www.instagram.com/lola") and es_no_propio("lola.business.site")
    assert not es_no_propio("https://peluquerialola.es")
    assert coincide_nombre("Peluquería Lola", "https://lolapeluqueria.com")
    assert not coincide_nombre("Peluquería Lola", "https://peluqueriasmadrid.com")


def test_verificar_casos():
    s = SesionFalsa({"peluquerialola.es": Resp(200, text="<title>Peluquería Lola</title>")})
    n = {"nombre": "Peluquería Lola", "web_ficha": "https://peluquerialola.es", "redes": []}
    assert verificar(n, session=s)["estado_web"] == "tiene_web"

    n = {"nombre": "Peluquería Lola", "web_ficha": "https://lola-caida.es", "redes": []}
    assert verificar(n, session=SesionFalsa({}))["estado_web"] == "web_caida"

    n = {"nombre": "Peluquería Lola", "web_ficha": "https://instagram.com/lola", "redes": []}
    r = verificar(n, session=SesionFalsa({}))
    assert r["estado_web"] == "sin_web" and r["redes"] == ["https://instagram.com/lola"]

    # Brave encuentra su web
    brave = Resp(json_data={"web": {"results": [
        {"url": "https://www.tripadvisor.es/lola", "title": "Peluquería Lola"},
        {"url": "https://lolapelu.com/", "title": "Peluquería Lola - Madrid"}]}})
    n = {"nombre": "Peluquería Lola", "ciudad": "Madrid", "web_ficha": None, "redes": []}
    r = verificar(n, session=SesionFalsa({"api.search.brave.com": brave}), brave_key="K")
    assert r["estado_web"] == "posible_web" and "lolapelu.com" in r["evidencia_web"]

    # Dominio típico existe y es suyo
    s = SesionFalsa({"peluquerialola.com": Resp(200, text="<title>Peluquería Lola</title> Bienvenidos a Lola")})
    assert verificar({"nombre": "Peluquería Lola", "redes": []}, session=s)["estado_web"] == "posible_web"


def test_mensajes(cfg):
    n = {"nombre": "Peluquería Lola", "ciudad": "Madrid", "sector": "peluquerías", "email": "a@b.es",
         "telefono": "+34612345678", "rating": 4.8, "num_resenas": 52, "estado_web": "sin_web", "redes": []}
    m = mensajes.preparar(n, cfg)
    assert m["canal"] == "email" and m["canales"] == ["email", "whatsapp", "llamar"]
    assert "Peluquería Lola" in m["asunto"] and "4,8 estrellas" in m["texto"] and "no volveré" in m["texto"]
    assert "600 11 12 22" in m["texto"]
    w = mensajes.preparar(n, cfg, canal="whatsapp")
    assert w["canal"] == "whatsapp" and w["asunto"] == ""
    caida = mensajes.preparar({**n, "email": None, "estado_web": "web_caida"}, cfg)
    assert "no carga" in caida["texto"] and caida["canal"] == "whatsapp"
    assert mensajes.canal_para({"telefono": "+34912345678"}) == "llamar"
