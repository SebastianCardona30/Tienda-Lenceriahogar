"""Modelos de envíos: zonas configurables y municipios de Santander.

Solo se envía al departamento de Santander (regla del negocio).
Las zonas se crean con valores de ejemplo desde seed_demo y se editan
en el panel de administración sin tocar código.
"""
from django.core.validators import MinValueValidator
from django.db import models


class ZonaEnvio(models.Model):
    """Zona de envío con su tarifa, tiempo estimado y umbral de envío gratis."""

    nombre = models.CharField("nombre", max_length=80, unique=True)
    descripcion = models.CharField(
        "descripción", max_length=200, blank=True,
        help_text="Ej.: Entrega propia con mensajero de la tienda.",
    )
    tarifa = models.DecimalField(
        "tarifa ($ COP)", max_digits=12, decimal_places=0,
        validators=[MinValueValidator(0)],
    )
    envio_gratis_desde = models.DecimalField(
        "envío gratis desde ($ COP)", max_digits=12, decimal_places=0,
        null=True, blank=True, validators=[MinValueValidator(0)],
        help_text="Vacío = nunca hay envío gratis en esta zona.",
    )
    tiempo_estimado = models.CharField(
        "tiempo estimado", max_length=80, default="1 a 2 días hábiles",
        help_text="Texto visible para el cliente. Ej.: 'Mismo día en Bucaramanga'.",
    )
    recogida_disponible = models.BooleanField(
        "permite recoger en punto", default=True,
        help_text="El cliente puede elegir recoger en la tienda y no paga envío.",
    )
    activa = models.BooleanField("activa", default=True)
    orden = models.PositiveIntegerField("orden", default=0)

    class Meta:
        verbose_name = "zona de envío"
        verbose_name_plural = "zonas de envío"
        ordering = ["orden", "nombre"]

    def __str__(self):
        return f"{self.nombre} (${int(self.tarifa):,})".replace(",", ".")

    def cobertura(self, subtotal):
        """Devuelve (costo_envio, falta_para_gratis, gratis) según el subtotal."""
        if self.envio_gratis_desde is not None and subtotal >= self.envio_gratis_desde:
            return 0, 0, True
        falta = None
        if self.envio_gratis_desde is not None:
            falta = self.envio_gratis_desde - subtotal
        return self.tarifa, falta, False


class MunicipioSantander(models.Model):
    """Municipio de Santander asignado a una zona de envío."""

    nombre = models.CharField("nombre", max_length=80, unique=True)
    slug = models.SlugField("slug", max_length=90, unique=True, blank=True)
    zona = models.ForeignKey(
        ZonaEnvio, on_delete=models.PROTECT, related_name="municipios",
        verbose_name="zona de envío", null=True, blank=True,
        help_text="Sin zona asignada = no se envía a ese municipio todavía.",
    )

    class Meta:
        verbose_name = "municipio de Santander"
        verbose_name_plural = "municipios de Santander"
        ordering = ["nombre"]

    def __str__(self):
        return self.nombre

    def save(self, *args, **kwargs):
        from django.utils.text import slugify

        if not self.slug:
            self.slug = slugify(self.nombre)[:90] or "municipio"
        super().save(*args, **kwargs)


def zona_para_municipio(nombre_municipio):
    """Busca la zona de un municipio por nombre (insensible a tildes/mayúsculas)."""
    from catalog.search import normalizar_texto

    objetivo = normalizar_texto(nombre_municipio)
    for m in MunicipioSantander.objects.select_related("zona").filter(zona__isnull=False):
        if normalizar_texto(m.nombre) == objetivo:
            return m.zona
    return None
