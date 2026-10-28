"""Vistas del carrito: página, líneas, cupón y envío por municipio."""
from django.contrib import messages
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from cart import servicios


def _volver(request, abrir_drawer=False):
    """
    Regresa a la página de donde venía el formulario (solo rutas de este
    sitio). Si abrir_drawer, deja ?carrito=1 para reabrir el drawer lateral.
    """
    url = request.META.get("HTTP_REFERER") or reverse("cart:pagina")
    if not url.startswith("/") or url.startswith("//"):
        url = reverse("cart:pagina")
    if abrir_drawer and "carrito=1" not in url:
        url += ("&" if "?" in url else "?") + "carrito=1"
    return redirect(url)


def _sku_y_cantidad(request):
    """
    Lee sku y cantidad del POST con valores seguros.

    Los botones −/+ envían "cantidad"; el campo digitado envía
    "cantidad_ingresada" (si viniera después en el DOM, ganaría el botón).
    """
    sku = (request.POST.get("sku") or "").strip()
    bruto = request.POST.get("cantidad")
    if bruto in (None, ""):
        bruto = request.POST.get("cantidad_ingresada")
    try:
        cantidad = int(bruto or 1)
    except (TypeError, ValueError):
        cantidad = 1
    return sku, max(1, cantidad)


def pagina(request):
    """Página completa del carrito."""
    from shipping.models import MunicipioSantander

    municipios = MunicipioSantander.objects.select_related("zona").order_by("nombre")
    return render(request, "cart/carrito.html", {"municipios": municipios})


@require_POST
def agregar(request):
    """Agrega una variante al carrito validando stock en el servidor."""
    from catalog.models import Variante

    sku, cantidad = _sku_y_cantidad(request)
    if not sku:
        messages.error(request, "Elige talla y color antes de agregar al carrito.")
        return _volver(request, abrir_drawer=True)

    variante = Variante.objects.select_related("producto").filter(sku=sku).first()
    if variante is None:
        messages.error(request, "Ese producto ya no está disponible.")
        return _volver(request, abrir_drawer=True)
    if not variante.disponible:
        messages.error(
            request, f"{variante.producto.nombre} está agotado por ahora."
        )
        return _volver(request, abrir_drawer=True)

    datos = servicios.leer(request)
    en_carrito = datos["lineas"].get(sku, 0)
    avisado = False
    if en_carrito + cantidad > variante.stock:
        cantidad = variante.stock - en_carrito
        if cantidad <= 0:
            messages.warning(
                request,
                f"Ya tienes todo el stock disponible de {variante.producto.nombre} "
                f"({variante.stock} unidades).",
            )
            return _volver(request, abrir_drawer=True)
        messages.warning(
            request,
            f"Ajustamos la cantidad: solo quedan {variante.stock} unidades "
            f"de {variante.producto.nombre}.",
        )
        avisado = True

    servicios.agregar_linea(request, sku, cantidad)
    if not avisado:
        messages.success(
            request, f"¡Listo! {variante.producto.nombre} está en tu carrito."
        )
    return _volver(request, abrir_drawer=True)


@require_POST
def actualizar(request):
    """Cambia la cantidad de una línea (mínimo 1; para quitar, usa 'Quitar')."""
    sku, cantidad = _sku_y_cantidad(request)
    if not sku:
        messages.error(request, "No pudimos identificar el producto.")
        return _volver(request, abrir_drawer=True)

    from catalog.models import Variante

    variante = Variante.objects.select_related("producto").filter(sku=sku).first()
    if variante and cantidad > variante.stock:
        cantidad = max(variante.stock, 0)
        if cantidad == 0:
            servicios.eliminar_linea(request, sku)
            messages.warning(
                request,
                f"{variante.producto.nombre} se agotó y lo quitamos de tu carrito.",
            )
            return _volver(request, abrir_drawer=True)
        messages.warning(
            request,
            f"De {variante.producto.nombre} solo quedan {variante.stock} unidades.",
        )

    servicios.actualizar_linea(request, sku, cantidad)
    if cantidad > 0:
        messages.success(request, "Carrito actualizado.")
    else:
        messages.info(request, "Producto quitado del carrito.")
    return _volver(request, abrir_drawer=True)


@require_POST
def eliminar(request):
    """Elimina una línea del carrito."""
    sku = (request.POST.get("sku") or "").strip()
    if sku:
        servicios.eliminar_linea(request, sku)
        messages.info(request, "Producto quitado del carrito.")
    return _volver(request, abrir_drawer=True)


@require_POST
def guardar_para_despues(request):
    """Mueve una línea a 'guardar para después'."""
    sku = (request.POST.get("sku") or "").strip()
    if sku:
        servicios.guardar_para_despues(request, sku)
        messages.success(request, "Guardado en tu lista. ¡Lo puedes restaurar cuando quieras!")
    return _volver(request, abrir_drawer=True)


@require_POST
def restaurar(request):
    """Devuelve un producto guardado al carrito."""
    sku = (request.POST.get("sku") or "").strip()
    if not sku:
        messages.error(request, "No pudimos identificar el producto.")
        return _volver(request, abrir_drawer=True)

    from catalog.models import Variante

    variante = Variante.objects.select_related("producto").filter(sku=sku).first()
    if variante is None:
        messages.error(request, "Ese producto ya no está disponible.")
        return _volver(request, abrir_drawer=True)
    if not variante.disponible:
        messages.error(request, f"{variante.producto.nombre} está agotado por ahora.")
        return _volver(request, abrir_drawer=True)

    servicios.restaurar(request, sku)
    messages.success(request, f"{variante.producto.nombre} volvió a tu carrito.")
    return _volver(request, abrir_drawer=True)


@require_POST
def cupon(request):
    """Aplica o retira el cupón de descuento."""
    codigo = (request.POST.get("codigo") or "").strip()
    if not codigo:
        servicios.quitar_cupon(request)
        messages.info(request, "Cupón retirado.")
        return _volver(request, abrir_drawer=True)

    servicios.set_cupon(request, codigo)
    from cart.servicios import resumen

    datos = resumen(request)
    if datos["cupon_error"]:
        messages.error(request, datos["cupon_error"])
    elif datos["cupon_aviso"]:
        messages.warning(request, datos["cupon_aviso"])
    else:
        messages.success(request, f"Cupón {datos['cupon'].codigo} aplicado.")
    return _volver(request, abrir_drawer=True)


@require_POST
def municipio(request):
    """Guarda el municipio de entrega para estimar el envío."""
    from shipping.models import MunicipioSantander

    nombre = (request.POST.get("municipio") or "").strip()
    if not nombre:
        servicios.set_municipio(request, "")
        messages.info(request, "Municipio retirado.")
        return _volver(request, abrir_drawer=True)

    existe = MunicipioSantander.objects.filter(nombre__iexact=nombre).exists()
    if not existe:
        messages.error(
            request,
            "Solo enviamos a municipios de Santander. Elige uno de la lista.",
        )
        return _volver(request, abrir_drawer=True)

    servicios.set_municipio(request, nombre)
    messages.success(request, f"Envío estimado a {nombre} listo.")
    return _volver(request, abrir_drawer=True)
