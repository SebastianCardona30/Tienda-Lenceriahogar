from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.translation import gettext_lazy as _
from unfold.admin import ModelAdmin as UnfoldModelAdmin

from accounts.models import Deseo, Direccion, Usuario


@admin.register(Usuario)
class UsuarioAdmin(UnfoldModelAdmin, UserAdmin):
    list_display = ("username", "email", "first_name", "last_name", "telefono", "is_active")
    search_fields = ("username", "email", "first_name", "last_name", "telefono")
    ordering = ("username",)

    fieldsets = (
        (None, {"fields": ("username", "password")}),
        (_("Información personal"), {"fields": ("first_name", "last_name", "email", "telefono", "cedula")}),
        (_("Permisos"), {
            "fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions"),
            "classes": ("collapse",),
        }),
        (_("Fechas importantes"), {
            "fields": ("last_login", "date_joined"),
            "classes": ("collapse",),
        }),
    )

    add_fieldsets = (
        (None, {
            "classes": ("wide",),
            "fields": ("username", "email", "password1", "password2"),
        }),
    )


@admin.register(Direccion)
class DireccionAdmin(UnfoldModelAdmin):
    list_display = ("destinatario", "usuario", "municipio", "barrio", "predeterminada")
    list_filter = ("municipio", "predeterminada")
    search_fields = ("destinatario", "direccion", "usuario__username", "usuario__email")
    list_editable = ("predeterminada",)


@admin.register(Deseo)
class DeseoAdmin(UnfoldModelAdmin):
    list_display = ("usuario", "producto", "creado")
    list_filter = ("creado",)
    search_fields = ("usuario__username", "usuario__email", "producto__nombre")
