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
