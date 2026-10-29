"""Búsqueda de negocios en OpenStreetMap (Nominatim para la ciudad + Overpass para los negocios).

Gratis y sin clave. Respeta las políticas de uso: identificarse con User-Agent y no abusar.
"""
import requests

NOMINATIM = "https://nominatim.openstreetmap.org/search"
# Servidores públicos de Overpass: si uno está saturado se prueba el siguiente
OVERPASS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
    "https://overpass.private.coffee/api/interpreter",
]
USER_AGENT = "MayerDigital-BuscadorClientes/1.0 (+https://mayerdigital.website)"

# Sector (como lo escribes en el panel) -> etiquetas de OpenStreetMap
SECTORES = {
    "peluquerías": ["shop=hairdresser"],
    "barberías": ["shop=hairdresser"],
    "centros de estética": ["shop=beauty"],
    "restaurantes": ["amenity=restaurant"],
    "cafeterías": ["amenity=cafe"],
    "bares": ["amenity=bar", "amenity=pub"],
    "panaderías": ["shop=bakery", "shop=pastry"],
    "carnicerías": ["shop=butcher"],
    "fruterías": ["shop=greengrocer"],
    "floristerías": ["shop=florist"],
    "talleres mecánicos": ["shop=car_repair"],
    "dentistas": ["amenity=dentist", "healthcare=dentist"],
    "fisioterapeutas": ["healthcare=physiotherapist"],
    "veterinarios": ["amenity=veterinary"],
    "gimnasios": ["leisure=fitness_centre"],
    "tiendas de ropa": ["shop=clothes"],
    "zapaterías": ["shop=shoes"],
    "ferreterías": ["shop=hardware", "shop=doityourself"],
    "ópticas": ["shop=optician"],
    "inmobiliarias": ["office=estate_agent"],
    "abogados": ["office=lawyer"],
    "gestorías": ["office=accountant", "office=tax_advisor"],
    "fontaneros": ["craft=plumber"],
    "electricistas": ["craft=electrician"],
    "academias": ["amenity=language_school", "amenity=training"],
    "tiendas de mascotas": ["shop=pet"],
    "lavanderías": ["shop=laundry", "shop=dry_cleaning"],
}


class ErrorOSM(Exception):
    pass


def sector_soportado(sector: str) -> bool:
    return sector.strip().lower() in SECTORES


def buscar(sector: str, ciudad: str, max_resultados: int = 150,
           session: requests.Session | None = None, log=print) -> list[dict]:
    etiquetas = SECTORES.get(sector.strip().lower())
    if not etiquetas:
        raise ErrorOSM(f"El sector «{sector}» no está en la lista de OpenStreetMap "
                       f"(edita SECTORES en buscador/fuentes/osm.py para añadirlo).")
    s = session or requests.Session()
    s.headers["User-Agent"] = USER_AGENT
    log(f"OpenStreetMap: buscando la ciudad «{ciudad}»…")
    lugar = _lugar(ciudad, s)
    # Consulta por rectángulo (rápida para los servidores) y luego filtramos por el contorno real aquí
    sur, oeste, norte, este = lugar["bbox"]
    filtros = "".join(f'nwr["{e.split("=")[0]}"="{e.split("=")[1]}"][name];' for e in etiquetas)
    consulta = (f"[out:json][timeout:90][bbox:{sur},{oeste},{norte},{este}];"
                f"({filtros});out center tags {max_resultados * 3};")
    errores = []
    for servidor in OVERPASS:
        nombre = servidor.split("/")[2]
        log(f"OpenStreetMap: consultando {nombre}…")
        try:
            r = s.post(servidor, data={"data": consulta}, timeout=(10, 100))
        except requests.RequestException as e:
            errores.append(f"{nombre}: {type(e).__name__}")
            continue
        if r.status_code == 200:
            try:
                elementos = r.json().get("elements", [])
            except ValueError:
                errores.append(f"{nombre}: respuesta no válida")
                continue
            negocios = [_normalizar(el) for el in elementos]
            if lugar["poligono"]:
                negocios = [n for n in negocios if n["lat"] is None or
                            dentro((n["lon"], n["lat"]), lugar["poligono"])]
            return negocios[:max_resultados]
        errores.append(f"{nombre}: HTTP {r.status_code}")
    raise ErrorOSM("Los servidores de OpenStreetMap no respondieron (" + "; ".join(errores) +
                   "). Suelen estar saturados a ratos: prueba de nuevo en unos minutos o busca una zona "
                   "más pequeña (por ejemplo «Chamberí, Madrid»).")


def _lugar(ciudad: str, s: requests.Session) -> dict:
    """Rectángulo y contorno de la ciudad según Nominatim."""
    r = s.get(NOMINATIM, params={"q": ciudad, "format": "json", "limit": 5, "countrycodes": "es",
                                 "polygon_geojson": 1, "polygon_threshold": 0.0005}, timeout=(10, 30))
    r.raise_for_status()
    resultados = r.json()
    # Preferimos una zona (relation: municipio, distrito, barrio…) antes que un punto
    for lugar in sorted(resultados, key=lambda x: x.get("osm_type") != "relation"):
        if lugar.get("boundingbox"):
            sur, norte, oeste, este = (float(v) for v in lugar["boundingbox"])
            geo = lugar.get("geojson") or {}
            poligono = None
            if geo.get("type") == "Polygon":
                poligono = [geo["coordinates"]]
            elif geo.get("type") == "MultiPolygon":
                poligono = geo["coordinates"]
            return {"bbox": (sur, oeste, norte, este), "poligono": poligono}
    raise ErrorOSM(f"No encontré la ciudad «{ciudad}» en OpenStreetMap.")


def _en_anillo(punto, anillo) -> bool:
    x, y = punto
    dentro_ = False
    j = len(anillo) - 1
    for i in range(len(anillo)):
        xi, yi = anillo[i][0], anillo[i][1]
        xj, yj = anillo[j][0], anillo[j][1]
        if (yi > y) != (yj > y) and x < (xj - xi) * (y - yi) / (yj - yi) + xi:
            dentro_ = not dentro_
        j = i
    return dentro_


def dentro(punto, poligonos) -> bool:
    """¿El punto (lon, lat) está dentro de algún polígono (anillo exterior menos huecos)?"""
    for anillos in poligonos:
        if anillos and _en_anillo(punto, anillos[0]) and not any(_en_anillo(punto, h) for h in anillos[1:]):
            return True
    return False


def _normalizar(el: dict) -> dict:
    t = el.get("tags", {})
    centro = el.get("center") or el
    calle = " ".join(x for x in (t.get("addr:street"), t.get("addr:housenumber")) if x)
    direccion = ", ".join(x for x in (calle, t.get("addr:postcode"), t.get("addr:city")) if x) or None
    redes = [v for k in ("contact:instagram", "contact:facebook", "facebook", "instagram") if (v := t.get(k))]
    return {
        "nombre": t.get("name", "").strip(),
        "direccion": direccion,
        "telefono": t.get("phone") or t.get("contact:phone") or t.get("contact:mobile"),
        "email": t.get("email") or t.get("contact:email"),
        "web": t.get("website") or t.get("contact:website") or t.get("url"),
        "rating": None,
        "num_resenas": None,
        "maps_url": f"https://www.openstreetmap.org/{el['type']}/{el['id']}",
        "lat": centro.get("lat"),
        "lon": centro.get("lon"),
        "redes": redes,
        "fuente": "osm",
    }
