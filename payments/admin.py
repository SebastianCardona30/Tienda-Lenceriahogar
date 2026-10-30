from django.contrib import admin
from unfold.admin import ModelAdmin as UnfoldModelAdmin

from payments.models import Pago


@admin.register(Pago)
class PagoAdmin(UnfoldModelAdmin):
    list_display = ("pedido", "metodo", "monto", "estado", "comprobante", "creado")
    list_filter = ("estado", "metodo")
    search_fields = ("pedido__numero", "referencia", "pedido__nombre")
    readonly_fields = ("creado", "actualizado")
    actions = ["aprobar_pagos", "rechazar_pagos"]

    @admin.action(description="✓ Aprobar seleccionados (el pedido pasa a Pagado)")
    def aprobar_pagos(self, request, queryset):
        """Aprobación con un clic desde el panel."""
        from orders.servicios import cambiar_estado

        aprobados = 0
        for pago in queryset.select_related("pedido"):
            if pago.estado == "aprobado":
                continue
            pago.estado = "aprobado"
            pago.save(update_fields=["estado", "actualizado"])
            if pago.pedido.estado != "pagado":
                cambiar_estado(
                    pago.pedido, "pagado",
                    nota="Pago aprobado desde el panel.",
                    usuario=request.user if request.user.is_authenticated else None,
                )
            aprobados += 1
        self.message_user(
            request, f"{aprobados} pago(s) aprobado(s); los pedidos ya están en Pagado."
        )

    @admin.action(description="✕ Rechazar seleccionados (el pedido vuelve a Pendiente)")
    def rechazar_pagos(self, request, queryset):
        from orders.servicios import cambiar_estado

        rechazados = 0
        for pago in queryset.select_related("pedido"):
            if pago.estado == "rechazado":
                continue
            pago.estado = "rechazado"
            pago.save(update_fields=["estado", "actualizado"])
            if pago.pedido.estado in ("pendiente", "por_verificar"):
                cambiar_estado(
                    pago.pedido, "pendiente",
                    nota="Pago rechazado desde el panel; el cliente debe enviar "
                         "otro comprobante o elegir otro método.",
                    usuario=request.user if request.user.is_authenticated else None,
                )
            rechazados += 1
        self.message_user(
            request,
            f"{rechazados} pago(s) rechazado(s); los pedidos vuelven a Pendiente "
            "para que el cliente reenvíe el comprobante.",
        )

    def save_model(self, request, obj, form, change):
        """Al aprobar un pago desde el formulario, el pedido pasa a pagado."""
        super().save_model(request, obj, form, change)
        if obj.estado == "aprobado" and obj.pedido.estado != "pagado":
            from orders.servicios import cambiar_estado

            cambiar_estado(
                obj.pedido, "pagado",
                nota="Pago aprobado desde el panel.",
                usuario=request.user if request.user.is_authenticated else None,
            )
