from django.contrib import admin
from django.contrib.admin.models import ADDITION, CHANGE, DELETION, LogEntry
from django.contrib.auth.admin import UserAdmin
from django.utils.translation import gettext_lazy as _
from unfold.admin import ModelAdmin as UnfoldModelAdmin

from accounts.models import Deseo, Direccion, Usuario
from accounts.roles import obtener_rol


@admin.register(Usuario)
class UsuarioAdmin(UnfoldModelAdmin, UserAdmin):
    list_display = (
        "username", "email", "first_name", "last_name", "telefono",
        "rol", "tiene_2fa", "is_active",
    )
    search_fields = ("username", "email", "first_name", "last_name", "telefono")
    ordering = ("username",)

    @admin.display(description="Rol")
    def rol(self, obj):
        return obtener_rol(obj) or ("Superusuario" if obj.is_superuser else "Cliente")

    @admin.display(boolean=True, description="2FA activo")
    def tiene_2fa(self, obj):
        from django_otp import user_has_device

        return user_has_device(obj)

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


@admin.register(LogEntry)
class AuditoriaAdmin(UnfoldModelAdmin):
    """Bitácora inmutable de auditoría: quién hizo qué y cuándo en el panel."""

    list_display = (
        "action_time", "user", "tipo_accion", "content_type",
        "object_repr", "change_message",
    )
    list_filter = ("action_flag", "content_type", "action_time")
    search_fields = ("object_repr", "change_message", "user__username", "user__email")
    date_hierarchy = "action_time"
    ordering = ("-action_time",)

    @admin.display(description="Acción")
    def tipo_accion(self, obj):
        if obj.action_flag == ADDITION:
            return "Creación"
        if obj.action_flag == CHANGE:
            return "Modificación"
        if obj.action_flag == DELETION:
            return "Eliminación"
        return "Acción"

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


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
