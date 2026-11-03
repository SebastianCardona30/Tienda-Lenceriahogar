from django.contrib import admin
from unfold.admin import ModelAdmin as UnfoldModelAdmin

from notifications.models import PlantillaCorreo


@admin.register(PlantillaCorreo)
class PlantillaCorreoAdmin(UnfoldModelAdmin):
    list_display = ("clave", "asunto", "activo", "actualizada")
    list_filter = ("activo",)
    search_fields = ("clave", "asunto", "cuerpo")
    list_editable = ("activo",)
