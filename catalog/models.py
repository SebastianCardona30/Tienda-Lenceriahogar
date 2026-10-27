"""
Modelos del catálogo: categorías, productos, variantes, fotos, reseñas y combos.

Diseño pensado para una persona no técnica: nombres claros, estados simples
y todo editable desde el panel sin tocar código.
"""
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models
from django.urls import reverse
from django.utils.text import slugify

from catalog.images import procesar_imagen_producto
from catalog.search import normalizar_texto


class Categoria(models.Model):
    """Categoría del catálogo con subcategorías (un solo nivel de anidamiento)."""

    nombre = models.CharField("nombre", max_length=80, unique=True)
    slug = models.SlugField("slug", max_length=90, unique=True, blank=True)
    padre = models.ForeignKey(
        "self", on_delete=models.CASCADE, related_name="hijas",
        verbose_name="categoría padre", blank=True, null=True,
        help_text="Déjalo vacío para una categoría principal.",
    )
    descripcion = models.TextField("descripción", blank=True)
    imagen = models.ImageField("imagen", upload_to="categorias/", blank=True)
    orden = models.PositiveIntegerField("orden", default=0)
    activa = models.BooleanField("activa", default=True)
    meta_titulo = models.CharField("título SEO", max_length=70, blank=True)
    meta_descripcion = models.CharField("meta descripción SEO", max_length=160, blank=True)

    class Meta:
        verbose_name = "categoría"
        verbose_name_plural = "categorías"
        ordering = ["orden", "nombre"]

    def __str__(self):
        return self.nombre

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.nombre)[:90] or "categoria"
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("catalog:categoria", args=[self.slug])

    @property
    def es_principal(self):
        return self.padre is None


class Proveedor(models.Model):
    """Proveedor tercero de productos."""

    nombre = models.CharField("nombre", max_length=120, unique=True)
    contacto = models.CharField("persona de contacto", max_length=120, blank=True)
    telefono = models.CharField("teléfono", max_length=30, blank=True)
    email = models.EmailField("correo", blank=True)
    tiempo_reposicion_dias = models.PositiveIntegerField(
        "tiempo de reposición (días)", default=7,
        help_text="Cuántos días tarda en traer mercancía nueva.",
    )
    notas = models.TextField("notas", blank=True)
    activo = models.BooleanField("activo", default=True)

    class Meta:
        verbose_name = "proveedor"
        verbose_name_plural = "proveedores"
        ordering = ["nombre"]

    def __str__(self):
        return self.nombre


class Producto(models.Model):
    """Producto del catálogo. El precio y el stock viven en las variantes."""

    ESTADO_CHOICES = [
        ("borrador", "Borrador (no visible)"),
        ("publicado", "Publicado"),
        ("agotado", "Agotado"),
    ]

    nombre = models.CharField("nombre", max_length=160)
    slug = models.SlugField("slug", max_length=180, unique=True, blank=True)
    descripcion_corta = models.CharField(
        "descripción corta", max_length=200, blank=True,
        help_text="Una o dos líneas que se ven en la tarjeta del catálogo.",
    )
    descripcion_larga = models.TextField("descripción larga", blank=True)
    marca = models.CharField("marca", max_length=80, blank=True)
    proveedor = models.ForeignKey(
        Proveedor, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="productos", verbose_name="proveedor",
    )
    categorias = models.ManyToManyField(
        Categoria, related_name="productos", verbose_name="categorías", blank=True
    )
    etiquetas = models.CharField(
        "etiquetas", max_length=200, blank=True,
        help_text="Separadas por coma. Ej.: regalo, matrimonio, microfibra.",
    )
    material = models.CharField("material", max_length=100, blank=True)
    composicion = models.CharField("composición", max_length=160, blank=True)
    cuidado = models.TextField("cuidado", blank=True, help_text="Instrucciones de lavado.")
    estado = models.CharField("estado", max_length=12, choices=ESTADO_CHOICES, default="borrador")
    destacado = models.BooleanField("destacado", default=False)
    es_bordado = models.BooleanField(
        "permite bordado personalizado", default=False,
        help_text="Los productos personalizados no tienen cambio ni retracto (salvo defecto de fábrica).",
    )
    # SEO
    meta_titulo = models.CharField("título SEO", max_length=70, blank=True)
    meta_descripcion = models.CharField("meta descripción SEO", max_length=160, blank=True)
    # Búsqueda normalizada (sin tildes ni mayúsculas); se recalcula en save()
    busqueda = models.CharField("texto de búsqueda", max_length=400, blank=True, db_index=True)

    creado = models.DateTimeField("creado el", auto_now_add=True)
    actualizado = models.DateTimeField("actualizado el", auto_now=True)

    class Meta:
        verbose_name = "producto"
        verbose_name_plural = "productos"
        ordering = ["-creado"]

    def __str__(self):
        return self.nombre

    def save(self, *args, **kwargs):
        if not self.slug:
            base = slugify(self.nombre)[:170] or "producto"
            slug = base
            n = 1
            while Producto.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                n += 1
                slug = f"{base}-{n}"
            self.slug = slug
        # Texto normalizado para búsqueda (nombre, marca, etiquetas y categorías).
        # En la primera creación aún no existen las categorías (M2M requiere PK).
        if self.pk:
            partes = [self.nombre, self.marca, self.etiquetas,
                      " ".join(c.nombre for c in self.categorias.all())]
        else:
            partes = [self.nombre, self.marca, self.etiquetas]
        self.busqueda = normalizar_texto(" ".join(p for p in partes if p))[:400]
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("catalog:producto", args=[self.slug])

    # ---------- Consultas útiles ----------
    @property
    def variantes_activas(self):
        return self.variantes.filter(activa=True)

    @property
    def precio_minimo(self):
        """Menor precio entre variantes activas (ya con oferta aplicada)."""
        valores = [
            v.precio_final for v in self.variantes_activas if v.precio_final is not None
        ]
        return min(valores) if valores else None

    @property
    def precio_tachado(self):
        """Precio normal a mostrar tachado si la variante más barata está en oferta."""
        variantes = [v for v in self.variantes_activas if v.precio_final is not None]
        if not variantes:
            return None
        mejor = min(variantes, key=lambda v: float(v.precio_final))
        return mejor.precio if mejor.precio_oferta is not None else None

    @property
    def ahorro_pct(self):
        """% de ahorro de la mejor oferta del producto."""
        variantes = [v for v in self.variantes_activas if v.precio_oferta is not None]
        if not variantes:
            return 0
        return max(v.ahorro_pct for v in variantes)

    @property
    def es_nuevo(self):
        from datetime import timedelta
        from django.utils import timezone
        return self.creado >= timezone.now() - timedelta(days=15)

    @property
    def tiene_oferta(self):
        """¿Algún producto tiene precio de oferta? (no confundir con la anotación 'en_oferta')"""
        return any(v.precio_oferta is not None for v in self.variantes_activas)

    @property
    def agotado(self):
        return not any(v.stock > 0 for v in self.variantes_activas)

    @property
    def stock_disponible(self):
        """Suma del stock de variantes activas (no confundir con la anotación 'stock_total')."""
        return sum(v.stock for v in self.variantes_activas)

    @property
    def promedio_calificacion(self):
        resenas = self.resenas.filter(aprobada=True)
        if not resenas.exists():
            return None
        return round(sum(r.calificacion for r in resenas) / resenas.count(), 1)

    @property
    def total_resenas(self):
        return self.resenas.filter(aprobada=True).count()

    @property
    def portada(self):
        """Primera foto o None (la plantilla muestra un marcador SVG)."""
        return self.fotos.order_by("orden").first()


class Variante(models.Model):
    """Variante (SKU): talla, color, material… con su precio y stock."""

    TALLA_CHOICES = [
        ("Sencilla", "Sencilla"),
        ("Semidoble", "Semidoble"),
        ("Doble", "Doble"),
        ("Queen", "Queen"),
        ("King", "King"),
        ("Cara", "Toalla cara"),
        ("Mano", "Toalla de mano"),
        ("Baño", "Toalla de baño"),
        ("Playa", "Toalla de playa"),
        ("Otra medida", "Otra medida (escribir abajo)"),
    ]

    producto = models.ForeignKey(
        Producto, on_delete=models.CASCADE, related_name="variantes", verbose_name="producto"
    )
    sku = models.CharField("SKU", max_length=40, unique=True)
    talla = models.CharField("talla/medida", max_length=20, choices=TALLA_CHOICES, blank=True)
    medida_personalizada = models.CharField(
        "otra medida", max_length=40, blank=True,
        help_text="Si elegiste 'Otra medida', escríbela aquí. Ej.: 2,40 x 2,20",
    )
    color = models.CharField("color", max_length=40, blank=True)
    color_hex = models.CharField(
        "código de color (hex)", max_length=7, blank=True,
        help_text="Para la miniatura de color. Ej.: #5B2A86",
    )
    material = models.CharField("material", max_length=80, blank=True)
    hilos = models.PositiveIntegerField(
        "conteo de hilos", null=True, blank=True, help_text="Ej.: 180, 200, 300."
    )
    gramaje = models.PositiveIntegerField(
        "gramaje (g/m²)", null=True, blank=True, help_text="Principalmente para toallas."
    )
    precio = models.DecimalField(
        "precio", max_digits=12, decimal_places=0,
        validators=[MinValueValidator(0)],
    )
    precio_oferta = models.DecimalField(
        "precio de oferta", max_digits=12, decimal_places=0, null=True, blank=True,
        validators=[MinValueValidator(0)],
        help_text="Si tiene oferta, deja el precio normal arriba para mostrarlo tachado.",
    )
    costo = models.DecimalField(
        "costo (privado)", max_digits=12, decimal_places=0, null=True, blank=True,
        help_text="Solo lo ve el personal con permisos. Sirve para el margen.",
    )
    stock = models.IntegerField("stock", default=0, validators=[MinValueValidator(0)])
    umbral_stock_bajo = models.IntegerField(
        "alertar cuando el stock baje de", default=3
    )
    peso_gramos = models.PositiveIntegerField(
        "peso para envío (gramos)", default=500
    )
    foto = models.ImageField("foto propia", upload_to="variantes/", blank=True)
    activa = models.BooleanField("activa", default=True)

    class Meta:
        verbose_name = "variante"
        verbose_name_plural = "variantes"
        ordering = ["producto__nombre", "talla", "color"]

    def __str__(self):
        partes = [self.producto.nombre, self.talla_label, self.color]
        return " - ".join(p for p in partes if p)

    def save(self, *args, **kwargs):
        if not self.sku:
            base = slugify(f"{self.producto.nombre}-{self.talla}-{self.color}")[:30].upper().replace("-", "")
            sku = base or "SKU"
            n = 1
            while Variante.objects.filter(sku=sku).exclude(pk=self.pk).exists():
                n += 1
                sku = f"{base}{n}"
            self.sku = sku
        if self.precio_oferta is not None and self.precio_oferta >= self.precio:
            # Una oferta debe ser menor que el precio normal
            self.precio_oferta = None
        super().save(*args, **kwargs)

    @property
    def talla_label(self):
        if self.talla == "Otra medida" and self.medida_personalizada:
            return self.medida_personalizada
        return self.talla

    @property
    def precio_final(self):
        """Precio a cobrar: la oferta si existe, si no el normal."""
        return self.precio_oferta if self.precio_oferta is not None else self.precio

    @property
    def ahorro_pct(self):
        if self.precio_oferta is None or not self.precio:
            return 0
        return round((1 - float(self.precio_oferta) / float(self.precio)) * 100)

    @property
    def disponible(self):
        return self.activa and self.stock > 0

    @property
    def stock_bajo(self):
        return 0 < self.stock <= self.umbral_stock_bajo


class FotoProducto(models.Model):
    """Fotos múltiples ordenables de un producto (se convierten a WebP)."""

    producto = models.ForeignKey(
        Producto, on_delete=models.CASCADE, related_name="fotos", verbose_name="producto"
    )
    imagen = models.ImageField("imagen", upload_to="productos/")
    miniatura = models.ImageField(
        "miniatura", upload_to="productos/miniaturas/", blank=True
    )
    alt = models.CharField(
        "texto alternativo", max_length=160, blank=True,
        help_text="Describe la foto para Google y personas con discapacidad visual.",
    )
    orden = models.PositiveIntegerField("orden", default=0)

    class Meta:
        verbose_name = "foto de producto"
        verbose_name_plural = "fotos de productos"
        ordering = ["orden"]

    def __str__(self):
        return f"Foto de {self.producto.nombre}"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        # Convierte a WebP y crea la miniatura la primera vez que se sube.
        procesar_imagen_producto(self)


class Resena(models.Model):
    """Reseña de 1–5 estrellas. Solo compradores verificados; moderadas desde el admin."""

    producto = models.ForeignKey(
        Producto, on_delete=models.CASCADE, related_name="resenas", verbose_name="producto"
    )
    usuario = models.ForeignKey(
        "accounts.Usuario", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="resenas", verbose_name="cliente",
    )
    nombre = models.CharField("nombre", max_length=80)
    calificacion = models.PositiveSmallIntegerField(
        "calificación", validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    comentario = models.TextField("comentario")
    verificada = models.BooleanField(
        "compra verificada", default=False,
        help_text="Se marca automáticamente cuando el cliente compró el producto.",
    )
    aprobada = models.BooleanField("aprobada", default=False)
    creada = models.DateTimeField("creada el", auto_now_add=True)

    class Meta:
        verbose_name = "reseña"
        verbose_name_plural = "reseñas"
        ordering = ["-creada"]

    def __str__(self):
        return f"{self.nombre} → {self.producto.nombre} ({self.calificacion}★)"


class Combo(models.Model):
    """Combo o set de productos con precio especial."""

    nombre = models.CharField("nombre", max_length=120)
    slug = models.SlugField("slug", max_length=140, unique=True, blank=True)
    descripcion = models.TextField("descripción", blank=True)
    precio_combo = models.DecimalField("precio del combo", max_digits=12, decimal_places=0)
    imagen = models.ImageField("imagen", upload_to="combos/", blank=True)
    activo = models.BooleanField("activo", default=True)
    orden = models.PositiveIntegerField("orden", default=0)
    creado = models.DateTimeField("creado el", auto_now_add=True)

    class Meta:
        verbose_name = "combo / set"
        verbose_name_plural = "combos y sets"
        ordering = ["orden", "nombre"]

    def __str__(self):
        return self.nombre

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.nombre)[:140] or "combo"
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("catalog:combo", args=[self.slug])

    @property
    def precio_normal(self):
        return sum(
            (item.producto.precio_minimo or 0) * item.cantidad for item in self.items.all()
        )

    @property
    def ahorro_pct(self):
        normal = self.precio_normal
        if not normal:
            return 0
        return round((1 - float(self.precio_combo) / float(normal)) * 100)


class ComboItem(models.Model):
    """Producto dentro de un combo."""

    combo = models.ForeignKey(Combo, on_delete=models.CASCADE, related_name="items")
    producto = models.ForeignKey(
        Producto, on_delete=models.CASCADE, related_name="combos", verbose_name="producto"
    )
    cantidad = models.PositiveIntegerField("cantidad", default=1)

    class Meta:
        verbose_name = "producto del combo"
        verbose_name_plural = "productos del combo"
        ordering = ["id"]

    def __str__(self):
        return f"{self.cantidad}x {self.producto.nombre}"


class Sinonimo(models.Model):
    """Sinónimos de búsqueda editables: 'sábana, sabana, sabanas'."""

    palabras = models.CharField(
        "palabras separadas por coma", max_length=200, unique=True,
        help_text="Ej.: edredón, cubrelecho, plumón. Si alguien busca cualquiera, "
                  "se muestran productos de todas.",
    )
    activo = models.BooleanField("activo", default=True)

    class Meta:
        verbose_name = "sinónimo de búsqueda"
        verbose_name_plural = "sinónimos de búsqueda"
        ordering = ["palabras"]

    def __str__(self):
        return self.palabras

    def lista(self):
        return [p.strip() for p in self.palabras.split(",") if p.strip()]


class BusquedaSinResultados(models.Model):
    """Registro de búsquedas sin resultados (para ver qué piden los clientes)."""

    consulta = models.CharField("consulta", max_length=200)
    fecha = models.DateTimeField("fecha", auto_now_add=True)
    revisada = models.BooleanField("revisada", default=False)

    class Meta:
        verbose_name = "búsqueda sin resultados"
        verbose_name_plural = "búsquedas sin resultados"
        ordering = ["-fecha"]

    def __str__(self):
        return self.consulta

    def save(self, *args, **kwargs):
        self.consulta = self.consulta[:200]
        super().save(*args, **kwargs)
