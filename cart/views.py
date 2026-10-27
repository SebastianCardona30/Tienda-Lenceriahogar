from django.contrib import messages
from django.shortcuts import redirect
from django.views.decorators.http import require_POST


@require_POST
def agregar(request):
    """
    Agregar producto al carrito.

    MARCADOR DE FASE: el carrito real (sesión, stock, cupones) llega en la Fase 2.
    Por ahora se confirma al cliente que el pedido quedó registrado como interés.
    """
    sku = request.POST.get("sku", "")
    cantidad = request.POST.get("cantidad", "1")
    messages.info(
        request,
        f"Tu selección (referencia {sku}, cantidad {cantidad}) quedó lista. "
        "El carrito de compras se habilita en la próxima fase; "
        "mientras tanto puedes pedir por WhatsApp. 😉",
    )
    return redirect(request.META.get("HTTP_REFERER", "/"))
