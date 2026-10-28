"""Búsqueda y verificación en segundo plano, para que el panel no se quede colgado."""
import threading
import time

import requests

from . import verificador
from .db import DB
from .fuentes import google_places, osm
from .unificar import unificar


class Trabajo:
    def __init__(self):
        self.lock = threading.Lock()
        self.activo = False
        self.fase = ""
        self.total = 0
        self.hechos = 0
        self.mensajes: list[str] = []

    def estado(self) -> dict:
        with self.lock:
            return {"activo": self.activo, "fase": self.fase, "total": self.total,
                    "hechos": self.hechos, "mensajes": self.mensajes[-8:]}

    def _log(self, msg: str) -> None:
        with self.lock:
            self.mensajes.append(msg)

    def lanzar(self, cfg, sector: str, ciudad: str, fuentes: list[str]) -> bool:
        with self.lock:
            if self.activo:
                return False
            self.activo, self.fase, self.total, self.hechos, self.mensajes = True, "Buscando negocios…", 0, 0, []
        threading.Thread(target=self._ejecutar, args=(cfg, sector, ciudad, fuentes), daemon=True).start()
        return True

    def lanzar_verificacion(self, cfg) -> bool:
        with self.lock:
            if self.activo:
                return False
            self.activo, self.fase, self.total, self.hechos, self.mensajes = True, "Verificando…", 0, 0, []
        threading.Thread(target=self._ejecutar, args=(cfg, None, None, []), daemon=True).start()
        return True

    def _ejecutar(self, cfg, sector, ciudad, fuentes) -> None:
        db = DB(cfg.ruta_db)
        s = requests.Session()
        try:
            if sector:
                listas = []
                if "google" in fuentes:
                    if not cfg.google_key:
                        self._log("Google: falta GOOGLE_PLACES_API_KEY en el .env")
                    else:
                        try:
                            r = google_places.buscar(sector, ciudad, cfg.google_key, session=s)
                            listas.append(r)
                            self._log(f"Google: {len(r)} negocios")
                        except (google_places.ErrorGoogle, requests.RequestException) as e:
                            self._log(f"Google: {e}")
                if "osm" in fuentes:
                    try:
                        r = osm.buscar(sector, ciudad, session=s)
                        listas.append(r)
                        self._log(f"OpenStreetMap: {len(r)} negocios")
                    except (osm.ErrorOSM, requests.RequestException) as e:
                        self._log(f"OpenStreetMap: {e}")
                negocios = unificar(listas, sector=sector.strip().lower(), ciudad=ciudad.strip().title())
                nuevos = sum(db.guardar(n) for n in negocios)
                self._log(f"{len(negocios)} negocios únicos ({nuevos} nuevos)")

            pendientes = db.pendientes_verificar()
            with self.lock:
                self.fase, self.total = "Comprobando si tienen web…", len(pendientes)
            for n in pendientes:
                res = verificador.verificar(n, session=s, brave_key=cfg.brave_key)
                db.actualizar(n["id"], **res)
                with self.lock:
                    self.hechos += 1
                if cfg.brave_key:
                    time.sleep(1.1)  # el plan gratuito de Brave permite 1 consulta por segundo
            self._log("Listo ✔")
        except Exception as e:  # noqa: BLE001 - mostramos cualquier fallo en el panel
            self._log(f"Error inesperado: {e}")
        finally:
            with self.lock:
                self.activo, self.fase = False, ""
            db.con.close()
