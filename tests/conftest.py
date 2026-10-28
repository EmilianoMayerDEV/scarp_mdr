import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from buscador.config import Config  # noqa: E402


class Resp:
    def __init__(self, status=200, json_data=None, text=""):
        self.status_code, self._json, self.text = status, json_data, text

    def json(self):
        return self._json

    def raise_for_status(self):
        if self.status_code >= 400:
            import requests
            raise requests.HTTPError(str(self.status_code))


class SesionFalsa:
    """Responde según la URL. `rutas` = {fragmento_url: Resp | Exception}."""
    def __init__(self, rutas):
        self.rutas, self.llamadas, self.headers = rutas, [], {}

    def _r(self, url, **kw):
        self.llamadas.append((url, kw))
        for frag, r in self.rutas.items():
            if frag in url:
                if isinstance(r, Exception):
                    raise r
                return r.pop(0) if isinstance(r, list) else r
        import requests
        raise requests.ConnectionError(f"sin red: {url}")

    get = post = _r


@pytest.fixture
def cfg(tmp_path):
    return Config(google_key="", brave_key="", firma_nombre="Emiliano Mayer", firma_empresa="Mayer Digital",
                  firma_web="mayerdigital.website", firma_telefono="600111222", smtp_host="smtp.test",
                  smtp_port=465, smtp_usuario="", smtp_contrasena="", smtp_copia_a_mi=True,
                  limite_diario=2, dias_seguimiento=5, ruta_db=tmp_path / "t.db")
