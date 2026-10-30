"""Pasarela simulada: misma interfaz que la real, para probar todo el flujo.

La pantalla muestra el monto, la referencia (número de pedido) y los tres
resultados posibles: Aprobado, Rechazado o Pendiente. No toca internet ni
guarda datos de tarjeta. Con una llave real (Wompi) se cambia la vista y
esta pantalla se oculta.
"""
from django.conf import settings
from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from orders.models import Pedido
from orders.servicios import cambiar_estado


def activa():
    """La pasarela simulada está disponible donde se pida (desarrollo o pruebas)."""
    return getattr(settings, "PASARELA_SIMULADA", False)


def pagar(request, numero):
    """Pantalla de pago (simulada). Muestra el resumen y espera el resultado."""
    if not activa():
        messages.info(request, "El pago en línea no está habilitado todavía.")
        return redirect("orders:confirmacion", numero=numero)

    pedido = get_object_or_404(
        Pedido.objects.prefetch_related("items"), numero=numero
    )
    if pedido.estado not in ("pendiente", "por_verificar"):
        messages.info(request, f"El pedido {pedido.numero} ya está pagado.")
        return redirect("orders:confirmacion", numero=pedido.numero)

    return render(request, "payments/pagar.html", {"pedido": pedido})


@require_POST
def registrar_resultado(request, numero):
    """Guarda el resultado elegido en la pantalla simulada y avanza el pedido."""
    if not activa():
        messages.info(request, "El pago en línea no está habilitado todavía.")
        return redirect("orders:confirmacion", numero=numero)

    pedido = get_object_or_404(Pedido, numero=numero)
    if pedido.estado not in ("pendiente", "por_verificar"):
        messages.info(request, f"El pedido {pedido.numero} ya está pagado.")
        return redirect("orders:confirmacion", numero=pedido.numero)

    resultado = request.POST.get("resultado", "")
    if resultado == "aprobado":
        cambiar_estado(
            pedido, "pagado",
            nota="Pasarela simulada: pago aprobado.",
        )
        messages.success(
            request,
            f"¡Pago aprobado! Tu pedido {pedido.numero} ya está en preparación. 🎉",
        )
    elif resultado == "rechazado":
        messages.error(
            request,
            "El pago fue rechazado por la tarjeta. Puedes intentarlo de nuevo "
            "o elegir otro método de pago en tu carrito.",
        )
    elif resultado == "pendiente":
        messages.warning(
            request,
            "Tu pago quedó pendiente de confirmación. Te avisamos por WhatsApp "
            "cuando se acredite.",
        )
    else:
        messages.error(request, "No entendimos el resultado del pago.")
    return redirect("orders:confirmacion", numero=pedido.numero)
