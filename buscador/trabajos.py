"""Búsqueda y verificación en segundo plano, para que el panel no se quede colgado."""
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests

from . import verificador
from .db import DB
from .fuentes import google_places, osm
from .unificar import unificar

HILOS_VERIFICACION = 8


class Cancelado(Exception):
    pass


class Trabajo:
    def __init__(self):
        self.lock = threading.Lock()
        self.activo = False
        self.cancelar = False
        self.fase = ""
        self.total = 0
        self.hechos = 0
        self.inicio = 0.0
        self.mensajes: list[str] = []

    def estado(self) -> dict:
        with self.lock:
            return {"activo": self.activo, "fase": self.fase, "total": self.total, "hechos": self.hechos,
                    "segundos": int(time.monotonic() - self.inicio) if self.activo else 0,
                    "mensajes": self.mensajes[-10:]}

    def _log(self, msg: str) -> None:
        print(f"[buscador] {msg}", flush=True)  # también en la ventana negra, por si hay que diagnosticar
        with self.lock:
            self.mensajes.append(msg)

    def _fase(self, fase: str) -> None:
        with self.lock:
            self.fase = fase
        self._log(fase)

    def _comprobar_cancelado(self) -> None:
        if self.cancelar:
            raise Cancelado

    def pedir_cancelar(self) -> None:
        self.cancelar = True

    def _arrancar(self, objetivo, *args) -> bool:
        with self.lock:
            if self.activo:
                return False
            self.activo, self.cancelar, self.total, self.hechos, self.mensajes = True, False, 0, 0, []
            self.inicio = time.monotonic()
        threading.Thread(target=objetivo, args=args, daemon=True).start()
        return True

    def lanzar(self, cfg, sector: str, ciudad: str, fuentes: list[str]) -> bool:
        return self._arrancar(self._ejecutar, cfg, sector, ciudad, fuentes)

    def lanzar_verificacion(self, cfg) -> bool:
        return self._arrancar(self._ejecutar, cfg, None, None, [])

    def _ejecutar(self, cfg, sector, ciudad, fuentes) -> None:
        db = DB(cfg.ruta_db)
        s = requests.Session()
        try:
            purga = db.purgar_google()
            if purga["borrados"] or purga["limpiados"]:
                self._log(f"Datos de Google de más de 30 días: {purga['borrados']} negocios eliminados, "
                          f"{purga['limpiados']} limpiados (se conserva tu historial de contacto)")
            if sector:
                self._buscar(cfg, db, s, sector, ciudad, fuentes)
            self._verificar(cfg, db)
            self._log("Listo ✔")
        except Cancelado:
            self._log("Cancelado. Lo que ya se había comprobado está guardado.")
        except Exception as e:  # noqa: BLE001 - mostramos cualquier fallo en el panel
            self._log(f"Error inesperado: {type(e).__name__}: {e}")
        finally:
            with self.lock:
                self.activo, self.fase = False, ""
            db.con.close()

    def _buscar(self, cfg, db, s, sector, ciudad, fuentes) -> None:
        listas = []
        if "google" in fuentes:
            if not cfg.google_key:
                self._log("Google: falta GOOGLE_PLACES_API_KEY en el .env")
            else:
                self._fase("Buscando en Google…")
                try:
                    r = google_places.buscar(sector, ciudad, cfg.google_key, session=s)
                    listas.append(r)
                    self._log(f"Google: {len(r)} negocios")
                except (google_places.ErrorGoogle, requests.RequestException) as e:
                    self._log(f"Google: {e}")
        self._comprobar_cancelado()
        if "osm" in fuentes:
            self._fase("Buscando en OpenStreetMap…")
            try:
                r = osm.buscar(sector, ciudad, session=s, log=self._log)
                listas.append(r)
                self._log(f"OpenStreetMap: {len(r)} negocios")
            except (osm.ErrorOSM, requests.RequestException) as e:
                self._log(f"OpenStreetMap: {e}")
        self._comprobar_cancelado()
        negocios = unificar(listas, sector=sector.strip().lower(), ciudad=ciudad.strip().title())
        nuevos = sum(db.guardar(n) for n in negocios)
        self._log(f"{len(negocios)} negocios únicos ({nuevos} nuevos)")

    def _verificar(self, cfg, db) -> None:
        pendientes = db.pendientes_verificar()
        if not pendientes:
            return
        with self.lock:
            self.total = len(pendientes)
        self._fase("Comprobando si tienen web…")
        sesion_local = threading.local()

        def comprobar(n):
            if self.cancelar:
                return n, None
            if not hasattr(sesion_local, "s"):
                sesion_local.s = requests.Session()
            return n, verificador.verificar(n, session=sesion_local.s, brave_key=cfg.brave_key)

        with ThreadPoolExecutor(HILOS_VERIFICACION) as ex:
            futuros = [ex.submit(comprobar, n) for n in pendientes]
            for f in as_completed(futuros):
                n, res = f.result()
                if res:
                    db.actualizar(n["id"], **res)  # se guarda uno a uno: si cancelas no se pierde nada
                with self.lock:
                    self.hechos += 1
            self._comprobar_cancelado()
