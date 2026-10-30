from django.contrib.auth.models import AbstractUser
from django.db import models


class Usuario(AbstractUser):
    """Usuario de la tienda (cliente o administrador)."""

    telefono = models.CharField("celular (WhatsApp)", max_length=20, blank=True)
    cedula = models.CharField("cédula", max_length=20, blank=True)
    carrito = models.JSONField(
        "carrito guardado", default=dict, blank=True,
        help_text="Copia del carrito al cerrar sesión; se fusiona al volver a entrar.",
    )
    carrito_actualizado = models.DateTimeField(
        "carrito actualizado el", null=True, blank=True,
        help_text="Última vez que se tocó el carrito; lo usa el recordatorio "
                  "de carrito abandonado.",
    )
    aviso_carrito = models.DateTimeField(
        "aviso de carrito enviado el", null=True, blank=True,
        help_text="Evita repetir el correo de carrito abandonado.",
    )

    class Meta:
        verbose_name = "usuario"
        verbose_name_plural = "usuarios"

    def __str__(self):
        return self.get_full_name() or self.username

    @property
    def direccion_predeterminada(self):
        return self.direcciones.filter(predeterminada=True).first()

    @property
    def total_deseos(self):
        return self.deseos.count()


class Direccion(models.Model):
    """Dirección de entrega guardada por el cliente."""

    usuario = models.ForeignKey(
        Usuario, on_delete=models.CASCADE, related_name="direcciones",
        verbose_name="cliente",
    )
    destinatario = models.CharField(
        "nombre de quien recibe", max_length=120,
        help_text="Ej.: María Pérez",
    )
    municipio = models.ForeignKey(
        "shipping.MunicipioSantander", on_delete=models.PROTECT,
        related_name="direcciones", verbose_name="municipio de Santander",
    )
    barrio = models.CharField("barrio", max_length=80, blank=True)
    direccion = models.CharField(
        "dirección", max_length=160,
        help_text="Calle, número y apartamento. Ej.: Cra 15 # 42-10, apto 302",
    )
    indicaciones = models.CharField(
        "indicaciones para la entrega", max_length=200, blank=True,
        help_text="Ej.: portón negro, tocar el timbre 302.",
    )
    telefono = models.CharField("teléfono de contacto", max_length=20, blank=True)
    predeterminada = models.BooleanField("dirección predeterminada", default=False)
    creada = models.DateTimeField("creada el", auto_now_add=True)

    class Meta:
        verbose_name = "dirección"
        verbose_name_plural = "direcciones"
        ordering = ["-predeterminada", "-creada"]

    def __str__(self):
        return (
            f"{self.destinatario} — {self.direccion}, {self.barrio} "
            f"({self.municipio.nombre})"
        )

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if self.predeterminada:
            # Solo una dirección predeterminada por cliente
            (
                Direccion.objects.filter(usuario=self.usuario, predeterminada=True)
                .exclude(pk=self.pk)
                .update(predeterminada=False)
            )


class Deseo(models.Model):
    """Producto en la lista de deseos de un cliente."""

    usuario = models.ForeignKey(
        Usuario, on_delete=models.CASCADE, related_name="deseos",
        verbose_name="cliente",
    )
    producto = models.ForeignKey(
        "catalog.Producto", on_delete=models.CASCADE, related_name="deseos",
        verbose_name="producto",
    )
    creado = models.DateTimeField("agregado el", auto_now_add=True)

    class Meta:
        verbose_name = "deseo"
        verbose_name_plural = "listas de deseos"
        ordering = ["-creado"]
        constraints = [
            models.UniqueConstraint(
                fields=["usuario", "producto"], name="unico_deseo_por_usuario"
            )
        ]

    def __str__(self):
        return f"{self.usuario} ♥ {self.producto.nombre}"
