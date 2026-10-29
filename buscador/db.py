"""Almacenamiento en SQLite: negocios encontrados, su estado y el registro de envíos."""
import json
import sqlite3
from datetime import date, datetime, timedelta
from pathlib import Path

ESTADOS = ("nuevo", "contactado", "respondio", "descartado", "no_contactar")

ESQUEMA = """
CREATE TABLE IF NOT EXISTS negocios (
    id            TEXT PRIMARY KEY,
    nombre        TEXT NOT NULL,
    direccion     TEXT,
    ciudad        TEXT,
    sector        TEXT,
    telefono      TEXT,
    email         TEXT,
    web_ficha     TEXT,
    rating        REAL,
    num_resenas   INTEGER,
    maps_url      TEXT,
    lat           REAL,
    lon           REAL,
    fuentes       TEXT,
    redes         TEXT DEFAULT '[]',
    estado_web    TEXT DEFAULT 'pendiente',
    evidencia_web TEXT,
    estado        TEXT DEFAULT 'nuevo',
    canal         TEXT,
    contactado_en TEXT,
    seguimiento_en TEXT,
    notas         TEXT,
    creado_en     TEXT
);
CREATE TABLE IF NOT EXISTS envios (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    negocio_id  TEXT NOT NULL,
    canal       TEXT NOT NULL,
    tipo        TEXT NOT NULL,
    fecha       TEXT NOT NULL,
    mensaje     TEXT
);
"""

# Campos que vienen de las fuentes; el resto (estado, notas...) se conserva al volver a buscar.
CAMPOS_FUENTE = ("nombre", "direccion", "ciudad", "sector", "telefono", "email", "web_ficha",
                 "rating", "num_resenas", "maps_url", "lat", "lon", "fuentes", "redes", "place_id")

# Columnas añadidas después de la primera versión (se crean solas en bases de datos antiguas)
COLUMNAS_NUEVAS = {"place_id": "TEXT", "google_obtenido_en": "TEXT"}

# Datos de Google que se borran pasados DIAS_GOOGLE (condiciones de Google Maps Platform:
# solo el place_id se puede guardar indefinidamente)
DIAS_GOOGLE = 30
CAMPOS_GOOGLE_BORRAR = ("direccion", "web_ficha", "rating", "num_resenas", "maps_url", "lat", "lon")


class DB:
    def __init__(self, ruta: Path | str):
        if str(ruta) != ":memory:":
            Path(ruta).parent.mkdir(parents=True, exist_ok=True)
        self.con = sqlite3.connect(str(ruta), check_same_thread=False)
        self.con.row_factory = sqlite3.Row
        self.con.executescript(ESQUEMA)
        existentes = {f[1] for f in self.con.execute("PRAGMA table_info(negocios)")}
        with self.con:
            for col, tipo in COLUMNAS_NUEVAS.items():
                if col not in existentes:
                    self.con.execute(f"ALTER TABLE negocios ADD COLUMN {col} {tipo}")

    # --- negocios ---
    def guardar(self, n: dict) -> bool:
        """Inserta o actualiza un negocio. Devuelve True si es nuevo."""
        datos = {k: n.get(k) for k in CAMPOS_FUENTE}
        datos["redes"] = json.dumps(n.get("redes") or [])
        if "google" in (n.get("fuentes") or "").split(","):
            datos["google_obtenido_en"] = datetime.now().isoformat(timespec="seconds")
        existe = self.con.execute("SELECT 1 FROM negocios WHERE id=?", (n["id"],)).fetchone()
        with self.con:
            if existe:
                sets = ", ".join(f"{k}=COALESCE(?, {k})" for k in datos)
                self.con.execute(f"UPDATE negocios SET {sets} WHERE id=?", (*datos.values(), n["id"]))
                return False
            cols = ", ".join(["id", "creado_en", *datos])
            marcas = ", ".join("?" * (len(datos) + 2))
            self.con.execute(f"INSERT INTO negocios ({cols}) VALUES ({marcas})",
                             (n["id"], datetime.now().isoformat(timespec="seconds"), *datos.values()))
            return True

    def obtener(self, id_: str) -> dict | None:
        fila = self.con.execute("SELECT * FROM negocios WHERE id=?", (id_,)).fetchone()
        return _a_dict(fila) if fila else None

    def listar(self, estado_web=None, estado=None, sector=None, ciudad=None,
               seguimiento_dias=None) -> list[dict]:
        sql, args = "SELECT * FROM negocios WHERE 1=1", []
        if estado_web:
            sql += " AND estado_web=?"; args.append(estado_web)
        if estado:
            sql += " AND estado=?"; args.append(estado)
        if sector:
            sql += " AND sector=?"; args.append(sector)
        if ciudad:
            sql += " AND ciudad=?"; args.append(ciudad)
        if seguimiento_dias is not None:
            limite = (datetime.now() - timedelta(days=seguimiento_dias)).isoformat()
            sql += " AND estado='contactado' AND seguimiento_en IS NULL AND contactado_en <= ?"
            args.append(limite)
        sql += " ORDER BY (estado='nuevo') DESC, COALESCE(num_resenas,0) DESC, nombre"
        return [_a_dict(f) for f in self.con.execute(sql, args)]

    def pendientes_verificar(self) -> list[dict]:
        return [_a_dict(f) for f in self.con.execute(
            "SELECT * FROM negocios WHERE estado_web='pendiente'")]

    def actualizar(self, id_: str, **campos) -> None:
        if "redes" in campos:
            campos["redes"] = json.dumps(campos["redes"])
        sets = ", ".join(f"{k}=?" for k in campos)
        with self.con:
            self.con.execute(f"UPDATE negocios SET {sets} WHERE id=?", (*campos.values(), id_))

    def valores(self, columna: str) -> list[str]:
        assert columna in ("sector", "ciudad")
        return [f[0] for f in self.con.execute(
            f"SELECT DISTINCT {columna} FROM negocios WHERE {columna} IS NOT NULL ORDER BY 1")]

    def resumen(self) -> dict:
        filas = self.con.execute("SELECT estado_web, COUNT(*) FROM negocios GROUP BY 1").fetchall()
        return {f[0]: f[1] for f in filas}

    # --- envíos ---
    def registrar_envio(self, negocio_id: str, canal: str, tipo: str, mensaje: str) -> None:
        ahora = datetime.now().isoformat(timespec="seconds")
        with self.con:
            self.con.execute("INSERT INTO envios (negocio_id, canal, tipo, fecha, mensaje) VALUES (?,?,?,?,?)",
                             (negocio_id, canal, tipo, ahora, mensaje))
            if tipo == "seguimiento":
                self.con.execute("UPDATE negocios SET seguimiento_en=? WHERE id=?", (ahora, negocio_id))
            else:
                self.con.execute("UPDATE negocios SET estado='contactado', canal=?, contactado_en=? WHERE id=?",
                                 (canal, ahora, negocio_id))

    def purgar_google(self, dias: int = DIAS_GOOGLE) -> dict:
        """Borra los datos de Google con más de `dias` días.

        - Negocios que no has contactado: se eliminan (si vuelves a buscar, se recuperan actualizados).
        - Negocios contactados, que respondieron o en «no contactar»: se conserva tu registro (nombre,
          contacto que usaste, estado, notas y place_id) y se borran dirección, valoración, mapa, etc.
        """
        limite = (datetime.now() - timedelta(days=dias)).isoformat(timespec="seconds")
        filtro = "google_obtenido_en IS NOT NULL AND google_obtenido_en < ?"
        with self.con:
            borrados = self.con.execute(f"DELETE FROM negocios WHERE {filtro} AND estado IN ('nuevo', 'descartado')",
                                        (limite,)).rowcount
            sets = ", ".join(f"{c}=NULL" for c in CAMPOS_GOOGLE_BORRAR)
            limpiados = self.con.execute(f"UPDATE negocios SET {sets}, google_obtenido_en=NULL WHERE {filtro}",
                                         (limite,)).rowcount
        return {"borrados": borrados, "limpiados": limpiados}

    def envios_hoy(self) -> int:
        return self.con.execute("SELECT COUNT(*) FROM envios WHERE fecha >= ?",
                                (date.today().isoformat(),)).fetchone()[0]


def _a_dict(fila: sqlite3.Row) -> dict:
    d = dict(fila)
    d["redes"] = json.loads(d.get("redes") or "[]")
    return d
