from django.contrib import admin

from unfold.admin import ModelAdmin

from shipping.models import MunicipioSantander, ZonaEnvio


@admin.register(ZonaEnvio)
class ZonaEnvioAdmin(ModelAdmin):
    list_display = (
        "nombre", "tarifa", "envio_gratis_desde", "tiempo_estimado",
        "recogida_disponible", "activa", "orden",
    )
    list_editable = ("activa", "orden")
    search_fields = ("nombre",)


@admin.register(MunicipioSantander)
class MunicipioSantanderAdmin(ModelAdmin):
    list_display = ("nombre", "zona")
    list_filter = ("zona",)
    search_fields = ("nombre",)
    list_editable = ("zona",)
    ordering = ("nombre",)
