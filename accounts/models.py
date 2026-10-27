from django.contrib.auth.models import AbstractUser
from django.db import models


class Usuario(AbstractUser):
    """Usuario de la tienda (cliente o administrador)."""

    telefono = models.CharField("celular (WhatsApp)", max_length=20, blank=True)
    cedula = models.CharField("cédula", max_length=20, blank=True)

    class Meta:
        verbose_name = "usuario"
        verbose_name_plural = "usuarios"

    def __str__(self):
        return self.get_full_name() or self.username
