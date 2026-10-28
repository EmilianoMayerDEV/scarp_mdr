"""Plantillas de mensajes. Edítalas aquí para cambiar el texto que se propone en el panel.

Variables disponibles: {nombre} {ciudad} {sector} {detalle} {problema} {firma} {firma_corta}
"""
from . import telefonos

ASUNTO_EMAIL = "Una idea para {nombre}"

EMAIL = """Hola, equipo de {nombre}:

Encontré {nombre} buscando {sector} en {ciudad}{detalle}, {problema}.

Hoy muchos clientes buscan en Google antes de visitar o llamar, y sin web es fácil que acaben eligiendo otro negocio que sí aparece con su información, fotos y horarios.

Me dedico a crear páginas web sencillas y profesionales para negocios como el vuestro: con vuestros servicios, ubicación, botón de WhatsApp y diseño adaptado al móvil. Me encargo de todo, sin que tengáis que saber nada técnico.

¿Os interesaría que os prepare una propuesta sin compromiso?

Un saludo,
{firma}

P. D.: Si no os interesa, respondedme con un «no» y no volveré a escribiros."""

WHATSAPP = """Hola, ¿qué tal? Soy {firma_corta}.

Encontré {nombre} buscando {sector} en {ciudad}{detalle}, {problema}.

Hago webs sencillas para negocios como el vuestro (servicios, ubicación, botón de WhatsApp, adaptada al móvil) y me encargo de todo.

¿Os paso una propuesta sin compromiso? Si no os interesa, decídmelo y no vuelvo a escribir 🙂"""

ASUNTO_SEGUIMIENTO = "Re: Una idea para {nombre}"

SEGUIMIENTO = """Hola de nuevo,

Solo quería saber si pudisteis ver mi mensaje anterior sobre la página web para {nombre}. Si ahora no es buen momento, no hay problema.

Un saludo,
{firma_corta}"""


def _detalle(n: dict) -> str:
    if (n.get("rating") or 0) >= 4.3 and (n.get("num_resenas") or 0) >= 10:
        r = f"{n['rating']:.1f}".replace(".", ",")
        return f" y vi que tenéis muy buenas reseñas ({r} estrellas)"
    if n.get("redes"):
        return " y vi que estáis en redes sociales"
    return ""


def _contexto(n: dict, cfg) -> dict:
    firma = "\n".join(x for x in (cfg.firma_nombre, cfg.firma_empresa, cfg.firma_web,
                                   telefonos.bonito(telefonos.normalizar(cfg.firma_telefono))) if x)
    corta = " de ".join(x for x in (cfg.firma_nombre, cfg.firma_empresa) if x)
    detalle = _detalle(n)
    problema = ("pero la web que aparece en vuestra ficha no carga" if n.get("estado_web") == "web_caida"
                else "pero no encontré una página web propia")
    return {"nombre": n["nombre"], "ciudad": n.get("ciudad") or "tu zona",
            "sector": (n.get("sector") or "negocios").lower(), "detalle": detalle, "problema": problema,
            "firma": firma, "firma_corta": corta}


def canales_disponibles(n: dict) -> list[str]:
    canales = []
    if n.get("email"):
        canales.append("email")
    if telefonos.es_movil(n.get("telefono")):
        canales.append("whatsapp")
    if n.get("telefono"):
        canales.append("llamar")
    return canales


def canal_para(n: dict) -> str:
    """Email si tiene correo; si no, WhatsApp si es móvil; si no, llamar; si no, nada."""
    canales = canales_disponibles(n)
    return canales[0] if canales else "ninguno"


def preparar(n: dict, cfg, tipo: str = "primero", canal: str | None = None) -> dict:
    disponibles = canales_disponibles(n)
    canal = canal if canal in disponibles else canal_para(n)
    ctx = _contexto(n, cfg)
    if tipo == "seguimiento":
        asunto, texto = ASUNTO_SEGUIMIENTO.format(**ctx), SEGUIMIENTO.format(**ctx)
    elif canal == "email":
        asunto, texto = ASUNTO_EMAIL.format(**ctx), EMAIL.format(**ctx)
    else:
        asunto, texto = "", WHATSAPP.format(**ctx)
    return {"canal": canal, "canales": disponibles, "asunto": asunto, "texto": texto, "tipo": tipo,
            "email": n.get("email"), "telefono": n.get("telefono"),
            "telefono_bonito": telefonos.bonito(n.get("telefono"))}
