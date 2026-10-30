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

from core.models import SiteConfig
from orders.models import Pedido
from orders.servicios import cambiar_estado
from payments.forms import ComprobanteForm


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


def comprobante(request, numero):
    """Transferencia/Nequi/Daviplata: muestra los datos de la cuenta y recibe
    el comprobante. Página pública (la compra como invitado siempre está permitida).
    """
    config = SiteConfig.get()
    medios = config.medios_pago_manuales()
    pedido = get_object_or_404(
        Pedido.objects.prefetch_related("pagos"), numero=numero
    )

    if pedido.metodo_pago != "transferencia":
        messages.info(request, "Este pedido no espera comprobante de transferencia.")
        return redirect("orders:confirmacion", numero=pedido.numero)
    if pedido.estado not in ("pendiente", "por_verificar"):
        messages.info(request, f"El pedido {pedido.numero} ya fue pagado.")
        return redirect("orders:confirmacion", numero=pedido.numero)
    if not medios:
        messages.error(
            request,
            "La transferencia no está habilitada todavía; escríbenos por WhatsApp "
            "para acordar el pago.",
        )
        return redirect("orders:confirmacion", numero=pedido.numero)

    pago_actual = next(
        (p for p in pedido.pagos.all() if p.comprobante), None
    )

    if request.method == "POST":
        form = ComprobanteForm(request.POST, request.FILES, instance=pago_actual)
        if form.is_valid():
            if pago_actual:
                pago = form.save()
            else:
                # Un pedido recibe un solo comprobante por intento de pago
                pago = form.save(commit=False)
                pago.pedido = pedido
                pago.metodo = "transferencia"
                pago.monto = pedido.total
                pago.save()
            cambiar_estado(
                pedido, "por_verificar",
                nota=f"Comprobante de {pago.get_metodo_display()} recibido; "
                     "esperando aprobación.",
            )
            messages.success(
                request,
                "¡Comprobante enviado! Revisamos el pago y te avisamos por "
                "WhatsApp en cuanto esté aprobado (suele tomar menos de un "
                "día hábil).",
            )
            return redirect("orders:confirmacion", numero=pedido.numero)
    else:
        form = ComprobanteForm(instance=pago_actual)

    return render(request, "payments/comprobante.html", {
        "pedido": pedido,
        "medios": medios,
        "form": form,
        "pago_actual": pago_actual,
    })
