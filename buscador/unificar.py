"""Une los resultados de Google y OpenStreetMap eliminando duplicados."""
import hashlib
from math import cos, radians, sqrt

from . import telefonos
from .texto import normalizar_nombre

DISTANCIA_MAX_M = 150


def _distancia_m(a: dict, b: dict) -> float | None:
    if None in (a.get("lat"), a.get("lon"), b.get("lat"), b.get("lon")):
        return None
    dx = (a["lon"] - b["lon"]) * 111_320 * cos(radians(a["lat"]))
    dy = (a["lat"] - b["lat"]) * 110_540
    return sqrt(dx * dx + dy * dy)


def _mismo_negocio(a: dict, b: dict) -> bool:
    if a.get("telefono") and a["telefono"] == b.get("telefono"):
        return True
    if normalizar_nombre(a["nombre"]) == normalizar_nombre(b["nombre"]):
        d = _distancia_m(a, b)
        return d is None or d <= DISTANCIA_MAX_M
    return False


def _fusionar(a: dict, b: dict) -> dict:
    r = dict(a)
    for k, v in b.items():
        if k == "redes":
            r["redes"] = list(dict.fromkeys((a.get("redes") or []) + (v or [])))
        elif k == "fuentes":
            r["fuentes"] = ",".join(sorted(set(a["fuentes"].split(",")) | set(v.split(","))))
        elif r.get(k) in (None, "") and v not in (None, ""):
            r[k] = v
    return r


def identificador(n: dict) -> str:
    base = n.get("telefono") or f"{normalizar_nombre(n['nombre'])}|{round(n.get('lat') or 0, 3)}|{round(n.get('lon') or 0, 3)}"
    return hashlib.sha1(base.encode()).hexdigest()[:16]


def unificar(listas: list[list[dict]], sector: str, ciudad: str) -> list[dict]:
    unicos: list[dict] = []
    for lista in listas:
        for n in lista:
            if not n.get("nombre"):
                continue
            n = dict(n)
            n["telefono"] = telefonos.normalizar(n.get("telefono"))
            n["web_ficha"] = n.pop("web", None)
            n["fuentes"] = n.pop("fuente", "")
            n["email"] = (n.get("email") or "").strip().lower() or None
            for i, u in enumerate(unicos):
                if _mismo_negocio(u, n):
                    unicos[i] = _fusionar(u, n)
                    break
            else:
                unicos.append(n)
    for n in unicos:
        n.update(sector=sector, ciudad=ciudad, id=identificador(n))
    return unicos
