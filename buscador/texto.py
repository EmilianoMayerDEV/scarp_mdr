"""Utilidades de texto: normalizar nombres para comparar y deduplicar."""
import re
import unicodedata

# Palabras que no distinguen a un negocio (no sirven para reconocer su web)
GENERICAS = {
    "bar", "bares", "restaurante", "cafeteria", "cafe", "peluqueria", "barberia", "estetica", "centro",
    "taller", "clinica", "dental", "tienda", "panaderia", "pasteleria", "floristeria", "gimnasio",
    "academia", "farmacia", "optica", "inmobiliaria", "abogados", "gestoria", "asesoria", "hotel",
    "hostal", "the", "los", "las", "del", "con", "san", "santa", "madrid", "calle", "plaza",
    "sl", "slu", "sa", "scp", "cb", "y", "de", "la", "el", "en", "and",
}


def sin_acentos(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")


def normalizar_nombre(nombre: str) -> str:
    s = sin_acentos(nombre.lower())
    s = re.sub(r"\b(s\.?\s?l\.?u?|s\.?\s?a\.?|c\.?\s?b\.?)\b\.?", " ", s)
    s = re.sub(r"[^a-z0-9]+", " ", s)
    return " ".join(s.split())


def tokens_distintivos(nombre: str) -> list[str]:
    """Palabras del nombre que sirven para reconocerlo (p. ej. «Peluquería Lola» -> ['lola'])."""
    return [t for t in normalizar_nombre(nombre).split() if len(t) >= 3 and t not in GENERICAS]


def slug(nombre: str) -> str:
    return normalizar_nombre(nombre).replace(" ", "")
