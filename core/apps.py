from django.apps import AppConfig


class CoreConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "core"
    verbose_name = "Configuración de la tienda"

    def ready(self):
        # Activa los pragmas de SQLite (WAL) apenas se abre una conexión.
        from core import db  # noqa: F401
