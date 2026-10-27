"""Modelos de promociones: cupones (el motor de descuentos llega en la Fase 2)."""
from django.core.validators import MinValueValidator
from django.db import models


class Cupon(models.Model):
    """Cupón de descuento con código."""

    TIPO_CHOICES = [
        ("porcentaje", "Porcentaje (%)"),
        ("valor", "Valor fijo ($ COP)"),
    ]

    codigo = models.CharField("código", max_length=30, unique=True)
    tipo = models.CharField("tipo de descuento", max_length=10, choices=TIPO_CHOICES, default="porcentaje")
    valor = models.DecimalField(
        "valor", max_digits=12, decimal_places=2,
        validators=[MinValueValidator(0)],
        help_text="Si es porcentaje: 10 = 10%. Si es valor fijo: 10000 = $10.000.",
    )
    monto_minimo = models.DecimalField(
        "monto mínimo del pedido", max_digits=12, decimal_places=0, default=0
    )
    fecha_inicio = models.DateTimeField("válido desde", null=True, blank=True)
    fecha_fin = models.DateTimeField("válido hasta", null=True, blank=True)
    max_usos = models.PositiveIntegerField(
        "límite total de usos", null=True, blank=True,
        help_text="Vacío = usos ilimitados.",
    )
    solo_primera_compra = models.BooleanField("solo primera compra", default=False)
    activo = models.BooleanField("activo", default=True)
    creada = models.DateTimeField("creado el", auto_now_add=True)

    class Meta:
        verbose_name = "cupón"
        verbose_name_plural = "cupones"
        ordering = ["-creada"]

    def __str__(self):
        return self.codigo

    def save(self, *args, **kwargs):
        self.codigo = self.codigo.upper().strip()
        super().save(*args, **kwargs)
