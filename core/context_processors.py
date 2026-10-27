from core.models import SiteConfig


def site_config(request):
    """
    Contexto global: configuración del negocio + menú de categorías.
    """
    config = SiteConfig.get()

    # Categorías del menú: raíces activas con sus hijas activas
    from catalog.models import Categoria

    categorias_menu = list(
        Categoria.objects.filter(activa=True, padre=None)
        .prefetch_related("hijas")
        .order_by("orden", "nombre")
    )

    return {
        "site": config,
        "categorias_menu": categorias_menu,
    }
