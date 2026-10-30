"""Modelos de pagos: pasarela simulada, comprobantes de transferencia y Wompi."""
from django.db import models


class Pago(models.Model):
    """Intento de pago de un pedido (pasarela, transferencia o contraentrega)."""

    METODOS = [
        ("pasarela", "Pasarela en línea"),
        ("transferencia", "Transferencia / Nequi / Daviplata"),
        ("contraentrega", "Contraentrega"),
    ]
    ESTADOS = [
        ("pendiente", "Pendiente"),
        ("aprobado", "Aprobado"),
        ("rechazado", "Rechazado"),
    ]

    pedido = models.ForeignKey(
        "orders.Pedido", on_delete=models.CASCADE, related_name="pagos",
        verbose_name="pedido",
    )
    metodo = models.CharField("método", max_length=20, choices=METODOS, default="pasarela")
    monto = models.DecimalField("monto", max_digits=12, decimal_places=0)
    estado = models.CharField(
        "estado", max_length=20, choices=ESTADOS, default="pendiente"
    )
    referencia = models.CharField(
        "referencia", max_length=40, blank=True,
        help_text="Identificador devuelto por la pasarela.",
    )
    # Motivo del rechazo o datos de la respuesta (nunca datos de tarjeta)
    detalle = models.CharField("detalle", max_length=200, blank=True)
    comprobante = models.ImageField(
        "comprobante", upload_to="comprobantes/", blank=True,
        help_text="Imagen o PDF del pago (transferencia / Nequi / Daviplata).",
    )
    creado = models.DateTimeField("creado el", auto_now_add=True)
    actualizado = models.DateTimeField("actualizado el", auto_now=True)

    class Meta:
        verbose_name = "pago"
        verbose_name_plural = "pagos"
        ordering = ["-creado"]

    def __str__(self):
        return f"{self.get_metodo_display()} {self.monto} — {self.pedido.numero}"

    @property
    def comprobante_nombre(self):
        return self.comprobante.name.rsplit("/", 1)[-1] if self.comprobante else ""
