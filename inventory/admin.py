"""Admin de inventario: bitácora de movimientos, órdenes y alertas de stock."""
from django import forms
from django.contrib import admin
from django.core.exceptions import ValidationError
from django.db.models import F
from unfold.admin import ModelAdmin as UnfoldModelAdmin

from catalog.models import Variante
from inventory.models import MovimientoStock, OrdenCompra, OrdenCompraItem
from inventory.servicios import anotar_ajuste, recibir_orden, registrar_movimiento


class StockBajoFilter(admin.SimpleListFilter):
    """Alerta de stock: variantes en o por debajo de su umbral."""

    title = "alerta de stock"
    parameter_name = "alerta_stock"

    def lookups(self, request, model_admin):
        return (
            ("bajo", "Stock bajo o en el umbral"),
            ("sin", "Sin stock"),
        )

    def queryset(self, request, queryset):
        if self.value() == "bajo":
            return queryset.filter(
                activa=True, stock__gt=0, stock__lte=F("umbral_stock_bajo"),
            )
        if self.value() == "sin":
            return queryset.filter(activa=True, stock=0)
        return queryset


class MovimientoForm(forms.ModelForm):
    """Alta manual de un movimiento (ajuste, merma, corrección)."""

    class Meta:
        model = MovimientoStock
        fields = ("variante", "cantidad", "motivo", "referencia", "nota")

    def clean(self):
        datos = super().clean()
        variante, cantidad = datos.get("variante"), datos.get("cantidad")
        if variante is not None and cantidad:
            if variante.stock + cantidad < 0:
                raise ValidationError(
                    f"Ese movimiento dejaría {variante.stock + cantidad} unidades "
                    f"de {variante.sku}. Ajusta la cantidad."
                )
        return datos


@admin.register(MovimientoStock)
class MovimientoStockAdmin(UnfoldModelAdmin):
    """Bitácora: se da de alta, pero no se edita ni se borra."""

    list_display = ("creado", "variante", "cantidad", "stock_resultante",
                    "motivo", "referencia", "usuario")
    list_filter = ("motivo", "creado")
    search_fields = ("variante__sku", "variante__producto__nombre", "referencia")
    date_hierarchy = "creado"
    form = MovimientoForm
    autocomplete_fields = ("variante",)
    readonly_fields = ("stock_resultante", "usuario", "creado")

    def has_change_permission(self, request, obj=None):
        # La bitácora no se edita: cualquier corrección es un movimiento nuevo
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def save_model(self, request, obj, form, change):
        if change:
            return
        # El servicio ajusta el stock y crea el registro en una sola transacción
        movimiento = registrar_movimiento(
            obj.variante, obj.cantidad, obj.motivo,
            referencia=obj.referencia, nota=obj.nota, usuario=request.user,
        )
        # Reutiliza el registro creado por el servicio para la respuesta del admin
        obj.pk = movimiento.pk
        obj.stock_resultante = movimiento.stock_resultante
        obj.creado = movimiento.creado
        obj.usuario = movimiento.usuario


class OrdenCompraItemInline(admin.TabularInline):
    model = OrdenCompraItem
    extra = 1
    autocomplete_fields = ("variante",)


@admin.register(OrdenCompra)
class OrdenCompraAdmin(UnfoldModelAdmin):
    list_display = ("numero", "proveedor", "estado", "total_formateado",
                    "creada", "recibida")
    list_filter = ("estado", "proveedor", "creada")
    search_fields = ("numero", "proveedor__nombre")
    readonly_fields = ("numero", "creada", "recibida")
    inlines = (OrdenCompraItemInline,)
    actions = ("accion_recibir", "accion_enviar", "accion_cancelar")

    @admin.display(description="total")
    def total_formateado(self, obj):
        return f"${obj.total:,}".replace(",", ".")

    @admin.action(description="Marcar como recibida y sumar el stock")
    def accion_recibir(self, request, queryset):
        n = 0
        for orden in queryset:
            if orden.estado == "recibida":
                continue
            recibir_orden(orden, usuario=request.user)
            n += 1
        self.message_user(request, f"{n} orden(es) recibida(s) y stock sumado.")

    @admin.action(description="Marcar como enviada al proveedor")
    def accion_enviar(self, request, queryset):
        n = queryset.filter(estado="borrador").update(estado="enviada")
        self.message_user(request, f"{n} orden(es) marcadas como enviadas.")

    @admin.action(description="Cancelar órdenes seleccionadas")
    def accion_cancelar(self, request, queryset):
        n = queryset.exclude(estado="recibida").update(estado="cancelada")
        self.message_user(request, f"{n} orden(es) canceladas.")


@admin.register(Variante)
class VarianteInventarioAdmin(UnfoldModelAdmin):
    """Vista de inventario por variante: stock, umbral y valorizado."""

    list_display = ("sku", "producto", "talla_label", "color", "stock",
                    "umbral_stock_bajo", "alerta", "precio_final", "costo",
                    "valor_en_stock", "activa")
    list_filter = (StockBajoFilter, "activa", "producto")
    search_fields = ("sku", "producto__nombre", "color")
    readonly_fields = ("alerta", "valor_en_stock")

    @admin.display(boolean=True, ordering="stock_bajo", description="alerta")
    def alerta(self, obj):
        return obj.stock_bajo or obj.stock == 0

    @admin.display(description="valor en stock")
    def valor_en_stock(self, obj):
        if obj.costo is None:
            return "sin costo"
        return f"${obj.costo * obj.stock:,}".replace(",", ".")

    def save_model(self, request, obj, form, change):
        """Un cambio manual de stock queda en la bitácora como ajuste."""
        if change and "stock" in form.changed_data:
            anterior = Variante.objects.get(pk=obj.pk).stock
            obj.save()
            # El delta ya está aplicado: solo queda anotarlo en la bitácora
            anotar_ajuste(
                obj, obj.stock - anterior,
                nota=f"Ajuste manual desde el inventario: {anterior} → {obj.stock}",
                usuario=request.user,
            )
            return
        super().save_model(request, obj, form, change)
