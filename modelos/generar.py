"""Genera una web modelo por cada sector.

Uso:
  python modelos/generar.py                      -> modelos/webs/<sector>.html (para abrir en tu ordenador)
  python modelos/generar.py --publicar CARPETA   -> CARPETA/<sector>/index.html (para subir a tu web:
                                                    mayerdigital.website/modelos/<sector>/)
"""
import argparse
import html
import json
from pathlib import Path
from urllib.parse import quote_plus

from contenido import ESTILOS, SECTORES

AQUI = Path(__file__).resolve().parent
SALIDA = AQUI / "webs"
ICONOS = json.loads((AQUI / "iconos.json").read_text(encoding="utf-8"))
TEL, TEL_VISIBLE, WA = "+34600000000", "600 000 000", "https://wa.me/34600000000"

e = html.escape

TIPO = {"peluquerias": "Peluquería", "barberias": "Barbería", "centros-de-estetica": "Centro de estética",
        "restaurantes": "Restaurante", "cafeterias": "Cafetería", "bares": "Bar", "panaderias": "Panadería",
        "carnicerias": "Carnicería", "fruterias": "Frutería", "floristerias": "Floristería",
        "talleres-mecanicos": "Taller mecánico", "dentistas": "Clínica dental", "fisioterapeutas": "Fisioterapia",
        "veterinarios": "Clínica veterinaria", "gimnasios": "Gimnasio", "tiendas-de-ropa": "Tienda de ropa",
        "zapaterias": "Zapatería", "ferreterias": "Ferretería", "opticas": "Óptica", "inmobiliarias": "Inmobiliaria",
        "abogados": "Despacho de abogados", "gestorias": "Gestoría", "fontaneros": "Fontanero",
        "electricistas": "Electricista", "academias": "Academia", "tiendas-de-mascotas": "Tienda de mascotas",
        "lavanderias": "Lavandería"}


def ico(nombre: str, tam: int = 22, clase: str = "") -> str:
    return (f'<svg class="ico {clase}" width="{tam}" height="{tam}" viewBox="0 0 24 24" fill="none" '
            f'stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" '
            f'aria-hidden="true">{ICONOS[nombre]}</svg>')


def fuentes(est: dict) -> str:
    familias = {est["display"]: f'{est["display_w"]}', est["body"]: "400;500;700"}
    if est["display"] == est["body"]:
        familias = {est["body"]: f'400;500;700;{est["display_w"]}'}
    q = "&".join(f"family={quote_plus(f)}:wght@{';'.join(sorted(set(w.split(';')), key=int))}"
                 for f, w in familias.items())
    return f"https://fonts.googleapis.com/css2?{q}&display=swap"


CSS = """
*{box-sizing:border-box}html{scroll-behavior:smooth}
body{margin:0;background:var(--bg);color:var(--ink);font-family:var(--body),system-ui,sans-serif;font-size:17px;line-height:1.6;-webkit-font-smoothing:antialiased}
img,svg{display:block}a{color:inherit}
.wrap{max-width:1160px;margin:0 auto;padding:0 20px}
h1,h2,h3{font-family:var(--display),Georgia,serif;font-weight:var(--dw);line-height:1.1;margin:0;letter-spacing:-.01em}
.oscuro h1,.oscuro h2,.oscuro h3{text-transform:uppercase;letter-spacing:.01em}
.cinta{background:var(--ink);color:var(--bg);font-size:13px;text-align:center;padding:7px 16px}
.cinta a{color:inherit;font-weight:700}
header{position:sticky;top:0;z-index:20;background:color-mix(in srgb,var(--bg) 88%,transparent);backdrop-filter:blur(10px);border-bottom:1px solid var(--line)}
.nav{display:flex;align-items:center;justify-content:space-between;gap:16px;height:68px}
.logo{display:flex;align-items:center;gap:10px;text-decoration:none;font-family:var(--display),serif;font-weight:var(--dw);font-size:20px}
.logo .marca{width:38px;height:38px;border-radius:calc(var(--r) * .6 + 4px);background:var(--accent);color:var(--accent-ink);display:grid;place-items:center}
.menu{display:flex;gap:26px;font-size:15px}.menu a{text-decoration:none;color:var(--muted)}.menu a:hover{color:var(--ink)}
.btn{display:inline-flex;align-items:center;gap:8px;background:var(--accent);color:var(--accent-ink);text-decoration:none;font-weight:700;font-size:15px;padding:13px 22px;border-radius:var(--r);border:2px solid var(--accent);transition:transform .15s}
.btn:hover{transform:translateY(-2px)}
.btn.sec{background:transparent;color:var(--ink);border-color:var(--line)}
.btn.peq{padding:9px 16px;font-size:14px}
.hero{padding:72px 0 64px}
.hero .wrap{display:grid;grid-template-columns:1.1fr .9fr;gap:56px;align-items:center}
.etiqueta{display:inline-flex;align-items:center;gap:8px;font-size:14px;color:var(--muted);margin-bottom:18px}
.etiqueta .punto{width:8px;height:8px;border-radius:50%;background:var(--accent)}
.hero h1{font-size:clamp(40px,6vw,68px)}
.hero p.sub{font-size:19px;color:var(--muted);max-width:540px;margin:20px 0 30px}
.acciones{display:flex;flex-wrap:wrap;gap:12px}
.nota{display:flex;align-items:center;gap:8px;margin-top:26px;font-size:15px;color:var(--muted)}
.estrellas{display:flex;color:#F5B301}.estrellas svg{fill:#F5B301;stroke:#F5B301}
.visual{position:relative;aspect-ratio:1/1.05;border-radius:calc(var(--r) * 2 + 8px);background:var(--accent);color:var(--accent-ink);overflow:hidden;display:grid;place-items:center}
.visual::before,.visual::after{content:"";position:absolute;border-radius:50%;border:2px solid currentColor;opacity:.18}
.visual::before{width:78%;aspect-ratio:1;top:-18%;right:-22%}.visual::after{width:60%;aspect-ratio:1;bottom:-20%;left:-16%}
.visual .grande{width:42%;height:auto;stroke-width:1.3;opacity:.95}
.visual .foto{position:absolute;left:20px;bottom:20px;font-size:13px;opacity:.8;display:flex;gap:6px;align-items:center}
.chip{position:absolute;background:var(--surface);color:var(--ink);border-radius:var(--r);padding:12px 16px;font-size:14px;font-weight:700;display:flex;align-items:center;gap:10px;box-shadow:0 14px 34px rgba(0,0,0,.14);max-width:calc(100% - 44px)}
.chip svg{color:var(--accent);flex:none}
.chip.c1{top:22px;left:22px}.chip.c2{bottom:56px;right:22px}
.franja{border-top:1px solid var(--line);border-bottom:1px solid var(--line);background:var(--surface)}
.franja .wrap{display:grid;grid-template-columns:repeat(3,1fr)}
.dest{display:flex;gap:16px;padding:30px 24px}.dest+.dest{border-left:1px solid var(--line)}
.dest .i{width:46px;height:46px;flex:none;border-radius:var(--r);background:var(--soft);color:var(--accent);display:grid;place-items:center}
.oscuro .dest .i{color:var(--accent)}
.dest h3{font-family:var(--body),sans-serif;font-size:17px;font-weight:700;text-transform:none;letter-spacing:0}
.dest p{margin:4px 0 0;color:var(--muted);font-size:15px;line-height:1.5}
section.bloque{padding:88px 0}
.cab{display:flex;justify-content:space-between;align-items:end;gap:20px;margin-bottom:40px;flex-wrap:wrap}
.cab .pre{font-size:14px;font-weight:700;color:var(--accent);text-transform:uppercase;letter-spacing:.08em;margin-bottom:10px}
.cab h2{font-size:clamp(32px,4.4vw,48px);max-width:640px}
.servicios{display:grid;grid-template-columns:repeat(2,1fr);gap:0 56px}
.serv{display:flex;justify-content:space-between;gap:20px;padding:22px 0;border-bottom:1px solid var(--line)}
.serv h3{font-family:var(--body),sans-serif;font-size:18px;font-weight:700;text-transform:none;letter-spacing:0}
.serv p{margin:3px 0 0;color:var(--muted);font-size:15px}
.serv .precio{font-weight:700;white-space:nowrap;color:var(--accent);font-size:17px}
.sobre{background:var(--soft)}
.sobre .wrap{display:grid;grid-template-columns:1fr 1fr;gap:64px;align-items:center}
.sobre p{font-size:19px;color:var(--muted);margin:22px 0 0}
.cifras{display:grid;grid-template-columns:repeat(3,1fr);gap:16px}
.cifra{background:var(--surface);border-radius:var(--r);padding:28px 20px;border:1px solid var(--line)}
.cifra b{display:block;font-family:var(--display),serif;font-weight:var(--dw);font-size:40px;line-height:1;color:var(--accent)}
.cifra span{display:block;margin-top:8px;color:var(--muted);font-size:14px}
.galeria{display:grid;grid-template-columns:repeat(3,1fr);grid-auto-rows:220px;gap:14px}
.foto-hueco{position:relative;border-radius:var(--r);overflow:hidden;background:linear-gradient(135deg,var(--soft),color-mix(in srgb,var(--accent) 22%,var(--soft)));display:grid;place-items:center;color:var(--accent)}
.foto-hueco:nth-child(1){grid-row:span 2;grid-column:span 2}
.foto-hueco svg{opacity:.55}
.foto-hueco span{position:absolute;left:14px;bottom:12px;font-size:14px;font-weight:700;color:var(--ink);background:var(--surface);padding:5px 10px;border-radius:calc(var(--r) * .5 + 2px)}
.resenas{display:grid;grid-template-columns:repeat(3,1fr);gap:20px}
.resena{background:var(--surface);border:1px solid var(--line);border-radius:var(--r);padding:28px;display:flex;flex-direction:column;gap:14px}
.resena p{margin:0;font-size:16.5px}
.resena .autor{margin-top:auto;font-weight:700;font-size:15px;display:flex;align-items:center;gap:10px}
.avatar{width:34px;height:34px;border-radius:50%;background:var(--soft);color:var(--accent);display:grid;place-items:center;font-size:14px}
.visita .wrap{display:grid;grid-template-columns:1fr 1.2fr;gap:40px}
.tarjeta{background:var(--surface);border:1px solid var(--line);border-radius:var(--r);padding:32px}
.horario{width:100%;border-collapse:collapse;margin-top:18px}
.horario td{padding:13px 0;border-bottom:1px solid var(--line);font-size:16px}.horario td:last-child{text-align:right;font-weight:700}
.datos{list-style:none;padding:0;margin:24px 0 0;display:grid;gap:14px}
.datos li{display:flex;gap:12px;align-items:center;color:var(--muted)}.datos svg{color:var(--accent);flex:none}
.mapa{border-radius:var(--r);overflow:hidden;border:1px solid var(--line);min-height:380px}
.mapa iframe{width:100%;height:100%;min-height:380px;border:0;display:block}
.cta{padding:0 0 88px}
.cta .caja{background:var(--accent);color:var(--accent-ink);border-radius:calc(var(--r) * 2 + 8px);padding:56px;display:flex;justify-content:space-between;align-items:center;gap:30px;flex-wrap:wrap}
.cta h2{font-size:clamp(28px,3.6vw,42px);max-width:620px}
.cta .btn{background:var(--accent-ink);color:var(--accent);border-color:var(--accent-ink)}
.cta .btn.sec{background:transparent;color:var(--accent-ink);border-color:currentColor}
footer{border-top:1px solid var(--line);padding:30px 0;color:var(--muted);font-size:14px}
footer .wrap{display:flex;justify-content:space-between;gap:16px;flex-wrap:wrap}
.wa{position:fixed;right:20px;bottom:20px;width:58px;height:58px;border-radius:50%;background:#25D366;color:#fff;display:grid;place-items:center;box-shadow:0 10px 26px rgba(0,0,0,.25);z-index:30}
@media(max-width:900px){
 .menu{display:none}.hero{padding:44px 0}.hero .wrap,.sobre .wrap,.visita .wrap{grid-template-columns:1fr;gap:36px}
 .visual{aspect-ratio:4/3}.franja .wrap{grid-template-columns:1fr}.dest+.dest{border-left:0;border-top:1px solid var(--line)}
 .servicios{grid-template-columns:1fr}.resenas{grid-template-columns:1fr}.galeria{grid-template-columns:repeat(2,1fr);grid-auto-rows:160px}
 .foto-hueco:nth-child(1){grid-row:auto}.foto-hueco:nth-child(6){grid-column:span 2}section.bloque{padding:64px 0}.cta .caja{padding:36px 26px}
}
@media(max-width:520px){.nav .btn{display:none}.cifras{grid-template-columns:1fr 1fr 1fr;gap:8px}.cifra{padding:18px 10px}.cifra b{font-size:28px}.chip{font-size:13px;padding:10px 12px}}
"""


def pagina(s: dict) -> str:
    est = dict(ESTILOS[s["estilo"]])
    if s.get("acento"):
        est["accent"] = s["acento"]
    if s.get("acento_ink"):
        est["accent_ink"] = s["acento_ink"]
    nota = next((v for v, t in s["cifras"] if "Google" in t), "4,9")
    variables = (f'--bg:{est["bg"]};--surface:{est["surface"]};--ink:{est["ink"]};--muted:{est["muted"]};'
                 f'--line:{est["line"]};--accent:{est["accent"]};--accent-ink:{est["accent_ink"]};--soft:{est["soft"]};'
                 f'--display:"{est["display"]}";--body:"{est["body"]}";--dw:{est["display_w"]};--r:{est["radius"]}')
    if s["estilo"] == "oscuro":  # el "soft" en oscuro se tiñe del acento
        variables += f';--soft:color-mix(in srgb,{est["accent"]} 12%,{est["surface"]})'
    estrellas = '<span class="estrellas">' + ico("star", 16) * 5 + "</span>"
    destacados = "".join(f'<div class="dest"><div class="i">{ico(i)}</div><div><h3>{e(t)}</h3><p>{e(d)}</p></div></div>'
                         for i, t, d in s["destacados"])
    servicios = "".join(f'<div class="serv"><div><h3>{e(n)}</h3><p>{e(d)}</p></div><div class="precio">{e(p)}</div></div>'
                        for n, d, p in s["servicios"])
    cifras = "".join(f'<div class="cifra"><b>{e(v)}</b><span>{e(t)}</span></div>' for v, t in s["cifras"])
    galeria = "".join(f'<div class="foto-hueco">{ico(s["icono"] if i % 2 == 0 else "image", 40)}<span>{e(c)}</span></div>'
                      for i, c in enumerate(s["galeria"]))
    resenas = "".join(f'<div class="resena">{estrellas}<p>«{e(t)}»</p><div class="autor"><span class="avatar">{e(n[0])}</span>{e(n)}</div></div>'
                      for n, t in s["resenas"])
    horario = "".join(f"<tr><td>{e(d)}</td><td>{e(h)}</td></tr>" for d, h in s["horario"])
    direccion = f"Calle Ejemplo, 12 · {s['barrio']}" + ("" if "Madrid" in s["barrio"] else ", Madrid")
    correo = "hola@" + s["slug"].split("-")[0] + "-ejemplo.es"
    return f"""<!doctype html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{e(s["nombre"])} · {e(TIPO[s["slug"]])} en {e(s["barrio"])}</title>
<meta name="description" content="{e(s["sub"])}">
<meta name="robots" content="noindex">
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="{fuentes(est)}" rel="stylesheet">
<style>:root{{{variables}}}{CSS}</style>
</head>
<body class="{s["estilo"]}">
<div class="cinta">Web de ejemplo para {e(s["sector"].lower())} · diseñada por <a href="https://mayerdigital.website">Mayer Digital</a></div>
<header><div class="wrap nav">
  <a class="logo" href="#"><span class="marca">{ico(s["icono"], 20)}</span>{e(s["nombre"])}</a>
  <nav class="menu"><a href="#servicios">Servicios</a><a href="#nosotros">Nosotros</a><a href="#opiniones">Opiniones</a><a href="#visitanos">Horario</a></nav>
  <a class="btn peq" href="#contacto">{e(s["cta"])}</a>
</div></header>

<section class="hero"><div class="wrap">
  <div>
    <div class="etiqueta"><span class="punto"></span>{e(TIPO[s["slug"]])} en {e(s["barrio"])}</div>
    <h1>{e(s["titular"])}</h1>
    <p class="sub">{e(s["sub"])}</p>
    <div class="acciones">
      <a class="btn" href="{WA}">{ico("message-circle", 18)}{e(s["cta"])}</a>
      <a class="btn sec" href="tel:{TEL}">{ico("phone", 18)}{TEL_VISIBLE}</a>
    </div>
    <div class="nota">{estrellas}<span><b>{e(nota)}</b> en Google · {e(s["resenas"][0][0].split()[0])} y muchos más lo recomiendan</span></div>
  </div>
  <div class="visual" role="img" aria-label="Imagen principal del negocio">
    {ico(s["icono"], 200, "grande")}
    <div class="chip c1">{ico("check", 18)}{e(s["chips"][0])}</div>
    <div class="chip c2">{ico("star", 18)}{e(s["chips"][1])}</div>
    <div class="foto">{ico("image", 14)}Aquí va la foto principal</div>
  </div>
</div></section>

<div class="franja"><div class="wrap">{destacados}</div></div>

<section class="bloque" id="servicios"><div class="wrap">
  <div class="cab"><div><div class="pre">Servicios y precios</div><h2>Lo que hacemos por ti</h2></div>
  <a class="btn sec" href="#contacto">Pedir información {ico("arrow-right", 16)}</a></div>
  <div class="servicios">{servicios}</div>
</div></section>

<section class="bloque sobre" id="nosotros"><div class="wrap">
  <div><div class="cab" style="margin:0"><div><div class="pre">Quiénes somos</div><h2>{e(s["nombre"])}</h2></div></div>
  <p>{e(s["sobre"])}</p></div>
  <div class="cifras">{cifras}</div>
</div></section>

<section class="bloque"><div class="wrap">
  <div class="cab"><div><div class="pre">Galería</div><h2>Así trabajamos</h2></div></div>
  <div class="galeria">{galeria}</div>
</div></section>

<section class="bloque" id="opiniones" style="padding-top:0"><div class="wrap">
  <div class="cab"><div><div class="pre">Opiniones</div><h2>Lo que dicen nuestros clientes</h2></div>
  <div class="nota" style="margin:0">{estrellas}<span><b>{e(nota)}</b> de media en Google</span></div></div>
  <div class="resenas">{resenas}</div>
</div></section>

<section class="bloque visita" id="visitanos" style="padding-top:0"><div class="wrap">
  <div class="tarjeta">
    <h2 style="font-size:32px">Horario</h2>
    <table class="horario">{horario}</table>
    <ul class="datos">
      <li>{ico("map-pin", 20)}{e(direccion)}</li>
      <li>{ico("phone", 20)}<a href="tel:{TEL}">{TEL_VISIBLE}</a></li>
      <li>{ico("mail", 20)}{e(correo)}</li>
    </ul>
  </div>
  <div class="mapa"><iframe title="Mapa" loading="lazy" src="https://www.openstreetmap.org/export/embed.html?bbox=-3.7140%2C40.4120%2C-3.6940%2C40.4220&amp;layer=mapnik&amp;marker=40.4168%2C-3.7038"></iframe></div>
</div></section>

<section class="cta" id="contacto"><div class="wrap"><div class="caja">
  <h2>¿Hablamos? Escríbenos por WhatsApp y te respondemos hoy mismo.</h2>
  <div class="acciones">
    <a class="btn" href="{WA}">{ico("message-circle", 18)}WhatsApp</a>
    <a class="btn sec" href="tel:{TEL}">{ico("phone", 18)}Llamar</a>
  </div>
</div></div></section>

<footer><div class="wrap">
  <span>© 2026 {e(s["nombre"])} · {e(direccion)}</span>
  <span>Web de ejemplo · <a href="https://mayerdigital.website">Mayer Digital</a></span>
</div></footer>
<a class="wa" href="{WA}" aria-label="Escribir por WhatsApp">{ico("message-circle", 28)}</a>
</body>
</html>
"""


def indice(carpetas: bool = False) -> str:
    tarjetas = []
    for s in SECTORES:
        est = ESTILOS[s["estilo"]]
        acc = s.get("acento") or est["accent"]
        tarjetas.append(
            f'<a class="t" href="{s["slug"] + "/" if carpetas else s["slug"] + ".html"}"><span class="m" style="background:{acc};color:{s.get("acento_ink") or est["accent_ink"]}">'
            f'{ico(s["icono"], 26)}</span><b>{e(s["sector"])}</b><small>{e(s["nombre"])}</small></a>')
    return f"""<!doctype html>
<html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Webs modelo · Mayer Digital</title>
<meta name="robots" content="noindex">
<link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@500;600&family=IBM+Plex+Sans:wght@400;600;700&display=swap" rel="stylesheet">
<style>
body{{margin:0;background:#0c0e10;color:#e6e9ec;font-family:"IBM Plex Sans",system-ui,sans-serif}}
.wrap{{max-width:1160px;margin:0 auto;padding:56px 20px}}
h1{{font-size:clamp(32px,5vw,52px);margin:0 0 10px;letter-spacing:-.02em}}h1 b{{color:#c8f169}}
p{{color:#8a949e;margin:0 0 36px;font-size:18px}}
.g{{display:grid;grid-template-columns:repeat(auto-fill,minmax(220px,1fr));gap:14px}}
.t{{display:flex;flex-direction:column;gap:6px;padding:20px;border:1px solid #252b31;border-radius:8px;background:#15191d;text-decoration:none;color:inherit;transition:border-color .15s,transform .15s}}
.t:hover{{border-color:#c8f169;transform:translateY(-2px)}}
.m{{width:48px;height:48px;border-radius:10px;display:grid;place-items:center;margin-bottom:10px}}
.t small{{color:#8a949e;font-family:"IBM Plex Mono",monospace;font-size:13px}}
</style></head><body><div class="wrap">
<h1>Webs <b>modelo</b></h1>
<p>{len(SECTORES)} ejemplos por sector para enseñar a cada negocio cómo se vería su página.</p>
<div class="g">{"".join(tarjetas)}</div></div></body></html>
"""


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--publicar", metavar="CARPETA", help="genera carpetas <sector>/index.html para publicar")
    args = ap.parse_args()
    if args.publicar:
        destino = Path(args.publicar)
        for s in SECTORES:
            (destino / s["slug"]).mkdir(parents=True, exist_ok=True)
            (destino / s["slug"] / "index.html").write_text(pagina(s), encoding="utf-8")
        (destino / "index.html").write_text(indice(carpetas=True), encoding="utf-8")
    else:
        destino = SALIDA
        destino.mkdir(exist_ok=True)
        for s in SECTORES:
            (destino / f"{s['slug']}.html").write_text(pagina(s), encoding="utf-8")
        (destino / "index.html").write_text(indice(), encoding="utf-8")
    print(f"{len(SECTORES)} webs generadas en {destino}")
