from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from unfold.admin import ModelAdmin

from core.models import SiteConfig, Suscripcion


@admin.register(Suscripcion)
class SuscripcionAdmin(ModelAdmin):
    list_display = ("email", "activo", "creada")
    list_filter = ("activo",)
    search_fields = ("email",)
    list_editable = ("activo",)
    actions = ["exportar_csv"]

    @admin.action(description="Exportar seleccionadas a CSV")
    def exportar_csv(self, request, queryset):
        import csv
        from django.http import HttpResponse

        respuesta = HttpResponse(content_type="text/csv; charset=utf-8")
        respuesta["Content-Disposition"] = 'attachment; filename="suscripciones.csv"'
        escritor = csv.writer(respuesta)
        escritor.writerow(["correo", "activo", "fecha"])
        for s in queryset:
            escritor.writerow([s.email, "sí" if s.activo else "no", s.creada.strftime("%Y-%m-%d")])
        return respuesta


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
        (_("Ofertas de la semana"), {
            "fields": ("ofertas_hasta",),
            "description": "Cuenta regresiva del inicio. Se muestran los productos con precio de oferta.",
        }),
        (_("Medios de pago manuales (marcadores configurables)"), {
            "fields": ("pago_nequi", "pago_daviplata", "pago_transferencia",
                       "reserva_horas_transferencia"),
            "description": "Datos que ve el cliente para transferir y subir el comprobante. "
                           "Dejar en blanco un medio lo oculta del checkout.",
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
