"""Reglas de inventario: movimientos de stock, recepción de órdenes y valorizado.

El ajuste de stock y su registro siempre van juntos: no se mueve stock sin
dejar motivo (así se explica cualquier diferencia).
"""
from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from inventory.models import MovimientoStock, OrdenCompra


class StockInsuficiente(Exception):
    """El movimiento dejaría el stock en negativo."""


def registrar_movimiento(variante, cantidad, motivo, referencia="", nota="",
                         usuario=None):
    """
    Aplica un cambio de stock y deja el registro en la bitácora.

    cantidad: positiva suma, negativa resta. Lanza StockInsuficiente si el
    resultado quedaría por debajo de 0 (nunca se pierde stock sin explicación).
    """
    with transaction.atomic():
        # Bloquea la fila para que dos ventas simultáneas no descuadren el stock
        variante = type(variante).objects.select_for_update().get(pk=variante.pk)
        nuevo = variante.stock + cantidad
        if nuevo < 0:
            raise StockInsuficiente(
                f"Quedaría {nuevo} unidades de {variante.sku}; no se permite."
            )
        variante.stock = nuevo
        variante.save(update_fields=["stock"])
        movimiento = MovimientoStock.objects.create(
            variante=variante,
            cantidad=cantidad,
            stock_resultante=nuevo,
            motivo=motivo,
            referencia=referencia,
            nota=nota,
            usuario=usuario,
        )
    return movimiento


def anotar_ajuste(variante, diferencia, nota="", usuario=None):
    """
    Anota en la bitácora un cambio de stock YA aplicado por otro camino
    (por ejemplo, el form de la variante en el admin).

    Si la diferencia es 0 no registra nada. Lanza StockInsuficiente si el
    stock actual quedara por debajo de 0 (nunca se pierde stock sin explicación).
    """
    if not diferencia:
        return None
    if variante.stock < 0:
        raise StockInsuficiente(
            f"El stock de {variante.sku} quedó en {variante.stock}; no se permite."
        )
    return MovimientoStock.objects.create(
        variante=variante,
        cantidad=diferencia,
        stock_resultante=variante.stock,
        motivo="ajuste",
        nota=nota,
        usuario=usuario,
    )


def recibir_orden(orden, usuario=None):
    """
    Marca la orden como recibida y suma el stock de cada línea.

    Idempotente: si ya estaba recibida, no vuelve a sumar.
    """
    if orden.estado == "recibida":
        return orden
    with transaction.atomic():
        for item in orden.items.select_related("variante"):
            registrar_movimiento(
                item.variante, item.cantidad, "orden",
                referencia=orden.numero,
                nota=f"Recepción de {orden.proveedor.nombre}",
                usuario=usuario,
            )
        orden.estado = "recibida"
        orden.recibida = timezone.now()
        orden.save(update_fields=["estado", "recibida"])
    return orden


def valorizar_inventario():
    """
    Valor del inventario a costo y a precio de venta, más el faltante de costos.

    Es el "reporte valorizado": cuánto está metido el negocio en mercancía.
    """
    from catalog.models import Variante

    variantes = Variante.objects.filter(activa=True).select_related("producto")
    unidades = valor_costo = valor_venta = 0
    sin_costo = 0
    for v in variantes:
        if v.stock <= 0:
            continue
        unidades += v.stock
        if v.costo is None:
            sin_costo += 1
        else:
            valor_costo += v.costo * v.stock
        valor_venta += v.precio_final * v.stock

    margen = valor_venta - valor_costo
    porcentaje = (
        (margen / valor_venta * 100).quantize(Decimal("0.1"))
        if valor_venta else None
    )
    return {
        "unidades": unidades,
        "valor_costo": valor_costo,
        "valor_venta": valor_venta,
        "margen_potencial": margen,
        "porcentaje": porcentaje,
        "sin_costo": sin_costo,
    }
