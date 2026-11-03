"""Comando manage.py backup_db para respaldar la base de datos y la carpeta media/."""
import shutil
from datetime import datetime
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Copia la base de datos SQLite y la carpeta media/ a un directorio fechado."

    def add_arguments(self, parser):
        parser.add_argument(
            "--destino",
            type=str,
            default=None,
            help="Carpeta donde se guardará la copia (por defecto backups/ en la raíz del proyecto).",
        )

    def handle(self, *args, **options):
        base_dir = settings.BASE_DIR
        ahora = datetime.now().strftime("%Y%m%d_%H%M%S")
        nombre_carpeta = f"backup_{ahora}"

        if options["destino"]:
            carpeta_destino = Path(options["destino"]) / nombre_carpeta
        else:
            carpeta_destino = base_dir / "backups" / nombre_carpeta

        carpeta_destino.mkdir(parents=True, exist_ok=True)

        self.stdout.write(f"Iniciando respaldo en: {carpeta_destino}")

        # 1. Copiar base de datos SQLite
        db_path = Path(settings.DATABASES["default"]["NAME"])
        if db_path.exists():
            destino_db = carpeta_destino / db_path.name
            shutil.copy2(db_path, destino_db)
            self.stdout.write(f"OK: Base de datos respaldada ({db_path.name})")

            # Respaldar también -wal y -shm si existen (modo WAL de SQLite)
            for sufijo in ("-wal", "-shm"):
                wal_path = Path(str(db_path) + sufijo)
                if wal_path.exists():
                    shutil.copy2(wal_path, carpeta_destino / wal_path.name)
        else:
            self.stdout.write(
                self.style.WARNING(f"Aviso: Archivo de BD no encontrado en {db_path}")
            )

        # 2. Copiar carpeta media/ (imágenes de catálogo y comprobantes)
        media_root = Path(settings.MEDIA_ROOT)
        if media_root.exists() and any(media_root.iterdir()):
            destino_media = carpeta_destino / "media"
            shutil.copytree(media_root, destino_media, dirs_exist_ok=True)
            total_archivos = sum(1 for _ in destino_media.rglob("*") if _.is_file())
            self.stdout.write(f"OK: Carpeta media/ respaldada ({total_archivos} archivo(s))")
        else:
            self.stdout.write("Aviso: Carpeta media/ vacía o no existe.")

        self.stdout.write(
            self.style.SUCCESS(
                f"\nListo: Respaldo completado exitosamente en:\n{carpeta_destino.resolve()}"
            )
        )
