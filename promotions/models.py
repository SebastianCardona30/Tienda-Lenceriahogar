"""
Modelos de promociones y motor de descuentos.

Todo se calcula en el servidor (promotions/engine.py) y se cubre con pruebas.
Valores y fechas se editan desde el panel de administración, sin tocar código.
"""
from decimal import ROUND_HALF_UP, Decimal

from django.core.validators import MinValueValidator
from django.db import models

from catalog.models import Categoria, Producto, Variante

ENTERO = Decimal("1")


def _d(valor):
    """Convierte a Decimal redondeando a entero (la tienda usa pesos sin decimales)."""
    return Decimal(valor).quantize(ENTERO, rounding=ROUND_HALF_UP)


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
    max_usos_por_cliente = models.PositiveIntegerField(
        "límite de usos por cliente", null=True, blank=True,
        help_text="Vacío = sin límite por cliente.",
    )
    solo_primera_compra = models.BooleanField("solo primera compra", default=False)
    acumulable = models.BooleanField(
        "acumulable con otras ofertas", default=True,
        help_text="Si se desactiva, el cupón se aplica solo cuando el carrito "
                  "no tiene otras ofertas automáticas.",
    )
    categorias = models.ManyToManyField(
        Categoria, blank=True, related_name="cupones", verbose_name="categorías",
        help_text="Vacío = válido para todo el catálogo.",
    )
    es_bienvenida = models.BooleanField(
        "es cupón plantilla de bienvenida", default=False,
        help_text="Al suscribirse al boletín se genera un cupón único por "
                  "suscriptor copiando este (usos limitados a 1).",
    )
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

    @classmethod
    def crear_bienvenida(cls):
        """
        Crea un cupón único de bienvenida copiando la plantilla marcada
        como es_bienvenida. Devuelve el cupón o None si no hay plantilla.
        """
        import secrets

        plantilla = cls.objects.filter(es_bienvenida=True).order_by("id").first()
        if plantilla is None:
            return None
        while True:
            codigo = f"BIENVENIDA-{secrets.token_hex(3).upper()}"
            if not cls.objects.filter(codigo=codigo).exists():
                break
        return cls.objects.create(
            codigo=codigo,
            tipo=plantilla.tipo,
            valor=plantilla.valor,
            monto_minimo=plantilla.monto_minimo,
            acumulable=plantilla.acumulable,
            max_usos=1,
            max_usos_por_cliente=1,
            solo_primera_compra=True,
            activo=True,
        )


class UsoCupon(models.Model):
    """Registro de cada uso de un cupón (para respetar límites)."""

    cupon = models.ForeignKey(
        Cupon, on_delete=models.CASCADE, related_name="usos", verbose_name="cupón"
    )
    usuario = models.ForeignKey(
        "accounts.Usuario", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="usos_cupon", verbose_name="cliente",
    )
    email = models.EmailField("correo", blank=True)
    pedido = models.CharField("pedido", max_length=20, blank=True)
    creado = models.DateTimeField("usado el", auto_now_add=True)

    class Meta:
        verbose_name = "uso de cupón"
        verbose_name_plural = "usos de cupones"
        ordering = ["-creado"]

    def __str__(self):
        return f"{self.cupon.codigo} → {self.email or self.usuario or 'invitado'}"


class Descuento(models.Model):
    """Descuento directo por producto, variante o categoría (con fechas)."""

    OBJETOS = [
        ("producto", "Producto"),
        ("variante", "Variante"),
        ("categoria", "Categoría"),
    ]
    TIPOS = [
        ("porcentaje", "Porcentaje (%)"),
        ("valor", "Valor fijo ($ COP) por unidad"),
    ]

    nombre = models.CharField("nombre", max_length=80, help_text="Visible en el admin. Ej.: Rebajas de sábanas.")
    tipo = models.CharField("tipo", max_length=10, choices=TIPOS, default="porcentaje")
    valor = models.DecimalField(
        "valor", max_digits=12, decimal_places=2, validators=[MinValueValidator(0)]
    )
    sobre = models.CharField("aplica a", max_length=10, choices=OBJETOS)
    producto = models.ForeignKey(
        Producto, on_delete=models.CASCADE, null=True, blank=True,
        related_name="descuentos", verbose_name="producto",
    )
    variante = models.ForeignKey(
        Variante, on_delete=models.CASCADE, null=True, blank=True,
        related_name="descuentos", verbose_name="variante",
    )
    categoria = models.ForeignKey(
        Categoria, on_delete=models.CASCADE, null=True, blank=True,
        related_name="descuentos", verbose_name="categoría",
    )
    fecha_inicio = models.DateTimeField("desde", null=True, blank=True)
    fecha_fin = models.DateTimeField("hasta", null=True, blank=True)
    activo = models.BooleanField("activo", default=True)

    class Meta:
        verbose_name = "descuento"
        verbose_name_plural = "descuentos"
        ordering = ["-activo", "nombre"]

    def __str__(self):
        return self.nombre

    def clean(self):
        from django.core.exceptions import ValidationError

        esperado = {"producto": self.producto, "variante": self.variante,
                    "categoria": self.categoria}.get(self.sobre)
        otros = [v for k, v in (("producto", self.producto), ("variante", self.variante),
                                ("categoria", self.categoria)) if k != self.sobre and v]
        if not esperado:
            raise ValidationError({"sobre": "Selecciona el objetivo del descuento."})
        if otros:
            raise ValidationError("Deja en blanco los otros objetivos; solo aplica el elegido.")

    def vigente(self, ahora=None):
        from django.utils import timezone

        if not self.activo:
            return False
        ahora = ahora or timezone.now()
        if self.fecha_inicio and ahora < self.fecha_inicio:
            return False
        if self.fecha_fin and ahora > self.fecha_fin:
            return False
        return True

    def aplica_a(self, variante):
        if self.sobre == "variante":
            return self.variante_id == variante.id
        if self.sobre == "producto":
            return self.producto_id == variante.producto_id
        return variante.producto.categorias.filter(pk=self.categoria_id).exists()


class PromoUnidades(models.Model):
    """Promo 'llerva X paga Y': 2x1, 3x2 o personalizada, por producto o categoría."""

    OBJETOS = [
        ("producto", "Producto"),
        ("categoria", "Categoría"),
    ]

    nombre = models.CharField("nombre", max_length=80, help_text="Ej.: Sábanas 2x1.")
    producto = models.ForeignKey(
        Producto, on_delete=models.CASCADE, null=True, blank=True,
        related_name="promos_unidades", verbose_name="producto",
    )
    categoria = models.ForeignKey(
        Categoria, on_delete=models.CASCADE, null=True, blank=True,
        related_name="promos_unidades", verbose_name="categoría",
    )
    llevar = models.PositiveIntegerField("llevar", default=2, validators=[MinValueValidator(2)])
    pagar = models.PositiveIntegerField("pagar", default=1, validators=[MinValueValidator(1)])
    fecha_inicio = models.DateTimeField("desde", null=True, blank=True)
    fecha_fin = models.DateTimeField("hasta", null=True, blank=True)
    activo = models.BooleanField("activo", default=True)

    class Meta:
        verbose_name = "promo por unidades (2x1, 3x2)"
        verbose_name_plural = "promos por unidades (2x1, 3x2)"
        ordering = ["-activo", "nombre"]

    def __str__(self):
        return self.nombre

    def clean(self):
        from django.core.exceptions import ValidationError

        if self.producto and self.categoria:
            raise ValidationError("Elige producto O categoría, no ambos.")
        if not self.producto and not self.categoria:
            raise ValidationError("Elige un producto o una categoría.")
        if self.pagar >= self.llevar:
            raise ValidationError({"pagar": "Debe ser menor que 'llevar' (sino no hay descuento)."})

    def vigente(self, ahora=None):
        from django.utils import timezone

        if not self.activo:
            return False
        ahora = ahora or timezone.now()
        if self.fecha_inicio and ahora < self.fecha_inicio:
            return False
        if self.fecha_fin and ahora > self.fecha_fin:
            return False
        return True

    def aplica_a(self, variante):
        if self.producto_id:
            return self.producto_id == variante.producto_id
        return variante.producto.categorias.filter(pk=self.categoria_id).exists()

    @property
    def etiqueta(self):
        return f"Lleva {self.llevar} paga {self.pagar}"


class PromoVolumen(models.Model):
    """Descuento por llevar cierta cantidad (ej.: 3 o más → 10% o $10.000 menos)."""

    OBJETOS = [
        ("producto", "Producto"),
        ("categoria", "Categoría"),
    ]
    TIPOS = [
        ("porcentaje", "Porcentaje (%)"),
        ("valor", "Valor fijo ($ COP) por línea"),
    ]

    nombre = models.CharField("nombre", max_length=80, help_text="Ej.: 3 toallas con descuento.")
    tipo = models.CharField("tipo", max_length=10, choices=TIPOS, default="porcentaje")
    valor = models.DecimalField(
        "valor", max_digits=12, decimal_places=2, validators=[MinValueValidator(0)]
    )
    cantidad_minima = models.PositiveIntegerField(
        "cantidad mínima", default=3, validators=[MinValueValidator(2)]
    )
    producto = models.ForeignKey(
        Producto, on_delete=models.CASCADE, null=True, blank=True,
        related_name="promos_volumen", verbose_name="producto",
    )
    categoria = models.ForeignKey(
        Categoria, on_delete=models.CASCADE, null=True, blank=True,
        related_name="promos_volumen", verbose_name="categoría",
    )
    fecha_inicio = models.DateTimeField("desde", null=True, blank=True)
    fecha_fin = models.DateTimeField("hasta", null=True, blank=True)
    activo = models.BooleanField("activo", default=True)

    class Meta:
        verbose_name = "descuento por volumen"
        verbose_name_plural = "descuentos por volumen"
        ordering = ["-activo", "nombre"]

    def __str__(self):
        return self.nombre

    def clean(self):
        from django.core.exceptions import ValidationError

        if self.producto and self.categoria:
            raise ValidationError("Elige producto O categoría, no ambos.")
        if not self.producto and not self.categoria:
            raise ValidationError("Elige un producto o una categoría.")

    def vigente(self, ahora=None):
        from django.utils import timezone

        if not self.activo:
            return False
        ahora = ahora or timezone.now()
        if self.fecha_inicio and ahora < self.fecha_inicio:
            return False
        if self.fecha_fin and ahora > self.fecha_fin:
            return False
        return True

    def aplica_a(self, variante):
        if self.producto_id:
            return self.producto_id == variante.producto_id
        return variante.producto.categorias.filter(pk=self.categoria_id).exists()


class VentaRelampago(models.Model):
    """Venta relámpago: precio especial por tiempo limitado sobre una variante."""

    variante = models.ForeignKey(
        Variante, on_delete=models.CASCADE, related_name="relampagos",
        verbose_name="variante",
    )
    precio = models.DecimalField(
        "precio relámpago ($ COP)", max_digits=12, decimal_places=0,
        validators=[MinValueValidator(0)],
    )
    desde = models.DateTimeField("desde")
    hasta = models.DateTimeField("hasta")
    activo = models.BooleanField("activo", default=True)

    class Meta:
        verbose_name = "venta relámpago"
        verbose_name_plural = "ventas relámpago"
        ordering = ["desde"]

    def __str__(self):
        return f"Relámpago {self.variante.sku} a ${int(self.precio):,}".replace(",", ".")

    def clean(self):
        from django.core.exceptions import ValidationError

        if self.precio >= self.variante.precio:
            raise ValidationError({"precio": "Debe ser menor que el precio normal de la variante."})
        if self.hasta <= self.desde:
            raise ValidationError({"hasta": "La fecha final debe ser posterior a la inicial."})

    def vigente(self, ahora=None):
        from django.utils import timezone

        if not self.activo:
            return False
        ahora = ahora or timezone.now()
        return self.desde <= ahora <= self.hasta

    @property
    def ahorro_pct(self):
        precio_normal = self.variante.precio_final
        if not precio_normal or precio_normal <= self.precio:
            return 0
        return round((1 - float(self.precio) / float(precio_normal)) * 100)
