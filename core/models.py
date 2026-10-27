from django.db import models


class SiteConfig(models.Model):
    """
    Configuración general del negocio (singleton con pk=1).

    Todos los datos sensibles o legales se dejan como marcadores
    configurables: el agente nunca inventa NIT, direcciones ni teléfonos.
    """

    # Identidad
    nombre_negocio = models.CharField(
        "nombre del negocio", max_length=120, default="Lencería de Hogar Ciudad Bonita"
    )
    lema = models.CharField(
        "lema", max_length=160, blank=True,
        help_text="Frase corta que aparece en el encabezado o el pie.",
    )
    logo = models.ImageField("logo", upload_to="config/", blank=True, help_text="PNG o SVG.")

    # Contacto (marcadores configurables)
    ciudad = models.CharField("ciudad y departamento", max_length=80, default="Bucaramanga, Santander")
    whatsapp = models.CharField(
        "WhatsApp", max_length=20, blank=True,
        help_text="Solo dígitos con código de país. Ejemplo: 573001112233",
    )
    telefono = models.CharField("teléfono", max_length=20, blank=True)
    email_contacto = models.EmailField("correo de contacto", blank=True)
    nit = models.CharField("NIT", max_length=20, blank=True, help_text="Dejar en blanco si aún no se tiene.")
    direccion = models.CharField("dirección", max_length=160, blank=True)
    horario = models.CharField(
        "horario de atención", max_length=120, blank=True,
        help_text="Ejemplo: Lunes a sábado de 9:00 a.m. a 7:00 p.m.",
    )

    # Barra superior de promociones
    banner_promo_activo = models.BooleanField("mostrar banner de promoción", default=True)
    banner_promo_texto = models.CharField(
        "texto de promoción", max_length=160,
        default="Envíos en todo Santander · Pagos con Nequi, PSE y contraentrega",
    )

    # Ofertas de la semana (cuenta regresiva del inicio)
    ofertas_hasta = models.DateTimeField(
        "ofertas de la semana hasta", null=True, blank=True,
        help_text="Fecha y hora en que termina la cuenta regresiva de ofertas del inicio. "
                  "Si está vacía, no se muestra la sección.",
    )

    # Impuestos y moneda
    iva_incluido = models.BooleanField(
        "precios con IVA incluido", default=True,
        help_text="Si se desactiva, el IVA se calcula aparte en el checkout.",
    )
    iva_tasa = models.DecimalField(
        "tasa de IVA (%)", max_digits=5, decimal_places=2, default=19.00,
    )

    # Redes sociales (opcionales)
    instagram = models.URLField("Instagram", blank=True)
    facebook = models.URLField("Facebook", blank=True)
    tiktok = models.URLField("TikTok", blank=True)

    class Meta:
        verbose_name = "configuración del negocio"
        verbose_name_plural = "configuración del negocio"

    def __str__(self):
        return f"Configuración de {self.nombre_negocio}"

    def save(self, *args, **kwargs):
        # Singleton: siempre guarda en la fila pk=1.
        self.pk = 1
        super().save(*args, **kwargs)
        SiteConfig.objects.filter(pk=1).exclude(pk=self.pk).delete()

    @classmethod
    def get(cls):
        """Devuelve la configuración creándola con valores por defecto si no existe."""
        obj, _created = cls.objects.get_or_create(pk=1)
        return obj

    def delete(self, *args, **kwargs):
        # Evita borrar la configuración por accidente desde el admin.
        pass


class Suscripcion(models.Model):
    """Correos suscritos al boletín (cupón de bienvenida en Fase 2)."""

    email = models.EmailField("correo", unique=True)
    activo = models.BooleanField("activo", default=True)
    creada = models.DateTimeField("creada el", auto_now_add=True)

    class Meta:
        verbose_name = "suscripción"
        verbose_name_plural = "suscripciones al boletín"
        ordering = ["-creada"]

    def __str__(self):
        return self.email
