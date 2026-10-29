"""Comprueba, una por una, las conexiones que usa el buscador.  Uso:  python diagnostico.py"""
import sys
import time

import requests

from buscador.config import cargar_config
from buscador.fuentes import osm

OK, MAL = "  [OK] ", "  [FALLO] "


def probar(nombre, funcion):
    t = time.monotonic()
    try:
        detalle = funcion()
        print(f"{OK}{nombre} ({time.monotonic() - t:.1f}s) {detalle or ''}")
        return True
    except Exception as e:  # noqa: BLE001
        print(f"{MAL}{nombre} ({time.monotonic() - t:.1f}s) -> {type(e).__name__}: {str(e)[:300]}")
        return False


def main():
    cfg = cargar_config()
    ciudad = sys.argv[1] if len(sys.argv) > 1 else "Madrid"
    s = requests.Session()
    s.headers["User-Agent"] = osm.USER_AGENT
    print(f"Python {sys.version.split()[0]} · requests {requests.__version__}\n")

    print("1) Conexión a internet")
    probar("google.com", lambda: s.get("https://www.google.com", timeout=10).status_code)

    print("\n2) OpenStreetMap")
    area = {}

    def nominatim():
        area.update(osm._lugar(ciudad, s))
        return f"ciudad «{ciudad}» -> rectángulo {area['bbox']}"
    probar("Nominatim (buscar la ciudad)", nominatim)
    if area:
        sur, oeste, norte, este = area["bbox"]
        consulta = f'[out:json][timeout:25][bbox:{sur},{oeste},{norte},{este}];nwr["shop"="hairdresser"][name];out center tags 5;'
        for servidor in osm.OVERPASS:
            def overpass(servidor=servidor):
                r = s.post(servidor, data={"data": consulta}, timeout=(10, 40))
                if r.status_code != 200:
                    raise RuntimeError(f"HTTP {r.status_code}: {r.text[:200]}")
                return f"{len(r.json().get('elements', []))} peluquerías de prueba"
            probar(f"Overpass {servidor.split('/')[2]}", overpass)

    print("\n3) Google Places")
    if not cfg.google_key:
        print("  [--] Sin GOOGLE_PLACES_API_KEY en el .env (no se usa Google)")
    else:
        from buscador.fuentes import google_places
        probar("Places API (New)", lambda: f"{len(google_places.buscar('peluquerías', ciudad, cfg.google_key, max_resultados=5, session=requests.Session()))} resultados")

    print("\n4) Brave Search")
    if not cfg.brave_key:
        print("  [--] Sin BRAVE_API_KEY (opcional)")
    else:
        from buscador.verificador import buscar_en_web
        probar("Brave Search", lambda: f"{len(buscar_en_web('Mayer Digital', 'Madrid', cfg.brave_key, requests.Session()))} resultados")

    print("\nCopia todo este texto y envíalo para revisarlo.")


if __name__ == "__main__":
    main()
