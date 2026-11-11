# -*- coding: utf-8 -*-
"""Productos ampliados del catálogo de demostración (24 piezas nuevas).

Cada entrada sigue el mismo formato que seed_demo.PRODUCTOS:
    (nombre, categoría, material, precio, [(talla, color), ...])

Las fotos se generan con scripts/nuevos_productos.py (Pixabay, costo $0)
y se guardan en media/productos/<slug>-1.webp + miniatura 400 px.
"""

EXTRA_PRODUCTOS = [
    # ---------- Sábanas y juegos de cama ----------
    ("Juego de sábanas satén 250 hilos - Blanco",
     "Sábanas y juegos de cama", "Satén de algodón", 159900,
     [("Sencilla", "Blanco"), ("Semidoble", "Blanco"), ("Doble", "Blanco")]),
    ("Juego de sábanas estampado geométrico - Gris",
     "Sábanas y juegos de cama", "Algodón", 149900,
     [("Semidoble", "Gris"), ("Doble", "Gris"), ("Queen", "Gris")]),
    ("Sábana ajustable lisa - Verde agua",
     "Sábanas y juegos de cama", "Microfibra", 59900,
     [("Sencilla", "Verde agua"), ("Semidoble", "Verde agua"), ("Doble", "Verde agua")]),

    # ---------- Edredones ----------
    ("Edredón plumón ligero 150 gr - Marfil",
     "Edredones", "Poliéster", 189900,
     [("Sencilla", "Marfil"), ("Doble", "Marfil")]),
    ("Edredón tejido acanalado - Rosa palo",
     "Edredones", "Algodón", 169900,
     [("Semidoble", "Rosa palo"), ("Doble", "Rosa palo")]),
    ("Funda para edredón lino lavado - Beige",
     "Edredones", "Lino", 129900,
     [("Doble", "Beige"), ("Queen", "Beige")]),

    # ---------- Cobijas y cubrelechos ----------
    ("Cobija térmica doble cara - Gris perla",
     "Cobijas y cubrelechos", "Poliéster", 119900,
     [("Doble", "Gris perla"), ("Queen", "Gris perla")]),
    ("Manta de fibra suave - Terracota",
     "Cobijas y cubrelechos", "Poliéster", 99900,
     [("Otra medida", "130 x 170 cm")]),
    ("Cubrelecho matelaseado - Blanco",
     "Cobijas y cubrelechos", "Algodón", 139900,
     [("Semidoble", "Blanco"), ("Doble", "Blanco"), ("King", "Blanco")]),

    # ---------- Almohadas y protectores ----------
    ("Almohada suave sensación pluma - Blanco",
     "Almohadas y protectores", "Poliéster", 49900,
     [("Otra medida", "50 x 70 cm")]),
    ("Pack de 2 protectores de almohada - Blanco",
     "Almohadas y protectores", "Algodón", 45900,
     [("Otra medida", "50 x 70 cm")]),
    ("Almohada cervical ergonómica - Gris",
     "Almohadas y protectores", "Viscoelástica", 89900,
     [("Otra medida", "40 x 60 cm")]),

    # ---------- Toallas ----------
    ("Toalla de baño 450 g/m² - Azul cielo",
     "Toallas", "Algodón", 45900,
     [("Baño", "Azul cielo"), ("Baño", "Blanco")]),
    ("Set de 3 toallas de cocina - Estampado",
     "Toallas", "Algodón", 35900,
     [("Mano", "Multicolor"), ("Mano", "Blanco")]),
    ("Toalla de manos premium - Rosa palo",
     "Toallas", "Algodón", 32900,
     [("Mano", "Rosa palo"), ("Mano", "Gris perla")]),

    # ---------- Artículos de baño ----------
    ("Bata de baño acolchada - Blanco",
     "Artículos de baño", "Poliéster", 89900,
     [("Otra medida", "M"), ("Otra medida", "L")]),
    ("Tapete de baño set x2 - Gris",
     "Artículos de baño", "Poliéster", 54900,
     [("Otra medida", "50 x 80 cm")]),
    ("Organizador de baño colgante - Beige",
     "Artículos de baño", "Poliéster", 39900,
     [("Otra medida", "Estándar")]),

    # ---------- Cortinas ----------
    ("Cortina blackout pana - Gris topo",
     "Cortinas", "Poliéster", 119900,
     [("Otra medida", "140 x 250 cm")]),
    ("Cortina de voile con aros - Marfil",
     "Cortinas", "Poliéster", 69900,
     [("Otra medida", "140 x 250 cm")]),
    ("Cortina estampada con forro - Azul noche",
     "Cortinas", "Poliéster", 129900,
     [("Otra medida", "160 x 260 cm")]),

    # ---------- Cojines, decoración y mantelería ----------
    ("Cojín terciopelo cuadrado 45x45 - Vino",
     "Cojines, decoración y mantelería", "Terciopelo", 42900,
     [("Otra medida", "45 x 45 cm")]),
    ("Mantel cuadrado lino - Blanco",
     "Cojines, decoración y mantelería", "Lino", 79900,
     [("Otra medida", "140 x 140 cm")]),
    ("Pack de 4 fundas de cojín - Multicolor",
     "Cojines, decoración y mantelería", "Algodón", 59900,
     [("Otra medida", "45 x 45 cm")]),
]

EXTRA_DATOS_PRODUCTO = {
    "Juego de sábanas satén 250 hilos - Blanco": (
        "Wamsutta", "sábanas, satén, 250 hilos, blanco, cama, hotel, regalo"),
    "Juego de sábanas estampado geométrico - Gris": (
        "IKEA", "sábanas, estampado, geométrico, gris, moderno, juvenil"),
    "Sábana ajustable lisa - Verde agua": (
        "IKEA", "sábana ajustable, verde agua, lisa, fresca, cama"),
    "Edredón plumón ligero 150 gr - Marfil": (
        "Pottery Barn", "edredón, plumón, ligero, marfil, cálido, invierno"),
    "Edredón tejido acanalado - Rosa palo": (
        "Zara Home", "edredón, acanalado, rosa palo, tejido, decoración"),
    "Funda para edredón lino lavado - Beige": (
        "Zara Home", "funda edredón, lino, beige, natural, minimalista"),
    "Cobija térmica doble cara - Gris perla": (
        "Pendleton", "cobija, térmica, doble cara, gris perla, abrigo"),
    "Manta de fibra suave - Terracota": (
        "Pendleton", "manta, fibra suave, terracota, sofá, decorativa"),
    "Cubrelecho matelaseado - Blanco": (
        "Williams Sonoma", "cubrelecho, matelaseado, blanco, elegante, cama"),
    "Almohada suave sensación pluma - Blanco": (
        "Serta", "almohada, suave, sensación pluma, blanco, descanso"),
    "Pack de 2 protectores de almohada - Blanco": (
        "Serta", "protector almohada, blanco, higiene, pack"),
    "Almohada cervical ergonómica - Gris": (
        "Serta", "almohada cervical, ergonómica, gris, soporte, ortopédica"),
    "Toalla de baño 450 g/m² - Azul cielo": (
        "1888 Mills", "toalla baño, 450 gramos, azul cielo, algodón, suave"),
    "Set de 3 toallas de cocina - Estampado": (
        "Christy", "toallas cocina, set, estampado, algodón, práctico"),
    "Toalla de manos premium - Rosa palo": (
        "Christy", "toalla manos, premium, rosa palo, baño, suave"),
    "Bata de baño acolchada - Blanco": (
        "Calvin Klein Home", "bata, baño, acolchada, blanco, cómoda, spa"),
    "Tapete de baño set x2 - Gris": (
        "IKEA", "tapete baño, set, gris, antideslizante, suave"),
    "Organizador de baño colgante - Beige": (
        "IKEA", "organizador, baño, colgante, beige, orden"),
    "Cortina blackout pana - Gris topo": (
        "H&M Home", "cortina, blackout, pana, gris topo, oscuridad, dormitorio"),
    "Cortina de voile con aros - Marfil": (
        "H&M Home", "cortina, voile, aros, marfil, luz, delicada"),
    "Cortina estampada con forro - Azul noche": (
        "H&M Home", "cortina, estampada, forro, azul noche, elegante"),
    "Cojín terciopelo cuadrado 45x45 - Vino": (
        "Zara Home", "cojín, terciopelo, vino, cuadrado, decorativo"),
    "Mantel cuadrado lino - Blanco": (
        "Williams Sonoma", "mantel, lino, blanco, cuadrado, mesa, cena"),
    "Pack de 4 fundas de cojín - Multicolor": (
        "Zara Home", "funda cojín, pack, multicolor, decoración, renovar"),
}

# Consultas de Pixabay por producto (misma filosofía que definiciones_fotos.py:
# consulta específica en inglés + palabras prohibidas para filtrar personas/texto)
EXTRA_CONSULTAS = {
    "Juego de sábanas satén 250 hilos - Blanco": "white satin bed sheets bedroom",
    "Juego de sábanas estampado geométrico - Gris": "patterned bed sheets grey",
    "Sábana ajustable lisa - Verde agua": "fitted bed sheet pastel",
    "Edredón plumón ligero 150 gr - Marfil": "ivory duvet fluffy bed",
    "Edredón tejido acanalado - Rosa palo": "pink knitted blanket bed",
    "Funda para edredón lino lavado - Beige": "beige linen duvet cover",
    "Cobija térmica doble cara - Gris perla": "grey blanket folded cozy",
    "Manta de fibra suave - Terracota": "soft throw blanket terracotta",
    "Cubrelecho matelaseado - Blanco": "white quilted bedspread bed",
    "Almohada suave sensación pluma - Blanco": "white soft pillow bed",
    "Pack de 2 protectores de almohada - Blanco": "white pillowcase stack",
    "Almohada cervical ergonómica - Gris": "ergonomic pillow grey",
    "Toalla de baño 450 g/m² - Azul cielo": "light blue bath towels stack",
    "Set de 3 toallas de cocina - Estampado": "kitchen towels patterned",
    "Toalla de manos premium - Rosa palo": "pink hand towels bathroom",
    "Bata de baño acolchada - Blanco": "white bathrobe spa",
    "Tapete de baño set x2 - Gris": "grey bath mat floor",
    "Organizador de baño colgante - Beige": "bathroom organizer shelf",
    "Cortina blackout pana - Gris topo": "dark grey blackout curtain window",
    "Cortina de voile con aros - Marfil": "ivory sheer curtain window",
    "Cortina estampada con forro - Azul noche": "navy blue curtain window",
    "Cojín terciopelo cuadrado 45x45 - Vino": "red velvet cushion pillow",
    "Mantel cuadrado lino - Blanco": "white linen tablecloth table",
    "Pack de 4 fundas de cojín - Multicolor": "boho pillows sofa colorful",
}

NEGADAS = ["woman", "women", "man", "men", "girl", "boy", "child", "baby",
           "people", "person", "model", "text", "logo", "lettering", "sign",
           "poster", "illustration", "cartoon", "drawing", "render"]
