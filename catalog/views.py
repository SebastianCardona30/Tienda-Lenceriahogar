"""Vistas de la tienda: listado, categoría, ficha de producto, búsqueda y combos."""
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Prefetch, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from catalog.filters import (
    ORDENES, aplicar_busqueda, aplicar_filtros, aplicar_orden, conteos_por_opcion,
    opciones_filtros, queryset_base,
)
from catalog.models import Categoria, Combo, Producto, Resena, Variante

POR_PAGINA = 12


def _contexto_listado(request, qs, titulo, contexto_extra=None):
    """Comparte el armado de listado entre tienda, categoría, ofertas y búsqueda."""
    consulta = request.GET.get("q", "").strip()
    if consulta:
        qs = aplicar_busqueda(qs, consulta)

    qs, filtros_activos = aplicar_filtros(qs, request.GET)
    orden = request.GET.get("orden", "")
    qs = aplicar_orden(qs, orden)

    paginador = Paginator(qs, POR_PAGINA)
    pagina = paginador.get_page(request.GET.get("pagina", 1))

    # Chips de filtros activos, con su enlace para quitarlos uno a uno
    chips = []
    for clave, _valor, etiqueta in filtros_activos:
        params = request.GET.copy()
        params.pop(clave, None)
        chips.append({"etiqueta": etiqueta, "url": "?" + params.urlencode()})

    # "Limpiar todo" conserva solo la búsqueda y el orden
    params_limpiar = request.GET.copy()
    for clave in list(params_limpiar.keys()):
        if clave not in ("q", "orden", "categoria"):
            params_limpiar.pop(clave)

    contexto = {
        "productos": pagina,
        "titulo": titulo,
        "consulta": consulta,
        "filtros_activos": filtros_activos,
        "chips": chips,
        "url_limpiar": "?" + params_limpiar.urlencode(),
        "ordenes": [(clave, titulo_op) for clave, (titulo_op, _c) in ORDENES.items()],
        "orden_actual": orden,
        "categorias_raiz": Categoria.objects.filter(activa=True, padre=None).prefetch_related("hijas"),
        "opciones": opciones_filtros(),
        "conteos": conteos_por_opcion(queryset_base()),
        "total_resultados": paginador.count,
        "es_htmx": request.headers.get("HX-Request") == "true",
        "params_base": request.GET.copy(),
    }
    if contexto_extra:
        contexto.update(contexto_extra)
    return contexto


def tienda(request):
    """Listado principal de la tienda con filtros y orden."""
    contexto = _contexto_listado(request, queryset_base(), "Todos los productos")
    if contexto["es_htmx"]:
        return render(request, "catalog/partials/_grilla.html", contexto)
    return render(request, "catalog/tienda.html", contexto)


def categoria(request, slug):
    """Página de categoría (incluye subcategorías y sus productos)."""
    cat = get_object_or_404(
        Categoria.objects.filter(activa=True).prefetch_related("padre"), slug=slug
    )
    # Muestra los productos de la categoría y de sus hijas
    qs = queryset_base().filter(Q(categorias=cat) | Q(categorias__padre=cat)).distinct()
    contexto = _contexto_listado(
        request, qs, cat.nombre,
        {
            "categoria": cat,
            "subcategorias": cat.hijas.filter(activa=True),
            "padre": cat.padre,
        },
    )
    if contexto["es_htmx"]:
        return render(request, "catalog/partials/_grilla.html", contexto)
    return render(request, "catalog/categoria.html", contexto)


def buscar(request):
    """Página de resultados de búsqueda."""
    consulta = request.GET.get("q", "").strip()
    if not consulta:
        return redirect("catalog:tienda")
    contexto = _contexto_listado(request, queryset_base(), f'Resultados para "{consulta}"')
    if contexto["es_htmx"]:
        return render(request, "catalog/partials/_grilla.html", contexto)
    return render(request, "catalog/buscar.html", contexto)


def ofertas(request):
    """Productos con precio de oferta."""
    qs = queryset_base().filter(variantes__precio_oferta__isnull=False, variantes__activa=True).distinct()
    contexto = _contexto_listado(request, qs, "Ofertas de la semana")
    if contexto["es_htmx"]:
        return render(request, "catalog/partials/_grilla.html", contexto)
    return render(request, "catalog/ofertas.html", contexto)


def producto(request, slug):
    """Ficha de producto con galería, variantes, reseñas y relacionados."""
    prod = get_object_or_404(
        Producto.objects
        .filter(estado__in=("publicado", "agotado"))
        .select_related("proveedor")
        .prefetch_related(
            Prefetch("variantes", queryset=Variante.objects.filter(activa=True)),
            "fotos", "categorias",
        ),
        slug=slug,
    )
    variantes = list(prod.variantes.all())

    # Variantes en JSON para que Alpine.js actualice precio y disponibilidad
    import json
    variantes_json = json.dumps([
        {
            "sku": v.sku,
            "talla": v.talla_label,
            "color": v.color,
            "material": v.material,
            "hilos": v.hilos or "",
            "gramaje": v.gramaje or "",
            "precio": float(v.precio),
            "precio_oferta": float(v.precio_oferta) if v.precio_oferta is not None else None,
            "precio_final": float(v.precio_final),
            "ahorro": v.ahorro_pct,
            "stock": v.stock,
            "disponible": v.disponible,
        }
        for v in variantes
    ])

    # Selectores con valores únicos
    def valores(campo):
        vistos, lista = set(), []
        for v in variantes:
            valor = getattr(v, campo)
            if valor not in (None, "") and valor not in vistos:
                vistos.add(valor)
                lista.append(valor)
        return lista

    # Pestañas con contenido relacionado a categorías hermanas
    relacionados = (
        queryset_base()
        .filter(categorias__in=prod.categorias.all())
        .exclude(pk=prod.pk)
        .distinct()[:4]
    )

    # Combos que incluyen este producto ("completa tu set")
    combos_producto = [
        item.combo for item in prod.combos.select_related("combo").filter(combo__activo=True)
    ]

    # Vistos recientemente (sesión, últimos 8)
    vistos = []
    historial = request.session.get("vistos", [])
    if prod.slug in historial:
        historial.remove(prod.slug)
    historial.insert(0, prod.slug)
    request.session["vistos"] = historial[:8]
    otros = [s for s in historial[1:8]]
    if otros:
        vistos = queryset_base().filter(slug__in=otros)[:4]

    # Datos estructurados schema.org (JSON-LD)
    import json
    from core.models import SiteConfig

    nombre_negocio = SiteConfig.get().nombre_negocio
    schema = {
        "@context": "https://schema.org",
        "@type": "Product",
        "name": prod.nombre,
        "description": prod.descripcion_corta or prod.nombre,
        "brand": {"@type": "Brand", "name": prod.marca or nombre_negocio},
        "offers": {
            "@type": "AggregateOffer",
            "priceCurrency": "COP",
            "lowPrice": float(prod.precio_minimo or 0),
            "offerCount": len(variantes),
            "availability": (
                "https://schema.org/OutOfStock" if prod.agotado
                else "https://schema.org/InStock"
            ),
        },
    }
    if prod.portada:
        schema["image"] = prod.portada.imagen.url
    if prod.promedio_calificacion:
        schema["aggregateRating"] = {
            "@type": "AggregateRating",
            "ratingValue": prod.promedio_calificacion,
            "reviewCount": prod.total_resenas,
        }

    contexto = {
        "producto": prod,
        "variantes": variantes,
        "variantes_json": variantes_json,
        "tallas": valores("talla"),
        "colores": valores("color"),
        "materiales": valores("material"),
        "hilos": valores("hilos"),
        "gramajes": valores("gramaje"),
        "relacionados": relacionados,
        "resenas": prod.resenas.filter(aprobada=True),
        "combos_producto": combos_producto,
        "vistos": vistos,
        "schema_json": json.dumps(schema, ensure_ascii=False),
        "producto_nombre_json": json.dumps(prod.nombre, ensure_ascii=False),
    }
    return render(request, "catalog/producto.html", contexto)


def autocomplete(request):
    """Sugerencias del buscador (HTMX): 6 productos que coinciden."""
    consulta = request.GET.get("q", "").strip()
    if len(consulta) < 2:
        return render(request, "catalog/partials/_sugerencias.html", {"sugerencias": []})
    qs = aplicar_busqueda(queryset_base(), consulta, registrar_vacios=False)
    sugerencias = qs.order_by("-rating", "nombre")[:6]
    return render(request, "catalog/partials/_sugerencias.html", {
        "sugerencias": sugerencias,
        "consulta": consulta,
    })


def combos(request):
    """Listado de combos y sets."""
    combos_activos = Combo.objects.filter(activo=True).prefetch_related("items__producto")
    return render(request, "catalog/combos.html", {"combos": combos_activos})


def combo(request, slug):
    """Detalle de un combo."""
    combo_obj = get_object_or_404(
        Combo.objects.filter(activo=True).prefetch_related("items__producto__variantes"), slug=slug
    )
    return render(request, "catalog/combo_detalle.html", {"combo": combo_obj})


@require_POST
def suscribir(request):
    """Suscripción al boletín desde el inicio."""
    from core.models import Suscripcion

    email = (request.POST.get("email") or "").strip().lower()
    if not email or "@" not in email:
        messages.error(request, "Escribe un correo válido para suscribirte.")
        return redirect(request.META.get("HTTP_REFERER", reverse("core:home")))

    suscripcion, creada = Suscripcion.objects.get_or_create(email=email)
    if creada:
        messages.success(
            request,
            "¡Listo! Te escribiremos con las ofertas de la semana. "
            "Tu cupón de bienvenida te llegará por correo.",
        )
    else:
        messages.info(request, "Este correo ya estaba suscrito. ¡Gracias por seguir con nosotros!")
    return redirect(request.META.get("HTTP_REFERER", reverse("core:home")))


@require_POST
def enviar_resena(request, slug):
    """Formulario de reseña desde la ficha de producto (queda pendiente de moderación)."""
    prod = get_object_or_404(Producto, slug=slug, estado="publicado")
    nombre = (request.POST.get("nombre") or "").strip()
    comentario = (request.POST.get("comentario") or "").strip()
    try:
        calificacion = int(request.POST.get("calificacion", 0))
    except ValueError:
        calificacion = 0

    if not nombre or not comentario or not (1 <= calificacion <= 5):
        messages.error(request, "Completa tu nombre, la estrella y tu comentario.")
    else:
        Resena.objects.create(
            producto=prod, usuario=request.user if request.user.is_authenticated else None,
            nombre=nombre, calificacion=calificacion, comentario=comentario,
            aprobada=False,
        )
        messages.success(request, "¡Gracias por tu reseña! La publicaremos apenas la revisemos.")
    return redirect(prod.get_absolute_url())
