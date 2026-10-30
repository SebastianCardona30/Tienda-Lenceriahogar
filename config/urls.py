"""URLs raíz del proyecto Ciudad Bonita."""
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
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
