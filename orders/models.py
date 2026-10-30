"""Modelos de pedidos: Pedido, ítems e historial de estados."""
from django.db import models

from catalog.models import Variante


class Pedido(models.Model):
    """Un pedido de la tienda. Puede ser de un cliente registrado o de un invitado."""

    ESTADOS = [
        ("pendiente", "Pendiente de pago"),
        ("por_verificar", "Pago por verificar"),
        ("pagado", "Pagado"),
        ("preparacion", "En preparación"),
        ("enviado", "Enviado"),
        ("entregado", "Entregado"),
        ("cancelado", "Cancelado"),
        ("devuelto", "Devuelto / Reembolsado"),
    ]

    numero = models.CharField("número de pedido", max_length=20, unique=True)
    usuario = models.ForeignKey(
        "accounts.Usuario", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="pedidos", verbose_name="cliente",
        help_text="Vacío si la compra fue como invitado.",
    )

    # ---------- Datos de contacto (foto del momento de la compra) ----------
    nombre = models.CharField("nombre de quien recibe", max_length=120)
    email = models.EmailField("correo")
    telefono = models.CharField("celular (WhatsApp)", max_length=20)
    cedula = models.CharField("cédula", max_length=20, blank=True)
    autoriza_datos = models.BooleanField("autoriza el tratamiento de datos", default=False)
    mayor_de_edad = models.BooleanField("confirmó ser mayor de edad", default=False)

    # ---------- Entrega ----------
    municipio = models.ForeignKey(
        "shipping.MunicipioSantander", on_delete=models.PROTECT,
        related_name="pedidos", verbose_name="municipio de entrega",
    )
    zona_nombre = models.CharField("zona de envío", max_length=80, blank=True)
    direccion = models.CharField("dirección", max_length=160)
    barrio = models.CharField("barrio", max_length=80, blank=True)
    indicaciones = models.CharField("indicaciones", max_length=200, blank=True)

    # ---------- Dinero (todo congelado al confirmar) ----------
    subtotal = models.DecimalField("subtotal", max_digits=12, decimal_places=0, default=0)
    descuento_ofertas = models.DecimalField(
        "descuento de ofertas", max_digits=12, decimal_places=0, default=0
    )
    descuento_cupon = models.DecimalField(
        "descuento de cupón", max_digits=12, decimal_places=0, default=0
    )
    cupon_codigo = models.CharField("cupón aplicado", max_length=30, blank=True)
    costo_envio = models.DecimalField(
        "costo de envío", max_digits=12, decimal_places=0, default=0
    )
    total = models.DecimalField("total", max_digits=12, decimal_places=0, default=0)

    # ---------- Estado y pago ----------
    estado = models.CharField(
        "estado", max_length=20, choices=ESTADOS, default="pendiente"
    )
    metodo_pago = models.CharField(
        "método de pago", max_length=30,
        choices=[("pasarela", "Pasarela en línea"),
                 ("contraentrega", "Contraentrega"),
                 ("transferencia", "Transferencia / Nequi / Daviplata")],
        default="contraentrega",
    )
    notas = models.CharField(
        "notas internas", max_length=300, blank=True,
        help_text="Solo para el equipo; no se muestran al cliente.",
    )

    # ---------- Reserva de stock ----------
    # El stock se descuenta al confirmar y queda reservado hasta esta fecha.
    # Si no se paga a tiempo, cancel_expired_orders cancela y devuelve el stock.
    reserva_hasta = models.DateTimeField(
        "reserva de stock hasta", null=True, blank=True,
        help_text="Vacío cuando el pedido no espera pago (contraentrega).",
    )
    stock_devuelto = models.BooleanField("stock devuelto", default=False)

    creado = models.DateTimeField("creado el", auto_now_add=True)
    actualizado = models.DateTimeField("actualizado el", auto_now=True)

    class Meta:
        verbose_name = "pedido"
        verbose_name_plural = "pedidos"
        ordering = ["-creado"]

    def __str__(self):
        return f"{self.numero} — {self.nombre}"

    def save(self, *args, **kwargs):
        if not self.numero:
            self.numero = self._generar_numero()
        super().save(*args, **kwargs)

    @staticmethod
    def _generar_numero():
        """Número único tipo CB-004832 (difícil de adivinar)."""
        import secrets

        while True:
            numero = f"CB-{secrets.randbelow(10 ** 6):06d}"
            if not Pedido.objects.filter(numero=numero).exists():
                return numero

    @property
    def total_descuentos(self):
        return self.descuento_ofertas + self.descuento_cupon

    @property
    def tiene_envio(self):
        return self.costo_envio > 0

    @property
    def estado_label(self):
        return dict(self.ESTADOS).get(self.estado, self.estado)


class ItemPedido(models.Model):
    """Un producto dentro de un pedido, con los precios congelados al confirmar."""

    pedido = models.ForeignKey(
        Pedido, on_delete=models.CASCADE, related_name="items", verbose_name="pedido"
    )
    variante = models.ForeignKey(
        Variante, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="items_pedido", verbose_name="variante",
    )
    # Fotografías del producto en el momento de la compra
    producto_nombre = models.CharField("producto", max_length=200)
    variante_label = models.CharField("talla y color", max_length=120, blank=True)
    sku = models.CharField("referencia (SKU)", max_length=40)

    cantidad = models.PositiveIntegerField("cantidad", default=1)
    precio_unitario = models.DecimalField(
        "precio unitario", max_digits=12, decimal_places=0
    )
    precio_base = models.DecimalField(
        "precio sin ofertas", max_digits=12, decimal_places=0, default=0
    )
    descuento = models.DecimalField(
        "descuento", max_digits=12, decimal_places=0, default=0
    )

    class Meta:
        verbose_name = "ítem del pedido"
        verbose_name_plural = "ítems del pedido"

    def __str__(self):
        return f"{self.cantidad} x {self.producto_nombre}"

    @property
    def subtotal(self):
        return self.precio_unitario * self.cantidad - self.descuento


class HistorialPedido(models.Model):
    """Cambio de estado de un pedido, con fecha y quién lo hizo."""

    pedido = models.ForeignKey(
        Pedido, on_delete=models.CASCADE, related_name="historial", verbose_name="pedido"
    )
    estado = models.CharField("estado", max_length=20, choices=Pedido.ESTADOS)
    nota = models.CharField("nota", max_length=200, blank=True)
    usuario = models.ForeignKey(
        "accounts.Usuario", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="cambios_pedido", verbose_name="usuario",
    )
    creado = models.DateTimeField("creado el", auto_now_add=True)

    class Meta:
        verbose_name = "historial del pedido"
        verbose_name_plural = "historial de pedidos"
        ordering = ["creado"]

    def __str__(self):
        return f"{self.pedido.numero}: {self.get_estado_display()}"
