"""Creación de pedidos desde el carrito (transacción, stock y cupón)."""
from datetime import timedelta
from decimal import Decimal

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from cart import servicios as carrito_servicios
from orders.models import HistorialPedido, ItemPedido, Pedido


class ErrorDeCompra(Exception):
    """Problema que impide confirmar el pedido (mensaje ya en español)."""


def cambiar_estado(pedido, estado, nota="", usuario=None):
    """Cambia el estado del pedido y deja constancia en el historial.

    Al cancelar o devolver un pedido, el stock reservado se devuelve al
    inventario (una sola vez; el pedido lleva la marca stock_devuelto).
    """
    if pedido.estado == estado:
        return pedido
    pedido.estado = estado
    campos = ["estado", "actualizado"]
    # Al confirmarse el pago (o salir a preparación) la reserva deja de contar
    if estado in ("pagado", "preparacion", "enviado", "entregado"):
        pedido.reserva_hasta = None
        campos.append("reserva_hasta")
    pedido.save(update_fields=campos)
    HistorialPedido.objects.create(
        pedido=pedido, estado=estado, nota=nota, usuario=usuario,
    )
    if estado in ("cancelado", "devuelto"):
        devolver_stock(pedido)
    # Aviso al cliente por correo en los estados que le importan (on_commit)
    from core import correos

    transaction.on_commit(lambda: correos.cambio_estado_pedido(pedido))
    return pedido


def devolver_stock(pedido):
    """Devuelve al inventario las unidades de un pedido (idempotente)."""
    from catalog.models import Variante

    if pedido.stock_devuelto:
        return False
    skus = list(pedido.items.values_list("sku", flat=True))
    with transaction.atomic():
        variantes = {
            v.sku: v
            for v in Variante.objects.select_for_update().filter(sku__in=skus)
        }
        for item in pedido.items.all():
            variante = variantes.get(item.sku)
            if variante:
                variante.stock += item.cantidad
                variante.save(update_fields=["stock"])
        # Marca el pedido dentro de la misma transacción para no devolver dos veces
        Pedido.objects.filter(pk=pedido.pk, stock_devuelto=False).update(
            stock_devuelto=True
        )
    pedido.stock_devuelto = True
    return True


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
    if metodo_pago not in ("pasarela", "contraentrega", "transferencia"):
        metodo_pago = "contraentrega"

    # Reserva de stock: la pasarela espera 15 minutos (ajustable en settings);
    # la transferencia, las horas configuradas en el admin del negocio.
    ahora = timezone.now()
    if metodo_pago == "pasarela":
        reserva_hasta = ahora + timedelta(
            minutes=getattr(settings, "RESERVA_MINUTOS_PASARELA", 15)
        )
    elif metodo_pago == "transferencia":
        from core.models import SiteConfig

        reserva_hasta = ahora + timedelta(
            hours=SiteConfig.get().reserva_horas_transferencia
        )
    else:
        reserva_hasta = None  # contraentrega: sin pago que esperar

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
        # Contraentrega no espera pago; pasarela y transferencia sí
        estado="preparacion" if metodo_pago == "contraentrega" else "pendiente",
        reserva_hasta=reserva_hasta,
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

    # Correos de marca: se envían solo si la transacción se confirma (on_commit)
    # y nunca rompen la compra (fail_silently dentro de core.correos).
    from core import correos

    transaction.on_commit(lambda: correos.confirmacion_pedido(pedido))
    transaction.on_commit(lambda: correos.aviso_interno_pedido(pedido))

    # El carrito queda limpio (sesión y cuenta)
    vacio = carrito_servicios.VACIO
    carrito_servicios.guardar(request, dict(vacio))
    return pedido
