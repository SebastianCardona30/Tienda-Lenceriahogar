#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Genera las fotos de los productos extra con Pixabay (costo $0).

Uso: python scripts/nuevos_productos.py
Descarga 1 foto por producto (WebP 1200 px + miniatura 400 px cuadrada)
a media/productos/, igual que las 40 existentes. Sin conexión no corre;
una vez generadas, los archivos viajan en git y Vercel no necesita la API.
"""
import os
import sys
import time
import json
import urllib.parse
import urllib.request
from pathlib import Path

from PIL import Image, ImageOps

BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE))
from dotenv import load_dotenv  # noqa: E402

load_dotenv(BASE / ".env")

from catalog.productos_extra import (  # noqa: E402
    EXTRA_PRODUCTOS, EXTRA_CONSULTAS, NEGADAS,
)

CLAVE = os.environ.get("PIXABAY_API_KEY", "").strip()
CACHE = BASE / "scripts" / "candidatas" / "cache_nuevos"
CACHE.mkdir(parents=True, exist_ok=True)
MEDIA = BASE / "media" / "productos"
MINIS = MEDIA / "miniaturas"


def buscar(consulta):
    """Consulta cacheada en disco (evita repetir llamadas a la API)."""
    cache = CACHE / ("".join(c if c.isalnum() else "_" for c in consulta) + ".json")
    if cache.exists():
        return json.loads(cache.read_text(encoding="utf-8"))
    if not CLAVE:
        raise SystemExit("Falta PIXABAY_API_KEY en .env")
    url = ("https://pixabay.com/api/?" + urllib.parse.urlencode({
        "key": CLAVE, "q": consulta, "image_type": "photo",
        "orientation": "horizontal", "min_width": 1200,
        "safesearch": "true", "per_page": 20, "order": "popular",
    }))
    req = urllib.request.Request(url, headers={"User-Agent": "CiudadBonitaDemo/1.0"})
    with urllib.request.urlopen(req, timeout=30) as r:
        datos = json.loads(r.read().decode("utf-8"))
    cache.write_text(json.dumps(datos, ensure_ascii=False), encoding="utf-8")
    time.sleep(1.1)
    return datos


def elegir(hits):
    """Primera foto apta: sin personas/texto y con buen ancho."""
    for h in hits:
        tags = (h.get("tags") or "").lower()
        if any(n in tags for n in NEGADAS):
            continue
        if int(h.get("imageWidth") or 0) < 1200:
            continue
        return h
    return None


def procesar(ruta_origen, nombre_salida):
    """Recorte cuadrado centrado -> WebP 1200 + miniatura 400."""
    im = Image.open(ruta_origen).convert("RGB")
    im = ImageOps.exif_transpose(im)
    lado = min(im.size)
    izq = (im.width - lado) // 2
    arr = (im.height - lado) // 2
    im = im.crop((izq, arr, izq + lado, arr + lado))
    grande = im.resize((1200, 1200), Image.LANCZOS)
    grande.save(MEDIA / nombre_salida, format="WEBP", quality=82, method=6)
    mini = im.resize((400, 400), Image.LANCZOS)
    mini.save(MINIS / nombre_salida, format="WEBP", quality=80, method=6)


def main():
    MINIS.mkdir(parents=True, exist_ok=True)
    sin_foto = []
    for nombre, *_ in EXTRA_PRODUCTOS:
        consulta = EXTRA_CONSULTAS.get(nombre)
        if not consulta:
            continue
        slug = (nombre.lower()
                .replace("á", "a").replace("é", "e").replace("í", "i")
                .replace("ó", "o").replace("ú", "u").replace("ñ", "n")
                .replace("²", "2"))
        import re as _re
        slug = _re.sub(r"[^a-z0-9]+", "-", slug).strip("-")
        salida = f"{slug}-1.webp"
        if (MEDIA / salida).exists():
            print(f"= ya existe {salida}")
            continue
        hits = buscar(consulta).get("hits", [])
        foto = elegir(hits)
        if not foto:
            sin_foto.append(nombre)
            print(f"! sin foto apta: {nombre}")
            continue
        raw = CACHE / f"{slug}.jpg"
        if not raw.exists():
            req = urllib.request.Request(
                foto["largeImageURL"] or foto["webformatURL"],
                headers={"User-Agent": "CiudadBonitaDemo/1.0"})
            with urllib.request.urlopen(req, timeout=60) as r:
                raw.write_bytes(r.read())
            time.sleep(0.8)
        procesar(raw, salida)
        print(f"+ {salida}  (Pixabay id {foto['id']})")
    if sin_foto:
        print("\nRevisar consultas para:", ", ".join(sin_foto))


if __name__ == "__main__":
    main()
