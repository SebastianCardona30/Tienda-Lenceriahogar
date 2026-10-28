"""Creación de pedidos desde el carrito (transacción, stock y cupón)."""
from decimal import Decimal

from django.db import transaction

from cart import servicios as carrito_servicios
from orders.models import HistorialPedido, ItemPedido, Pedido


class ErrorDeCompra(Exception):
    """Problema que impide confirmar el pedido (mensaje ya en español)."""


@transaction.atomic
def crear_pedido(request, datos):
    """
    Confirma la compra: congela precios, descuenta stock, registra el cupón
    y limpia el carrito. Devuelve el Pedido recién creado.

    datos: nombre, email, telefono, cedula, municipio (objeto), direccion,
           barrio, indicaciones, metodo_pago, autoriza_datos, mayor_de_edad.
    """
    from catalog.models import Variante
    from promotions.models import UsoCupon

    ui = carrito_servicios.resumen(request)
    crudo = carrito_servicios.leer(request)["lineas"]
    if not crudo:
        raise ErrorDeCompra("Tu carrito está vacío; agrega algo antes de comprar.")

    if not datos.get("mayor_de_edad"):
        raise ErrorDeCompra("Debes confirmar que eres mayor de edad.")
    if not datos.get("autoriza_datos"):
        raise ErrorDeCompra("Debes aceptar los términos y la política de datos.")

    # Bloquea las variantes para no vender el mismo stock dos veces a la vez
    skus = list(crudo)
    variantes = {
        v.sku: v
        for v in Variante.objects.select_for_update().select_related("producto")
        .filter(sku__in=skus)
    }

    # Valida contra lo que el cliente pidió (no contra el ajuste amable del carrito)
    for sku, cantidad in crudo.items():
        variante = variantes.get(sku)
        if variante is None or not variante.disponible:
            raise ErrorDeCompra(
                f"{sku} se agotó mientras confirmabas; "
                "quítilo del carrito e inténtalo de nuevo."
            )
        if cantidad > variante.stock:
            raise ErrorDeCompra(
                f"De {variante.producto.nombre} solo quedan {variante.stock} unidades; "
                "ajusta la cantidad en tu carrito."
            )

    items = []
    for linea in ui["lineas"]:
        variante = variantes[linea.variante.sku]
        items.append((variante, linea))

    costo_envio = Decimal(0)
    if ui["envio"] and not ui["envio"]["gratis"]:
        costo_envio = ui["envio"]["costo"]
    elif ui["envio"]:
        costo_envio = Decimal(0)  # envío gratis por umbral de la zona

    metodo_pago = datos.get("metodo_pago") or "contraentrega"
    if metodo_pago not in ("contraentrega", "transferencia"):
        metodo_pago = "contraentrega"

    pedido = Pedido.objects.create(
        usuario=request.user if request.user.is_authenticated else None,
        nombre=datos["nombre"],
        email=datos["email"],
        telefono=datos["telefono"],
        cedula=datos.get("cedula", ""),
        autoriza_datos=True,
        mayor_de_edad=True,
        municipio=datos["municipio"],
        zona_nombre=(ui["envio"]["zona"].nombre if ui["envio"] else ""),
        direccion=datos["direccion"],
        barrio=datos.get("barrio", ""),
        indicaciones=datos.get("indicaciones", ""),
        subtotal=ui["subtotal"],
        descuento_ofertas=ui["descuento_ofertas"],
        descuento_cupon=ui["cupon_descuento"],
        cupon_codigo=(ui["cupon"].codigo if ui["cupon"] else ""),
        costo_envio=costo_envio,
        total=ui["total"],
        metodo_pago=metodo_pago,
        # Contraentrega no espera pago; transferencia queda esperando comprobante
        estado="pendiente" if metodo_pago == "transferencia" else "preparacion",
    )

    for variante, linea in items:
        ItemPedido.objects.create(
            pedido=pedido,
            variante=variante,
            producto_nombre=variante.producto.nombre,
            variante_label=variante.talla_label
            + (f" · {variante.color}" if variante.color else ""),
            sku=variante.sku,
            cantidad=linea.cantidad,
            precio_unitario=linea.precio_unitario,
            precio_base=linea.precio_base,
            descuento=linea.descuento,
        )
        variante.stock -= linea.cantidad
        variante.save(update_fields=["stock"])

    # Deja constancia del cupón usado (respeta los límites de uso)
    if ui["cupon"]:
        UsoCupon.objects.create(
            cupon=ui["cupon"],
            usuario=request.user if request.user.is_authenticated else None,
            email=pedido.email,
            pedido=pedido.numero,
        )

    HistorialPedido.objects.create(
        pedido=pedido,
        estado=pedido.estado,
        nota="Pedido confirmado por el cliente.",
        usuario=request.user if request.user.is_authenticated else None,
    )

    # El carrito queda limpio (sesión y cuenta)
    vacio = carrito_servicios.VACIO
    carrito_servicios.guardar(request, dict(vacio))
    return pedido
