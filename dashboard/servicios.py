"""Métricas del panel de administración (dashboard de la dueña).

Todo se calcula con consultas simples sobre los modelos existentes; sin
librerías externas ni servicios pagados. Las gráficas usan Chart.js local
(static/vendor/chart.umd.min.js).
"""
from datetime import timedelta
from decimal import Decimal

from django.db.models import Count, Sum
from django.utils import timezone

from catalog.models import BusquedaSinResultados, Variante
from orders.models import ItemPedido, Pedido
from promotions.models import UsoCupon

# Estados que cuentan como venta hecha (no cancelados ni devueltos)
ESTADOS_VENTA = ("pagado", "preparacion", "enviado", "entregado")


def _inicio_del_dia():
    ahora = timezone.localtime()
    return ahora.replace(hour=0, minute=0, second=0, microsecond=0)


def ventas_por_periodo():
    """Ventas (suma de totales) de hoy, la semana y el mes en curso."""
    hoy = _inicio_del_dia()
    semana = hoy - timedelta(days=6)  # hoy + 6 días atrás
    mes = hoy.replace(day=1)

    base = Pedido.objects.filter(estado__in=ESTADOS_VENTA)

    def suma(desde):
        return base.filter(creado__gte=desde).aggregate(t=Sum("total"))["t"] or Decimal(0)

    def conteo(desde):
        return base.filter(creado__gte=desde).count()

    return {
        "hoy": {"monto": suma(hoy), "pedidos": conteo(hoy)},
        "semana": {"monto": suma(semana), "pedidos": conteo(semana)},
        "mes": {"monto": suma(mes), "pedidos": conteo(mes)},
    }


def pedidos_por_estado():
    """Conteo de pedidos por estado, en el orden en que los muestra el panel."""
    conteos = dict(
        Pedido.objects.values_list("estado").annotate(n=Count("id"))
    )
    return [
        {"estado": estado, "nombre": nombre, "cantidad": conteos.get(estado, 0)}
        for estado, nombre in Pedido.ESTADOS
    ]


def requieren_accion():
    """Pedidos que la dueña debe atender hoy."""
    def contar(**filtros):
        return Pedido.objects.filter(**filtros).count()

    return {
        "por_verificar": contar(estado="por_verificar"),
        "pendiente_pago": contar(estado="pendiente"),
        "por_enviar": contar(estado__in=("pagado", "preparacion")),
        "stock_bajo": _variantes_bajas().count(),
    }


def _variantes_bajas():
    """Variantes con stock en o por debajo de su umbral (y con producto publicado)."""
    from django.db.models import F

    return (
        Variante.objects.filter(producto__estado="publicado")
        .filter(stock__lte=F("umbral_stock_bajo"))
    )


def stock_bajo(limite=8):
    """Lista corta de variantes con poco stock para la tarjeta del panel."""
    return list(
        _variantes_bajas()
        .select_related("producto")
        .order_by("stock")[:limite]
    )


def mas_vendidos(limite=5):
    """Productos más vendidos (por unidades) entre las ventas hechas."""
    from django.db.models import F

    filas = (
        ItemPedido.objects.filter(pedido__estado__in=ESTADOS_VENTA)
        .values("producto_nombre")
        .annotate(
            unidades=Sum("cantidad"),
            # subtotal = precio_unitario × cantidad − descuento (misma regla del modelo)
            monto=Sum(F("precio_unitario") * F("cantidad") - F("descuento")),
        )
        .order_by("-unidades")[:limite]
    )
    return list(filas)


def ingresos_y_margen():
    """Ingresos, costos y margen estimado del mes en curso.

    El costo usa Variante.costo (privado, editable en el admin). Si un producto
    nunca tuvo costo cargado, se cuenta como 0 y el margen queda marcado como
    estimado.
    """
    mes = _inicio_del_dia().replace(day=1)
    ventas = Pedido.objects.filter(estado__in=ESTADOS_VENTA, creado__gte=mes)
    ingresos = ventas.aggregate(t=Sum("total"))["t"] or Decimal(0)

    items = ItemPedido.objects.filter(
        pedido__estado__in=ESTADOS_VENTA, pedido__creado__gte=mes,
    ).select_related("variante")
    costos = Decimal(0)
    sin_costo = False
    for item in items:
        if item.variante and item.variante.costo:
            costos += item.variante.costo * item.cantidad
        else:
            sin_costo = True

    margen = ingresos - costos
    porcentaje = (margen / ingresos * 100).quantize(Decimal("0.1")) if ingresos else None
    return {
        "ingresos": ingresos,
        "costos": costos,
        "margen": margen,
        "porcentaje": porcentaje,
        "estimado": sin_costo,
    }


def clientes_nuevos(limite_dias=30):
    """Clientes registrados en los últimos N días."""
    from django.contrib.auth import get_user_model

    Usuario = get_user_model()
    desde = timezone.now() - timedelta(days=limite_dias)
    return Usuario.objects.filter(date_joined__gte=desde, is_staff=False).count()


def cupones_mas_usados(limite=5):
    """Cupones más usados, con su conteo de usos."""
    filas = (
        UsoCupon.objects.values("cupon__codigo")
        .annotate(n=Count("id"))
        .order_by("-n")[:limite]
    )
    return list(filas)


def busquedas_sin_resultados(limite=5):
    """Lo que los clientes buscaron y no encontraron (sin revisar)."""
    return list(
        BusquedaSinResultados.objects.filter(revisada=False)
        .order_by("-fecha")[:limite]
    )


def ventas_por_dia(dias=14):
    """Serie de ventas de los últimos N días para la gráfica."""
    from django.db.models.functions import TruncDate

    hoy = _inicio_del_dia()
    desde = hoy - timedelta(days=dias - 1)
    ventas = {
        fila["dia"]: fila["t"]
        for fila in Pedido.objects.filter(
            estado__in=ESTADOS_VENTA, creado__gte=desde,
        ).annotate(dia=TruncDate("creado")).values("dia").annotate(t=Sum("total"))
    }

    etiquetas, montos = [], []
    for i in range(dias):
        dia = (desde + timedelta(days=i)).date()
        etiquetas.append(f"{dia.day:02d}/{dia.month:02d}")
        montos.append(float(ventas.get(dia, 0) or 0))
    return {"etiquetas": etiquetas, "montos": montos}


def panel_completo():
    """Todas las métricas del dashboard en un solo diccionario."""
    return {
        "ventas": ventas_por_periodo(),
        "estados": pedidos_por_estado(),
        "accion": requieren_accion(),
        "stock_bajo": stock_bajo(),
        "mas_vendidos": mas_vendidos(),
        "margen": ingresos_y_margen(),
        "clientes_nuevos": clientes_nuevos(),
        "cupones": cupones_mas_usados(),
        "busquedas": busquedas_sin_resultados(),
        "serie_ventas": ventas_por_dia(),
    }
