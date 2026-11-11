"""Filtros de plantilla para formato colombiano."""
from django import template

register = template.Library()


@register.filter
def dictkey(d, clave):
    """Obtiene un valor de un diccionario: {{ conteos.tallas|dictkey:t }}."""
    if not d:
        return ""
    return d.get(clave, "")


@register.filter
def separar(texto, separador=","):
    """Divide un texto en lista: 'sábanas, queen' -> ['sábanas', 'queen']."""
    if not texto:
        return []
    return [p.strip() for p in str(texto).split(separador) if p.strip()]


@register.filter
def cop(valor):
    """
    Formato de moneda colombiana sin decimales: 89900 -> "$89.900".
    """
    try:
        n = int(round(float(valor)))
    except (TypeError, ValueError):
        return "$0"
    signo = "-" if n < 0 else ""
    return f"{signo}${abs(n):,}".replace(",", ".")


# Colores de tejido -> muestra visual (swatch) de la ficha de producto
_MUESTRAS = {
    "blanco": "#F7F4EF", "blanco nacar": "#F3EFE6", "marfil": "#EFE6D2",
    "crema": "#F1E6CE", "beige": "#DCC9A8", "natural": "#E7D9BF",
    "gris": "#B9B4BD", "gris perla": "#CFC9D2", "gris topo": "#9A8F8B",
    "negro": "#2E2A31", "azul": "#4E6E9E", "azul cielo": "#A7C7E7",
    "azul noche": "#2C3A5A", "índigo": "#4B4E8F", "indigo": "#4B4E8F",
    "verde agua": "#A8D8D0", "verde salvia": "#B7C9A8",
    "rosa": "#E9A7B8", "rosa palo": "#E7B7C2", "rosa antiguo": "#D9A0A8",
    "mostaza": "#E0A82E", "terracota": "#C96F4A", "vino": "#7B2D3B",
    "mostaza": "#E0A82E", "multicolor": "conic-gradient(#E9A7B8,#A7C7E7,#E0A82E,#A8D8D0)",
}


@register.filter
def color_hex(nombre):
    """Muestra CSS para un color: {{ color|color_hex }}."""
    clave = str(nombre or "").strip().lower()
    if clave in _MUESTRAS:
        return _MUESTRAS[clave] if "gradient" in _MUESTRAS[clave] else _MUESTRAS[clave]
    if not clave:
        return "#DDD6E0"
    # Color estable y suave derivado del nombre (para colores no listados)
    total = sum(ord(c) for c in clave)
    return f"hsl({total % 360}, 32%, 72%)"
