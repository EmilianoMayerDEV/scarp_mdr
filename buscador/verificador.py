"""Comprueba si un negocio tiene página web propia.

Pasos:
1. Web de la ficha (Google/OSM). Si es una red social o un directorio, no cuenta como web propia.
   Si es propia y responde -> tiene_web. Si no responde -> web_caida (¡también es una oportunidad!).
2. Búsqueda en internet del nombre + ciudad (Brave Search API, si hay clave).
3. Prueba de dominios típicos: nombre.com / nombre.es.
Si nada aparece -> sin_web. Si algo podría ser su web -> posible_web (revísalo tú).
"""
import re
from urllib.parse import urlparse

import requests

from .texto import slug, tokens_distintivos

# Dominios que NO son una web propia del negocio
NO_PROPIOS = {
    "facebook.com", "instagram.com", "tiktok.com", "twitter.com", "x.com", "linkedin.com", "youtube.com",
    "google.com", "goo.gl", "g.page", "business.site", "linktr.ee", "wa.me", "whatsapp.com",
    "tripadvisor.es", "tripadvisor.com", "yelp.es", "yelp.com", "paginasamarillas.es", "thefork.es",
    "eltenedor.es", "just-eat.es", "glovoapp.com", "ubereats.com", "booksy.com", "treatwell.es",
    "fresha.com", "doctoralia.es", "habitissimo.es", "milanuncios.com", "wallapop.com", "empresite.eleconomista.es",
    "infoempresa.com", "axesor.es", "einforma.com", "cylex.es", "qdq.com", "guiadeempresas.es",
    "foursquare.com", "restaurantguru.com", "carta.menu", "covermanager.com", "wikipedia.org",
    "openstreetmap.org", "apple.com", "bing.com", "duckduckgo.com", "infoisinfo.es", "hotfrog.es",
    "vulka.es", "misterwhat.es", "top-rated.online", "cybo.com", "salonized.com", "uala.es",
}
REDES = {"facebook.com", "instagram.com", "tiktok.com", "linktr.ee"}
BRAVE_URL = "https://api.search.brave.com/res/v1/web/search"
UA = {"User-Agent": "Mozilla/5.0 (compatible; MayerDigital-Verificador/1.0)"}


def dominio(url: str) -> str:
    if "://" not in url:
        url = "http://" + url
    d = (urlparse(url).hostname or "").lower()
    return d[4:] if d.startswith("www.") else d


def es_no_propio(url: str) -> bool:
    d = dominio(url)
    return any(d == x or d.endswith("." + x) for x in NO_PROPIOS)


def es_red_social(url: str) -> bool:
    d = dominio(url)
    return any(d == x or d.endswith("." + x) for x in REDES)


def coincide_nombre(nombre: str, url: str, titulo: str = "") -> bool:
    """¿El dominio o el título de la página corresponden a este negocio?"""
    tokens = tokens_distintivos(nombre)
    if not tokens:
        return False
    d = re.sub(r"[^a-z0-9]", "", dominio(url).rsplit(".", 1)[0])
    if slug(nombre) and slug(nombre) in d:
        return True
    if any(len(t) >= 4 and t in d for t in tokens):
        return True
    titulo_n = slug(titulo)
    return bool(titulo_n) and all(t in titulo_n for t in tokens)


def responde(url: str, session: requests.Session, timeout: float = 8) -> tuple[bool, str]:
    """Devuelve (responde, html)."""
    if "://" not in url:
        url = "https://" + url
    try:
        r = session.get(url, timeout=timeout, headers=UA, allow_redirects=True)
        return r.status_code < 400, r.text[:200_000] if r.status_code < 400 else ""
    except requests.RequestException:
        return False, ""


def _titulo(html: str) -> str:
    m = re.search(r"<title[^>]*>(.*?)</title>", html, re.I | re.S)
    return m.group(1).strip() if m else ""


def buscar_en_web(nombre: str, ciudad: str, brave_key: str, session: requests.Session) -> list[dict]:
    r = session.get(BRAVE_URL, params={"q": f'"{nombre}" {ciudad}', "country": "ES", "count": 10},
                    headers={"X-Subscription-Token": brave_key, "Accept": "application/json"}, timeout=15)
    r.raise_for_status()
    return r.json().get("web", {}).get("results", [])


def verificar(n: dict, session: requests.Session | None = None, brave_key: str = "",
              probar_dominios: bool = True) -> dict:
    """Devuelve {'estado_web', 'evidencia_web', 'redes'}."""
    s = session or requests.Session()
    redes = list(n.get("redes") or [])
    web = n.get("web_ficha")

    # 1) Web de la ficha
    if web:
        if es_no_propio(web):
            if es_red_social(web) and web not in redes:
                redes.append(web)
        else:
            ok, _ = responde(web, s)
            if ok:
                return {"estado_web": "tiene_web", "evidencia_web": web, "redes": redes}
            return {"estado_web": "web_caida", "evidencia_web": f"La web de su ficha no carga: {web}", "redes": redes}

    # 2) Búsqueda en internet
    if brave_key:
        try:
            for res in buscar_en_web(n["nombre"], n.get("ciudad") or "", brave_key, s):
                url = res.get("url", "")
                if es_no_propio(url):
                    if es_red_social(url) and coincide_nombre(n["nombre"], url, res.get("title", "")) \
                            and url not in redes:
                        redes.append(url)
                    continue
                if coincide_nombre(n["nombre"], url, res.get("title", "")):
                    return {"estado_web": "posible_web",
                            "evidencia_web": f"Aparece en buscador: {url}", "redes": redes}
        except requests.RequestException:
            pass  # la búsqueda es opcional: seguimos con los otros métodos

    # 3) Dominios típicos
    if probar_dominios and (base := slug(n["nombre"])) and len(base) >= 5:
        for tld in (".es", ".com"):
            ok, html = responde(base + tld, s, timeout=5)
            if ok and coincide_nombre(n["nombre"], base + tld, _titulo(html)) \
                    and any(t in slug(html) for t in tokens_distintivos(n["nombre"])):
                return {"estado_web": "posible_web", "evidencia_web": f"Existe el dominio {base}{tld}", "redes": redes}

    evidencia = "Sin web en la ficha" + (" ni en el buscador" if brave_key else "") + \
                ("; solo redes sociales" if redes else "")
    return {"estado_web": "sin_web", "evidencia_web": evidencia, "redes": redes}
