"""Sitemaps para buscadores (Google, Bing) generados dinámicamente."""
from django.contrib.sitemaps import Sitemap
from django.urls import reverse

from catalog.models import Categoria, Producto
from core.models import PaginaLegal
from core.views import PAGINAS


class ProductoSitemap(Sitemap):
    changefreq = "weekly"
    priority = 0.8

    def items(self):
        return Producto.objects.filter(estado="publicado").order_by("-creado")

    def lastmod(self, obj):
        return getattr(obj, "creado", None)


class CategoriaSitemap(Sitemap):
    changefreq = "weekly"
    priority = 0.7

    def items(self):
        return Categoria.objects.filter(activa=True).order_by("orden", "nombre")


class PaginasSitemap(Sitemap):
    changefreq = "monthly"
    priority = 0.5

    def items(self):
        rutas = ["core:home", "catalog:tienda"]
        # Añadir slugs de páginas institucionales
        slugs_db = set(PaginaLegal.objects.filter(publicada=True).values_list("slug", flat=True))
        todos_slugs = sorted(slugs_db.union(PAGINAS.keys()))
        return rutas + [( "core:pagina", s) for s in todos_slugs]

    def location(self, item):
        if isinstance(item, tuple):
            view_name, slug = item
            return reverse(view_name, kwargs={"slug": slug})
        return reverse(item)
