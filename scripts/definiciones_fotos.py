import os
import sys
import json
import urllib.request
import urllib.parse
from pathlib import Path
from PIL import Image, ImageOps, ImageEnhance
import io
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))
load_dotenv(BASE_DIR / ".env")

API_KEY = os.environ.get("PIXABAY_API_KEY", "").strip()

# Definición precisa de búsqueda para cada producto del catálogo
# Cada entrada tiene:
# - slug
# - query principal para Pixabay
# - palabras obligatorias o preferidas en tags
# - palabras prohibidas en tags
# - ajuste de color opcional (black_color, mid_color, white_color, blend_alpha)
CATALOGO_SPECS = [
    {
        "slug": "juego-de-sabanas-400-hilos-blanco-nacar",
        "query": "white bed sheets linen",
        "pos": ["bed", "sheet", "linen", "bedroom"],
        "neg": ["cat", "dog", "cocoa", "jeans", "girl", "woman", "bikini"],
        "color": None,
    },
    {
        "slug": "juego-de-sabanas-algodon-peinado-gris-perla",
        "query": "grey bed sheets bedroom",
        "pos": ["bed", "sheet", "bedroom", "grey", "gray"],
        "neg": ["cat", "dog", "woman", "girl"],
        "color": ((30, 30, 35), (150, 155, 160), (240, 242, 245), 0.7),
    },
    {
        "slug": "sabana-ajustable-con-cierre-rosa-palo",
        "query": "bed sheets bedroom linen",
        "pos": ["bed", "sheet", "linen", "bedroom"],
        "neg": ["flower", "bouquet", "roses", "coffee", "cat", "dog", "baby"],
        "color": ((45, 20, 25), (210, 150, 165), (250, 230, 235), 0.82),
    },
    {
        "slug": "juego-de-sabanas-300-hilos-estampado-floral",
        "query": "floral bed sheets",
        "pos": ["bed", "sheets", "floral", "bedroom"],
        "neg": ["cat", "dog", "food", "breakfast"],
        "color": None,
    },
    {
        "slug": "sabana-sencilla-lisas-6-colores",
        "query": "folded bed sheets linen stack",
        "pos": ["sheet", "linen", "folded", "stack", "textile", "towels"],
        "neg": ["cat", "dog", "jeans"],
        "color": None,
    },
    {
        "slug": "edredon-doble-plumon-200-gr-blanco",
        "query": "white fluffy duvet bed",
        "pos": ["bed", "duvet", "comforter", "bedroom", "white"],
        "neg": ["clock", "alarm", "cat", "dog", "girl", "woman"],
        "color": None,
    },
    {
        "slug": "edredon-semidoble-sintetico-acolchado",
        "query": "quilted comforter bed duvet",
        "pos": ["bed", "comforter", "duvet", "bedroom"],
        "neg": ["clock", "cat", "dog"],
        "color": None,
    },
    {
        "slug": "funda-para-edredon-400-hilos-estampado-lunares",
        "query": "patterned duvet cover bedding",
        "pos": ["bed", "duvet", "bedding", "pillow"],
        "neg": ["cat", "dog", "baby", "coffee"],
        "color": None,
    },
    {
        "slug": "edredon-infantil-plano-motivos-de-flores",
        "query": "floral duvet bedding cozy",
        "pos": ["bed", "duvet", "bedroom", "linen"],
        "neg": ["family", "baby", "woman", "child", "girl"],
        "color": None,
    },
    {
        "slug": "cobija-acolchada-doble-beige",
        "query": "beige blanket cozy bed",
        "pos": ["blanket", "bed", "cozy", "bedroom"],
        "neg": ["sleeping", "woman", "girl", "man", "cat", "dog"],
        "color": ((40, 32, 20), (195, 175, 140), (250, 245, 235), 0.75),
    },
    {
        "slug": "cubrelechos-semidoble-jacquard",
        "query": "bedspread bedroom cozy",
        "pos": ["bed", "bedspread", "bedroom", "interior"],
        "neg": ["cat", "dog", "reading", "books"],
        "color": None,
    },
    {
        "slug": "cobija-pesada-tipo-manta-gris",
        "query": "grey knit throw blanket",
        "pos": ["blanket", "throw", "knit", "sofa", "bed"],
        "neg": ["cat", "dog", "woman"],
        "color": None,
    },
    {
        "slug": "cubrelechos-king-bordado-en-esquinas",
        "query": "luxury bedspread master bedroom",
        "pos": ["bed", "bedroom", "luxury", "hotel", "bedspread"],
        "neg": ["chandelier", "cat", "dog"],
        "color": None,
    },
    {
        "slug": "almohada-rectangular-50x65-fibra-siliconada",
        "query": "white bed pillow",
        "pos": ["pillow", "bed", "sleep", "white"],
        "neg": ["cat", "dog", "alarm", "clock"],
        "color": None,
    },
    {
        "slug": "almohada-ortopedica-viscoelastica",
        "query": "orthopedic pillow memory foam",
        "pos": ["pillow", "bed", "sleep"],
        "neg": ["cat", "dog"],
        "color": None,
    },
    {
        "slug": "protector-de-colchon-impermeable-queen",
        "query": "mattress bed fitted",
        "pos": ["bed", "mattress", "bedroom"],
        "neg": ["cat", "dog"],
        "color": None,
    },
    {
        "slug": "pack-de-2-almohadas-con-funda-bordada",
        "query": "pillows bed linen headboard",
        "pos": ["pillow", "bed", "bedroom"],
        "neg": ["cat", "dog"],
        "color": None,
    },
    {
        "slug": "toalla-de-bano-500-gm2-blanco",
        "query": "white bath towels spa",
        "pos": ["towel", "bath", "spa", "white"],
        "neg": ["cat", "dog", "beach"],
        "color": None,
    },
    {
        "slug": "toalla-cara-y-mano-set-x2-verde-agua",
        "query": "bath towels spa",
        "pos": ["towel", "bath", "spa", "cotton"],
        "neg": ["cat", "dog", "beach"],
        "color": ((15, 35, 25), (95, 175, 145), (225, 245, 235), 0.85),
    },
    {
        "slug": "toalla-de-playa-gigante-90x180",
        "query": "striped beach towel sand",
        "pos": ["towel", "beach", "sand", "summer"],
        "neg": ["person", "bikini", "woman", "man", "sunbathing"],
        "color": None,
    },
    {
        "slug": "toalla-de-bano-600-gm2-premium",
        "query": "folded bath towels stack",
        "pos": ["towel", "bath", "spa", "stack"],
        "neg": ["cat", "dog"],
        "color": None,
    },
    {
        "slug": "set-de-4-toallas-de-bano-linea-hotel",
        "query": "stack of white towels hotel bathroom",
        "pos": ["towel", "towels", "bath", "white", "hotel"],
        "neg": ["cat", "dog"],
        "color": None,
    },
    {
        "slug": "cortina-de-bano-peva-con-imanes",
        "query": "shower curtain bathroom clean",
        "pos": ["curtain", "shower", "bathroom"],
        "neg": ["cat", "dog"],
        "color": None,
    },
    {
        "slug": "tapete-de-bano-antideslizante-blanco",
        "query": "bath mat bathroom floor",
        "pos": ["bath", "bathroom", "mat", "floor", "tub"],
        "neg": ["cat", "dog", "living room"],
        "color": None,
    },
    {
        "slug": "set-de-3-accesorios-de-bano-con-soporte",
        "query": "bathroom accessories soap dispenser",
        "pos": ["bathroom", "accessories", "soap", "sink"],
        "neg": ["cat", "dog"],
        "color": None,
    },
    {
        "slug": "cortina-de-bano-textil-con-diseno-de-piedras",
        "query": "shower curtain bathroom bathtub",
        "pos": ["curtain", "shower", "bathroom"],
        "neg": ["cat", "dog"],
        "color": None,
    },
    {
        "slug": "tapete-masajeador-de-goma-gris",
        "query": "bathroom mat floor interior",
        "pos": ["bathroom", "mat", "floor", "bath"],
        "neg": ["cat", "dog", "living room", "chairs"],
        "color": ((25, 25, 28), (120, 125, 130), (220, 222, 225), 0.8),
    },
    {
        "slug": "cortina-blackout-140x250-vino",
        "query": "curtains window modern",
        "pos": ["curtain", "window", "fabric", "drape"],
        "neg": ["cat", "dog", "dublin", "theater", "stage", "audience"],
        "color": ((35, 5, 12), (125, 18, 38), (240, 195, 205), 0.88),
    },
    {
        "slug": "cortina-con-vuelo-y-ojales-crema",
        "query": "beige curtains window living room",
        "pos": ["curtain", "window", "living room", "beige"],
        "neg": ["cat", "dog", "tv", "dublin"],
        "color": None,
    },
    {
        "slug": "cortina-voile-con-paneles-blanco",
        "query": "white sheer curtains window sunlight",
        "pos": ["curtain", "window", "white", "light"],
        "neg": ["cat", "dog", "crystals", "beads"],
        "color": None,
    },
    {
        "slug": "cortina-triple-capa-blackout-estampada",
        "query": "patterned curtains window bedroom",
        "pos": ["curtain", "window", "fabric"],
        "neg": ["cat", "dog", "facade", "hotel"],
        "color": None,
    },
    {
        "slug": "cojin-decorativo-cuadrado-45x45-terracota",
        "query": "decorative throw pillow sofa",
        "pos": ["pillow", "cushion", "sofa", "living room"],
        "neg": ["cat", "dog", "bed"],
        "color": ((45, 15, 8), (185, 85, 45), (250, 210, 190), 0.85),
    },
    {
        "slug": "pack-de-2-cojines-redondos-rosa-antiguo",
        "query": "cushions sofa pillows living room",
        "pos": ["pillow", "cushion", "sofa", "pillows"],
        "neg": ["cat", "dog"],
        "color": ((40, 15, 22), (195, 125, 140), (250, 225, 230), 0.82),
    },
    {
        "slug": "mantel-rectangular-6-plazas-lino-natural",
        "query": "linen tablecloth dining table",
        "pos": ["table", "tablecloth", "dining", "linen"],
        "neg": ["cat", "dog"],
        "color": None,
    },
    {
        "slug": "servilletas-de-tela-x4-crema-bordadas",
        "query": "cloth napkins table setting dining",
        "pos": ["napkins", "table", "dining", "cloth"],
        "neg": ["cat", "dog"],
        "color": None,
    },
    {
        "slug": "cojin-de-sofa-rectangular-30x50-indigo",
        "query": "blue cushion pillow sofa",
        "pos": ["pillow", "cushion", "sofa"],
        "neg": ["cat", "dog"],
        "color": ((10, 15, 35), (45, 65, 115), (200, 215, 245), 0.85),
    },
    {
        "slug": "camino-de-mesa-estampado-flores",
        "query": "table runner dining table flowers",
        "pos": ["table", "runner", "dining"],
        "neg": ["cat", "dog"],
        "color": None,
    },
    {
        "slug": "juego-de-sabanas-para-cama-sencilla-azul-cielo",
        "query": "blue bed sheets bedroom",
        "pos": ["bed", "sheets", "bedroom"],
        "neg": ["cat", "dog", "woman", "girl"],
        "color": ((15, 25, 45), (110, 155, 205), (225, 240, 255), 0.85),
    },
    {
        "slug": "toalla-de-playa-microfibra-compacta-multicolor",
        "query": "colorful beach towel sand",
        "pos": ["towel", "beach", "sand", "summer"],
        "neg": ["person", "woman", "family", "picnic"],
        "color": None,
    },
    {
        "slug": "cojin-lumbar-rectangular-20x40-mostaza",
        "query": "cushion pillow sofa living room",
        "pos": ["pillow", "cushion", "sofa"],
        "neg": ["cat", "dog", "bed"],
        "color": ((35, 25, 5), (205, 155, 25), (255, 245, 200), 0.88),
    },
]

print(f"Total specs definidas: {len(CATALOGO_SPECS)}")
