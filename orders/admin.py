from django.contrib import admin
from unfold.admin import ModelAdmin as UnfoldModelAdmin

from orders.models import HistorialPedido, ItemPedido, Pedido


class ItemPedidoInline(admin.TabularInline):
    model = ItemPedido
    extra = 0
    readonly_fields = (
        "producto_nombre", "variante_label", "sku", "cantidad",
        "precio_unitario", "precio_base", "descuento", "subtotal",
    )
    can_delete = False


class HistorialInline(admin.TabularInline):
    model = HistorialPedido
    extra = 0
    readonly_fields = ("estado", "nota", "usuario", "creado")
    can_delete = False


@admin.register(Pedido)
class PedidoAdmin(UnfoldModelAdmin):
    list_display = (
        "numero", "nombre", "municipio", "total", "estado", "metodo_pago", "creado",
    )
    list_filter = ("estado", "metodo_pago", "municipio", "creado")
    search_fields = ("numero", "nombre", "email", "telefono", "cedula")
    readonly_fields = ("numero", "creado", "actualizado", "subtotal",
                       "descuento_ofertas", "descuento_cupon", "total")
    inlines = (ItemPedidoInline, HistorialInline)
    date_hierarchy = "creado"

    def save_model(self, request, obj, form, change):
        """Al cambiar el estado desde el admin, deja constancia en el historial."""
        estado_anterior = None
        if change:
            estado_anterior = (
                Pedido.objects.filter(pk=obj.pk).values_list("estado", flat=True).first()
            )
        super().save_model(request, obj, form, change)
        if estado_anterior != obj.estado:
            HistorialPedido.objects.create(
                pedido=obj,
                estado=obj.estado,
                nota="Cambio de estado desde el panel.",
                usuario=request.user if request.user.is_authenticated else None,
            )


@admin.register(ItemPedido)
class ItemPedidoAdmin(UnfoldModelAdmin):
    list_display = ("pedido", "producto_nombre", "cantidad", "subtotal")
    search_fields = ("pedido__numero", "producto_nombre", "sku")


@admin.register(HistorialPedido)
class HistorialPedidoAdmin(UnfoldModelAdmin):
    list_display = ("pedido", "estado", "creado")
    list_filter = ("estado",)
