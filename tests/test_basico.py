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


def test_verificar_casos(monkeypatch):
    import buscador.verificador as v
    monkeypatch.setattr(v, "existe_dominio", lambda host: host == "peluquerialola.com")
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


def test_dominio_inexistente_no_hace_peticion(monkeypatch):
    import buscador.verificador as v
    monkeypatch.setattr(v, "existe_dominio", lambda host: False)
    s = SesionFalsa({})
    assert verificar({"nombre": "Peluquería Lola", "redes": []}, session=s)["estado_web"] == "sin_web"
    assert s.llamadas == []


def test_osm_prueba_otro_servidor_si_falla():
    # Cuadrado de Madrid simplificado: lon -3.8..-3.6, lat 40.3..40.5
    cuadrado = [[[-3.8, 40.3], [-3.6, 40.3], [-3.6, 40.5], [-3.8, 40.5], [-3.8, 40.3]]]
    nominatim = Resp(json_data=[{"osm_type": "relation", "osm_id": 5326784,
                                 "boundingbox": ["40.3", "40.5", "-3.8", "-3.6"],
                                 "geojson": {"type": "Polygon", "coordinates": cuadrado}}])
    elementos = [{"type": "node", "id": 1, "lat": 40.4, "lon": -3.7, "tags": {"name": "Bar Pepe"}},
                 {"type": "node", "id": 2, "lat": 40.45, "lon": -3.9, "tags": {"name": "Bar de fuera"}}]
    s = SesionFalsa({"nominatim": nominatim,
                     "overpass-api.de": Resp(504),
                     "kumi.systems": Resp(json_data={"elements": elementos})})
    r = osm.buscar("bares", "Madrid", session=s, log=lambda m: None)
    assert [n["nombre"] for n in r] == ["Bar Pepe"]  # el de fuera del contorno se descarta
    consulta = s.llamadas[2][1]["data"]["data"]
    assert "[bbox:40.3,-3.8,40.5,-3.6]" in consulta and "area(" not in consulta


def test_dentro_con_huecos():
    exterior = [[0, 0], [10, 0], [10, 10], [0, 10], [0, 0]]
    hueco = [[4, 4], [6, 4], [6, 6], [4, 6], [4, 4]]
    assert osm.dentro((2, 2), [[exterior, hueco]])
    assert not osm.dentro((5, 5), [[exterior, hueco]])
    assert not osm.dentro((12, 5), [[exterior, hueco]])
    otra_isla = [[20, 0], [22, 0], [22, 2], [20, 2], [20, 0]]
    assert osm.dentro((21, 1), [[exterior], [otra_isla]])


def test_enlace_modelo(cfg):
    base = "https://mayerdigital.website/modelos"
    assert mensajes.enlace_modelo("peluquerías", base) == base + "/peluquerias/"
    assert mensajes.enlace_modelo("Peluqueria", base) == base + "/peluquerias/"
    assert mensajes.enlace_modelo("barberías", base) == base + "/barberias/"
    assert mensajes.enlace_modelo("bares", base) == base + "/bares/"
    assert mensajes.enlace_modelo("talleres mecánicos", base) == base + "/talleres-mecanicos/"
    assert mensajes.enlace_modelo("clínica dental", base) == base + "/dentistas/"
    assert mensajes.enlace_modelo("tiendas de mascotas", base) == base + "/tiendas-de-mascotas/"
    assert mensajes.enlace_modelo("joyerías", base) is None
    assert mensajes.enlace_modelo("peluquerías", "") is None
    n = {"nombre": "Bar Pepe", "ciudad": "Madrid", "sector": "bares", "telefono": "+34612345678", "redes": []}
    texto = mensajes.preparar(n, cfg)["texto"]
    assert "https://mayerdigital.website/modelos/bares/" in texto
    sin = mensajes.preparar({**n, "sector": "joyerías"}, cfg)["texto"]
    assert "modelos" not in sin and "\n\n\n" not in sin


def test_web_gratuita_blogspot(cfg):
    n = {"nombre": "The Clover Irish Tavern", "ciudad": "Madrid", "sector": "bares", "telefono": "+34612345678",
         "web_ficha": "https://theclovermirasierra.blogspot.com/p/donde-estamos.html", "redes": []}
    r = verificar(n, session=SesionFalsa({}))
    assert r["estado_web"] == "web_basica" and "Blogspot" in r["evidencia_web"]
    m = mensajes.preparar({**n, **r}, cfg)
    assert m["canal"] == "whatsapp"
    t = m["texto"]
    assert t.startswith("Buenos días.") and "Mi nombre es Emiliano Mayer, de Mayer Digital" in t
    assert "está en Blogspot, una plataforma gratuita" in t
    assert "https://mayerdigital.website/modelos/bares/" in t and "no volveré a escribirles" in t
    assert "español e inglés" in t
    assert "español e inglés" in mensajes.preparar({**n, **r, "email": "a@b.es"}, cfg)["texto"]
    assert "{" not in t
    for tipo in ("sin_web", "web_caida"):
        assert "{" not in mensajes.preparar({**n, "estado_web": tipo}, cfg)["texto"]


def test_purga_google_30_dias(tmp_path):
    from datetime import datetime, timedelta
    from buscador.db import DB
    db = DB(tmp_path / "p.db")
    base = {"ciudad": "Madrid", "sector": "bares", "direccion": "Calle X", "rating": 4.5, "num_resenas": 30,
            "maps_url": "https://maps", "lat": 40.4, "lon": -3.7, "redes": []}
    db.guardar({**base, "id": "g_nuevo", "nombre": "Bar A", "telefono": "+34600000001", "fuentes": "google", "place_id": "P1"})
    db.guardar({**base, "id": "g_contactado", "nombre": "Bar B", "telefono": "+34600000002", "fuentes": "google,osm", "place_id": "P2"})
    db.guardar({**base, "id": "g_reciente", "nombre": "Bar C", "fuentes": "google"})
    db.guardar({**base, "id": "solo_osm", "nombre": "Bar D", "fuentes": "osm"})
    db.registrar_envio("g_contactado", "whatsapp", "primero", "hola")
    db.actualizar("g_contactado", notas="Llamar en enero")
    viejo = (datetime.now() - timedelta(days=31)).isoformat(timespec="seconds")
    db.con.execute("UPDATE negocios SET google_obtenido_en=? WHERE id IN ('g_nuevo','g_contactado')", (viejo,))
    db.con.commit()

    assert db.purgar_google() == {"borrados": 1, "limpiados": 1}
    assert db.obtener("g_nuevo") is None
    b = db.obtener("g_contactado")
    assert b["nombre"] == "Bar B" and b["telefono"] == "+34600000002" and b["place_id"] == "P2"
    assert b["estado"] == "contactado" and b["notas"] == "Llamar en enero"
    assert b["rating"] is None and b["direccion"] is None and b["lat"] is None and b["google_obtenido_en"] is None
    assert db.obtener("g_reciente")["rating"] == 4.5          # menos de 30 días: intacto
    assert db.obtener("solo_osm")["direccion"] == "Calle X"    # OpenStreetMap: no se toca
    assert db.purgar_google() == {"borrados": 0, "limpiados": 0}

    # Volver a encontrarlo en Google rellena los datos y conserva tu historial
    db.guardar({**base, "id": "g_contactado", "nombre": "Bar B", "fuentes": "google", "rating": 4.6})
    b = db.obtener("g_contactado")
    assert b["rating"] == 4.6 and b["estado"] == "contactado" and b["google_obtenido_en"]


def test_migracion_bd_antigua(tmp_path):
    import sqlite3
    from buscador.db import DB
    ruta = tmp_path / "vieja.db"
    con = sqlite3.connect(ruta)
    con.execute("CREATE TABLE negocios (id TEXT PRIMARY KEY, nombre TEXT NOT NULL, fuentes TEXT, estado TEXT DEFAULT 'nuevo', redes TEXT)")
    con.execute("INSERT INTO negocios (id, nombre, fuentes) VALUES ('x', 'Viejo', 'osm')")
    con.commit(); con.close()
    db = DB(ruta)
    cols = {f[1] for f in db.con.execute("PRAGMA table_info(negocios)")}
    assert {"place_id", "google_obtenido_en"} <= cols
    assert db.obtener("x")["nombre"] == "Viejo"


def test_google_guarda_place_id():
    s = SesionFalsa({"places.googleapis.com": Resp(json_data={"places": [
        {"id": "ChIJabc", "displayName": {"text": "Bar Pepe"}, "nationalPhoneNumber": "612 34 56 78"}]})})
    r = google_places.buscar("bares", "Madrid", "KEY", session=s)
    assert r[0]["place_id"] == "ChIJabc"
