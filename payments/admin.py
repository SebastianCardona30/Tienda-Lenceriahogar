from django.contrib import admin
from unfold.admin import ModelAdmin as UnfoldModelAdmin

from payments.models import Pago


@admin.register(Pago)
class PagoAdmin(UnfoldModelAdmin):
    list_display = ("pedido", "metodo", "monto", "estado", "creado")
    list_filter = ("estado", "metodo")
    search_fields = ("pedido__numero", "referencia", "pedido__nombre")
    readonly_fields = ("creado", "actualizado")

    def save_model(self, request, obj, form, change):
        """Al aprobar un pago desde el admin, el pedido pasa a pagado."""
        super().save_model(request, obj, form, change)
        if obj.estado == "aprobado" and obj.pedido.estado == "pendiente":
            from orders.servicios import cambiar_estado

            cambiar_estado(
                obj.pedido, "pagado",
                nota="Pago aprobado desde el panel.",
                usuario=request.user if request.user.is_authenticated else None,
            )
