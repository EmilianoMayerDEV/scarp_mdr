"""Búsqueda de negocios en OpenStreetMap (Nominatim para la ciudad + Overpass para los negocios).

Gratis y sin clave. Respeta las políticas de uso: identificarse con User-Agent y no abusar.
"""
import requests

NOMINATIM = "https://nominatim.openstreetmap.org/search"
OVERPASS = "https://overpass-api.de/api/interpreter"
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


def buscar(sector: str, ciudad: str, max_resultados: int = 200,
           session: requests.Session | None = None) -> list[dict]:
    etiquetas = SECTORES.get(sector.strip().lower())
    if not etiquetas:
        raise ErrorOSM(f"El sector «{sector}» no está en la lista de OpenStreetMap "
                       f"(edita SECTORES en buscador/fuentes/osm.py para añadirlo).")
    s = session or requests.Session()
    s.headers["User-Agent"] = USER_AGENT
    area = _area_ciudad(ciudad, s)
    filtros = "".join(f'nwr[{e.split("=")[0]}="{e.split("=")[1]}"][name](area.a);' for e in etiquetas)
    consulta = f"[out:json][timeout:90];area({area})->.a;({filtros});out center tags {max_resultados};"
    r = s.post(OVERPASS, data={"data": consulta}, timeout=120)
    if r.status_code != 200:
        raise ErrorOSM(f"Overpass respondió {r.status_code}. Prueba de nuevo en un minuto.")
    return [_normalizar(el) for el in r.json().get("elements", [])]


def _area_ciudad(ciudad: str, s: requests.Session) -> int:
    r = s.get(NOMINATIM, params={"q": ciudad, "format": "json", "limit": 5, "countrycodes": "es"}, timeout=20)
    r.raise_for_status()
    for lugar in r.json():
        if lugar.get("osm_type") == "relation":
            return 3600000000 + int(lugar["osm_id"])
    raise ErrorOSM(f"No encontré la ciudad «{ciudad}» en OpenStreetMap.")


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
