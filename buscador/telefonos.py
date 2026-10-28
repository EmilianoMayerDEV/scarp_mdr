"""Normalización de teléfonos españoles y enlaces de WhatsApp."""
import re
from urllib.parse import quote


def normalizar(telefono: str | None) -> str | None:
    """Devuelve el teléfono en formato +34XXXXXXXXX, o None si no es válido."""
    if not telefono:
        return None
    # Algunas fichas traen varios números separados por ; o /
    telefono = re.split(r"[;/,]", telefono)[0]
    t = re.sub(r"[^\d+]", "", telefono)
    if t.startswith("00"):
        t = "+" + t[2:]
    if t.startswith("+"):
        digitos = t[1:]
        if digitos.startswith("34") and len(digitos) == 11:
            return "+" + digitos
        return "+" + digitos if 8 <= len(digitos) <= 15 else None
    if len(t) == 11 and t.startswith("34"):
        return "+" + t
    if len(t) == 9 and t[0] in "6789":
        return "+34" + t
    return None


def es_movil(telefono: str | None) -> bool:
    """En España los móviles empiezan por 6 o 7. Los fijos (8, 9) no suelen tener WhatsApp."""
    return bool(telefono) and telefono.startswith("+34") and telefono[3] in "67"


def bonito(telefono: str | None) -> str:
    if not telefono:
        return ""
    if telefono.startswith("+34") and len(telefono) == 12:
        n = telefono[3:]
        return f"{n[:3]} {n[3:5]} {n[5:7]} {n[7:]}"
    return telefono


def enlace_whatsapp(telefono: str, texto: str) -> str:
    return f"https://wa.me/{telefono.lstrip('+')}?text={quote(texto)}"
