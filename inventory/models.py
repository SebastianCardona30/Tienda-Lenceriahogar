"""Inventario: bitácora de movimientos de stock y órdenes de compra.

Todo movimiento deja registro con motivo (venta, devolución, orden de compra,
ajuste…) para poder explicar cualquier diferencia de stock.
"""
from django.conf import settings
from django.db import models

from catalog.models import Proveedor, Variante


class MovimientoStock(models.Model):
    """Un cambio de stock de una variante, con su motivo y resultado."""

    MOTIVOS = [
        ("venta", "Venta"),
        ("devolucion", "Devolución de cliente"),
        ("orden", "Orden de compra recibida"),
        ("ajuste", "Ajuste manual"),
        ("merma", "Merma / daño"),
        ("correccion", "Corrección"),
    ]

    variante = models.ForeignKey(
        Variante, on_delete=models.PROTECT, related_name="movimientos",
        verbose_name="variante",
    )
    # Positivo suma stock, negativo resta
    cantidad = models.IntegerField("cantidad")
    stock_resultante = models.IntegerField(
        "stock después", help_text="Cómo quedó el stock tras este movimiento."
    )
    motivo = models.CharField("motivo", max_length=20, choices=MOTIVOS)
    referencia = models.CharField(
        "referencia", max_length=40, blank=True,
        help_text="N.° de pedido u orden de compra.",
    )
    nota = models.CharField("nota", max_length=200, blank=True)
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="movimientos_stock", verbose_name="usuario",
    )
    creado = models.DateTimeField("creado el", auto_now_add=True)

    class Meta:
        verbose_name = "movimiento de stock"
        verbose_name_plural = "movimientos de stock"
        ordering = ["-creado"]

    def __str__(self):
        signo = "+" if self.cantidad > 0 else ""
        return f"{signo}{self.cantidad} {self.variante.sku} · {self.get_motivo_display()}"


class OrdenCompra(models.Model):
    """Orden de compra simple a un proveedor (mercancía nueva)."""

    ESTADOS = [
        ("borrador", "Borrador"),
        ("enviada", "Enviada al proveedor"),
        ("recibida", "Recibida"),
        ("cancelada", "Cancelada"),
    ]

    numero = models.CharField("número", max_length=20, unique=True, blank=True)
    proveedor = models.ForeignKey(
        Proveedor, on_delete=models.PROTECT, related_name="ordenes_compra",
        verbose_name="proveedor",
    )
    estado = models.CharField("estado", max_length=20, choices=ESTADOS, default="borrador")
    notas = models.TextField("notas", blank=True)
    creada_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="ordenes_compra", verbose_name="creada por",
    )
    creada = models.DateTimeField("creada el", auto_now_add=True)
    recibida = models.DateTimeField("recibida el", null=True, blank=True)

    class Meta:
        verbose_name = "orden de compra"
        verbose_name_plural = "órdenes de compra"
        ordering = ["-creada"]

    def __str__(self):
        return f"{self.numero} · {self.proveedor.nombre}"

    def save(self, *args, **kwargs):
        if not self.numero:
            n = OrdenCompra.objects.count() + 1
            while OrdenCompra.objects.filter(numero=f"OC-{n:05d}").exists():
                n += 1
            self.numero = f"OC-{n:05d}"
        super().save(*args, **kwargs)

    @property
    def total(self):
        """Suma de las líneas (cantidad × costo unitario)."""
        return sum((i.cantidad * i.costo_unitario for i in self.items.all()), 0)


class OrdenCompraItem(models.Model):
    """Una línea de la orden: variante, cantidad y costo acordado."""

    orden = models.ForeignKey(
        OrdenCompra, on_delete=models.CASCADE, related_name="items",
        verbose_name="orden",
    )
    variante = models.ForeignKey(
        Variante, on_delete=models.PROTECT, related_name="ordenes_compra",
        verbose_name="variante",
    )
    cantidad = models.PositiveIntegerField("cantidad")
    costo_unitario = models.DecimalField(
        "costo unitario", max_digits=12, decimal_places=0,
        help_text="Costo que cobra el proveedor (sin IVA si aplica).",
    )

    class Meta:
        verbose_name = "línea de la orden"
        verbose_name_plural = "líneas de la orden"

    def __str__(self):
        return f"{self.cantidad} x {self.variante.sku}"

    @property
    def subtotal(self):
        return self.cantidad * self.costo_unitario
