"""Correos de marca de la tienda.

Plantillas HTML + texto plano con la identidad del negocio. En desarrollo el
correo va a la consola (EMAIL_BACKEND); en producción, al SMTP opcional del .env.

Regla: un correo nunca rompe una compra — se envía en transaction.on_commit y
con fail_silently.
"""
import logging

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string

from core.models import SiteConfig

logger = logging.getLogger(__name__)


def _enviar(para, asunto, plantilla, contexto):
    """Envía un correo de marca (HTML + texto). Devuelve True si salió."""
    if not para:
        return False
    contexto = {"site": SiteConfig.get(), "site_url": settings.SITE_URL, **contexto}
    asunto_completo = f"{asunto} · {contexto['site'].nombre_negocio}"
    try:
        texto = render_to_string(f"email/{plantilla}.txt", contexto)
        html = render_to_string(f"email/{plantilla}.html", contexto)
    except Exception:
        logger.exception("Falta la plantilla de correo %s", plantilla)
        return False
    mensaje = EmailMultiAlternatives(
        asunto_completo, texto, settings.DEFAULT_FROM_EMAIL, [para],
    )
    mensaje.attach_alternative(html, "text/html")
    return bool(mensaje.send(fail_silently=True))


# ---------- Pedidos ----------

def confirmacion_pedido(pedido):
    """Al cliente: «recibimos tu pedido» con resumen y siguiente paso."""
    return _enviar(
        pedido.email,
        f"Pedido {pedido.numero} confirmado",
        "confirmacion_pedido",
        {"pedido": pedido, "items": pedido.items.all()},
    )


def cambio_estado_pedido(pedido):
    """Al cliente: aviso cuando su pedido cambia a un estado que le importa."""
    if pedido.estado not in ("pagado", "enviado", "cancelado", "devuelto"):
        return False
    return _enviar(
        pedido.email,
        f"Tu pedido {pedido.numero}: {pedido.get_estado_display().lower()}",
        "cambio_estado_pedido",
        {"pedido": pedido, "items": pedido.items.all()},
    )


def aviso_interno_pedido(pedido):
    """Al negocio (email_contacto): aviso de pedido nuevo con resumen.

    Incluye un enlace de WhatsApp con el mensaje armado, para que el equipo
    pueda confirmarlo al cliente sin costo (la analítica no es necesaria).
    """
    config = SiteConfig.get()
    if not config.email_contacto:
        return False
    return _enviar(
        config.email_contacto,
        f"Nuevo pedido {pedido.numero}",
        "aviso_interno_pedido",
        {"pedido": pedido, "items": pedido.items.all()},
    )


# ---------- Carrito abandonado ----------

def carrito_abandonado(usuario, lineas, total):
    """Recordatorio amable a quien dejó productos en el carrito sin comprar.

    lineas: lista de {"nombre", "cantidad", "precio"}.
    """
    return _enviar(
        usuario.email,
        "Te faltan unos clics para tu pedido",
        "carrito_abandonado",
        {"usuario": usuario, "lineas": lineas, "total": total},
    )
