"""
Ajustes de la base de datos que no se configuran con settings.

Con SQLite activamos WAL (mejor concurrencia lectura/escritura) y la
llave foránea. En PostgreSQL estos pragmas no aplican y se ignoran.
"""
from django.db.backends.signals import connection_created
from django.dispatch import receiver


@receiver(connection_created)
def activar_wal(sender, connection, **kwargs):
    """Modo WAL + foreign_keys para SQLite."""
    if connection.vendor == "sqlite":
        cursor = connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL;")
        cursor.execute("PRAGMA foreign_keys=ON;")
        cursor.close()
