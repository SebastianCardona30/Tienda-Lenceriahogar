"""
Construcción para Vercel.

Vercel ejecuta este script automáticamente durante el despliegue
(después de instalar dependencias y antes de publicar), gracias a la
sección [tool.vercel.scripts] de pyproject.toml.

Qué hace:
1. Migra y carga los datos demo en una base SQLite que viaja "horneada"
   en el despliegue (Vercel no tiene disco persistente gratis).
2. Recopila los estáticos (whitenoise los sirve desde la función).
3. Copia media/ a public/ para que las imágenes las sirva el CDN de Vercel.
"""
import os
import shutil
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

# Variables mínimas para la construcción (en Vercel no hay .env)
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
os.environ.setdefault("SECRET_KEY", "clave-temporal-solo-de-construccion")
os.environ.setdefault("DEBUG", "False")

import django  # noqa: E402
from django.core.management import call_command  # noqa: E402


def main():
    if "CI" not in os.environ:
        # Aviso amable cuando alguien lo corre en su máquina
        print("Aviso: build.py es para el despliegue en Vercel.")
        print("En local usa 'iniciar.bat' o 'manage.py runserver'.\n")

    django.setup()

    print("==> Creando/migrando la base de datos (datos demo horneados)")
    call_command("migrate", interactive=False, verbosity=1)

    print("==> Cargando datos demo (idempotente: no duplica)")
    call_command("seed_demo")

    print("==> Recopilando archivos estaticos (whitenoise)")
    call_command("collectstatic", interactive=False, verbosity=1)

    # Las imágenes subidas (media/) se copian a public/ para que Vercel
    # las sirva directamente desde su CDN sin invocar la función.
    origen = BASE_DIR / "media"
    destino = BASE_DIR / "public" / "media"
    if destino.exists():
        shutil.rmtree(destino)
    if origen.exists():
        shutil.copytree(origen, destino)
        print(f"==> Imagenes copiadas a public/media ({sum(1 for _ in destino.rglob('*'))} archivos)")

    print("==> Listo para publicar en Vercel")
    return 0


if __name__ == "__main__":
    sys.exit(main())
