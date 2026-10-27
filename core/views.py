from django.shortcuts import render

# Páginas institucionales simples. En fases posteriores se completan con
# contenido editable desde el admin (Fase 5 - textos legales).
PAGINAS = {
    "quienes-somos": {
        "titulo": "Quiénes somos",
        "bajada": "Somos una tienda de Bucaramanga que vende ropa de cama y artículos "
                  "para el hogar a precios accesibles y con trato de confianza.",
    },
    "contacto": {
        "titulo": "Contacto y PQRS",
        "bajada": "Escríbenos por WhatsApp o déjanos tus preguntas, quejas, reclamos, "
                  "sugerencias o felicitaciones (PQRS). Te respondemos pronto.",
    },
    "preguntas-frecuentes": {
        "titulo": "Preguntas frecuentes",
        "bajada": "Aquí respondemos las dudas más comunes sobre pedidos, envíos, pagos y cambios.",
    },
    "envios-y-cobertura": {
        "titulo": "Envíos y cobertura en Santander",
        "bajada": "Entregamos en el área metropolitana de Bucaramanga y en todo el "
                  "departamento de Santander con transportadora.",
    },
    "cambios-y-devoluciones": {
        "titulo": "Cambios, devoluciones y retracto",
        "bajada": "En compras a distancia tienes derecho a retractarte dentro de los "
                  "5 días hábiles siguientes a la entrega. Los productos personalizados "
                  "(bordados) no tienen cambio ni retracto salvo defecto de fabricación.",
    },
    "terminos": {
        "titulo": "Términos y condiciones",
        "bajada": "Términos de uso y compra de la tienda. Texto base pendiente de revisión profesional.",
    },
    "privacidad": {
        "titulo": "Política de privacidad y tratamiento de datos",
        "bajada": "Tratamiento de datos personales conforme a la Ley 1581 de 2012 (Colombia). "
                  "Texto base pendiente de revisión profesional.",
    },
    "cookies": {
        "titulo": "Política de cookies",
        "bajada": "Usamos cookies necesarias para el carrito y, con tu consentimiento, "
                  "cookies de analítica opcionales.",
    },
    # Placeholders temporales (se reemplazan en la Fase 2)
    "carrito": {
        "titulo": "Tu carrito",
        "bajada": "El carrito se está construyendo. En la Fase 2 ya podrás agregar productos aquí.",
    },
    "cuenta": {
        "titulo": "Mi cuenta",
        "bajada": "El área de cliente se está construyendo. Siempre podrás comprar como invitado.",
    },
}


def home(request):
    """Página de inicio con todas las secciones del diseño."""
    from catalog.filters import queryset_base
    from catalog.models import Categoria, Combo, Resena

    base = queryset_base()

    contexto = {
        "categorias_home": Categoria.objects.filter(activa=True, padre=None)
                                          .prefetch_related("hijas")[:8],
        # "Ofertas de la semana": productos con precio de oferta
        "ofertas": base.filter(variantes__precio_oferta__isnull=False,
                               variantes__activa=True).distinct()[:8],
        # Mientras no haya ventas reales se muestran los destacados
        "mas_vendidos": base.filter(destacado=True)[:4],
        "novedades": base.order_by("-creado")[:4],
        # Productos con bordado personalizable
        "bordados": base.filter(es_bordado=True)[:4],
        "combos_home": Combo.objects.filter(activo=True)[:3],
        "resenas_home": Resena.objects.filter(aprobada=True)
                            .select_related("producto")[:6],
    }
    return render(request, "core/home.html", contexto)


def pagina(request, slug):
    """Página institucional simple por slug."""
    info = PAGINAS.get(slug)
    if info is None:
        from django.http import Http404
        raise Http404("Página no encontrada")
    return render(request, "core/pagina.html", {"pagina": info})


def error_404(request, exception=None):
    return render(request, "404.html", status=404)


def error_500(request):
    return render(request, "500.html", status=500)
