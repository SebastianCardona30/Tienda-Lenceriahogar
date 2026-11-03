"""Reportes del negocio exportables a CSV (una consulta por tipo).

Cada reporte devuelve (encabezados, filas) y la vista lo convierte en un
archivo CSV con punto y coma (se abre directo en Excel en español).
"""
from datetime import date, datetime, timedelta
from decimal import Decimal

from django.db.models import Count, Sum
from django.utils import timezone

from catalog.models import Variante
from orders.models import ItemPedido, Pedido
from promotions.models import UsoCupon

# Estados que cuentan como venta hecha (mismo criterio que el dashboard)
ESTADOS_VENTA = ("pagado", "preparacion", "enviado", "entregado")


def _parsear_fecha(texto, defecto):
    """'2026-11-03' → date; si está vacía o mal, devuelve el defecto."""
    if not texto:
        return defecto
    try:
        return datetime.strptime(str(texto)[:10], "%Y-%m-%d").date()
    except ValueError:
        return defecto


def _rango(desde_texto, hasta_texto):
    """Devuelve (desde_inclusivo, hasta_exclusivo) como datetimes."""
    hoy = timezone.localtime().date()
    desde = _parsear_fecha(desde_texto, hoy - timedelta(days=29))
    hasta = _parsear_fecha(hasta_texto, hoy)
    # desde las 00:00 del día desde; hasta 00:00 del día DESPUÉS del hasta
    desde_dt = timezone.make_aware(datetime.combine(desde, datetime.min.time()))
    hasta_dt = timezone.make_aware(
        datetime.combine(hasta + timedelta(days=1), datetime.min.time())
    )
    return desde_dt, hasta_dt


def _ventas_en(desde_dt, hasta_dt):
    return Pedido.objects.filter(
        estado__in=ESTADOS_VENTA, creado__gte=desde_dt, creado__lt=hasta_dt,
    )


def _numero(texto):
    """Formatea un entero como número simple (el Excel ya pone los puntos)."""
    if texto is None:
        return ""
    if isinstance(texto, Decimal):
        texto = int(texto)
    return texto


def ventas_por_periodo(desde=None, hasta=None):
    """Detalle de cada venta en el período (para conciliar cobros)."""
    desde_dt, hasta_dt = _rango(desde, hasta)
    pedidos = _ventas_en(desde_dt, hasta_dt).select_related("municipio").order_by(
        "creado"
    )
    encabezados = [
        "numero", "fecha", "cliente", "telefono", "municipio", "metodo_pago",
        "estado", "subtotal", "descuento_ofertas", "descuento_cupon",
        "costo_envio", "total",
    ]
    filas = [
        [
            p.numero,
            timezone.localtime(p.creado).strftime("%d/%m/%Y %H:%M"),
            p.nombre, p.telefono,
            p.municipio.nombre if p.municipio else "",
            p.metodo_pago, p.get_estado_display(),
            _numero(p.subtotal), _numero(p.descuento_ofertas),
            _numero(p.descuento_cupon), _numero(p.costo_envio),
            _numero(p.total),
        ]
        for p in pedidos
    ]
    return encabezados, filas


def ventas_por_producto(desde=None, hasta=None):
    """Unidades y monto por producto vendido en el período."""
    from django.db.models import F

    desde_dt, hasta_dt = _rango(desde, hasta)
    items = (
        ItemPedido.objects.filter(
            pedido__estado__in=ESTADOS_VENTA,
            pedido__creado__gte=desde_dt, pedido__creado__lt=hasta_dt,
        )
        .values("producto_nombre")
        .annotate(
            unidades=Sum("cantidad"),
            # subtotal = precio × cantidad − descuento (misma regla del modelo)
            monto=Sum(F("precio_unitario") * F("cantidad") - F("descuento")),
            pedidos=Count("pedido", distinct=True),
        )
        .order_by("-unidades")
    )
    filas = [
        [f["producto_nombre"], f["unidades"], f["pedidos"], _numero(f["monto"])]
        for f in items
    ]
    return ["producto", "unidades", "pedidos", "monto"], filas


def ventas_por_categoria(desde=None, hasta=None):
    """Ventas agrupadas por la categoría principal de cada producto.

    Un producto con varias categorías cuenta en la primera (por orden);
    así los totales siempre cuadran con el total de ventas.
    """
    desde_dt, hasta_dt = _rango(desde, hasta)
    items = ItemPedido.objects.filter(
        pedido__estado__in=ESTADOS_VENTA,
        pedido__creado__gte=desde_dt, pedido__creado__lt=hasta_dt,
    ).select_related("variante__producto").prefetch_related(
        "variante__producto__categorias"
    )

    acumulados = {}
    for item in items:
        categoria = "Sin categoría"
        if item.variante and item.variante.producto:
            cats = list(item.variante.producto.categorias.all())
            if cats:
                categoria = cats[0].nombre
        clave = categoria
        datos = acumulados.setdefault(
            clave, {"unidades": 0, "pedidos": set(), "monto": Decimal(0)}
        )
        datos["unidades"] += item.cantidad
        datos["pedidos"].add(item.pedido_id)
        datos["monto"] += item.precio_unitario * item.cantidad - item.descuento

    filas = sorted(
        (
            [nombre, d["unidades"], len(d["pedidos"]), _numero(d["monto"])]
            for nombre, d in acumulados.items()
        ),
        key=lambda f: -f[1],
    )
    return ["categoria", "unidades", "pedidos", "monto"], filas


def ventas_por_proveedor(desde=None, hasta=None):
    """Lo vendido por proveedor (para saber a quién reponer)."""
    desde_dt, hasta_dt = _rango(desde, hasta)
    items = ItemPedido.objects.filter(
        pedido__estado__in=ESTADOS_VENTA,
        pedido__creado__gte=desde_dt, pedido__creado__lt=hasta_dt,
    ).select_related("variante__producto").prefetch_related(
        "variante__producto__categorias"
    )

    acumulados = {}
    for item in items:
        proveedor = "Sin proveedor"
        if item.variante and item.variante.producto and item.variante.producto.proveedor:
            proveedor = item.variante.producto.proveedor.nombre
        datos = acumulados.setdefault(
            proveedor, {"unidades": 0, "pedidos": set(), "monto": Decimal(0)}
        )
        datos["unidades"] += item.cantidad
        datos["pedidos"].add(item.pedido_id)
        datos["monto"] += item.precio_unitario * item.cantidad - item.descuento

    filas = sorted(
        (
            [nombre, d["unidades"], len(d["pedidos"]), _numero(d["monto"])]
            for nombre, d in acumulados.items()
        ),
        key=lambda f: -f[1],
    )
    return ["proveedor", "unidades", "pedidos", "monto"], filas


def ventas_por_municipio(desde=None, hasta=None):
    """Pedidos y montos por municipio de entrega (planear rutas)."""
    desde_dt, hasta_dt = _rango(desde, hasta)
    filas = []
    grupos = (
        _ventas_en(desde_dt, hasta_dt)
        .values("municipio__nombre")
        .annotate(pedidos=Count("id"), monto=Sum("total"))
        .order_by("-monto")
    )
    for g in grupos:
        filas.append([
            g["municipio__nombre"] or "Sin municipio",
            g["pedidos"], _numero(g["monto"]),
        ])
    return ["municipio", "pedidos", "monto"], filas


def cupones_usados(desde=None, hasta=None):
    """Uso de cupones en el período, con el descuento que costó."""
    desde_dt, hasta_dt = _rango(desde, hasta)
    grupos = (
        UsoCupon.objects.filter(creado__gte=desde_dt, creado__lt=hasta_dt)
        .values("cupon__codigo")
        .annotate(usos=Count("id"))
        .order_by("-usos")
    )
    descuentos = {
        f["cupon_codigo"]: f["total"]
        for f in Pedido.objects.filter(
            creado__gte=desde_dt, creado__lt=hasta_dt,
            descuento_cupon__gt=0,
        )
        .values("cupon_codigo")
        .annotate(total=Sum("descuento_cupon"))
    }
    filas = [
        [g["cupon__codigo"], g["usos"], _numero(descuentos.get(g["cupon__codigo"], 0))]
        for g in grupos
    ]
    return ["cupon", "usos", "descuento_otorgado"], filas


def inventario_valorizado():
    """Stock de cada variante con su costo y valor (no depende de fechas)."""
    variantes = Variante.objects.select_related("producto").order_by(
        "producto__nombre", "talla", "color"
    )
    encabezados = [
        "sku", "producto", "talla", "color", "stock", "umbral_stock_bajo",
        "costo_unitario", "valor_a_costo", "precio_venta", "valor_a_venta",
        "activa",
    ]
    filas = []
    for v in variantes:
        costo = v.costo * v.stock if v.costo is not None else None
        filas.append([
            v.sku, v.producto.nombre, v.talla, v.color, v.stock,
            v.umbral_stock_bajo,
            _numero(v.costo) if v.costo is not None else "",
            _numero(costo) if costo is not None else "",
            _numero(v.precio_final), _numero(v.precio_final * v.stock),
            "sí" if v.activa else "no",
        ])
    return encabezados, filas


# Catálogo de reportes: clave → (título, función, usa_fechas)
TIPOS = {
    "ventas_periodo": ("Ventas por período", ventas_por_periodo, True),
    "ventas_producto": ("Ventas por producto", ventas_por_producto, True),
    "ventas_categoria": ("Ventas por categoría", ventas_por_categoria, True),
    "ventas_proveedor": ("Ventas por proveedor", ventas_por_proveedor, True),
    "ventas_municipio": ("Ventas por municipio", ventas_por_municipio, True),
    "cupones": ("Cupones usados", cupones_usados, True),
    "inventario": ("Inventario valorizado", inventario_valorizado, False),
}


def generar_reporte(tipo, desde=None, hasta=None):
    """Devuelve (titulo, encabezados, filas); lanza KeyError si el tipo no existe."""
    titulo, funcion, usa_fechas = TIPOS[tipo]
    if usa_fechas:
        encabezados, filas = funcion(desde, hasta)
    else:
        encabezados, filas = funcion()
    return titulo, encabezados, filas


def a_csv(encabezados, filas):
    """Convierte encabezados y filas a texto CSV con ; (Excel es-CO)."""
    import csv
    import io

    buffer = io.StringIO()
    escritor = csv.writer(buffer, delimiter=";", lineterminator="\r\n")
    escritor.writerow(encabezados)
    escritor.writerows(filas)
    # utf-8-sig: Excel abre los tildes sin problema
    return "﻿" + buffer.getvalue()


def nombre_archivo(tipo, desde=None, hasta=None):
    """Nombre del archivo descargado: reporte_ventas_periodo_2026-11-03.csv."""
    partes = [tipo]
    if desde:
        partes.append(str(desde)[:10])
    if hasta:
        partes.append(str(hasta)[:10])
    return "_".join(partes) + ".csv"


def periodo_texto(desde=None, hasta=None):
    """Texto legible del período para el título del reporte."""
    d = _parsear_fecha(desde, timezone.localtime().date() - timedelta(days=29))
    h = _parsear_fecha(hasta, timezone.localtime().date())
    return f"del {d.strftime('%d/%m/%Y')} al {h.strftime('%d/%m/%Y')}"
