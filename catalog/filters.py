"""
Motor de búsqueda y filtros del catálogo.

Todo se calcula en el servidor con el ORM de Django (sin servicios externos)
para que funcione igual en SQLite y PostgreSQL.
"""
from django.db.models import (
    Avg, BooleanField, Count, DecimalField, F, Min, Q, Sum, Value,
)
from django.db.models.functions import Coalesce

from catalog.models import BusquedaSinResultados, Producto, Sinonimo
from catalog.search import busqueda_tolerante, expandir_consulta, normalizar_texto

# Opciones de orden disponibles en la tienda
ORDENES = {
    "": ("Relevancia", "-relevancia"),
    "mas-vendidos": ("Más vendidos", "-ventas"),
    "menor-precio": ("Menor precio", "precio_min"),
    "mayor-precio": ("Mayor precio", "-precio_min"),
    "novedades": ("Novedades", "-creado"),
    "mejor-calificados": ("Mejor calificados", "-rating"),
}


def queryset_base():
    """Publicados con anotaciones útiles para listado y filtros."""
    return (
        Producto.objects
        .filter(estado="publicado")
        .annotate(
            precio_min=Min(Coalesce("variantes__precio_oferta", "variantes__precio")),
            stock_total=Sum(
                Coalesce("variantes__stock", 0),
                filter=Q(variantes__activa=True),
            ),
            en_oferta=Coalesce(
                Count("variantes", filter=Q(variantes__precio_oferta__isnull=False, variantes__activa=True)),
                0, output_field=BooleanField(),
            ),
            rating=Coalesce(Avg("resenas__calificacion", filter=Q(resenas__aprobada=True)), Value(0.0)),
            ventas=Value(0, output_field=DecimalField(max_digits=12, decimal_places=0)),
            relevancia=Value(0),
        )
        .distinct()
    )


def aplicar_busqueda(qs, consulta, registrar_vacios=True):
    """
    Filtra por texto con tolerancia a errores y sinónimos.
    Si no hay resultados, registra la búsqueda para verla en el admin.
    """
    consulta = normalizar_texto(consulta)
    if not consulta:
        return qs

    sinonimos = [s.lista() for s in Sinonimo.objects.filter(activo=True)]
    palabras = expandir_consulta(consulta, sinonimos)

    condicion = Q()
    for palabra in palabras:
        condicion |= Q(busqueda__icontains=palabra)

    resultados = qs.filter(condicion).distinct()

    # Si no encontró nada y la consulta es corta, busca parecidos (typos)
    if not resultados.exists() and len(consulta.split()) <= 3:
        candidatos = list(qs.values_list("busqueda", flat=True)[:3000])
        parecidos = busqueda_tolerante(consulta, candidatos)
        if parecidos:
            condicion_p = Q()
            for p in parecidos:
                for sub in p.split():
                    if len(sub) > 3:
                        condicion_p |= Q(busqueda__icontains=sub)
            resultados = qs.filter(condicion_p).distinct()

    if not resultados.exists() and registrar_vacios:
        BusquedaSinResultados.objects.create(consulta=consulta)
    return resultados


def opciones_filtros():
    """Catálogos de valores disponibles para los filtros laterales."""
    variantes_publicadas = (
        Producto.objects.filter(estado="publicado")
        .values("variantes__talla", "variantes__color", "variantes__color_hex",
                "variantes__material", "variantes__hilos", "variantes__gramaje",
                "variantes__activa")
    )
    publicadas = variantes_publicadas.filter(variantes__activa=True)

    def lista(campo):
        return sorted({
            v[campo] for v in publicadas if v[campo] not in (None, "")
        })

    marcas = sorted(
        Producto.objects.filter(estado="publicado")
        .exclude(marca="").values_list("marca", flat=True).distinct()
    )
    return {
        "tallas": lista("variantes__talla"),
        "colores": [
            {"nombre": v["variantes__color"], "hex": v["variantes__color_hex"] or "#ccc"}
            for v in publicadas.values("variantes__color", "variantes__color_hex")
            .exclude(variantes__color="")
            .distinct()
        ],
        "materiales": lista("variantes__material"),
        "hilos": lista("variantes__hilos"),
        "gramajes": lista("variantes__gramaje"),
        "marcas": marcas,
    }


def aplicar_filtros(qs, params):
    """
    Aplica los filtros del panel lateral desde los parámetros GET.

    params: request.GET (QueryDict). Devuelve (qs, filtros_activos).
    """
    activos = []

    categoria = params.get("categoria", "").strip()
    if categoria:
        qs = qs.filter(categorias__slug=categoria)
        activos.append(("categoria", categoria, "Categoría"))

    talla = params.get("talla", "").strip()
    if talla:
        qs = qs.filter(variantes__talla=talla, variantes__activa=True)
        activos.append(("talla", talla, "Talla"))

    color = params.get("color", "").strip()
    if color:
        qs = qs.filter(variantes__color__iexact=color, variantes__activa=True)
        activos.append(("color", color, "Color"))

    material = params.get("material", "").strip()
    if material:
        qs = qs.filter(variantes__material__iexact=material, variantes__activa=True)
        activos.append(("material", material, "Material"))

    marca = params.get("marca", "").strip()
    if marca:
        qs = qs.filter(marca__iexact=marca)
        activos.append(("marca", marca, "Marca"))

    hilos = params.get("hilos", "").strip()
    if hilos:
        qs = qs.filter(variantes__hilos=hilos, variantes__activa=True)
        activos.append(("hilos", hilos, "Hilos"))

    gramaje = params.get("gramaje", "").strip()
    if gramaje:
        qs = qs.filter(variantes__gramaje=gramaje, variantes__activa=True)
        activos.append(("gramaje", gramaje, "Gramaje"))

    try:
        precio_min = int(params.get("precio_min", "") or 0)
    except ValueError:
        precio_min = 0
    try:
        precio_max = int(params.get("precio_max", "") or 0)
    except ValueError:
        precio_max = 0
    if precio_min or precio_max:
        rango = Q(variantes__activa=True)
        if precio_min:
            rango &= Q(variantes__precio__gte=precio_min)
        if precio_max:
            rango &= Q(variantes__precio__lte=precio_max)
        qs = qs.filter(rango)
        if precio_min and precio_max:
            etiqueta = f"${precio_min:,} - ${precio_max:,}".replace(",", ".")
        elif precio_min:
            etiqueta = f"Desde ${precio_min:,}".replace(",", ".")
        else:
            etiqueta = f"Hasta ${precio_max:,}".replace(",", ".")
        activos.append(("precio", f"{precio_min}-{precio_max}", etiqueta))

    if params.get("oferta") == "1":
        qs = qs.filter(variantes__precio_oferta__isnull=False, variantes__activa=True)
        activos.append(("oferta", "1", "En oferta"))

    if params.get("disponible") == "1":
        qs = qs.filter(variantes__stock__gt=0, variantes__activa=True)
        activos.append(("disponible", "1", "Disponible"))

    try:
        calificacion = int(params.get("calificacion", "") or 0)
    except ValueError:
        calificacion = 0
    if calificacion:
        qs = qs.filter(resenas__aprobada=True, resenas__calificacion__gte=calificacion)
        activos.append(("calificacion", str(calificacion), f"{calificacion}★ o más"))

    return qs.distinct(), activos


def aplicar_orden(qs, orden):
    """Ordena según la opción elegida en el combo."""
    _titulo, campo = ORDENES.get(orden, ORDENES[""])
    return qs.order_by(campo, "nombre")


def conteos_por_opcion(qs):
    """
    Contador de productos por opción de filtro (talla, color, material, marca).
    Se calcula sobre el listado base (con búsqueda aplicada, sin filtros).
    """
    variantes = qs.filter(variantes__activa=True)
    return {
        "tallas": {
            fila["variantes__talla"]: fila["n"]
            for fila in variantes.values("variantes__talla")
            .exclude(variantes__talla="")
            .annotate(n=Count("id", distinct=True))
        },
        "colores": {
            fila["variantes__color"]: fila["n"]
            for fila in variantes.values("variantes__color", "variantes__color_hex")
            .exclude(variantes__color="")
            .annotate(n=Count("id", distinct=True))
        },
        "materiales": {
            fila["variantes__material"]: fila["n"]
            for fila in variantes.values("variantes__material")
            .exclude(variantes__material="")
            .annotate(n=Count("id", distinct=True))
        },
        "marcas": {
            fila["marca"]: fila["n"]
            for fila in qs.exclude(marca="")
            .values("marca")
            .annotate(n=Count("id", distinct=True))
        },
        "hilos": {
            fila["variantes__hilos"]: fila["n"]
            for fila in variantes.values("variantes__hilos")
            .exclude(variantes__hilos__isnull=True)
            .annotate(n=Count("id", distinct=True))
        },
        "gramajes": {
            fila["variantes__gramaje"]: fila["n"]
            for fila in variantes.values("variantes__gramaje")
            .exclude(variantes__gramaje__isnull=True)
            .annotate(n=Count("id", distinct=True))
        },
    }
