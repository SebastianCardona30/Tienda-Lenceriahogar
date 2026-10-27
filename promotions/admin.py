from django.contrib import admin
from unfold.admin import ModelAdmin

from promotions.models import Cupon


@admin.register(Cupon)
class CuponAdmin(ModelAdmin):
    list_display = ("codigo", "tipo", "valor", "monto_minimo", "fecha_fin", "activo")
    list_filter = ("activo", "tipo", "solo_primera_compra")
    search_fields = ("codigo",)
    list_editable = ("activo",)
