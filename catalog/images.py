"""
Utilidades de imagen con Pillow: conversión a WebP y miniaturas.

Sin servicios de pago (Cloudinary etc.): todo se guarda en disco (media/).
"""
from pathlib import Path

from PIL import Image

ANCHO_MAX = 1200      # ancho máximo de la foto principal
ANCHO_MINIATURA = 300  # ancho de la miniatura


def _a_webp(imagen, ancho_max):
    """Redimensiona y devuelve la imagen como archivo WebP en memoria."""
    if imagen.width > ancho_max:
        proporcion = ancho_max / float(imagen.width)
        imagen = imagen.resize((ancho_max, int(imagen.height * proporcion)), Image.LANCZOS)

    import io

    salida = io.BytesIO()
    imagen.save(salida, format="WEBP", quality=85)
    salida.seek(0)
    nombre = Path(imagen.filename or "foto").stem + ".webp"
    return salida, nombre


def procesar_imagen_producto(foto):
    """
    Convierte la foto recién subida a WebP (principal y miniatura).

    Se ejecuta una sola vez; si ya está procesada, no hace nada.
    """
    if not foto.imagen or foto.miniatura:
        return

    try:
        imagen = Image.open(foto.imagen.path)
    except (FileNotFoundError, OSError):
        # Imagen de marcador de posición (SVG): no se procesa con Pillow.
        return

    if imagen.mode in ("RGBA", "P", "LA"):
        imagen = imagen.convert("RGB")

    # Foto principal en WebP
    datos, nombre = _a_webp(imagen.copy(), ANCHO_MAX)
    foto.imagen.save(nombre, datos, save=False)

    # Miniatura en WebP
    datos_mini, nombre_mini = _a_webp(imagen.copy(), ANCHO_MINIATURA)
    foto.miniatura.save(nombre_mini, datos_mini, save=False)

    super(type(foto), foto).save(update_fields=["imagen", "miniatura"])
