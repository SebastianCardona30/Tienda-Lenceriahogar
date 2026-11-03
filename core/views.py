from django.shortcuts import render

# Páginas institucionales y legales con texto base completo.
# La dueña puede editarlas en cualquier momento desde el panel de administración
# mediante el modelo PaginaLegal.
NOTA_LEGAL = (
    "\n\n*Aviso importante:* Este documento constituye un texto base orientativo "
    "adaptado al comercio electrónico en Colombia (Ley 1480 de 2011 y Ley 1581 de 2012). "
    "Se recomienda su validación por parte de un profesional del derecho antes de su adopción definitiva."
)

PAGINAS = {
    "quienes-somos": {
        "titulo": "Quiénes somos",
        "bajada": "Somos una tienda de Bucaramanga que vende ropa de cama y artículos "
                  "para el hogar a precios accesibles y con trato de confianza.",
        "contenido": (
            "En Lencería de Hogar Ciudad Bonita nos dedicamos a vestir los hogares de Santander "
            "con calidez, elegancia y economía. Nacimos en Bucaramanga con la convicción de que un buen descanso "
            "y un hogar acogedor no tienen por qué ser costosos.\n\n"
            "Seleccionamos cuidadosamente nuestros proveedores para ofrecerte sábanas suaves, edredones abrigados, "
            "toallas absorbentes, cortinas y accesorios que transforman cada rincón de tu casa. "
            "Además, ofrecemos servicio de bordado personalizado para darle un toque único a tus prendas.\n\n"
            "Atendemos de manera cercana y directa por WhatsApp, con envíos seguros a todos los 87 municipios "
            "de Santander y múltiples opciones de pago fáciles y confiables."
        ),
    },
    "contacto": {
        "titulo": "Contacto y PQRS",
        "bajada": "Escríbenos por WhatsApp o déjanos tus preguntas, quejas, reclamos, "
                  "sugerencias o felicitaciones (PQRS). Te respondemos pronto.",
        "contenido": (
            "En Lencería de Hogar Ciudad Bonita tu opinión y tu tranquilidad son nuestra prioridad. "
            "Ponemos a tu disposición nuestros canales oficiales de atención:\n\n"
            "• **WhatsApp:** Atención directa y personalizada para consultas y pedidos.\n"
            "• **Correo electrónico:** Puedes escribirnos directamente al correo registrado en nuestra información de contacto.\n"
            "• **Ciudad de origen:** Bucaramanga, Santander, Colombia.\n\n"
            "**Procedimiento para Peticiones, Quejas, Reclamos y Sugerencias (PQRS):**\n"
            "1. Envíanos tu solicitud indicando tu nombre completo, número de cédula, teléfono de contacto, "
            "número de pedido (si aplica) y la descripción clara de los hechos.\n"
            "2. Acusaremos recibo de tu solicitud dentro de las 24 horas hábiles siguientes.\n"
            "3. Conforme a la legislación colombiana (Código de Procedimiento Administrativo y Estatuto del Consumidor), "
            "daremos respuesta de fondo a tu PQRS en un plazo máximo de quince (15) días hábiles.\n\n"
            "Siempre buscaremos una solución justa, rápida y cordial para ti."
        ),
    },
    "preguntas-frecuentes": {
        "titulo": "Preguntas frecuentes",
        "bajada": "Aquí respondemos las dudas más comunes sobre pedidos, envíos, pagos y cambios.",
        "contenido": (
            "**¿Hacen envíos a todo Santander?**\n"
            "Sí, cubrimos los 87 municipios del departamento. En el área metropolitana de Bucaramanga "
            "(Floridablanca, Girón, Piedecuesta) las entregas suelen realizarse el mismo día o al día siguiente hábil. "
            "Para los demás municipios el tiempo oscila entre 2 y 4 días hábiles vía transportadora aliada.\n\n"
            "**¿Qué medios de pago aceptan?**\n"
            "Aceptamos pagos en línea (PSE, tarjetas de crédito/débito, Nequi y Daviplata), "
            "transferencias directas con comprobante y pago contraentrega en efectivo al momento de recibir en zonas autorizadas.\n\n"
            "**¿Cómo sé la medida correcta de sábanas para mi cama?**\n"
            "Nuestras fichas de producto indican las medidas exactas de colchón: Sencilla (100×190 cm), "
            "Semidoble (120×190 cm), Doble (140×190 cm), Queen (160×190 cm) y King (200×200 cm). "
            "Si tienes dudas sobre la altura de tu colchón, escríbenos por WhatsApp y te asesoramos al instante.\n\n"
            "**¿Los productos bordados tienen cambio?**\n"
            "Por ser confeccionados de forma exclusiva según las especificaciones del cliente, "
            "los productos personalizados no admiten cambio por gusto, únicamente por defectos demostrables de fabricación."
        ),
    },
    "envios-y-cobertura": {
        "titulo": "Envíos y cobertura en Santander",
        "bajada": "Entregamos en el área metropolitana de Bucaramanga y en todo el "
                  "departamento de Santander con transportadora.",
        "contenido": (
            "Realizamos despachos exclusivamente dentro del departamento de Santander, Colombia.\n\n"
            "**Zonas de despacho:**\n"
            "• **Área Metropolitana de Bucaramanga:** Bucaramanga, Floridablanca, Girón y Piedecuesta. "
            "Tarifa fija accesible y opción de envío gratis superando el monto mínimo de compra indicado en la tienda.\n"
            "• **Resto de Santander (87 municipios):** San Gil, Socorro, Barbosa, Barrancabermeja, Vélez, Málaga, "
            "Zapatoca y demás poblaciones mediante transportadoras reconocidas con guía de rastreo.\n\n"
            "**Tiempos de entrega:**\n"
            "Los pedidos confirmados antes de las 2:00 p.m. en días hábiles se procesan el mismo día. "
            "Una vez despachado el paquete, te compartimos tu número de guía y el enlace de seguimiento."
        ),
    },
    "cambios-y-devoluciones": {
        "titulo": "Cambios, garantías y derecho de retracto",
        "bajada": "Conoce los plazos y condiciones para solicitar cambios, garantías y el ejercicio del derecho de retracto.",
        "contenido": (
            "En cumplimiento del Estatuto del Consumidor (Ley 1480 de 2011), en Lencería de Hogar Ciudad Bonita "
            "garantizamos tus derechos en todas las compras realizadas a través de nuestra plataforma:\n\n"
            "**1. Derecho de Retracto (Compras a distancia):**\n"
            "Para ventas por medios no tradicionales o a distancia, tienes la facultad de ejercer tu derecho de retracto "
            "dentro de los cinco (5) días hábiles siguientes a la entrega del producto. "
            "Para ejercerlo, el producto debe encontrarse nuevo, sin uso, en su empaque original y con todas sus etiquetas intactas. "
            "Los costos de transporte por devolución por retracto son asumidos por el comprador conforme al art. 47 de la Ley 1480.\n"
            "*Excepción legal:* Los bienes confeccionados conforme a especificaciones del consumidor o claramente personalizados "
            "(como sábanas o toallas con bordado a medida) están expresamente exceptuados del derecho de retracto.\n\n"
            "**2. Garantía Legal:**\n"
            "Nuestros productos cuentan con una garantía legal de noventa (90) días calendario por defectos de confección o costura. "
            "La garantía no cubre daños causados por uso indebido, lavado con químicos abrasivos o incumplimiento de las instrucciones de cuidado.\n\n"
            "**3. Procedimiento para cambios y devoluciones:**\n"
            "Comunícate con nosotros por WhatsApp o correo dentro del plazo legal indicando tu número de pedido y fotos del estado del producto. "
            "Revisaremos tu caso en menos de 48 horas hábiles." + NOTA_LEGAL
        ),
    },
    "terminos": {
        "titulo": "Términos y condiciones",
        "bajada": "Términos y condiciones de uso y compraventa en la tienda online.",
        "contenido": (
            "Bienvenido al portal web de Lencería de Hogar Ciudad Bonita. El acceso y uso de este sitio se rige "
            "por las leyes de la República de Colombia y los siguientes términos:\n\n"
            "**1. Capacidad legal:** El usuario declara ser mayor de edad con plena capacidad legal para obligarse y realizar compras.\n\n"
            "**2. Precios e impuestos:** Todos los precios exhibidos están expresados en pesos colombianos (COP) e incluyen "
            "el Impuesto sobre las Ventas (IVA) conforme a la tasa aplicable.\n\n"
            "**3. Perfeccionamiento de la compra:** La orden se entiende confirmada una vez se verifique exitosamente el pago "
            "o, en la modalidad contraentrega, cuando el cliente confirme sus datos de entrega.\n\n"
            "**4. Disponibilidad y stock:** El inventario se actualiza en tiempo real. En caso fortuito de agotarse una referencia, "
            "se informará inmediatamente al comprador para acordar un reemplazo o la devolución íntegra del dinero sin penalidad.\n\n"
            "**5. Propiedad intelectual:** Las marcas, fotografías y diseños del portal son propiedad de la tienda o sus proveedores aliados."
            + NOTA_LEGAL
        ),
    },
    "privacidad": {
        "titulo": "Política de privacidad y tratamiento de datos",
        "bajada": "Tratamiento de datos personales conforme a la Ley Estatutaria 1581 de 2012 (Colombia).",
        "contenido": (
            "Lencería de Hogar Ciudad Bonita, en calidad de Responsable del Tratamiento, adopta la presente Política de Privacidad "
            "en cumplimiento de la Ley 1581 de 2012 y el Decreto 1377 de 2013 de Colombia:\n\n"
            "**1. Finalidad de la recolección:**\n"
            "Los datos personales recolectados (nombre, teléfono, correo electrónico, dirección de entrega y cédula) "
            "tienen como única finalidad gestionar la compra, tramitar el despacho de pedidos, enviar avisos de estado "
            "y atender solicitudes o garantías.\n\n"
            "**2. Derechos del titular (Habeas Data):**\n"
            "Como titular de tus datos personales tienes derecho a conocer, actualizar, rectificar y suprimir tu información, "
            "así como revocar la autorización otorgada. Puedes ejercer estos derechos en cualquier momento desde tu panel de cuenta "
            "(botón de eliminación de cuenta) o escribiéndonos directamente.\n\n"
            "**3. Confidencialidad y seguridad:**\n"
            "No vendemos, alquilamos ni compartimos tus datos personales con terceros para fines comerciales. "
            "Los datos de entrega solo se comparten con las transportadoras aliadas encargadas de llevar el paquete a tu domicilio."
            + NOTA_LEGAL
        ),
    },
    "cookies": {
        "titulo": "Política de cookies",
        "bajada": "Información sobre el uso de cookies y tecnologías de almacenamiento local.",
        "contenido": (
            "En Lencería de Hogar Ciudad Bonita utilizamos cookies y almacenamiento local con propósitos técnicos y de analítica:\n\n"
            "**1. Cookies estrictamente necesarias:**\n"
            "Imprescindibles para el funcionamiento de la tienda: mantener los productos en tu carrito de compras, "
            "recordar el inicio de sesión y proteger los formularios contra ataques informáticos (CSRF).\n\n"
            "**2. Cookies de analítica opcionales:**\n"
            "Solo se activan si nos otorgas tu consentimiento explícito a través del banner de cookies. "
            "Nos ayudan a entender de forma anónima cómo navegan las usuarias para optimizar la velocidad y el diseño del sitio.\n\n"
            "Puedes aceptar o rechazar las cookies de analítica en cualquier momento seleccionando 'Solo necesarias' en nuestro banner."
            + NOTA_LEGAL
        ),
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
    """Página institucional o legal por slug (desde BD o diccionario base)."""
    from core.models import PaginaLegal
    from django.http import Http404

    # 1. Buscar en BD si está publicada
    obj = PaginaLegal.objects.filter(slug=slug, publicada=True).first()
    if obj:
        info = {
            "titulo": obj.titulo,
            "bajada": obj.bajada,
            "contenido": obj.contenido,
        }
        return render(request, "core/pagina.html", {"pagina": info})

    # 2. Fallback a diccionario base
    info = PAGINAS.get(slug)
    if info is None:
        raise Http404("Página no encontrada")
    return render(request, "core/pagina.html", {"pagina": info})


def error_404(request, exception=None):
    return render(request, "404.html", status=404)


def error_500(request):
    return render(request, "500.html", status=500)


def robots_txt(request):
    """Archivo robots.txt optimizado para motores de búsqueda."""
    from django.conf import settings
    from django.http import HttpResponse

    sitemap_url = f"{settings.SITE_URL}/sitemap.xml"
    lineas = [
        "User-agent: *",
        "Disallow: /admin/",
        "Disallow: /cuenta/",
        "Disallow: /checkout/",
        "Disallow: /pago/",
        "Disallow: /carrito/",
        "Allow: /",
        "",
        f"Sitemap: {sitemap_url}",
    ]
    return HttpResponse("\n".join(lineas), content_type="text/plain; charset=utf-8")
