"""Importar y exportar el catálogo en CSV (una fila por variante).

Diseñado para cargar catálogos de proveedores: el SKU identifica la variante,
si existe se actualiza y si no se crea (junto con su producto). Si alguna fila
tiene errores, NO se aplica nada: se devuelven los errores fila por fila.
"""
import csv
import io
import re
from decimal import Decimal, InvalidOperation

from django.db import transaction
from django.utils.text import slugify

from catalog.models import Categoria, Producto, Variante
from catalog.search import normalizar_texto

# Encabezados en el orden exacto del archivo (plantilla y exportación)
COLUMNAS = [
    "sku", "producto", "categoria", "estado", "talla", "medida", "color",
    "material", "precio", "precio_oferta", "costo", "stock",
    "umbral_stock_bajo", "activo",
]

ESTADOS = ("borrador", "publicado", "agotado")
TRUEZAS = ("si", "sí", "true", "1", "verdadero", "s")
FALSAS = ("no", "false", "0", "falso", "n")


class ErroresDeCSV(Exception):
    """El archivo tiene errores; el mensaje lista los detalles."""

    def __init__(self, errores):
        self.errores = errores
        super().__init__("; ".join(f"Fila {n}: {m}" for n, m in errores))


def _numero(texto, permitir_vacio=False, defecto=None):
    """Convierte '89.900' / '89900' / '$89.900' a entero COP (sin decimales)."""
    t = (texto or "").strip().replace("$", "").replace(" ", "").replace("\u00a0", "")
    if not t:
        if permitir_vacio:
            return defecto
        raise ValueError("es obligatorio")
    t = t.replace(",", ".")
    if re.fullmatch(r"\d{1,3}(\.\d{3})+", t):  # puntos de miles: 1.234.567
        t = t.replace(".", "")
    try:
        valor = Decimal(t)
    except InvalidOperation:
        raise ValueError(f"'{texto}' no es un número")
    # COP sin decimales: 89.9 → 90
    return int(valor.quantize(Decimal("1")))


def _entero(texto, permitir_vacio=False, defecto=None):
    t = (texto or "").strip()
    if not t:
        if permitir_vacio:
            return defecto
        raise ValueError("es obligatorio")
    if not re.fullmatch(r"-?\d+", t.replace(".", "").replace(" ", "")):
        raise ValueError(f"'{texto}' no es un número entero")
    return int(t.replace(".", "").replace(" ", ""))


def _booleano(texto, permitir_vacio=False, defecto=None):
    t = (texto or "").strip().lower()
    if not t:
        if permitir_vacio:
            return defecto
        raise ValueError("es obligatorio (sí/no)")
    if t in TRUEZAS:
        return True
    if t in FALSAS:
        return False
    raise ValueError(f"'{texto}' no es válido (usa sí o no)")


def _decodificar(contenido):
    """Acepta bytes (subida) o texto; UTF-8 con BOM o Latin-1 (Excel viejo)."""
    if isinstance(contenido, bytes):
        for codificacion in ("utf-8-sig", "latin-1"):
            try:
                return contenido.decode(codificacion)
            except UnicodeDecodeError:
                continue
        return contenido.decode("utf-8", errors="replace")
    return contenido


def _leer_filas(contenido):
    """Lee el CSV detectando separador (; de Excel en español o ,)."""
    texto = _decodificar(contenido).lstrip("\ufeff")
    primera = texto.splitlines()[0] if texto.splitlines() else ""
    separador = ";" if primera.count(";") >= primera.count(",") else ","
    lector = csv.DictReader(io.StringIO(texto), delimiter=separador)
    if not lector.fieldnames:
        raise ErroresDeCSV([(1, "el archivo está vacío")])
    # Normaliza encabezados: "Precio Oferta" == "precio_oferta"
    mapa = {normalizar_texto(h).replace(" ", "_"): h for h in lector.fieldnames}
    faltantes = [c for c in ("producto", "precio") if c not in mapa]
    if faltantes:
        raise ErroresDeCSV([
            (1, f"falta la columna '{c}' (usa la plantilla de ejemplo)")
            for c in faltantes
        ])
    filas = []
    for i, fila in enumerate(lector, start=2):  # la fila 1 es el encabezado
        datos = {}
        for clave, original in mapa.items():
            datos[clave] = (fila.get(original) or "").strip()
        filas.append((i, datos))
    if not filas:
        raise ErroresDeCSV([(1, "no hay filas de datos")])
    return filas


def _validar_fila(fila, datos, vistos):
    """Valida una fila y devuelve el dict limpio; lanza ValueError con el motivo."""
    producto = datos.get("producto", "").strip()
    if not producto:
        raise ValueError("falta 'producto'")

    sku = datos.get("sku", "").strip().upper()
    if sku:
        if sku in vistos:
            raise ValueError(f"el SKU {sku} ya apareció en la fila {vistos[sku]}")
        vistos[sku] = fila

    precio = _numero(datos.get("precio"))
    if precio < 0:
        raise ValueError("el precio no puede ser negativo")

    precio_oferta = _numero(datos.get("precio_oferta"), permitir_vacio=True)
    if precio_oferta is not None and precio_oferta < 0:
        raise ValueError("el precio de oferta no puede ser negativo")
    if precio_oferta is not None and precio_oferta >= precio:
        raise ValueError("el precio de oferta debe ser menor que el precio")

    costo = _numero(datos.get("costo"), permitir_vacio=True)
    if costo is not None and costo < 0:
        raise ValueError("el costo no puede ser negativo")

    stock = _entero(datos.get("stock"), permitir_vacio=True, defecto=None)
    if stock is not None and stock < 0:
        raise ValueError("el stock no puede ser negativo")

    umbral = _entero(
        datos.get("umbral_stock_bajo"), permitir_vacio=True, defecto=None
    )
    if umbral is not None and umbral < 0:
        raise ValueError("el umbral no puede ser negativo")

    activo = _booleano(datos.get("activo"), permitir_vacio=True, defecto=None)

    estado = (datos.get("estado") or "").strip().lower()
    if estado and estado not in ESTADOS:
        raise ValueError(f"estado '{estado}' no es válido (borrador/publicado/agotado)")

    talla = datos.get("talla", "").strip()
    if talla and talla not in dict(Variante.TALLA_CHOICES):
        raise ValueError(f"talla '{talla}' no está en la lista de tallas")

    return {
        "sku": sku,
        "producto": producto,
        "categoria": datos.get("categoria", "").strip(),
        "talla": talla,
        "medida": datos.get("medida", "").strip(),
        "color": datos.get("color", "").strip(),
        "material": datos.get("material", "").strip(),
        "precio": precio,
        "precio_oferta": precio_oferta,
        "costo": costo,
        "stock": stock,
        "umbral": umbral,
        "activo": activo,
        "estado": estado,
    }


def importar_csv(contenido):
    """
    Procesa el CSV completo. Si hay errores, NO se guarda nada.

    Devuelve {"errores": [(fila, motivo)], "creados": n, "actualizados": n}.
    """
    filas = _leer_filas(contenido)
    errores, vistos, limpias = [], {}, []
    for fila, datos in filas:
        try:
            limpias.append((fila, _validar_fila(fila, datos, vistos)))
        except ValueError as exc:
            errores.append((fila, str(exc)))
    if errores:
        return {"errores": errores, "creados": 0, "actualizados": 0}

    creados = actualizados = 0
    with transaction.atomic():
        for fila, datos in limpias:
            if _aplicar_fila(datos):
                creados += 1
            else:
                actualizados += 1
    return {"errores": [], "creados": creados, "actualizados": actualizados}


def _aplicar_fila(datos):
    """Crea o actualiza una variante según su SKU. True = se creó."""
    variante = None
    producto = None

    # 1) El SKU manda: si existe, esa variante y su producto son el destino
    if datos["sku"]:
        variante = Variante.objects.filter(sku=datos["sku"]).select_related(
            "producto"
        ).first()
        if variante:
            producto = variante.producto

    # 2) Sin SKU (o SKU nuevo): buscar el producto por nombre normalizado
    if producto is None:
        nombre_norm = normalizar_texto(datos["producto"])
        producto = next(
            (p for p in Producto.objects.all()
             if normalizar_texto(p.nombre) == nombre_norm),
            None,
        )
        if producto is None:
            producto = Producto.objects.create(
                nombre=datos["producto"],
                slug=slugify(datos["producto"])[:170] or "producto",
                estado=datos["estado"] or "borrador",
                material=datos["material"],
            )
        elif datos["estado"] and producto.estado != datos["estado"]:
            producto.estado = datos["estado"]
            producto.save(update_fields=["estado"])

        if datos["categoria"]:
            categoria, _ = Categoria.objects.get_or_create(
                nombre=datos["categoria"],
                defaults={"slug": slugify(datos["categoria"])[:180] or "categoria"},
            )
            producto.categorias.add(categoria)

    # 3) Variante: crear si no existe, actualizar si ya existía
    if variante is None:
        variante = Variante(
            producto=producto,
            sku=datos["sku"],  # vacío: save() genera uno solo
            talla=datos["talla"],
            medida_personalizada=datos["medida"],
            color=datos["color"],
            material=datos["material"],
            precio=datos["precio"],
            precio_oferta=datos["precio_oferta"],
            costo=datos["costo"],
            stock=0,  # el stock entra por la bitácora, más abajo
            umbral_stock_bajo=datos["umbral"] if datos["umbral"] is not None else 3,
            activa=datos["activo"] if datos["activo"] is not None else True,
        )
        variante.save()
        nuevo = True
    else:
        if datos["talla"]:
            variante.talla = datos["talla"]
        if datos["medida"]:
            variante.medida_personalizada = datos["medida"]
        if datos["color"]:
            variante.color = datos["color"]
        if datos["material"]:
            variante.material = datos["material"]
        variante.precio = datos["precio"]
        variante.precio_oferta = datos["precio_oferta"]
        if datos["costo"] is not None:
            variante.costo = datos["costo"]
        if datos["umbral"] is not None:
            variante.umbral_stock_bajo = datos["umbral"]
        if datos["activo"] is not None:
            variante.activa = datos["activo"]
        variante.save()
        nuevo = False

    # 4) El stock pasa por la bitácora (motivo "ajuste", referencia CSV)
    if datos["stock"] is not None:
        from inventory.servicios import anotar_ajuste, registrar_movimiento

        if nuevo:
            if datos["stock"]:
                registrar_movimiento(
                    variante, datos["stock"], "ajuste",
                    nota="Importación CSV",
                )
        elif datos["stock"] != variante.stock:
            diferencia = datos["stock"] - variante.stock
            variante.stock = datos["stock"]
            variante.save(update_fields=["stock"])
            anotar_ajuste(variante, diferencia, nota="Importación CSV")
    return nuevo


def exportar_csv():
    """CSV con todas las variantes (una fila por SKU), listo para Excel."""
    buffer = io.StringIO()
    escritor = csv.writer(buffer, delimiter=";", lineterminator="\r\n")
    escritor.writerow(COLUMNAS)
    variantes = Variante.objects.select_related("producto").order_by(
        "producto__nombre", "talla", "color"
    )
    for v in variantes:
        escritor.writerow([
            v.sku,
            v.producto.nombre,
            ", ".join(v.producto.categorias.values_list("nombre", flat=True)),
            v.producto.estado,
            v.talla,
            v.medida_personalizada,
            v.color,
            v.material,
            v.precio,
            v.precio_oferta if v.precio_oferta is not None else "",
            v.costo if v.costo is not None else "",
            v.stock,
            v.umbral_stock_bajo,
            "sí" if v.activa else "no",
        ])
    # utf-8-sig: para que Excel abra bien los tildes
    return "﻿" + buffer.getvalue()


def plantilla_csv():
    """Plantilla de ejemplo con encabezados y una fila de muestra."""
    buffer = io.StringIO()
    escritor = csv.writer(buffer, delimiter=";", lineterminator="\r\n")
    escritor.writerow(COLUMNAS)
    escritor.writerow([
        "SAB-D-001", "Sábanas dobles algodón", "Dormitorio", "publicado",
        "Doble", "", "", "Algodón 180 hilos", "89900", "", "55000", "10", "3",
        "sí",
    ])
    escritor.writerow([
        "", "Toalla de baño blanca", "Baños", "publicado", "Baño", "", "Blanco",
        "Algodón", "39900", "34900", "22000", "24", "6", "sí",
    ])
    return "﻿" + buffer.getvalue()
