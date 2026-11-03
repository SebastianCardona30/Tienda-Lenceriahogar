from django.contrib import admin
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import render
from django.urls import path, reverse
from django.utils.html import format_html
from unfold.admin import ModelAdmin, StackedInline, TabularInline

from catalog import csv_io
from catalog.models import (
    BusquedaSinResultados, Categoria, Combo, ComboItem, FotoProducto,
    Producto, Proveedor, Resena, Sinonimo, Variante,
)


class FotoInline(TabularInline):
    model = FotoProducto
    extra = 1
    fields = ("imagen", "miniatura", "alt", "orden")
    readonly_fields = ("miniatura",)
    ordering = ("orden",)


class VarianteInline(StackedInline):
    model = Variante
    extra = 1
    fields = (
        "sku", "talla", "medida_personalizada", "color", "color_hex", "material",
        "hilos", "gramaje", "precio", "precio_oferta", "costo", "stock",
        "umbral_stock_bajo", "peso_gramos", "foto", "activa",
    )
    ordering = ("talla", "color")


@admin.register(Categoria)
class CategoriaAdmin(ModelAdmin):
    list_display = ("nombre", "padre", "orden", "activa", "ver_imagen")
    list_filter = ("activa", "padre")
    search_fields = ("nombre",)
    prepopulated_fields = {"slug": ("nombre",)}
    list_editable = ("orden", "activa")
    fields = (
        "nombre", "slug", "padre", "descripcion", "imagen", "ver_imagen",
        "orden", "activa", "meta_titulo", "meta_descripcion",
    )
    readonly_fields = ("ver_imagen",)

    @admin.display(description="Imagen")
    def ver_imagen(self, obj):
        if obj.imagen:
            return format_html('<img src="{}" style="height:40px;border-radius:8px;">', obj.imagen.url)
        return "—"


@admin.register(Proveedor)
class ProveedorAdmin(ModelAdmin):
    list_display = ("nombre", "contacto", "telefono", "tiempo_reposicion_dias", "activo")
    list_filter = ("activo",)
    search_fields = ("nombre", "contacto")
    list_editable = ("activo",)


@admin.register(Producto)
class ProductoAdmin(ModelAdmin):
    list_display = ("nombre", "marca", "estado", "destacado", "es_bordado", "stock_total", "precio_min")
    list_filter = ("estado", "destacado", "es_bordado", "categorias", "marca")
    search_fields = ("nombre", "marca", "etiquetas")
    prepopulated_fields = {"slug": ("nombre",)}
    filter_horizontal = ("categorias",)
    list_editable = ("estado", "destacado")
    inlines = (FotoInline, VarianteInline)
    change_list_template = "admin/catalog/producto/change_list.html"
    fieldsets = (
        ("Producto", {
            "fields": ("nombre", "slug", "estado", "destacado", "es_bordado"),
        }),
        ("Descripción", {
            "fields": ("descripcion_corta", "descripcion_larga", "cuidado"),
        }),
        ("Clasificación", {
            "fields": ("categorias", "marca", "proveedor", "etiquetas"),
        }),
        ("Composición", {
            "fields": ("material", "composicion"),
        }),
        ("SEO", {
            "fields": ("meta_titulo", "meta_descripcion"),
            "classes": ("collapse",),
        }),
    )

    @admin.display(description="Stock")
    def stock_total(self, obj):
        return obj.stock_disponible

    @admin.display(description="Desde")
    def precio_min(self, obj):
        precio = obj.precio_minimo
        return precio if precio is not None else "—"

    # ---------- Importar / exportar CSV ----------
    def get_urls(self):
        urls = super().get_urls()
        propias = [
            path(
                "csv/",
                self.admin_site.admin_view(self.vista_csv),
                name="catalog_producto_csv",
            ),
            path(
                "csv/exportar/",
                self.admin_site.admin_view(self.vista_exportar_csv),
                name="catalog_producto_csv_exportar",
            ),
            path(
                "csv/plantilla/",
                self.admin_site.admin_view(self.vista_plantilla_csv),
                name="catalog_producto_csv_plantilla",
            ),
        ]
        return propias + urls

    def vista_csv(self, request):
        """Página de importación: sube el archivo y muestra los errores por fila."""
        from django.contrib import messages

        contexto = {"titulo": "Importar catálogo desde CSV"}
        if request.method == "POST":
            archivo = request.FILES.get("archivo")
            if not archivo:
                messages.error(request, "Elige un archivo CSV primero.")
            else:
                resultado = csv_io.importar_csv(archivo.read())
                if resultado["errores"]:
                    messages.warning(
                        request,
                        f"El archivo tiene {len(resultado['errores'])} error(es); "
                        "no se importó nada. Corrige las filas marcadas.",
                    )
                    contexto["errores"] = resultado["errores"]
                else:
                    messages.success(
                        request,
                        f"Listo: {resultado['creados']} producto(s) nuevo(s) y "
                        f"{resultado['actualizados']} variante(s) actualizada(s).",
                    )
                    return HttpResponseRedirect(
                        reverse("admin:catalog_producto_changelist")
                    )
        return render(
            request, "admin/catalog/producto/csv_form.html", contexto
        )

    def vista_exportar_csv(self, request):
        respuesta = HttpResponse(
            csv_io.exportar_csv(), content_type="text/csv; charset=utf-8",
        )
        respuesta["Content-Disposition"] = 'attachment; filename="catalogo.csv"'
        return respuesta

    def vista_plantilla_csv(self, request):
        respuesta = HttpResponse(
            csv_io.plantilla_csv(), content_type="text/csv; charset=utf-8",
        )
        respuesta["Content-Disposition"] = (
            'attachment; filename="plantilla_catalogo.csv"'
        )
        return respuesta


@admin.register(Resena)
class ResenaAdmin(ModelAdmin):
    list_display = ("producto", "nombre", "calificacion_estrellas", "verificada", "aprobada", "creada")
    list_filter = ("aprobada", "verificada", "calificacion")
    search_fields = ("nombre", "comentario", "producto__nombre")
    list_editable = ("aprobada",)

    @admin.display(description="Estrellas")
    def calificacion_estrellas(self, obj):
        return "★" * obj.calificacion + "☆" * (5 - obj.calificacion)


@admin.register(Sinonimo)
class SinonimoAdmin(ModelAdmin):
    list_display = ("palabras", "activo")
    list_editable = ("activo",)


@admin.register(BusquedaSinResultados)
class BusquedaSinResultadosAdmin(ModelAdmin):
    list_display = ("consulta", "fecha", "revisada")
    list_filter = ("revisada",)
    search_fields = ("consulta",)
    list_editable = ("revisada",)
    actions = ["marcar_revisadas"]

    @admin.action(description="Marcar seleccionadas como revisadas")
    def marcar_revisadas(self, request, queryset):
        queryset.update(revisada=True)


class ComboItemInline(TabularInline):
    model = ComboItem
    extra = 1
    autocomplete_fields = ("producto",)


@admin.register(Combo)
class ComboAdmin(ModelAdmin):
    list_display = ("nombre", "precio_combo", "ahorro", "activo", "orden")
    list_filter = ("activo",)
    search_fields = ("nombre",)
    prepopulated_fields = {"slug": ("nombre",)}
    list_editable = ("activo", "orden")
    inlines = (ComboItemInline,)

    @admin.display(description="Ahorro")
    def ahorro(self, obj):
        pct = obj.ahorro_pct
        return f"-{pct}%" if pct else "—"
