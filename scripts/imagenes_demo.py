#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Prepara las fotos reales de la demo descargándolas de Pixabay (costo $0).

Subcomandos:
  descargar   Busca en la API de Pixabay y baja las miniaturas de los candidatos
              (12 por consulta; consultas cacheadas, como exigen los términos).
  hoja        Genera scripts/candidatas/index.html (hoja de contactos para elegir)
              con las miniaturas de los candidatos.
  finales     Lee scripts/elecciones.json y escribe las fotos finales en
              static/demo/ (WebP 1200 px / miniatura 400 px) + CREDITOS.md.

Uso (desde la raíz del proyecto, con el venv activo):
  python scripts/imagenes_demo.py descargar
  python scripts/imagenes_demo.py hoja
  python scripts/imagenes_demo.py finales

La clave PIXABAY_API_KEY se lee de .env: nunca se imprime ni se versiona.
Términos revisados (9-nov-2026): Pixabay Content License (uso libre, sin
atribución obligatoria), API 100 peticiones/min, sin hotlinking (hay que
descargar), respuestas cacheadas 24 h.
"""
import argparse
import html
import json
import os
import re
import time
import unicodedata
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
CANDIDATAS = RAIZ / "scripts" / "candidatas"
CACHE = CANDIDATAS / "cache"
DEMO = RAIZ / "static" / "demo"
ELECCIONES = RAIZ / "scripts" / "elecciones.json"

# Clave desde .env (python-dotenv está en requirements.txt)
from dotenv import load_dotenv  # noqa: E402

load_dotenv(RAIZ / ".env")
CLAVE = os.environ.get("PIXABAY_API_KEY", "").strip()

API = "https://pixabay.com/api/"
UA = "CiudadBonitaDemo/1.0 (proyecto educativo Django; fotos de Pixabay para demo)"

# Pixabay no expone orientación "square": se pide "vertical" (portrait) a los
# productos y "horizontal" a hero/banners/categorías; el recorte cuadrado
# centrado se aplica después con Pillow (PASO 5).

MIN_ANCHO = 1200
CANDIDATOS = 12    # candidatos por consulta que se conservan (PASO 3)
PEDIR = 40         # se piden más a la API para tener margen tras el filtro
DIA_SEG = 24 * 3600  # caché de 24 h que exigen los términos

# Palabras en tags/URL que descartan la foto (personas, texto, gráficos).
# Se buscan como palabras completas: sin \b, "apartment" caía por "men" y
# "design" por "sign" (falsos positivos que vaciaban consultas enteras).
PROHIBIDAS = [
    "person", "people", "woman", "women", "man", "men", "model", "baby",
    "child", "kid", "girl", "boy", "human", "couple", "portrait",
    "logo", "brand", "text", "lettering", "typography", "poster", "banner",
    "screenshot", "illustration", "cartoon", "drawing", "painting",
    "render", "ai generated", "clipart", "font", "sign", "advertisement",
]

# ---------------------------------------------------------------------------
# Consultas en inglés (PASO 2): una por tipo de producto + usos de la web.
# Cada entrada: (orientación, consulta, etiqueta corta para el archivo).
# ---------------------------------------------------------------------------
CONSULTAS = {
    # --- Productos (por categoría del catálogo) ---
    "producto:Sábanas y juegos de cama:Sencillas": (
        "vertical", "white bed sheets fitted sheet mattress", "sabanas-sencillas"),
    "producto:Sábanas y juegos de cama:Semidobles": (
        "vertical", "neatly made bed white linen bedding bedroom", "sabanas-semidobles"),
    "producto:Sábanas y juegos de cama:Dobles": (
        "vertical", "bed linen folded white cotton", "sabanas-dobles"),
    "producto:Sábanas y juegos de cama:Queen": (
        "vertical", "cozy bed with white sheets and pillows queen bed", "sabanas-queen"),
    "producto:Sábanas y juegos de cama:King": (
        "vertical", "large bed white duvet pillows luxury bedroom", "sabanas-king"),
    "producto:Edredones:Edredones con relleno": (
        "vertical", "duvet comforter on bed neutral bedroom", "edredones-relleno"),
    "producto:Edredones:Funda para edredón": (
        "vertical", "duvet cover grey bedding neatly made bed", "edredones-funda"),
    "producto:Cobijas y cubrelechos:Cobijas": (
        "vertical", "folded fleece blanket stack cozy", "cobijas"),
    "producto:Cobijas y cubrelechos:Cubrelechos": (
        "vertical", "bedspread covering bed bedroom", "cubrelechos"),
    "producto:Cobijas y cubrelechos:Mantas y plaids": (
        "vertical", "wool plaid throw blanket on sofa", "mantas-plaid"),
    "producto:Almohadas y protectores:Almohadas": (
        "vertical", "white bed pillows on bed close up", "almohadas"),
    "producto:Almohadas y protectores:Protectores": (
        "vertical", "white mattress bed bedroom", "protectores"),
    "producto:Almohadas y protectores:Almohadas ergonómicas": (
        "vertical", "orthopedic pillow on white bedding", "almohadas-ergo"),
    "producto:Toallas:Toallas de baño": (
        "vertical", "stack of white bath towels spa", "toallas-bano"),
    "producto:Toallas:Toallas de playa": (
        "vertical", "striped beach towel on sand", "toallas-playa"),
    "producto:Toallas:Toallas de cocina": (
        "vertical", "cotton kitchen towels hanging folded", "toallas-cocina"),
    "producto:Artículos de baño:Exfoliantes": (
        "vertical", "bath sponge loofah spa", "exfoliantes"),
    "producto:Artículos de baño:Batas": (
        "vertical", "bathrobe towel spa", "batas"),
    "producto:Artículos de baño:Accesorios de ducha": (
        "vertical", "shower accessories bathroom minimal", "ducha-accesorios"),
    "producto:Cortinas:Cortinas opacas": (
        "vertical", "blackout curtains living room window", "cortinas-opacas"),
    "producto:Cortinas:Cortinas decorativas": (
        "vertical", "sheer curtain window living room light", "cortinas-deco"),
    "producto:Cortinas:Cortinas baño": (
        "vertical", "shower curtain bathroom interior", "cortinas-bano"),
    "producto:Cojines decoración y mantelería:Cojines": (
        "vertical", "decorative cushions on sofa", "cojines"),
    "producto:Cojines decoración y mantelería:Mantelería": (
        "vertical", "linen tablecloth dining table setting", "manteleria"),
    "producto:Cojines decoración y mantelería:Manteles": (
        "vertical", "white table linen on rustic dining table", "manteles"),
    "producto:Cojines decoración y mantelería:Camino de mesa": (
        "vertical", "table runner wooden table decoration", "camino-mesa"),

    # --- Usos de la web (PASO 2) ---
    "web:hero": (
        "horizontal", "warm cozy bedroom morning light bed linen", "hero"),
    "web:banner_bordados": (
        "horizontal", "embroidered towels monogram detail", "banner-bordados"),
    "web:banner_suscripcion": (
        "horizontal", "folded linen towels stack soft pastel", "banner-suscripcion"),
    "web:categoria:Sábanas y juegos de cama": (
        "horizontal", "bedroom with made bed white sheets", "cat-sabanas"),
    "web:categoria:Edredones": (
        "horizontal", "bed with fluffy duvet winter bedroom", "cat-edredones"),
    "web:categoria:Cobijas y cubrelechos": (
        "horizontal", "blanket on bed cozy neutral tones", "cat-cobijas"),
    "web:categoria:Almohadas y protectores": (
        "horizontal", "pile of pillows on bed white", "cat-almohadas"),
    "web:categoria:Toallas": (
        "horizontal", "towels hanging spa bathroom shelf", "cat-toallas"),
    "web:categoria:Artículos de baño": (
        "horizontal", "minimal bathroom with bath accessories", "cat-bano"),
    "web:categoria:Cortinas": (
        "horizontal", "curtains window daylight living room", "cat-cortinas"),
    "web:categoria:Cojines decoración y mantelería": (
        "horizontal", "cushions and table linen living room decor", "cat-cojines"),
}


# ---------------------------------------------------------------------------
# Utilidades
# ---------------------------------------------------------------------------
def slug(texto):
    """Slug simple en ASCII para nombres de archivo."""
    texto = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-zA-Z0-9]+", "-", texto).strip("-").lower()


def pedir(url, intentos=3):
    """GET a la API con espera entre reintentos (límite de Pixabay)."""
    ultimo = None
    for i in range(intentos):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=30) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except Exception as exc:  # noqa: BLE001 — se reintenta cualquier fallo
            ultimo = exc
            time.sleep(2 * (i + 1))
    raise SystemExit(f"La API no respondió: {ultimo}")


def archivo_cache(nombre):
    """Devuelve (ruta, datos) si la caché de 24 h está vigente, si no None."""
    ruta = CACHE / f"{nombre}.json"
    if ruta.exists() and (time.time() - ruta.stat().st_mtime) < DIA_SEG:
        return json.loads(ruta.read_text(encoding="utf-8"))
    return None


def buscar(consulta, orientacion, forzar=False):
    """Resultado de búsqueda cacheado 24 h (términos de Pixabay)."""
    nombre = slug(f"{consulta}-{orientacion}-p{PEDIR}")
    if not forzar:
        cacheado = archivo_cache(nombre)
        if cacheado is not None:
            return cacheado
    if not CLAVE:
        raise SystemExit(
            "Falta PIXABAY_API_KEY en .env. La clave nunca va al repo."
        )
    params = urllib.parse.urlencode({
        "key": CLAVE,
        "q": consulta,
        "image_type": "photo",
        "orientation": orientacion,
        "min_width": MIN_ANCHO,
        "safesearch": "true",
        "per_page": PEDIR,
        "order": "popular",
    })
    datos = pedir(f"{API}?{params}")
    CACHE.mkdir(parents=True, exist_ok=True)
    (CACHE / f"{nombre}.json").write_text(
        json.dumps(datos, ensure_ascii=False, indent=1), encoding="utf-8")
    time.sleep(1.1)  # somos educados con el límite de 100/min
    return datos


def apta(foto):
    """Filtro automático (PASO 3): tamaño y ausencia de personas/texto.

    Coincide por palabra completa: con subcadena, "apartment" caía por
    "men" y "design" por "sign" (falsos positivos que vaciaban consultas).
    """
    if int(foto.get("imageWidth") or 0) < MIN_ANCHO:
        return False
    texto = f"{foto.get('tags', '')} {foto.get('pageURL', '')}".lower()
    return not any(re.search(rf"\b{re.escape(p)}\b", texto) for p in PROHIBIDAS)


def bajar(url, destino):
    """Descarga real (sin hotlinking) con reintentos."""
    destino.parent.mkdir(parents=True, exist_ok=True)
    for i in range(3):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=60) as resp:
                destino.write_bytes(resp.read())
            return True
        except Exception:  # noqa: BLE001
            time.sleep(2 * (i + 1))
    print(f"  ! no se pudo bajar: {url}")
    return False


# ---------------------------------------------------------------------------
# PASO 2-3: descarga de candidatos
# ---------------------------------------------------------------------------
# Segunda formulación por etiqueta: se usa cuando la primera da menos de
# 6 fotos aptas (REGLA: reformular en vez de quedarse con la primera foto).
REFORMULAS = {
    "sabanas-sencillas": "white bedsheet bed",
    "sabanas-semidobles": "made bed white linen",
    "sabanas-dobles": "folded bed sheets",
    "sabanas-queen": "bed white pillows bedroom",
    "sabanas-king": "big bed white duvet",
    "edredones-relleno": "duvet bed",
    "edredones-funda": "grey duvet bed",
    "cobijas": "folded blankets",
    "cubrelechos": "bedspread bed",
    "mantas-plaid": "plaid blanket",
    "almohadas": "pillows bed",
    "protectores": "mattress white",
    "almohadas-ergo": "pillow bedding",
    "toallas-bano": "bath towels stack",
    "toallas-playa": "beach towel",
    "toallas-cocina": "kitchen towels",
    "exfoliantes": "spa accessories",
    "batas": "bathrobe",
    "ducha-accesorios": "bathroom accessories",
    "cortinas-opacas": "curtains window",
    "cortinas-deco": "curtain window",
    "cortinas-bano": "bathroom curtain",
    "cojines": "throw pillows sofa",
    "manteleria": "tablecloth table",
    "manteles": "table linen",
    "camino-mesa": "table runner",
    "hero": "cozy bedroom",
    "banner-bordados": "towel embroidery",
    "banner-suscripcion": "folded towels",
    "cat-sabanas": "bedroom bed white",
    "cat-edredones": "duvet bedroom",
    "cat-cobijas": "blanket bed cozy",
    "cat-almohadas": "pillows white bed",
    "cat-toallas": "towels bathroom",
    "cat-bano": "bathroom interior",
    "cat-cortinas": "curtains living room",
    "cat-cojines": "pillows sofa decor",
}


def _aptos_de(consulta, orient, forzar):
    """Candidatos aptos de una consulta (el tope es su propio ranking)."""
    datos = buscar(consulta, orient, forzar=forzar)
    return [f for f in datos.get("hits", []) if apta(f)]


def cmd_descargar(forzar=False):
    """Baja hasta 12 candidatos por consulta a scripts/candidatas/<etiqueta>/."""
    if not CLAVE:
        raise SystemExit("Falta PIXABAY_API_KEY en .env (nunca va al repo).")
    # Limpia fotos de corridas anteriores (el manifiesto manda)
    for carpeta in CANDIDATAS.iterdir():
        if carpeta.is_dir() and carpeta.name != "cache":
            for viejo in carpeta.glob("*.jpg"):
                viejo.unlink()

    total_ok, resumen, manifiesto = 0, [], []
    # La misma foto puede ser candidata en dos consultas: se descarga una
    # sola vez y se referencia en ambos manifiestos. La duplicación real
    # (dos productos iguales) se evita al elegir las finales.
    descargadas = {}
    for clave, (orient, consulta, etiqueta) in CONSULTAS.items():
        elegibles = _aptos_de(consulta, orient, forzar)
        # Si la consulta salió débil, se reformula (REGLA del encargo)
        if len(elegibles) < 6 and etiqueta in REFORMULAS:
            otra = REFORMULAS[etiqueta]
            if otra != consulta:
                nuevos = _aptos_de(otra, orient, forzar)
                if len(nuevos) > len(elegibles):
                    elegibles, consulta = nuevos, otra
        elegibles = elegibles[:CANDIDATOS]
        carpeta = CANDIDATAS / etiqueta
        carpeta.mkdir(parents=True, exist_ok=True)
        bajados = 0
        for i, foto in enumerate(elegibles, 1):
            # Reutiliza la descarga si la foto ya bajó en otra consulta
            if foto["id"] in descargadas:
                etiq_orig, nom_orig = descargadas[foto["id"]]
                archivo, origen = nom_orig, f"{etiq_orig}/{nom_orig}"
            else:
                nombre = f"{etiqueta}_{i:02d}_{foto['id']}.jpg"
                ruta = carpeta / nombre
                # Calidad para el retoque final: largeImageURL (1920 px) y
                # webformatURL (1280 px) como respaldo; previewURL (640 px)
                # sería demasiado pequeña para la foto principal de 1200 px.
                fuentes = [foto.get("largeImageURL"), foto.get("webformatURL"),
                           foto.get("previewURL")]
                if not any(bajar(u, ruta) for u in fuentes if u):
                    continue
                descargadas[foto["id"]] = (etiqueta, nombre)
                archivo, origen = nombre, f"{etiqueta}/{nombre}"
            bajados += 1
            manifiesto.append({
                "clave": clave, "etiqueta": etiqueta, "consulta": consulta,
                "orden": i, "id": foto["id"], "archivo": archivo,
                "origen": origen,
                "fotografo": foto.get("user", ""),
                "url": foto.get("pageURL", ""),
                "licencia": "Pixabay Content License",
                "ancho": foto.get("imageWidth"), "alto": foto.get("imageHeight"),
                "tags": foto.get("tags", ""),
            })
        total_ok += bajados
        resumen.append((clave, consulta, bajados))
        print(f"  {etiqueta}: {bajados} candidatos  «{consulta}»")
    (CANDIDATAS / "catalogo.jsonl").write_text(
        "\n".join(json.dumps({
            "clave": c, "consulta": q, "candidatos": n,
        }, ensure_ascii=False) for c, q, n in resumen),
        encoding="utf-8")
    (CANDIDATAS / "manifiesto.json").write_text(
        json.dumps(manifiesto, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\nTotal: {total_ok} candidatos descargados en scripts/candidatas/")

# ---------------------------------------------------------------------------
# PASO 4: hoja de contactos para que el usuario elija
# ---------------------------------------------------------------------------
def cmd_hoja():
    """Genera scripts/candidatas/index.html con miniaturas numeradas."""
    manifiesto = json.loads((CANDIDATAS / "manifiesto.json").read_text(encoding="utf-8"))
    if not manifiesto:
        raise SystemExit("No hay manifiesto: corre primero `descargar`.")
    por_clave = {}
    for reg in manifiesto:
        por_clave.setdefault(reg["clave"], []).append(reg)

    filas = []
    for clave in CONSULTAS:
        regs = por_clave.get(clave, [])
        if not regs:
            continue
        orient, consulta, etiqueta = CONSULTAS[clave]
        tipo = "Producto" if clave.startswith("producto:") else "Web"
        filas.append(f'<h2 id="{slug(etiqueta)}">{html.escape(clave.split(":", 1)[1])}'
                     f' <small>· {tipo} · «{html.escape(consulta)}»</small></h2>')
        filas.append('<div class="grid">')
        for reg in regs:
            rel = reg.get("origen", f"{reg['etiqueta']}/{reg['archivo']}")
            filas.append(
                f'<figure id="foto-{reg["id"]}">'
                f'<a href="{rel}" target="_blank" rel="noopener">'
                f'<img src="{rel}" alt="{html.escape(reg["tags"])}" loading="lazy"></a>'
                f'<figcaption><b>{reg["etiqueta"]}_{reg["orden"]:02d}</b>'
                f' · id {reg["id"]}<br>{html.escape(reg["fotografo"] or "—")}'
                f'<br><span class="ancho">{reg["ancho"]}×{reg["alto"]}</span></figcaption>'
                f'</figure>')
        filas.append("</div>")

    indice = "".join(
        f'<a href="#{slug(val[2])}">{html.escape(val[1])}</a>'
        for val in CONSULTAS.values())

    doc = f"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Candidatas — fotos de la demo</title>
<style>
  :root {{ --borde:#E7DCEE; --texto:#2A2230; --purpura:#8A4FBF; }}
  * {{ box-sizing:border-box; }}
  body {{ font-family:system-ui,Segoe UI,sans-serif; color:var(--texto);
         background:#FFF8FB; margin:0; padding:24px; }}
  h1 {{ font-size:1.4rem; margin:0 0 6px; }}
  .intro {{ background:#F1E8FA; border:1px solid var(--borde); border-radius:12px;
            padding:12px 16px; margin:14px 0 20px; max-width:70ch; font-size:.92rem; }}
  nav {{ display:flex; flex-wrap:wrap; gap:8px; margin-bottom:20px; }}
  nav a {{ font-size:.78rem; background:#fff; border:1px solid var(--borde);
           border-radius:999px; padding:4px 11px; text-decoration:none; color:var(--purpura); }}
  h2 {{ font-size:1.02rem; margin:30px 0 10px; border-bottom:2px solid var(--borde);
        padding-bottom:6px; }}
  h2 small {{ font-weight:400; color:#6A6173; font-size:.8rem; }}
  .grid {{ display:grid; grid-template-columns:repeat(auto-fill,minmax(180px,1fr));
           gap:14px; }}
  figure {{ margin:0; background:#fff; border:1px solid var(--borde);
            border-radius:12px; overflow:hidden; }}
  figure img {{ width:100%; aspect-ratio:1/1; object-fit:cover; display:block; }}
  figcaption {{ font-size:.74rem; padding:7px 9px; line-height:1.45; }}
  figcaption b {{ color:var(--purpura); }}
  .ancho {{ color:#6A6173; }}
  footer {{ margin-top:34px; font-size:.8rem; color:#6A6173; }}
</style>
</head>
<body>
<h1>Candidatas — fotos reales de la demo</h1>
<p class="intro">Marca tus elecciones en <code>scripts/elecciones.json</code>
(clave de consulta → id de foto, o un objeto con <code>"principal"</code> y
<code>"galeria"</code> para productos). Después ejecuta
<code>python scripts/imagenes_demo.py finales</code>. Licencia de todas:
Pixabay Content License (uso libre, atribución agradecida).</p>
<nav>{indice}</nav>
{"".join(filas)}
<footer>Generado el {datetime.now().strftime("%d/%m/%Y %H:%M")} ·
Pulsa una miniatura para verla en tamaño completo.</footer>
</body>
</html>"""
    (CANDIDATAS / "index.html").write_text(doc, encoding="utf-8")
    print(f"Hoja generada: {CANDIDATAS / 'index.html'} ({len(manifiesto)} fotos)")

# ---------------------------------------------------------------------------
# PASO 5: fotos finales en static/demo/ (WebP con Pillow) + CREDITOS.md
# ---------------------------------------------------------------------------
def _abrir(ruta):
    from PIL import Image
    im = Image.open(ruta)
    return im.convert("RGB")


def _foto_de(reg):
    """Ruta local de la descarga (puede vivir en la carpeta de otra consulta)."""
    return CANDIDATAS / reg.get("origen", f"{reg['etiqueta']}/{reg['archivo']}")


def _guardar(im, destino, ancho_max, calidad=82):
    """Redimensiona (LANCZOS) y guarda como WebP en static/demo/."""
    if im.width > ancho_max:
        prop = ancho_max / float(im.width)
        im = im.resize((ancho_max, max(1, int(im.height * prop))), Image.LANCZOS)
    destino.parent.mkdir(parents=True, exist_ok=True)
    im.save(destino, format="WEBP", quality=calidad, method=6)


def _cuadrada(im):
    """Recorte cuadrado centrado (PASO 5)."""
    lado = min(im.size)
    izq = (im.width - lado) // 2
    arr = (im.height - lado) // 2
    return im.crop((izq, arr, izq + lado, arr + lado))


def _resolver(valor, candidatos, clave):
    """Convierte la marca de elecciones en una lista de registros candidatos.

    Acepta: un id (número), un objeto {"principal": id, "galeria": [ids]} o
    None (usa el primer candidato, con aviso). Devuelve [(reg, es_principal)].
    """
    por_id = {r["id"]: r for r in candidatos}
    if not candidatos:
        raise SystemExit(f"Sin candidatos para «{clave}»: corre `descargar`.")
    avisos = []

    def _uno(marcado):
        if marcado is None:
            return candidatos[0]
        try:
            buscado = int(marcado)
        except (TypeError, ValueError):
            return candidatos[0]
        if buscado not in por_id:
            avisos.append(f"  ! {clave}: id {buscado} no está entre los candidatos; "
                          f"se usa el primero.")
            return candidatos[0]
        return por_id[buscado]

    if isinstance(valor, dict):
        principal = _uno(valor.get("principal"))
        elegidos = [principal]
        for gid in valor.get("galeria", []):
            reg = _uno(gid)
            if reg["id"] != principal["id"] and reg not in elegidos:
                elegidos.append(reg)
        # Garantiza 2-3 fotos por producto si no se marcó galería
        for reg in candidatos:
            if len(elegidos) >= 3:
                break
            if reg["id"] not in {r["id"] for r in elegidos}:
                elegidos.append(reg)
        salida = [(elegidos[0], True)] + [(r, False) for r in elegidos[1:]]
    else:
        principal = _uno(valor)
        salida = [(principal, True)]
        for reg in candidatos:
            if len(salida) >= 3:
                break
            if reg["id"] != principal["id"]:
                salida.append((reg, False))
    for a in avisos:
        print(a)
    return salida


def cmd_finales():
    if not ELECCIONES.exists():
        raise SystemExit(
            "Falta scripts/elecciones.json. Genera la hoja (`hoja`), "
            "marca tus elecciones (o usa la preselección) y vuelve a correr.")
    elecciones = json.loads(ELECCIONES.read_text(encoding="utf-8"))
    manifiesto = json.loads((CANDIDATAS / "manifiesto.json").read_text(encoding="utf-8"))
    por_clave = {}
    for reg in manifiesto:
        por_clave.setdefault(reg["clave"], []).append(reg)

    usados_global, creditos = set(), []
    faltantes = []

    def _registrar(reg, uso):
        if reg["id"] in usados_global:
            return False
        usados_global.add(reg["id"])
        creditos.append((reg, uso))
        return True

    # --- Usos de la web: hero y banners ---
    for clave, nombre in [("web:hero", "hero"),
                          ("web:banner_bordados", "banner-bordados"),
                          ("web:banner_suscripcion", "banner-suscripcion")]:
        candidatos = por_clave.get(clave, [])
        if not candidatos:
            faltantes.append(clave)
            continue
        ancho = 1600 if clave == "web:hero" else 1400
        reg = _resolver(elecciones.get(clave), candidatos, clave)[0][0]
        if not _registrar(reg, nombre):
            continue
        _guardar(_abrir(_foto_de(reg)),
                 DEMO / f"{nombre}.webp", ancho)
        print(f"  {nombre}.webp  ← id {reg['id']} ({reg['fotografo']})")

    # --- 8 imágenes de categoría ---
    for clave in [k for k in CONSULTAS if k.startswith("web:categoria:")]:
        candidatos = por_clave.get(clave, [])
        if not candidatos:
            faltantes.append(clave)
            continue
        categoria = clave.split(":", 2)[1]
        reg = _resolver(elecciones.get(clave), candidatos, clave)[0][0]
        if not _registrar(reg, f"categoría: {categoria}"):
            continue
        destino = DEMO / "categorias" / f"{slug(categoria)}.webp"
        _guardar(_abrir(_foto_de(reg)), destino, 900)
        print(f"  categorías/{destino.name}  ← id {reg['id']}")

    # --- Fotos de producto: un pool por categoría (2-3 por consulta) ---
    for clave in [k for k in CONSULTAS if k.startswith("producto:")]:
        candidatos = por_clave.get(clave, [])
        if not candidatos:
            faltantes.append(clave)
            continue
        categoria = clave.split(":", 2)[1]
        subcat = clave.split(":", 2)[2]
        carpeta = DEMO / "productos" / slug(categoria)
        # Elegidos por el usuario + el resto del ranking como respaldo:
        # si una foto ya se usó en otra consulta, se salta y toma la siguiente
        # (evita repetir la misma foto en dos productos, PASO 3).
        elegidos = _resolver(elecciones.get(clave), candidatos, clave)
        orden = [r for r, _ in elegidos]
        orden += [r for r in candidatos if r["id"] not in {e["id"] for e in orden}]
        n, principal_visto = 0, False
        for reg in orden:
            if n >= 3:
                break
            if not _registrar(reg, f"{categoria} › {subcat}"):
                continue
            es_principal = not principal_visto
            principal_visto = True
            base = carpeta / f"{slug(subcat)}-{reg['id']}"
            im = _abrir(_foto_de(reg))
            _guardar(_cuadrada(im), base.with_suffix(".webp"), 1200)
            _guardar(_cuadrada(im),
                     base.with_name(base.name + "_mini.webp"), 400)
            n += 1
            print(f"  productos/{base.name}.webp"
                  f"{' (principal)' if es_principal else ''} ← id {reg['id']}")
        if n == 0:
            faltantes.append(clave)

    _escribir_creditos(creditos)
    if faltantes:
        print("\nSin foto (revisa elecciones.json): " + ", ".join(faltantes))
    print(f"\nListo: {len(creditos)} fotos en static/demo/ + CREDITOS.md")


def _escribir_creditos(creditos):
    lineas = [
        "# Créditos de las imágenes de demo",
        "",
        "Fotos descargadas de **Pixabay** con `scripts/imagenes_demo.py`.",
        "Todas usan la [Pixabay Content License](https://pixabay.com/service/license-summary/):"
        " uso libre, también comercial, sin atribución obligatoria (agradecemos el crédito).",
        "Son **imágenes de ejemplo con fines de demostración**: no representan el producto "
        "real. Cámbialas por fotos propias antes de vender.",
        "",
        "| # | Foto (id) | Fotógrafo | Enlace | Uso |",
        "|---|-----------|-----------|--------|-----|",
    ]
    for i, (reg, uso) in enumerate(creditos, 1):
        url = reg["url"].replace("|", "%7C")
        lineas.append(
            f"| {i} | {reg['id']} | {reg['fotografo'] or '—'} "
            f"| [pixabay.com]({url}) | {uso} |")
    lineas += [
        "",
        f"_Generado el {datetime.now().strftime('%d/%m/%Y %H:%M')} · "
        f"{len(creditos)} fotos._",
        "",
    ]
    DEMO.mkdir(parents=True, exist_ok=True)
    (DEMO / "CREDITOS.md").write_text("\n".join(lineas), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description="Fotos reales de la demo (Pixabay)")
    parser.add_argument(
        "comando", choices=["descargar", "hoja", "finales"],
        help="descargar | hoja | finales")
    parser.add_argument("--forzar", action="store_true",
                        help="ignora la caché de 24 h y reconsulta la API")
    args = parser.parse_args()
    if args.comando == "descargar":
        cmd_descargar(args.forzar)
    elif args.comando == "hoja":
        cmd_hoja()
    else:
        cmd_finales()


if __name__ == "__main__":
    main()
