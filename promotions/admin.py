from django.contrib import admin

from unfold.admin import ModelAdmin

from promotions.models import Cupon, Descuento, PromoUnidades, PromoVolumen, UsoCupon, VentaRelampago


@admin.register(Cupon)
class CuponAdmin(ModelAdmin):
    list_display = (
        "codigo", "tipo", "valor", "monto_minimo", "fecha_fin",
        "max_usos", "solo_primera_compra", "acumulable", "activo",
    )
    list_filter = ("activo", "tipo", "solo_primera_compra", "acumulable")
    search_fields = ("codigo",)
    list_editable = ("activo",)
    filter_horizontal = ("categorias",)


@admin.register(UsoCupon)
class UsoCuponAdmin(ModelAdmin):
    list_display = ("cupon", "usuario", "email", "pedido", "creado")
    list_filter = ("cupon",)
    search_fields = ("email", "pedido", "usuario__username")
    readonly_fields = ("creado",)


@admin.register(Descuento)
class DescuentoAdmin(ModelAdmin):
    list_display = ("nombre", "sobre", "tipo", "valor", "fecha_inicio", "fecha_fin", "activo")
    list_filter = ("activo", "sobre", "tipo")
    search_fields = ("nombre",)
    list_editable = ("activo",)


@admin.register(PromoUnidades)
class PromoUnidadesAdmin(ModelAdmin):
    list_display = ("nombre", "producto", "categoria", "llevar", "pagar", "fecha_fin", "activo")
    list_filter = ("activo",)
    search_fields = ("nombre",)
    list_editable = ("activo",)


@admin.register(PromoVolumen)
class PromoVolumenAdmin(ModelAdmin):
    list_display = (
        "nombre", "tipo", "valor", "cantidad_minima", "producto",
        "categoria", "fecha_fin", "activo",
    )
    list_filter = ("activo", "tipo")
    search_fields = ("nombre",)
    list_editable = ("activo",)


@admin.register(VentaRelampago)
class VentaRelampagoAdmin(ModelAdmin):
    list_display = ("variante", "precio", "desde", "hasta", "ahorro_pct", "activo")
    list_filter = ("activo",)
    search_fields = ("variante__sku", "variante__producto__nombre")
    list_editable = ("activo",)
    readonly_fields = ("ahorro_pct",)
