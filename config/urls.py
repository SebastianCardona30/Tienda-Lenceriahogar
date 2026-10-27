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
    path("", include("core.urls")),  # contiene <slug>/ que atrapa todo lo demás
]

if settings.DEBUG:
    # Sirve media/ en desarrollo con runserver
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

handler404 = "core.views.error_404"
handler500 = "core.views.error_500"
