"""
Motor de descuentos: TODO se calcula aquí, en el servidor.

Orden de aplicación:
1. Precio publicado de la variante (ya incluye precio_oferta si existe).
2. Oferta automática de la línea: se elige UNA sola, la que más descuente
   entre: venta relámpago, descuento directo (% o valor), promo de unidades
   (2x1 / 3x2) y descuento por volumen. Nunca se acumulan dos ofertas
   automáticas en la misma línea.
3. Cupón al final, sobre el subtotal resultante. Si el cupón NO es
   acumulable, se compara el total con ofertas automáticas contra el total
   con el cupón solo y se queda la opción más favorable para el cliente.
"""
from dataclasses import dataclass, field
from decimal import ROUND_HALF_UP, Decimal

from django.utils import timezone

from promotions.models import Cupon, Descuento, PromoUnidades, PromoVolumen, VentaRelampago

ENTERO = Decimal("1")
CERO = Decimal("0")


def _d(valor):
    return Decimal(valor).quantize(ENTERO, rounding=ROUND_HALF_UP)


def _cop(valor):
    """Formato de pesos: $15.000."""
    return f"${int(Decimal(valor)):,}".replace(",", ".")


@dataclass
class LineaCarrito:
    """Línea de carrito en crudo: variante + cantidad pedida."""

    variante: object
    cantidad: int


@dataclass
class LineaCalculada:
    """Resultado del cálculo de una línea: precio publicado + descuento."""

    variante: object
    cantidad: int
    precio_unitario: Decimal          # precio publicado (incluye oferta de catálogo)
    precio_base: Decimal              # precio sin ninguna promoción (para tachar)
    descuento: Decimal = CERO         # descuento total de la línea (una sola oferta)
    motivos: list = field(default_factory=list)  # etiquetas visibles ("2x1", "-10%", …)

    @property
    def subtotal(self):
        return _d(self.precio_unitario * self.cantidad - self.descuento)

    @property
    def subtotal_base(self):
        return _d(self.precio_base * self.cantidad)

    @property
    def ahorro(self):
        return self.subtotal_base - self.subtotal

    @property
    def precio_efectivo(self):
        """Precio unitario ya con el descuento repartido (para mostrar)."""
        if not self.cantidad:
            return self.precio_unitario
        return _d((self.precio_unitario * self.cantidad - self.descuento) / self.cantidad)


@dataclass
class ResumenCarrito:
    """Resumen completo: líneas + cupón + totales."""

    lineas: list
    cupon: Cupon = None
    cupon_descuento: Decimal = CERO
    cupon_error: str = ""
    cupon_aviso: str = ""
    descuento_ofertas: Decimal = CERO

    @property
    def subtotal(self):
        """Suma de las líneas con ofertas automáticas (antes del cupón)."""
        return _d(sum(l.subtotal for l in self.lineas))

    @property
    def subtotal_publicado(self):
        """Suma a precio publicado, sin promos automáticas ni cupón."""
        return _d(sum(l.precio_unitario * l.cantidad for l in self.lineas))

    @property
    def subtotal_base(self):
        """Suma sin ninguna promoción (para mostrar precios tachados)."""
        return _d(sum(l.subtotal_base for l in self.lineas))

    @property
    def total_descuentos(self):
        return _d(self.descuento_ofertas + self.cupon_descuento)

    @property
    def total(self):
        return _d(self.subtotal - self.cupon_descuento)

    @property
    def items(self):
        """Cantidad total de unidades."""
        return sum(l.cantidad for l in self.lineas)


def _contexto_promos(ahora):
    """Carga todas las promociones vigentes una sola vez para todo el carrito."""
    return {
        "relampagos": list(
            VentaRelampago.objects.filter(activo=True, desde__lte=ahora, hasta__gte=ahora)
        ),
        "descuentos": list(
            Descuento.objects.filter(activo=True)
            .select_related("producto", "variante", "categoria")
        ),
        "unidades": list(
            PromoUnidades.objects.filter(activo=True).select_related("producto", "categoria")
        ),
        "volumen": list(
            PromoVolumen.objects.filter(activo=True).select_related("producto", "categoria")
        ),
    }


def _aplica_a(promo, variante, cats):
    """Versión en memoria de promo.aplica_a (sin consultas)."""
    sobre = getattr(promo, "sobre", None)
    if sobre == "variante":
        return promo.variante_id == variante.id
    if sobre == "producto":
        return promo.producto_id == variante.producto_id
    if sobre == "categoria":
        return promo.categoria_id in cats
    # PromoUnidades / PromoVolumen: producto o categoría
    if promo.producto_id:
        return promo.producto_id == variante.producto_id
    return promo.categoria_id in cats


def _mejor_descuento_directo(variante, ahora, cats, descuentos):
    """Devuelve el mejor descuento directo vigente para la variante, o None."""
    candidatos = []
    for d in descuentos:
        if not d.vigente(ahora) or not _aplica_a(d, variante, cats):
            continue
        if d.tipo == "porcentaje":
            ahorro = _d(variante.precio_final * d.valor / 100)
        else:
            ahorro = _d(d.valor)
        candidatos.append((ahorro, d))
    if not candidatos:
        return None
    return max(candidatos, key=lambda c: c[0])[1]


def _calcular_linea(linea, ahora, ctx, permitir_automaticas=True):
    """
    Calcula una línea: elige la mejor oferta automática (una sola) y la
    expresa como descuento en pesos sobre el precio publicado.
    """
    v = linea.variante
    cantidad = max(1, int(linea.cantidad))
    precio_base = _d(v.precio)
    precio = _d(v.precio_final)
    motivos = []

    if not permitir_automaticas:
        # Cupón no acumulable que ganó: solo queda el precio publicado.
        return LineaCalculada(v, cantidad, precio, precio_base, CERO, motivos)

    cats = set(v.producto.categorias.values_list("id", flat=True))
    linea_total = precio * cantidad
    candidatos = []  # (ahorro en pesos, etiqueta visible)

    # Venta relámpago (ya filtrada por fecha en el contexto)
    relampagos = [r for r in ctx["relampagos"] if r.variante_id == v.id]
    if relampagos:
        relampago = min(relampagos, key=lambda r: r.precio)
        if relampago.precio < precio:
            ahorro = min(_d(linea_total - relampago.precio * cantidad), linea_total)
            candidatos.append((ahorro, f"Relámpago -{relampago.ahorro_pct}%"))

    # Descuento directo (el mejor de los vigentes)
    d = _mejor_descuento_directo(v, ahora, cats, ctx["descuentos"])
    if d is not None:
        if d.tipo == "porcentaje":
            ahorro = min(_d(linea_total * d.valor / 100), linea_total)
            etiqueta = f"-{d.valor:.0f}% {d.nombre}"
        else:
            ahorro = min(_d(d.valor), linea_total)
            etiqueta = f"-{_cop(d.valor)} {d.nombre}"
        candidatos.append((ahorro, etiqueta))

    # Promo de unidades (2x1, 3x2)
    for p in ctx["unidades"]:
        if not (p.vigente(ahora) and _aplica_a(p, v, cats)):
            continue
        grupos = cantidad // p.llevar
        if grupos <= 0:
            continue
        unidades_gratis = grupos * (p.llevar - p.pagar)
        ahorro = min(_d(precio * unidades_gratis), linea_total)
        candidatos.append((ahorro, p.etiqueta))

    # Descuento por volumen
    for p in ctx["volumen"]:
        if not (p.vigente(ahora) and _aplica_a(p, v, cats) and cantidad >= p.cantidad_minima):
            continue
        if p.tipo == "porcentaje":
            ahorro = min(_d(linea_total * p.valor / 100), linea_total)
            etiqueta = f"-{p.valor:.0f}% desde {p.cantidad_minima} uds."
        else:
            ahorro = min(_d(p.valor), linea_total)
            etiqueta = f"-{_cop(p.valor)} desde {p.cantidad_minima} uds."
        candidatos.append((ahorro, etiqueta))

    descuento = CERO
    if candidatos:
        mejor, motivo = max(candidatos, key=lambda c: c[0])
        if mejor > 0:
            descuento = min(_d(mejor), linea_total)
            motivos = [motivo]

    return LineaCalculada(v, cantidad, precio, precio_base, descuento, motivos)


def calcular_carrito(lineas, codigo_cupon=None, usuario=None, ahora=None):
    """
    Calcula el carrito completo.

    lineas: lista de LineaCarrito (o pares (variante, cantidad)).
    codigo_cupon: código escrito por el cliente (opcional).
    usuario: Usuario autenticado o None (invitado).
    """
    ahora = ahora or timezone.now()
    preparadas = []
    for l in lineas:
        if isinstance(l, LineaCarrito):
            preparadas.append(l)
        else:  # tupla (variante, cantidad)
            preparadas.append(LineaCarrito(variante=l[0], cantidad=l[1]))

    # Ofertas automáticas (una sola por línea, con promos cargadas una vez)
    ctx = _contexto_promos(ahora)
    lineas_calc = [_calcular_linea(l, ahora, ctx) for l in preparadas]
    descuento_ofertas = _d(sum(l.descuento for l in lineas_calc))

    resumen = ResumenCarrito(
        lineas=lineas_calc,
        descuento_ofertas=descuento_ofertas,
    )

    subtotal = resumen.subtotal

    # ---------- Cupón ----------
    if not codigo_cupon:
        return resumen

    codigo = codigo_cupon.strip().upper()
    try:
        cupon = Cupon.objects.get(codigo=codigo)
    except Cupon.DoesNotExist:
        resumen.cupon_error = "Ese cupón no existe."
        return resumen

    error = _validar_cupon(cupon, subtotal, usuario, ahora, lineas_calc)
    if error:
        resumen.cupon_error = error
        return resumen

    if cupon.tipo == "porcentaje":
        desc_cupon = _d(subtotal * cupon.valor / 100)
    else:
        desc_cupon = _d(min(cupon.valor, subtotal))
    desc_cupon = min(desc_cupon, subtotal)

    if not cupon.acumulable:
        # Se compara el total con ofertas automáticas vs el total con el cupón solo.
        publicado = resumen.subtotal_publicado
        if cupon.tipo == "porcentaje":
            desc_sin_ofertas = min(_d(publicado * cupon.valor / 100), publicado)
        else:
            desc_sin_ofertas = _d(min(cupon.valor, publicado))
        if publicado - desc_sin_ofertas < subtotal:
            # El cupón gana: se anulan las ofertas automáticas de las líneas.
            for l in resumen.lineas:
                l.descuento = CERO
                l.motivos = []
            resumen.descuento_ofertas = CERO
            resumen.cupon_descuento = desc_sin_ofertas
            resumen.cupon = cupon
            return resumen
        # Las ofertas automáticas ganan: el cupón no se aplica.
        resumen.cupon = None
        resumen.cupon_aviso = (
            "Este cupón no se acumula con ofertas; se aplicó la mejor opción para ti."
        )
        return resumen

    resumen.cupon = cupon
    resumen.cupon_descuento = desc_cupon
    return resumen


def _validar_cupon(cupon, subtotal, usuario, ahora, lineas):
    """Devuelve un mensaje de error en español o None si el cupón es válido."""
    if not cupon.activo:
        return "Ese cupón ya no está activo."
    if cupon.fecha_inicio and ahora < cupon.fecha_inicio:
        return "Ese cupón aún no es válido."
    if cupon.fecha_fin and ahora > cupon.fecha_fin:
        return "Ese cupón ya venció."
    if subtotal < cupon.monto_minimo:
        falta = _d(cupon.monto_minimo - subtotal)
        return (
            f"Este cupón aplica desde {_cop(cupon.monto_minimo)}. "
            f"Te faltan {_cop(falta)}."
        )
    if cupon.max_usos is not None and cupon.usos.count() >= cupon.max_usos:
        return "Ese cupón ya alcanzó su límite de usos."
    if cupon.max_usos_por_cliente is not None:
        if usuario and usuario.is_authenticated:
            usos = cupon.usos.filter(usuario=usuario).count()
        else:
            usos = 0  # invitado: sin historial por cliente todavía
        if usos >= cupon.max_usos_por_cliente:
            return "Ya usaste ese cupón antes."
    if cupon.solo_primera_compra:
        if usuario and usuario.is_authenticated:
            try:
                from orders.models import Pedido
            except ImportError:  # Pedido aún no existe (se crea en el paso 5)
                Pedido = None
            if Pedido is not None and Pedido.objects.filter(usuario=usuario).exists():
                return "Ese cupón es solo para tu primera compra."
        # Invitado: no hay forma de verificar; se audita al confirmar.
    if cupon.categorias.exists():
        # El cupón solo aplica si el carrito tiene productos de esas categorías.
        categorias_cupon = set(cupon.categorias.values_list("id", flat=True))
        tiene_productos = any(
            l.variante.producto.categorias.filter(id__in=categorias_cupon).exists()
            for l in lineas
        )
        if not tiene_productos:
            nombres = ", ".join(cupon.categorias.values_list("nombre", flat=True)[:3])
            return f"Ese cupón solo aplica en: {nombres}."
    return None
