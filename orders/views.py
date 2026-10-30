"""Checkout en 3 pasos (una página), confirmación y repetir pedido."""
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from orders.forms import CheckoutForm
from orders.models import Pedido
from orders.servicios import ErrorDeCompra, crear_pedido


def _volver(request, defecto="core:home"):
    url = request.META.get("HTTP_REFERER") or reverse(defecto)
    if not url.startswith("/") or url.startswith("//"):
        url = reverse(defecto)
    return redirect(url)


def _paso_con_errores(form):
    """Devuelve el primer paso (1-3) que tiene campos con error."""
    pasos = [
        ("nombre", "email", "telefono", "cedula", "mayor_de_edad", "autoriza_datos"),
        ("municipio", "direccion", "barrio", "indicaciones"),
        ("metodo_pago", "municipio"),  # el municipio inexistente se revisa al final
    ]
    for numero, campos in enumerate(pasos, start=1):
        for campo in campos:
            if form.has_error(campo):
                return numero
    return 3


def checkout(request):
    """Una página con 3 pasos: datos, envío y pago. El resumen queda siempre visible."""
    from shipping.models import zona_para_municipio

    if request.method == "POST":
        form = CheckoutForm(request.POST, usuario=request.user)
        if form.is_valid():
            zona = zona_para_municipio(form.cleaned_data["municipio"])
            if zona is None:
                form.add_error(
                    "municipio",
                    f"Todavía no enviamos a {form.cleaned_data['municipio']}; "
                    "elige otro municipio o escríbenos por WhatsApp para ayudarte.",
                )
            else:
                from shipping.models import MunicipioSantander

                municipio = MunicipioSantander.objects.get(nombre=form.cleaned_data["municipio"])
                try:
                    pedido = crear_pedido(request, {
                        **form.cleaned_data,
                        "municipio": municipio,
                    })
                except ErrorDeCompra as error:
                    form.add_error(None, str(error))
                else:
                    messages.success(
                        request,
                        f"¡Listo! Tu pedido {pedido.numero} quedó confirmado.",
                    )
                    if pedido.metodo_pago == "pasarela":
                        # Sigue a la pantalla de pago (simulada o real)
                        return redirect("payments:pagar", numero=pedido.numero)
                    return redirect("orders:confirmacion", numero=pedido.numero)
    else:
        form = CheckoutForm(usuario=request.user)

    from cart.servicios import resumen

    carrito_ui = resumen(request)
    if carrito_ui["vacio"] and request.method != "POST":
        messages.info(request, "Tu carrito está vacío; agrega algo antes de comprar.")
        return redirect("cart:pagina")

    # El paso inicial es el primero con errores (si el formulario no es válido)
    paso = _paso_con_errores(form) if form.is_bound and not form.is_valid() else 1

    zona = zona_para_municipio(carrito_ui["municipio"]) if carrito_ui["municipio"] else None
    return render(
        request,
        "orders/checkout.html",
        {
            "form": form,
            "carrito_ui": carrito_ui,
            "zona_actual": zona,
            "paso": paso,
        },
    )


def confirmacion(request, numero):
    """Página de éxito tras confirmar el pedido (accesible por número)."""
    pedido = get_object_or_404(Pedido.objects.prefetch_related("items"), numero=numero)
    return render(request, "orders/confirmacion.html", {"pedido": pedido})


@login_required
def mis_pedidos(request):
    pedidos = (
        Pedido.objects.filter(usuario=request.user)
        .prefetch_related("items")
        .order_by("-creado")
    )
    return render(request, "accounts/pedidos.html", {"pedidos": pedidos})


@login_required
def repetir(request, numero):
    """«Volver a comprar»: devuelve los ítems del pedido al carrito."""
    from cart import servicios
    from catalog.models import Variante

    pedido = get_object_or_404(Pedido, numero=numero, usuario=request.user)
    agregados = 0
    sin_stock = []
    for item in pedido.items.select_related("variante"):
        variante = item.variante
        if variante is None:
            variante = Variante.objects.filter(sku=item.sku).first()
        if variante is None or not variante.disponible:
            sin_stock.append(item.producto_nombre)
            continue
        servicios.agregar_linea(request, variante.sku, item.cantidad)
        agregados += 1

    if agregados:
        messages.success(
            request,
            f"Agregamos {agregados} producto{agregados == 1 and '' or 's'} "
            "de tu pedido al carrito. ¡Revisa las cantidades!",
        )
    if sin_stock:
        messages.warning(
            request,
            "Estos ya no están disponibles: " + ", ".join(sin_stock[:3]) + ".",
        )
    if not agregados and not sin_stock:
        messages.info(request, "No pudimos agregar nada de ese pedido.")
    return _volver(request, "cart:pagina")
