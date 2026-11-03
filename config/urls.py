"""URLs raíz del proyecto Ciudad Bonita."""
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.sitemaps.views import sitemap
from django.urls import include, path

from catalog.sitemaps import CategoriaSitemap, PaginasSitemap, ProductoSitemap
from core import views as vistas_core
from dashboard import vistas as vistas_dashboard

sitemaps = {
    "productos": ProductoSitemap,
    "categorias": CategoriaSitemap,
    "paginas": PaginasSitemap,
}

urlpatterns = [
    # SEO: robots.txt y sitemap.xml
    path("robots.txt", vistas_core.robots_txt, name="robots_txt"),
    path(
        "sitemap.xml",
        sitemap,
        {"sitemaps": sitemaps},
        name="django.contrib.sitemaps.views.sitemap",
    ),
    # Reportes del negocio: ANTES de admin/ para que no los atrape el AdminSite
    path(
        "admin/reportes/",
        admin.site.admin_view(vistas_dashboard.pagina_reportes),
        name="admin_reportes",
    ),
    path(
        "admin/reportes/csv/",
        admin.site.admin_view(vistas_dashboard.descargar_reporte),
        name="admin_reporte_csv",
    ),
    path("admin/", admin.site.urls),
    # El orden importa: las apps específicas ANTES del catch-all de core
    path("", include("catalog.urls")),
    path("", include("cart.urls")),
    path("", include("accounts.urls")),
    path("", include("orders.urls")),
    path("", include("payments.urls")),
    path("", include("core.urls")),  # contiene <slug>/ que atrapa todo lo demás
]

if settings.EN_VERCEL:
    # En Vercel las imágenes subidas se sirven desde el propio despliegue (media/ viaja
    # en el bundle; las copias estáticas públicas las resuelve antes el CDN de Vercel).
    from django.urls import re_path
    from django.views.static import serve as servir_archivo

    urlpatterns += [
        re_path(
            r"^media/(?P<path>.*)$",
            servir_archivo,
            {"document_root": settings.MEDIA_ROOT},
        ),
    ]
elif settings.DEBUG:
    # Sirve media/ en desarrollo con runserver
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

handler404 = "core.views.error_404"
handler500 = "core.views.error_500"
