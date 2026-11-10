import os
import sys
import json
import time
import urllib.request
import urllib.parse
from pathlib import Path
from PIL import Image, ImageOps, ImageEnhance
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))
load_dotenv(BASE_DIR / ".env")

API_KEY = os.environ.get("PIXABAY_API_KEY", "").strip()
CACHE_DIR = BASE_DIR / "scripts" / "candidatas" / "cache_api"
CACHE_DIR.mkdir(parents=True, exist_ok=True)
RAW_DIR = BASE_DIR / "scripts" / "candidatas" / "descargas_raw"
RAW_DIR.mkdir(parents=True, exist_ok=True)

MEDIA_PROD = BASE_DIR / "media" / "productos"
MEDIA_MINI = MEDIA_PROD / "miniaturas"
MEDIA_PROD.mkdir(parents=True, exist_ok=True)
MEDIA_MINI.mkdir(parents=True, exist_ok=True)

from scripts.definiciones_fotos import CATALOGO_SPECS

def buscar_pixabay(query):
    safe_q = "".join(c if c.isalnum() else "_" for c in query)
    cache_file = CACHE_DIR / f"{safe_q}.json"
    if cache_file.exists():
        with open(cache_file, "r", encoding="utf-8") as f:
            return json.load(f)
    
    url = f"https://pixabay.com/api/?key={API_KEY}&q={urllib.parse.quote(query)}&image_type=photo&per_page=30"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            data = json.loads(r.read().decode("utf-8"))
            with open(cache_file, "w", encoding="utf-8") as f:
                json.dump(data, f)
            time.sleep(0.3)
            return data
    except Exception as e:
        print(f"Error buscando '{query}': {e}")
        return {"hits": []}

def descargar_foto(url, raw_path):
    if raw_path.exists() and raw_path.stat().st_size > 5000:
        return True
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            data = r.read()
            with open(raw_path, "wb") as f:
                f.write(data)
            return True
    except Exception as e:
        print(f"Error descargando {url}: {e}")
        return False

def procesar_imagen(raw_path, out_1200, out_400, color_spec=None):
    im = Image.open(raw_path).convert("RGB")
    
    # 1. Tinte de color si aplica
    if color_spec:
        black_c, mid_c, white_c, alpha = color_spec
        gray = ImageOps.grayscale(im)
        colorized = ImageOps.colorize(gray, black=black_c, white=white_c, mid=mid_c)
        im = Image.blend(im, colorized, alpha=alpha)
        enhancer = ImageEnhance.Contrast(im)
        im = enhancer.enhance(1.1)
    
    # 2. Recorte cuadrado centrado
    w, h = im.size
    min_side = min(w, h)
    left = (w - min_side) // 2
    top = (h - min_side) // 2
    cropped = im.crop((left, top, left + min_side, top + min_side))
    
    # 3. Guardar 1200x1200
    im_1200 = cropped.resize((1200, 1200), Image.Resampling.LANCZOS)
    im_1200.save(out_1200, "WEBP", quality=88, method=6)
    
    # 4. Guardar 400x400 miniatura
    im_400 = cropped.resize((400, 400), Image.Resampling.LANCZOS)
    im_400.save(out_400, "WEBP", quality=85, method=6)

def ejecutar():
    creditos = []
    exitos = 0
    fallos = 0
    
    for i, spec in enumerate(CATALOGO_SPECS, 1):
        slug = spec["slug"]
        query = spec["query"]
        pos_words = spec.get("pos", [])
        neg_words = spec.get("neg", [])
        color_spec = spec.get("color")
        
        print(f"[{i:02d}/40] Procesando {slug}...")
        res = buscar_pixabay(query)
        hits = res.get("hits", [])
        
        # Filtrar hits
        candidato = None
        for h in hits:
            tags = h.get("tags", "").lower()
            # Descartar si tiene palabras negativas
            if any(nw in tags for nw in neg_words):
                continue
            # Aceptar si tiene alguna palabra positiva o si pos_words está vacío
            if not pos_words or any(pw in tags for pw in pos_words):
                candidato = h
                break
        
        if not candidato and hits:
            # Fallback al primer hit que no tenga personas
            for h in hits:
                tags = h.get("tags", "").lower()
                if not any(nw in tags for nw in ["person", "woman", "man", "girl", "baby", "cat", "dog"]):
                    candidato = h
                    break
        
        if not candidato:
            print(f"  ALERTA: No se encontró candidato para {slug}")
            fallos += 1
            continue
        
        raw_filename = f"{slug}_{candidato['id']}.jpg"
        raw_path = RAW_DIR / raw_filename
        img_url = candidato.get("largeImageURL") or candidato.get("webformatURL")
        
        ok = descargar_foto(img_url, raw_path)
        if not ok:
            print(f"  ERROR: No se pudo descargar imagen para {slug}")
            fallos += 1
            continue
        
        out_1200 = MEDIA_PROD / f"{slug}-1.webp"
        out_400 = MEDIA_MINI / f"{slug}-1.webp"
        
        procesar_imagen(raw_path, out_1200, out_400, color_spec)
        exitos += 1
        
        creditos.append({
            "slug": slug,
            "id": candidato["id"],
            "fotografo": candidato.get("user", "Desconocido"),
            "url": f"https://pixabay.com/photos/{candidato['id']}/",
            "tags": candidato.get("tags", ""),
            "color_tint": bool(color_spec)
        })
        print(f"  OK: {slug} procesado ({candidato['id']} por {candidato.get('user')})")
    
    with open("scripts/creditos_nuevos.json", "w", encoding="utf-8") as f:
        json.dump(creditos, f, indent=2)
    
    print(f"\nRESUMEN: {exitos} exitosos, {fallos} fallos.")

if __name__ == "__main__":
    ejecutar()
