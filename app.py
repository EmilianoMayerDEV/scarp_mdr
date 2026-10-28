"""Panel web local del buscador de clientes. Ejecuta:  python app.py  y abre http://127.0.0.1:5000"""
import csv
import io
import threading
import webbrowser
from urllib.parse import quote

from flask import Flask, Response, jsonify, render_template, request

from buscador import correo, mensajes, telefonos, verificador
from buscador.config import cargar_config
from buscador.db import DB, ESTADOS
from buscador.fuentes import osm
from buscador.trabajos import Trabajo

VISTAS = {
    "sin_web": "Sin web",
    "web_caida": "Web caída",
    "posible_web": "Revisar",
    "seguimiento": "Seguimiento",
    "tiene_web": "Con web",
    "todos": "Todos",
}


def crear_app(cfg=None, db=None) -> Flask:
    cfg = cfg or cargar_config()
    db = db or DB(cfg.ruta_db)
    trabajo = Trabajo()
    lock = threading.Lock()
    app = Flask(__name__)

    @app.get("/")
    def inicio():
        vista = request.args.get("vista", "sin_web")
        filtros = {k: request.args.get(k) or None for k in ("estado", "sector", "ciudad")}
        if vista == "seguimiento":
            negocios = db.listar(seguimiento_dias=cfg.dias_seguimiento, sector=filtros["sector"],
                                 ciudad=filtros["ciudad"])
        else:
            negocios = db.listar(estado_web=None if vista == "todos" else vista, **filtros)
        for n in negocios:
            n["canales"] = mensajes.canales_disponibles(n)
            n["telefono_bonito"] = telefonos.bonito(n["telefono"])
        resumen = db.resumen()
        resumen["seguimiento"] = len(db.listar(seguimiento_dias=cfg.dias_seguimiento))
        resumen["todos"] = sum(v for k, v in resumen.items() if k != "seguimiento")
        return render_template(
            "index.html", negocios=negocios, vista=vista, vistas=VISTAS, filtros=filtros,
            estados=ESTADOS, resumen=resumen, sectores=sorted(osm.SECTORES), cfg=cfg,
            sectores_db=db.valores("sector"), ciudades_db=db.valores("ciudad"),
            envios_hoy=db.envios_hoy(), trabajo=trabajo.estado())

    # --- búsqueda ---
    @app.post("/api/buscar")
    def buscar():
        d = request.get_json(force=True)
        sector, ciudad = (d.get("sector") or "").strip(), (d.get("ciudad") or "").strip()
        fuentes = d.get("fuentes") or []
        if not sector or not ciudad or not fuentes:
            return jsonify(error="Indica sector, ciudad y al menos una fuente."), 400
        if not trabajo.lanzar(cfg, sector, ciudad, fuentes):
            return jsonify(error="Ya hay una búsqueda en marcha."), 409
        return jsonify(ok=True)

    @app.post("/api/verificar-pendientes")
    def verificar_pendientes():
        if not trabajo.lanzar_verificacion(cfg):
            return jsonify(error="Ya hay una búsqueda en marcha."), 409
        return jsonify(ok=True)

    @app.post("/api/cancelar")
    def cancelar():
        trabajo.pedir_cancelar()
        return jsonify(ok=True)

    @app.get("/api/trabajo")
    def estado_trabajo():
        return jsonify(trabajo.estado())

    # --- negocio ---
    def _negocio(id_):
        n = db.obtener(id_)
        if not n:
            return None, (jsonify(error="Negocio no encontrado"), 404)
        return n, None

    def _puede_enviar(n):
        if n["estado"] == "no_contactar":
            return jsonify(error="Este negocio pidió no ser contactado."), 403
        if db.envios_hoy() >= cfg.limite_diario:
            return jsonify(error=f"Has llegado al límite diario ({cfg.limite_diario}). "
                                 "Es por la reputación de tu dominio: sigue mañana."), 429
        return None

    @app.get("/api/negocio/<id_>/mensaje")
    def mensaje(id_):
        n, err = _negocio(id_)
        if err:
            return err
        m = mensajes.preparar(n, cfg, tipo=request.args.get("tipo", "primero"), canal=request.args.get("canal"))
        m["smtp"] = cfg.smtp_configurado
        m["nombre"] = n["nombre"]
        return jsonify(m)

    @app.post("/api/negocio/<id_>/email")
    def enviar_email(id_):
        n, err = _negocio(id_)
        if err:
            return err
        if (bloqueo := _puede_enviar(n)):
            return bloqueo
        d = request.get_json(force=True)
        if not n.get("email"):
            return jsonify(error="Este negocio no tiene email."), 400
        try:
            with lock:
                correo.enviar(n["email"], d["asunto"], d["texto"], cfg)
        except Exception as e:  # noqa: BLE001
            return jsonify(error=f"No se pudo enviar: {e}"), 502
        db.registrar_envio(id_, "email", d.get("tipo", "primero"), d["texto"])
        return jsonify(ok=True)

    @app.post("/api/negocio/<id_>/registrar")
    def registrar(id_):
        """Marca como enviado un WhatsApp o un correo abierto en tu programa de correo."""
        n, err = _negocio(id_)
        if err:
            return err
        if (bloqueo := _puede_enviar(n)):
            return bloqueo
        d = request.get_json(force=True)
        canal = d.get("canal")
        if canal == "whatsapp":
            if not telefonos.es_movil(n.get("telefono")):
                return jsonify(error="El teléfono no es un móvil."), 400
            enlace = telefonos.enlace_whatsapp(n["telefono"], d["texto"])
        elif canal == "email":
            enlace = f"mailto:{n['email']}?subject={quote(d.get('asunto', ''))}&body={quote(d['texto'])}"
        else:
            return jsonify(error="Canal no válido"), 400
        db.registrar_envio(id_, canal, d.get("tipo", "primero"), d["texto"])
        return jsonify(ok=True, enlace=enlace)

    @app.post("/api/negocio/<id_>/estado")
    def cambiar_estado(id_):
        n, err = _negocio(id_)
        if err:
            return err
        d = request.get_json(force=True)
        campos = {}
        if "estado" in d:
            if d["estado"] not in ESTADOS:
                return jsonify(error="Estado no válido"), 400
            campos["estado"] = d["estado"]
        if "notas" in d:
            campos["notas"] = d["notas"][:2000]
        if "estado_web" in d:
            if d["estado_web"] not in ("sin_web", "tiene_web", "posible_web", "web_caida"):
                return jsonify(error="Estado de web no válido"), 400
            campos["estado_web"] = d["estado_web"]
        if campos:
            db.actualizar(id_, **campos)
        return jsonify(ok=True)

    @app.post("/api/negocio/<id_>/reverificar")
    def reverificar(id_):
        n, err = _negocio(id_)
        if err:
            return err
        res = verificador.verificar(n, brave_key=cfg.brave_key)
        db.actualizar(id_, **res)
        return jsonify(res)

    @app.get("/exportar.csv")
    def exportar():
        cols = ["nombre", "sector", "ciudad", "direccion", "telefono", "email", "estado_web",
                "evidencia_web", "estado", "contactado_en", "rating", "num_resenas", "maps_url", "notas"]
        buf = io.StringIO()
        w = csv.writer(buf, delimiter=";")
        w.writerow(cols)
        for n in db.listar():
            w.writerow([n.get(c) if n.get(c) is not None else "" for c in cols])
        return Response("﻿" + buf.getvalue(), mimetype="text/csv",
                        headers={"Content-Disposition": "attachment; filename=negocios.csv"})

    return app


if __name__ == "__main__":
    app = crear_app()
    threading.Timer(1.0, lambda: webbrowser.open("http://127.0.0.1:5000")).start()
    app.run(host="127.0.0.1", port=5000, debug=False)
