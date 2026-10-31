"""Plantillas de mensajes. Edítalas aquí para cambiar el texto que se propone en el panel.

Variables disponibles: {nombre} {ciudad} {sector} {detalle} {problema} {problema_formal} {ejemplo}
{ejemplo_formal} {firma} {firma_corta} {firma_nombre} {firma_empresa} {firma_web}
"""
from . import telefonos, verificador
from .texto import sin_acentos

# Web modelo publicada para cada sector: https://mayerdigital.website/modelos/<slug>/
MODELOS = {
    "peluquer": "peluquerias", "barber": "barberias", "estetica": "centros-de-estetica", "restaurante": "restaurantes",
    "cafeter": "cafeterias", "bar": "bares", "pub": "bares", "taberna": "bares", "panader": "panaderias",
    "pasteler": "panaderias", "carnicer": "carnicerias", "fruter": "fruterias", "florister": "floristerias",
    "taller": "talleres-mecanicos", "mecanic": "talleres-mecanicos", "dentist": "dentistas", "dental": "dentistas",
    "fisio": "fisioterapeutas", "veterinar": "veterinarios", "gimnasio": "gimnasios", "crossfit": "gimnasios",
    "ropa": "tiendas-de-ropa", "moda": "tiendas-de-ropa", "zapater": "zapaterias", "calzado": "zapaterias",
    "ferreter": "ferreterias", "optica": "opticas", "inmobiliar": "inmobiliarias", "abogad": "abogados",
    "gestor": "gestorias", "asesor": "gestorias", "fontaner": "fontaneros", "electricist": "electricistas",
    "academia": "academias", "mascota": "tiendas-de-mascotas", "lavander": "lavanderias", "tintorer": "lavanderias",
}


def enlace_modelo(sector: str | None, base: str) -> str | None:
    """Busca la web modelo que corresponde al sector escrito en el buscador (admite singular, plural, sin tildes)."""
    if not sector or not base:
        return None
    palabras = sin_acentos(sector.lower()).replace("-", " ").split()
    for clave, slug in MODELOS.items():
        # "bar" debe coincidir con la palabra exacta "bar(es)", no con "barberías"
        if clave == "bar":
            if any(p in ("bar", "bares") for p in palabras):
                return f"{base.rstrip('/')}/{slug}/"
        elif any(p.startswith(clave) for p in palabras):
            return f"{base.rstrip('/')}/{slug}/"
    return None

ASUNTO_EMAIL = "Una idea para {nombre}"

EMAIL = """Hola, equipo de {nombre}:

Encontré {nombre} buscando {sector} en {ciudad}{detalle}, {problema}.

Hoy muchos clientes buscan en Google antes de visitar o llamar, y sin web es fácil que acaben eligiendo otro negocio que sí aparece con su información, fotos y horarios.

Me dedico a crear páginas web sencillas y profesionales para negocios como el vuestro: con vuestros servicios, ubicación, botón de WhatsApp y diseño adaptado al móvil, en español e inglés para llegar también a clientes extranjeros. Me encargo de todo, sin que tengáis que saber nada técnico.

{ejemplo}¿Os interesaría que os prepare una propuesta sin compromiso?

Un saludo,
{firma}

P. D.: Si no os interesa, respondedme con un «no» y no volveré a escribiros."""

WHATSAPP = """Buenos días.

Mi nombre es {firma_nombre}, de {firma_empresa}, un estudio de diseño web en Madrid especializado en pequeños negocios.

Me pongo en contacto con {nombre} porque, al buscar su negocio en Google, {problema_formal}. Hoy en día muchos clientes consultan internet antes de elegir dónde ir, y una web con sus servicios, horarios y ubicación ayuda a atraer más visitas, sobre todo de quienes aún no les conocen.

La web puede estar en español e inglés, para que también les encuentren los clientes extranjeros y turistas.

Me gustaría enviarles una cotización sin compromiso, adaptada a su negocio. {ejemplo_formal}¿Podrían indicarme a qué persona o correo electrónico puedo dirigir la propuesta?

Muchas gracias por su atención. Si no les interesa, no volveré a escribirles.

Un saludo cordial,
{firma_nombre}
{firma_empresa} · {firma_web}"""

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
    plat = verificador.plataforma_gratuita(n.get("web_ficha") or "") or "una plataforma gratuita"
    if n.get("estado_web") == "web_basica":
        problema = f"aunque vuestra web está en {plat}, sin dominio propio"
        problema_formal = (f"he visto que su página web actual está en {plat}, una plataforma gratuita "
                           "sin dominio propio, que transmite menos profesionalidad que una web con su propio nombre")
    elif n.get("estado_web") == "web_caida":
        problema = "pero la web que aparece en vuestra ficha no carga"
        problema_formal = "he visto que la página web que aparece en su ficha no carga"
    else:
        problema = "pero no encontré una página web propia"
        problema_formal = "he visto que no cuenta con una página web propia"
    enlace = enlace_modelo(n.get("sector"), getattr(cfg, "modelos_url", ""))
    ejemplo = (f"Para que os hagáis una idea, aquí tenéis un ejemplo de cómo podría quedar: {enlace}\n\n"
               if enlace else "")
    ejemplo_formal = f"Pueden ver un ejemplo de cómo podría quedar aquí:\n{enlace}\n\n" if enlace else ""
    return {"ejemplo": ejemplo, "ejemplo_formal": ejemplo_formal, "problema_formal": problema_formal,
            "firma_nombre": cfg.firma_nombre, "firma_empresa": cfg.firma_empresa, "firma_web": cfg.firma_web,
            "nombre": n["nombre"], "ciudad": n.get("ciudad") or "tu zona",
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
