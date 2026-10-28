"""Vistas de cuentas: registro, ingreso, panel, datos, direcciones, deseos y borrado."""
from urllib.parse import urlencode

from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from accounts.forms import (
    DireccionForm,
    EliminarCuentaForm,
    IngresoForm,
    PerfilForm,
    RegistroForm,
)
from accounts.models import Direccion, Deseo


def _ruta_segura(ruta, defecto):
    """Solo redirige a rutas de este sitio (evita open redirect)."""
    if ruta and ruta.startswith("/") and not ruta.startswith("//"):
        return ruta
    return reverse(defecto)


def _volver(request, defecto="core:home"):
    url = request.META.get("HTTP_REFERER") or reverse(defecto)
    if not url.startswith("/") or url.startswith("//"):
        url = reverse(defecto)
    return redirect(url)


def _fusionar(request, usuario):
    """Junta el carrito de invitado con el guardado en la cuenta."""
    from cart import servicios

    fusion = servicios.fusionar_carrito(servicios.leer(request), usuario.carrito or {})
    servicios.guardar(request, fusion)


# ------------------------------------------------------------------ acceso

def registro(request):
    """Alta de cuenta: crea el usuario, lo deja dentro y fusiona el carrito."""
    if request.user.is_authenticated:
        return redirect("accounts:panel")
    proximo = request.POST.get("next") or request.GET.get("next") or ""
    if request.method == "POST":
        form = RegistroForm(request.POST)
        if form.is_valid():
            usuario = form.guardar()
            # authenticate() deja marcado el backend (hay varios configurados)
            usuario = authenticate(
                request, username=usuario.username,
                password=request.POST.get("password1"),
            )
            login(request, usuario)
            _fusionar(request, usuario)
            messages.success(
                request,
                f"¡Bienvenido/a, {usuario.first_name or usuario.username}! "
                "Tu cuenta quedó lista.",
            )
            return redirect(_ruta_segura(proximo, "accounts:panel"))
    else:
        form = RegistroForm()
    return render(request, "accounts/registro.html", {"form": form, "next": proximo})


def ingreso(request):
    """Inicio de sesión (siempre opcional: la compra como invitado se mantiene)."""
    if request.user.is_authenticated:
        return redirect("accounts:panel")
    proximo = request.POST.get("next") or request.GET.get("next") or ""
    if request.method == "POST":
        form = IngresoForm(request, data=request.POST)
        if form.is_valid():
            login(request, form.usuario)
            _fusionar(request, form.usuario)
            messages.success(
                request,
                f"¡Hola de nuevo, {form.usuario.first_name or form.usuario.username}!",
            )
            return redirect(_ruta_segura(proximo, "accounts:panel"))
    else:
        form = IngresoForm(request)
    return render(request, "accounts/ingreso.html", {"form": form, "next": proximo})


def salir(request):
    """Cierra sesión. El carrito quedó guardado en la cuenta (sin duplicar)."""
    mensaje = "Cerraste sesión. ¡Vuelve cuando quieras!" if request.user.is_authenticated else None
    logout(request)  # limpia la sesión completa, incluido el carrito
    if mensaje:
        messages.info(request, mensaje)
    return redirect("core:home")


# ------------------------------------------------------------------ panel

@login_required
def panel(request):
    usuario = request.user
    contexto = {
        "direcciones": list(usuario.direcciones.all()[:4]),
        "total_direcciones": usuario.direcciones.count(),
        "total_deseos": usuario.total_deseos,
    }
    return render(request, "accounts/panel.html", contexto)


@login_required
def mis_datos(request):
    if request.method == "POST":
        form = PerfilForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, "Actualizamos tus datos.")
            return redirect("accounts:datos")
    else:
        form = PerfilForm(instance=request.user)
    return render(request, "accounts/datos.html", {"form": form})


# ------------------------------------------------------------------ direcciones

@login_required
def direcciones(request):
    if request.method == "POST":
        form = DireccionForm(request.POST)
        if form.is_valid():
            direccion = form.save(commit=False)
            direccion.usuario = request.user
            direccion.save()
            messages.success(request, "Dirección guardada.")
            return redirect("accounts:direcciones")
    else:
        form = DireccionForm()
    return render(
        request,
        "accounts/direcciones.html",
        {"direcciones": request.user.direcciones.all(), "form": form},
    )


@login_required
def editar_direccion(request, pk):
    direccion = get_object_or_404(Direccion, pk=pk, usuario=request.user)
    if request.method == "POST":
        form = DireccionForm(request.POST, instance=direccion)
        if form.is_valid():
            form.save()
            messages.success(request, "Dirección actualizada.")
            return redirect("accounts:direcciones")
    else:
        form = DireccionForm(instance=direccion)
    return render(
        request,
        "accounts/direccion_form.html",
        {"form": form, "direccion": direccion},
    )


@login_required
@require_POST
def eliminar_direccion(request, pk):
    direccion = get_object_or_404(Direccion, pk=pk, usuario=request.user)
    direccion.delete()
    messages.info(request, "Dirección eliminada.")
    return redirect("accounts:direcciones")


# ------------------------------------------------------------------ deseos

@login_required
def deseos(request):
    from catalog.models import Producto

    ids = request.user.deseos.values_list("producto_id", flat=True)
    favoritos = list(
        Producto.objects.filter(pk__in=list(ids)).prefetch_related("fotos", "variantes")
    )
    return render(request, "accounts/deseos.html", {"favoritos": favoritos})


@require_POST
def alternar_deseo(request):
    """Corazón de la lista de deseos: agrega o quita (pide cuenta)."""
    from catalog.models import Producto

    try:
        pk = int(request.POST.get("producto") or 0)
    except (TypeError, ValueError):
        pk = 0
    producto = get_object_or_404(Producto, pk=pk)
    if not request.user.is_authenticated:
        url_ingreso = reverse("accounts:ingreso") + "?" + urlencode(
            {"next": request.META.get("HTTP_REFERER") or producto.get_absolute_url()}
        )
        messages.info(
            request, "Inicia sesión (o crea tu cuenta) para guardar tus favoritos."
        )
        return redirect(url_ingreso)

    deseado, creado = Deseo.objects.get_or_create(usuario=request.user, producto=producto)
    if creado:
        messages.success(request, f"Guardamos «{producto.nombre}» en tus deseos.")
    else:
        deseado.delete()  # segundo toque: quitarlo de la lista
        messages.info(request, f"Quitamos «{producto.nombre}» de tus deseos.")
    return _volver(request)


# ------------------------------------------------------------------ borrado (Habeas Data)

@login_required
def eliminar_cuenta(request):
    """
    Eliminación de la cuenta y datos personales (derechos Habeas Data,
    Ley 1581 de 2012). Los datos de venta se conservan anonimizados.
    """
    if request.method == "POST":
        form = EliminarCuentaForm(request.user, request.POST)
        if form.is_valid():
            usuario = request.user
            logout(request)
            # Habeas Data: la venta se conserva, los datos personales no
            from orders.models import Pedido

            Pedido.objects.filter(usuario=usuario).update(
                nombre="Cliente eliminada", email="", telefono="", cedula="",
                direccion="", barrio="", indicaciones="", usuario=None,
            )
            usuario.delete()  # direcciones, deseos y carrito se borran en cascada
            messages.success(
                request,
                "Tu cuenta y tus datos personales fueron eliminados. ¡Hasta pronto!",
            )
            return redirect("core:home")
    else:
        form = EliminarCuentaForm(request.user)
    return render(request, "accounts/eliminar.html", {"form": form})
