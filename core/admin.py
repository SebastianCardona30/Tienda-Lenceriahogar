from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from unfold.admin import ModelAdmin

from core.models import SiteConfig


@admin.register(SiteConfig)
class SiteConfigAdmin(ModelAdmin):
    """Panel de la configuración general del negocio (en español)."""

    list_display = ("nombre_negocio", "ciudad", "whatsapp", "email_contacto", "iva_tasa")
    fieldsets = (
        (_("Identidad del negocio"), {
            "fields": ("nombre_negocio", "lema", "logo", "ciudad"),
            "description": "Datos que se muestran en el encabezado y el pie de página.",
        }),
        (_("Contacto (marcadores configurables)"), {
            "fields": ("whatsapp", "telefono", "email_contacto", "nit", "direccion", "horario"),
            "description": "No inventes datos: deja los marcadores en blanco si aún no se tienen.",
        }),
        (_("Barra de promociones"), {
            "fields": ("banner_promo_activo", "banner_promo_texto"),
        }),
        (_("Impuestos y moneda"), {
            "fields": ("iva_incluido", "iva_tasa"),
        }),
        (_("Redes sociales (opcionales)"), {
            "fields": ("instagram", "facebook", "tiktok"),
        }),
    )

    def has_delete_permission(self, request, obj=None):
        # La configuración no se puede borrar.
        return False
