"""
Comando: python manage.py seed_demo

Carga datos de demostración realistas (sin fotos con derechos de autor):
8 categorías con subcategorías, proveedores, 40 productos con variantes,
reseñas, combos, sinónimos de búsqueda, cupones y fecha de ofertas.

Se puede ejecutar varias veces: no duplica datos (usa get_or_create).
"""
from datetime import timedelta
from decimal import Decimal
from pathlib import Path

from django.core.management.base import BaseCommand
from django.utils import timezone

from catalog.models import (
    Categoria, Combo, ComboItem, Producto, Proveedor, Resena, Sinonimo, Variante,
)
from core.models import SiteConfig
from promotions.models import Cupon

# Colores de la paleta para los marcadores de posición
COLORES = ["#5B2A86", "#8A4FBF", "#C2185B", "#FBD5E5", "#2E9E6B", "#F2A516"]

CATEGORIAS = {
    "Sábanas y juegos de cama": [
        "Sencillas", "Semidobles", "Dobles", "Queen", "King",
    ],
    "Edredones": ["Edredones con relleno", "Funda para edredón"],
    "Cobijas y cubrelechos": ["Cobijas acolchadas", "Cubrelechos"],
    "Almohadas y protectores": ["Almohadas", "Protectores de colchón"],
    "Toallas": ["Toalla cara", "Toalla de mano", "Toalla de baño", "Toalla de playa"],
    "Artículos de baño": ["Cortinas de baño", "Tapetes", "Accesorios"],
    "Cortinas": ["Cortinas estándar", "Cortinas a la medida"],
    "Cojines, decoración y mantelería": ["Cojines", "Mantelería", "Decoración"],
}

# (nombre, categoría, material, precio COP, variantes de ejemplo)
PRODUCTOS = [
    ("Juego de sábanas para cama sencilla - Azul cielo", "Sábanas y juegos de cama", "Microfibra", 139900,
     [("Sencilla", "Azul cielo"), ("Semidoble", "Azul cielo")]),
    ("Toalla de playa microfibra compacta - Multicolor", "Toallas", "Microfibra", 65900,
     [("Playa", "Multicolor"), ("Playa", "Rosa")]),
    ("Cojín lumbar rectangular 20x40 - Mostaza", "Cojines, decoración y mantelería", "Algodón", 39900,
     [("Otra medida", "20 x 40 cm")]),
    # Sábanas y juegos de cama
    ("Juego de sábanas 400 hilos - Blanco nacar", "Sábanas y juegos de cama", "Microfibra", 189900,
     [("Queen", "Blanco nacar"), ("Doble", "Blanco nacar"), ("King", "Blanco nacar")]),
    ("Juego de sábanas algodón peinado - Gris perla", "Sábanas y juegos de cama", "Algodón", 259900,
     [("Semidoble", "Gris perla"), ("Queen", "Gris perla")]),
    ("Sábana ajustable con cierre - Rosa palo", "Sábanas y juegos de cama", "Microfibra", 89900,
     [("Sencilla", "Rosa palo"), ("Semidoble", "Rosa palo"), ("Doble", "Rosa palo")]),
    ("Juego de sábanas 300 hilos estampado floral", "Sábanas y juegos de cama", "Algodón", 219900,
     [("Queen", "Floral"), ("Doble", "Floral")]),
    ("Sábana sencilla lisas - 6 colores", "Sábanas y juegos de cama", "Microfibra", 59900,
     [("Sencilla", "Lavanda"), ("Sencilla", "Blanco"), ("Sencilla", "Vino")]),
    # Edredones
    ("Edredón doble plumón 200 gr - Blanco", "Edredones", "Plumón", 349900,
     [("Doble", "Blanco"), ("Queen", "Blanco")]),
    ("Edredón semidoble sintético acolchado", "Edredones", "Poliéster", 179900,
     [("Semidoble", "Crema"), ("Semidoble", "Gris topo")]),
    ("Funda para edredón 400 hilos - Estampado lunares", "Edredones", "Algodón", 159900,
     [("Doble", "Lunares rosas"), ("Queen", "Lunares rosas")]),
    ("Edredón infantil plano - Motivos de flores", "Edredones", "Poliéster", 119900,
     [("Doble", "Flores"), ("Semidoble", "Flores")]),
    # Cobijas y cubrelechos
    ("Cobija acolchada doble - Beige", "Cobijas y cubrelechos", "Poliéster", 139900,
     [("Doble", "Beige"), ("Queen", "Beige")]),
    ("Cubrelechos semidoble jacquard", "Cobijas y cubrelechos", "Poliéster", 129900,
     [("Semidoble", "Azul rey"), ("Doble", "Azul rey")]),
    ("Cobija pesada tipo manta - Gris", "Cobijas y cubrelechos", "Poliéster", 99900,
     [("Doble", "Gris"), ("Semidoble", "Gris")]),
    ("Cubrelechos King bordado en esquinas", "Cobijas y cubrelechos", "Microfibra", 189900,
     [("King", "Blanco"), ("King", "Vino")]),
    # Almohadas y protectores
    ("Almohada rectangular 50x65 - Fibra siliconada", "Almohadas y protectores", "Fibra siliconada", 59900,
     [("Otra medida", "50 x 65 cm")]),
    ("Almohada ortopédica viscoelástica", "Almohadas y protectores", "Viscoelástico", 129900,
     [("Otra medida", "60 x 40 cm")]),
    ("Protector de colchón impermeable Queen", "Almohadas y protectores", "Poliéster", 119900,
     [("Queen", "Blanco"), ("Doble", "Blanco")]),
    ("Pack de 2 almohadas con funda bordada", "Almohadas y protectores", "Fibra siliconada", 139900,
     [("Otra medida", "50 x 65 cm")]),
    # Toallas
    ("Toalla de baño 500 g/m² - Blanco", "Toallas", "Algodón", 59900,
     [("Baño", "Blanco"), ("Baño", "Rosa"), ("Baño", "Gris")]),
    ("Toalla cara y mano set x2 - Verde agua", "Toallas", "Algodón", 45900,
     [("Cara", "Verde agua"), ("Mano", "Verde agua")]),
    ("Toalla de playa gigante 90x180", "Toallas", "Algodón", 79900,
     [("Playa", "Franja turquesa"), ("Playa", "Franja coral")]),
    ("Toalla de baño 600 g/m² premium", "Toallas", "Algodón peinado", 79900,
     [("Baño", "Marfil"), ("Baño", "Ceniza")]),
    ("Set de 4 toallas de baño - Línea hotel", "Toallas", "Algodón peinado", 199900,
     [("Baño", "Blanco"), ("Baño", "Gris perla")]),
    # Artículos de baño
    ("Cortina de baño PEVA con imanes", "Artículos de baño", "PEVA", 69900,
     [("Otra medida", "180 x 180 cm")]),
    ("Tapete de baño antideslizante - Blanco", "Artículos de baño", "Microfibra", 39900,
     [("Otra medida", "50 x 80 cm"), ("Otra medida", "70 x 120 cm")]),
    ("Set de 3 accesorios de baño con soporte", "Artículos de baño", "Plástico", 89900,
     [("Otra medida", "Set completo")]),
    ("Cortina de baño textil con diseño de piedras", "Artículos de baño", "Poliéster", 89900,
     [("Otra medida", "180 x 200 cm")]),
    ("Tapete masajeador de goma - Gris", "Artículos de baño", "Goma", 45900,
     [("Otra medida", "60 x 90 cm")]),
    # Cortinas
    ("Cortina blackout 140x250 - Vino", "Cortinas", "Poliéster", 119900,
     [("Otra medida", "140 x 250 cm"), ("Otra medida", "140 x 290 cm")]),
    ("Cortina con vuelo y ojales - Crema", "Cortinas", "Poliéster", 139900,
     [("Otra medida", "140 x 250 cm")]),
    ("Cortina voile con paneles - Blanco", "Cortinas", "Voile", 99900,
     [("Otra medida", "140 x 250 cm")]),
    ("Cortina triple capa blackout estampada", "Cortinas", "Poliéster", 179900,
     [("Otra medida", "140 x 290 cm")]),
    # Cojines, decoración y mantelería
    ("Cojín decorativo cuadrado 45x45 - Terracota", "Cojines, decoración y mantelería", "Algodón", 45900,
     [("Otra medida", "45 x 45 cm")]),
    ("Pack de 2 cojines redondos - Rosa antiguo", "Cojines, decoración y mantelería", "Terciopelo sintético", 89900,
     [("Otra medida", "Ø 45 cm")]),
    ("Mantel rectangular 6 plazas - Lino natural", "Cojines, decoración y mantelería", "Lino", 119900,
     [("Otra medida", "140 x 220 cm")]),
    ("Servilletas de tela x4 - Crema bordadas", "Cojines, decoración y mantelería", "Algodón", 59900,
     [("Otra medida", "40 x 40 cm")]),
    ("Cojín de sofá rectangular 30x50 - Índigo", "Cojines, decoración y mantelería", "Algodón", 55900,
     [("Otra medida", "30 x 50 cm")]),
    ("Camino de mesa estampado - Flores", "Cojines, decoración y mantelería", "Algodón", 69900,
     [("Otra medida", "40 x 150 cm")]),
]

PROVEEDORES = [
    ("Textiles del Oriente S.A.S.", "María Fernanda Rojas", "607690012345", 7),
    ("Hogar y Confort Ltda.", "Carlos Pérez", "6076312345", 10),
    ("Importadora Santander", "Ana Lucía Gómez", "6076709876", 15),
    ("Fábrica de Toallas Bucaramanga", "Jorge Medina", "6076456789", 5),
]

RESENAS = [
    ("Marcela", 5, "Llegó súper rápido y las sábanas están hermosas, muy suaves. Recomendadas."),
    ("Luz Adriana", 5, "El edredón es calientico y el color igual a la foto. Feliz con la compra."),
    ("Sandra", 4, "Muy buen precio. La toalla un poco más delgada de lo que esperaba, pero buena."),
    ("Yina", 5, "Compré por WhatsApp y me atendieron de maravilla. Todo llegó bien empacado."),
    ("Claudia", 5, "Las cortinas cubren perfecto y me ayudaron a medir. Excelente servicio."),
    ("Patricia", 4, "Buena calidad en las almohadas. Volvería a comprar."),
    ("Diana", 5, "El bordado quedó precioso, lo pedí para un regalo y encantaron."),
    ("Mónica", 5, "Precios accesibles y el tapete es antideslizante de verdad."),
]

SINONIMOS = [
    "sábana, sabana, sabanas, sabanera",
    "cobija, frazada, manta, cobertor",
    "edredón, edredon, cubrelecho, plumon, plumón",
    "cortina de baño, cortina ducha, cortina peina",
    "toalla, toallas, toallón",
    "almohada, almohadas, cabecera",
    "mantel, mantelería, camilla",
    "cojin, cojín, almohadón",
]

CUPONES = [
    ("BIENVENIDA10", "porcentaje", Decimal("10"), 80000),
    ("CIUDADBONITA", "valor", Decimal("15000"), 120000),
    ("ENVIOGRATIS", "valor", Decimal("12000"), 60000),
]

CATEGORIA_MARCADOR = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 600 400">
  <rect width="600" height="400" fill="{color}"/>
  <g opacity="0.25" fill="#FFFFFF">
    <ellipse cx="300" cy="200" rx="180" ry="110"/>
    <rect x="170" y="200" width="260" height="110" rx="30" fill="#00000022"/>
  </g>
  <text x="300" y="215" text-anchor="middle" font-family="Georgia, serif" font-size="30" font-weight="700" fill="#FFFFFF">{nombre}</text>
</svg>"""


class Command(BaseCommand):
    help = "Carga datos de demostración: categorías, productos, variantes, reseñas, combos y cupones."

    def handle(self, *args, **options):
        base_media = Path("media")

        # ---------- Proveedores ----------
        proveedores = {}
        for nombre, contacto, tel, dias in PROVEEDORES:
            prov, _ = Proveedor.objects.get_or_create(
                nombre=nombre,
                defaults={"contacto": contacto, "telefono": tel, "tiempo_reposicion_dias": dias},
            )
            proveedores[nombre] = prov
        self.stdout.write(f"· {len(proveedores)} proveedores")

        # ---------- Categorías (con imagen marcador) ----------
        categorias = {}
        for orden, (nombre, hijas) in enumerate(CATEGORIAS.items(), start=1):
            color = COLORES[orden % len(COLORES)]
            cat, creada = Categoria.objects.get_or_create(
                nombre=nombre,
                defaults={"orden": orden, "activa": True},
            )
            if creada and not cat.imagen:
                ruta = base_media / "categorias" / f"{cat.slug}.svg"
                ruta.parent.mkdir(parents=True, exist_ok=True)
                ruta.write_text(
                    CATEGORIA_MARCADOR.format(color=color, nombre=nombre), encoding="utf-8"
                )
                cat.imagen.name = f"categorias/{cat.slug}.svg"
                cat.save()
            categorias[nombre] = cat
            for i, sub in enumerate(hijas, start=1):
                Categoria.objects.get_or_create(
                    nombre=sub, defaults={"padre": cat, "orden": i, "activa": True}
                )
        self.stdout.write(f"· {len(categorias)} categorías con subcategorías")

        # ---------- Productos y variantes ----------
        creados = 0
        for idx, (nombre, categoria, material, precio, variantes) in enumerate(PRODUCTOS):
            prod, creada = Producto.objects.get_or_create(
                nombre=nombre,
                defaults={
                    "descripcion_corta": f"{material} de buena calidad. Precio accesible en Bucaramanga.",
                    "descripcion_larga": (
                        f"{nombre}. Elaborado en {material.lower()}, con acabados resistentes "
                        "y colores que no se destiñen con el lavado. Ideal para renovar tu cama "
                        "o tu baño con estilo y a buen precio.\n\n"
                        "• Tallas y medidas según selección.\n"
                        "• Envío en todo Santander.\n"
                        "• Cambios dentro de 5 días hábiles (excepto personalizados)."
                    ),
                    "marca": "Ciudad Bonita",
                    "proveedor": proveedores[PROVEEDORES[idx % len(PROVEEDORES)][0]],
                    "material": material,
                    "composicion": material,
                    "cuidado": "Lavar con agua fría, no usar blanqueante y secar a baja temperatura.",
                    "estado": "publicado",
                    "destacado": idx % 7 == 0,
                    "es_bordado": categoria in ("Sábanas y juegos de cama", "Toallas", "Almohadas y protectores"),
                },
            )
            prod.categorias.add(categorias[categoria])
            # Refresca el texto de búsqueda con la categoría recién agregada
            prod.save()
            if creada:
                creados += 1
                # Fotos marcador de posición (dos fotos por producto)
                from catalog.models import FotoProducto

                for n_foto in (1, 2):
                    if prod.fotos.count() >= n_foto:
                        continue
                    color = COLORES[(idx + n_foto) % len(COLORES)]
                    ruta = base_media / "productos" / f"{prod.slug}-{n_foto}.svg"
                    ruta.parent.mkdir(parents=True, exist_ok=True)
                    ruta.write_text(
                        CATEGORIA_MARCADOR.format(color=color, nombre=nombre[:40]),
                        encoding="utf-8",
                    )
                    foto = FotoProducto(producto=prod, orden=n_foto,
                                        alt=f"{nombre} - foto {n_foto}")
                    foto.imagen.name = f"productos/{prod.slug}-{n_foto}.svg"
                    foto.save()

            # Variantes
            for talla, color in variantes:
                variante, _v = Variante.objects.get_or_create(
                    producto=prod,
                    talla=talla if talla != "Otra medida" else "Otra medida",
                    medida_personalizada="" if talla != "Otra medida" else color,
                    color="" if talla == "Otra medida" else color,
                    defaults={
                        "precio": Decimal(precio),
                        "costo": Decimal(int(precio * 0.6)),
                        "stock": 8 + (idx % 12),
                        "material": material,
                        "peso_gramos": 900,
                    },
                )
                # Algunas variantes en oferta (para la sección de ofertas)
                if not _v and variante.precio_oferta is None and idx % 4 == 0:
                    variante.precio_oferta = Decimal(int(precio * 0.8))
                    variante.save()
                if _v and idx % 4 == 0:
                    variante.precio_oferta = Decimal(int(precio * 0.8))
                    variante.save()
        self.stdout.write(f"· {creados} productos nuevos con sus variantes")

        # ---------- Reseñas aprobadas ----------
        productos_list = list(Producto.objects.filter(estado="publicado"))
        for i, (nombre, estrellas, texto) in enumerate(RESENAS):
            prod = productos_list[i % len(productos_list)]
            Resena.objects.get_or_create(
                producto=prod, nombre=nombre, comentario=texto,
                defaults={"calificacion": estrellas, "aprobada": True, "verificada": True},
            )
        self.stdout.write(f"· {len(RESENAS)} reseñas")

        # ---------- Combos ----------
        combo_defs = [
            ("Set para renovar tu cama Queen", 449900,
             ["Juego de sábanas 400 hilos - Blanco nacar", "Almohada rectangular 50x65 - Fibra siliconada",
              "Protector de colchón impermeable Queen"]),
            ("Pack baño completo", 169900,
             ["Toalla de baño 500 g/m² - Blanco", "Toalla cara y mano set x2 - Verde agua",
              "Tapete de baño antideslizante - Blanco"]),
            ("Kit entrada en calor", 259900,
             ["Edredón semidoble sintético acolchado", "Cobija pesada tipo manta - Gris"]),
        ]
        for nombre, precio, items in combo_defs:
            combo, creado = Combo.objects.get_or_create(
                nombre=nombre,
                defaults={"precio_combo": Decimal(precio), "activo": True,
                          "descripcion": "Set armado con productos de la tienda, a mejor precio."},
            )
            if creado:
                for nombre_prod in items:
                    p = Producto.objects.filter(nombre=nombre_prod).first()
                    if p:
                        ComboItem.objects.create(combo=combo, producto=p, cantidad=1)
        self.stdout.write(f"· {len(combo_defs)} combos")

        # ---------- Sinónimos de búsqueda ----------
        for s in SINONIMOS:
            Sinonimo.objects.get_or_create(palabras=s)
        self.stdout.write(f"· {len(SINONIMOS)} sinónimos de búsqueda")

        # ---------- Cupones ----------
        for codigo, tipo, valor, minimo in CUPONES:
            Cupon.objects.get_or_create(
                codigo=codigo,
                defaults={"tipo": tipo, "valor": valor, "monto_minimo": Decimal(minimo)},
            )
        self.stdout.write(f"· {len(CUPONES)} cupones")

        # ---------- Configuración: ofertas de la semana (próximo domingo) ----------
        config = SiteConfig.get()
        if config.ofertas_hasta is None:
            hoy = timezone.localdate()
            dias_al_domingo = (6 - hoy.weekday()) % 7 or 7
            config.ofertas_hasta = timezone.make_aware(
                timezone.datetime.combine(hoy + timedelta(days=dias_al_domingo),
                                          timezone.datetime.min.time())
            ).replace(hour=23, minute=59)
            config.save()

        self.stdout.write(self.style.SUCCESS(
            "\nListo: datos de demostración cargados. Abre la tienda y el panel de administración."
        ))
