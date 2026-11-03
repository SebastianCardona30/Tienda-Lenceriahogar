"""Comando manage.py setup_roles para crear los grupos y permisos de los 3 roles."""
from django.core.management.base import BaseCommand

from accounts.roles import configurar_roles


class Command(BaseCommand):
    help = "Crea o actualiza los 3 roles de administración: Administradora, Empleado y Solo lectura."

    def handle(self, *args, **options):
        grupos = configurar_roles()
        for nombre, grupo in grupos.items():
            total = grupo.permissions.count()
            self.stdout.write(
                self.style.SUCCESS(f"OK: Rol '{nombre}' configurado con {total} permisos.")
            )
