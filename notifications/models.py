"""Modelos de notificaciones: plantillas de correo de marca editables."""
from django.db import models


class PlantillaCorreo(models.Model):
    """Plantilla de correo de marca editable desde el panel de administración."""

    PLANTILLAS = [
        ("confirmacion_pedido", "Confirmación de pedido al cliente"),
        ("cambio_estado_pedido", "Cambio de estado del pedido"),
        ("aviso_interno_pedido", "Aviso interno de pedido nuevo a la tienda"),
        ("carrito_abandonado", "Recordatorio de carrito abandonado"),
    ]

    clave = models.CharField(
        "tipo de correo", max_length=60, unique=True, choices=PLANTILLAS,
    )
    asunto = models.CharField(
        "asunto del correo", max_length=200,
        help_text="Asunto personalizado. Soporta variables del contexto.",
    )
    cuerpo = models.TextField(
        "mensaje o cuerpo personalizado", blank=True,
        help_text="Texto adicional o personalizado que se incluye en el correo.",
    )
    activo = models.BooleanField("usar personalización", default=True)
    actualizada = models.DateTimeField("actualizada el", auto_now=True)

    class Meta:
        verbose_name = "plantilla de correo"
        verbose_name_plural = "plantillas de correo"
        ordering = ["clave"]

    def __str__(self):
        return dict(self.PLANTILLAS).get(self.clave, self.clave)
