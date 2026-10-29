"""Búsqueda de negocios con Google Places API (New) - Text Search.

Documentación: https://developers.google.com/maps/documentation/places/web-service/text-search
"""
import requests

URL = "https://places.googleapis.com/v1/places:searchText"
CAMPOS = ",".join([
    "places.id", "places.displayName", "places.formattedAddress", "places.nationalPhoneNumber",
    "places.internationalPhoneNumber", "places.websiteUri", "places.rating", "places.userRatingCount",
    "places.googleMapsUri", "places.businessStatus", "places.location", "nextPageToken",
])


class ErrorGoogle(Exception):
    pass


def buscar(sector: str, ciudad: str, api_key: str, max_resultados: int = 60,
           session: requests.Session | None = None) -> list[dict]:
    """Devuelve hasta `max_resultados` negocios (Google da como máximo 60 por consulta)."""
    s = session or requests.Session()
    cabeceras = {"X-Goog-Api-Key": api_key, "X-Goog-FieldMask": CAMPOS, "Content-Type": "application/json"}
    cuerpo = {"textQuery": f"{sector} en {ciudad}", "languageCode": "es", "regionCode": "ES", "pageSize": 20}
    resultados: list[dict] = []
    while len(resultados) < max_resultados:
        r = s.post(URL, json=cuerpo, headers=cabeceras, timeout=20)
        if r.status_code != 200:
            try:
                msg = r.json().get("error", {}).get("message", r.text)
            except ValueError:
                msg = r.text
            raise ErrorGoogle(f"Google Places respondió {r.status_code}: {msg}")
        datos = r.json()
        for p in datos.get("places", []):
            if p.get("businessStatus", "OPERATIONAL") != "OPERATIONAL":
                continue  # cerrados temporal o permanentemente
            resultados.append(_normalizar(p))
        token = datos.get("nextPageToken")
        if not token:
            break
        cuerpo["pageToken"] = token
    return resultados[:max_resultados]


def _normalizar(p: dict) -> dict:
    loc = p.get("location") or {}
    return {
        "nombre": (p.get("displayName") or {}).get("text", "").strip(),
        "direccion": p.get("formattedAddress"),
        "telefono": p.get("internationalPhoneNumber") or p.get("nationalPhoneNumber"),
        "email": None,  # Google no publica correos
        "web": p.get("websiteUri"),
        "rating": p.get("rating"),
        "num_resenas": p.get("userRatingCount"),
        "maps_url": p.get("googleMapsUri"),
        "lat": loc.get("latitude"),
        "lon": loc.get("longitude"),
        "redes": [],
        "place_id": p.get("id"),
        "fuente": "google",
    }
