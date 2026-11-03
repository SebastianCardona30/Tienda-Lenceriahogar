"""Tags de plantilla del panel de administración (dashboard)."""
import json

from django import template

from dashboard import servicios

register = template.Library()


@register.inclusion_tag("dashboard/panel.html")
def dashboard_panel():
    """Renderiza el panel completo con todas las métricas del negocio.

    Se calcula solo al pintar el index del admin (sin tocar el contexto del
    AdminSite ni sobrescribir vistas).
    """
    datos = servicios.panel_completo()
    # Las gráficas reciben sus series en JSON listo para Chart.js
    datos["serie_ventas_json"] = json.dumps(datos["serie_ventas"])
    datos["estados_json"] = json.dumps([
        {"estado": e["estado"], "nombre": e["nombre"], "cantidad": e["cantidad"]}
        for e in datos["estados"]
    ])
    return datos
