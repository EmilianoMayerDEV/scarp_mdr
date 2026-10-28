"""Carga la configuración desde el archivo .env (sin dependencias externas)."""
import os
from dataclasses import dataclass
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent


def _cargar_env(ruta: Path) -> None:
    if not ruta.exists():
        return
    for linea in ruta.read_text(encoding="utf-8").splitlines():
        linea = linea.strip()
        if not linea or linea.startswith("#") or "=" not in linea:
            continue
        clave, valor = linea.split("=", 1)
        os.environ.setdefault(clave.strip(), valor.strip().strip('"').strip("'"))


@dataclass
class Config:
    google_key: str
    brave_key: str
    firma_nombre: str
    firma_empresa: str
    firma_web: str
    firma_telefono: str
    smtp_host: str
    smtp_port: int
    smtp_usuario: str
    smtp_contrasena: str
    smtp_copia_a_mi: bool
    limite_diario: int
    dias_seguimiento: int
    ruta_db: Path

    @property
    def smtp_configurado(self) -> bool:
        return bool(self.smtp_usuario and self.smtp_contrasena)


def cargar_config() -> Config:
    _cargar_env(RAIZ / ".env")
    e = os.environ.get
    return Config(
        google_key=e("GOOGLE_PLACES_API_KEY", ""),
        brave_key=e("BRAVE_API_KEY", ""),
        firma_nombre=e("FIRMA_NOMBRE", ""),
        firma_empresa=e("FIRMA_EMPRESA", "Mayer Digital"),
        firma_web=e("FIRMA_WEB", "mayerdigital.website"),
        firma_telefono=e("FIRMA_TELEFONO", ""),
        smtp_host=e("SMTP_HOST", "smtp.hostinger.com"),
        smtp_port=int(e("SMTP_PORT", "465") or 465),
        smtp_usuario=e("SMTP_USUARIO", ""),
        smtp_contrasena=e("SMTP_CONTRASENA", ""),
        smtp_copia_a_mi=e("SMTP_COPIA_A_MI", "si").lower() in ("si", "sí", "true", "1", "yes"),
        limite_diario=int(e("LIMITE_DIARIO", "15") or 15),
        dias_seguimiento=int(e("DIAS_SEGUIMIENTO", "5") or 5),
        ruta_db=Path(e("RUTA_DB", str(RAIZ / "datos" / "negocios.db"))),
    )
