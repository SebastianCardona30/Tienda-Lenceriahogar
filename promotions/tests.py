"""Pruebas del motor de descuentos: ofertas, cupones, 2x1, volumen y relámpago."""
from datetime import timedelta
from decimal import Decimal

from django.test import TestCase
from django.utils import timezone

from catalog.models import Categoria, Producto, Variante
from promotions.engine import LineaCarrito, calcular_carrito
from promotions.models import Cupon, Descuento, PromoUnidades, PromoVolumen, VentaRelampago


def crear_variante(nombre="Sábanas dobles", precio=100000, stock=10, **kwargs):
    prod = Producto.objects.create(nombre=nombre, estado="publicado")
    return Variante.objects.create(
        producto=prod, precio=Decimal(precio), stock=stock, **kwargs
    )


class OfertaBasicaTests(TestCase):
    def test_carrito_sin_ofertas(self):
        v = crear_variante(precio=100000)
        r = calcular_carrito([LineaCarrito(v, 2)])
        self.assertEqual(r.subtotal, Decimal(200000))
        self.assertEqual(r.total, Decimal(200000))
        self.assertEqual(r.total_descuentos, 0)

    def test_precio_oferta_de_variante(self):
        # La oferta de catálogo (precio_oferta) ya viene en precio_final.
        v = crear_variante(precio=100000, precio_oferta=Decimal(80000))
        r = calcular_carrito([LineaCarrito(v, 1)])
        self.assertEqual(r.subtotal, Decimal(80000))
        self.assertEqual(r.lineas[0].subtotal_base, Decimal(100000))
        self.assertEqual(r.lineas[0].ahorro, Decimal(20000))


class DescuentoDirectoTests(TestCase):
    def test_descuento_porcentual_producto(self):
        v = crear_variante(precio=100000)
        Descuento.objects.create(
            nombre="Rebajas", sobre="producto", producto=v.producto,
            tipo="porcentaje", valor=Decimal(10),
        )
        r = calcular_carrito([LineaCarrito(v, 1)])
        self.assertEqual(r.subtotal, Decimal(90000))

    def test_descuento_fijo_variante(self):
        v = crear_variante(precio=100000)
        Descuento.objects.create(
            nombre="$15.000 menos", sobre="variante", variante=v,
            tipo="valor", valor=Decimal(15000),
        )
        r = calcular_carrito([LineaCarrito(v, 2)])
        self.assertEqual(r.subtotal, Decimal(200000 - 15000))

    def test_descuento_por_categoria(self):
        cat = Categoria.objects.create(nombre="Toallas")
        v = crear_variante(nombre="Toalla")
        v.producto.categorias.add(cat)
        Descuento.objects.create(
            nombre="Toallas en sale", sobre="categoria", categoria=cat,
            tipo="porcentaje", valor=Decimal(20),
        )
        r = calcular_carrito([LineaCarrito(v, 1)])
        self.assertEqual(r.subtotal, Decimal(80000))

    def test_descuento_vencido_no_aplica(self):
        v = crear_variante(precio=100000)
        ahora = timezone.now()
        Descuento.objects.create(
            nombre="Vencido", sobre="producto", producto=v.producto,
            tipo="porcentaje", valor=Decimal(50),
            fecha_fin=ahora - timedelta(days=1),
        )
        r = calcular_carrito([LineaCarrito(v, 1)])
        self.assertEqual(r.subtotal, Decimal(100000))

    def test_mejor_descuento_gana(self):
        v = crear_variante(precio=100000)
        Descuento.objects.create(
            nombre="10%", sobre="producto", producto=v.producto,
            tipo="porcentaje", valor=Decimal(10),
        )
        Descuento.objects.create(
            nombre="30%", sobre="producto", producto=v.producto,
            tipo="porcentaje", valor=Decimal(30),
        )
        r = calcular_carrito([LineaCarrito(v, 1)])
        self.assertEqual(r.subtotal, Decimal(70000))


class PromoUnidadesTests(TestCase):
    def test_2x1(self):
        v = crear_variante(precio=50000)
        PromoUnidades.objects.create(
            nombre="Sábanas 2x1", producto=v.producto, llevar=2, pagar=1
        )
        r = calcular_carrito([LineaCarrito(v, 2)])
        self.assertEqual(r.subtotal, Decimal(50000))  # paga 1 de 2
        self.assertIn("Lleva 2 paga 1", r.lineas[0].motivos)

    def test_2x1_con_cantidad_impar(self):
        v = crear_variante(precio=50000)
        PromoUnidades.objects.create(
            nombre="2x1", producto=v.producto, llevar=2, pagar=1
        )
        r = calcular_carrito([LineaCarrito(v, 3)])
        # 1 grupo de 2 (paga 1) + 1 suelto
        self.assertEqual(r.subtotal, Decimal(100000))

    def test_3x2(self):
        v = crear_variante(precio=30000)
        PromoUnidades.objects.create(
            nombre="3x2", producto=v.producto, llevar=3, pagar=2
        )
        r = calcular_carrito([LineaCarrito(v, 3)])
        self.assertEqual(r.subtotal, Decimal(60000))


class VolumenTests(TestCase):
    def test_volumen_porcentaje(self):
        cat = Categoria.objects.create(nombre="Cojines")
        v = crear_variante(nombre="Cojín", precio=20000)
        v.producto.categorias.add(cat)
        PromoVolumen.objects.create(
            nombre="3 cojines -10%", categoria=cat, tipo="porcentaje",
            valor=Decimal(10), cantidad_minima=3,
        )
        r = calcular_carrito([LineaCarrito(v, 3)])
        self.assertEqual(r.subtotal, Decimal(54000))  # 60.000 - 10%

    def test_volumen_no_aplica_bajo_minimo(self):
        v = crear_variante(precio=20000)
        PromoVolumen.objects.create(
            nombre="3 o más", producto=v.producto, tipo="porcentaje",
            valor=Decimal(10), cantidad_minima=3,
        )
        r = calcular_carrito([LineaCarrito(v, 2)])
        self.assertEqual(r.subtotal, Decimal(40000))


class RelampagoTests(TestCase):
    def test_relampago_aplica(self):
        v = crear_variante(precio=100000)
        ahora = timezone.now()
        VentaRelampago.objects.create(
            variante=v, precio=Decimal(70000),
            desde=ahora - timedelta(hours=1), hasta=ahora + timedelta(hours=2),
        )
        r = calcular_carrito([LineaCarrito(v, 1)])
        self.assertEqual(r.subtotal, Decimal(70000))

    def test_relampago_vencido_no_aplica(self):
        v = crear_variante(precio=100000)
        ahora = timezone.now()
        VentaRelampago.objects.create(
            variante=v, precio=Decimal(70000),
            desde=ahora - timedelta(days=2), hasta=ahora - timedelta(days=1),
        )
        r = calcular_carrito([LineaCarrito(v, 1)])
        self.assertEqual(r.subtotal, Decimal(100000))


class CuponTests(TestCase):
    def setUp(self):
        self.v = crear_variante(precio=100000)

    def test_cupon_porcentaje(self):
        Cupon.objects.create(codigo="BIENVENIDA10", tipo="porcentaje", valor=Decimal(10))
        r = calcular_carrito([LineaCarrito(self.v, 1)], codigo_cupon="bienvenida10")
        self.assertEqual(r.cupon_descuento, Decimal(10000))
        self.assertEqual(r.total, Decimal(90000))

    def test_cupon_valor_fijo(self):
        Cupon.objects.create(codigo="BAJON20", tipo="valor", valor=Decimal(20000))
        r = calcular_carrito([LineaCarrito(self.v, 1)], codigo_cupon="BAJON20")
        self.assertEqual(r.total, Decimal(80000))

    def test_cupon_monto_minimo(self):
        Cupon.objects.create(
            codigo="SOLOGRANDE", tipo="porcentaje", valor=Decimal(10),
            monto_minimo=Decimal(500000),
        )
        r = calcular_carrito([LineaCarrito(self.v, 1)], codigo_cupon="SOLOGRANDE")
        self.assertEqual(r.cupon_descuento, 0)
        self.assertIn("Te faltan", r.cupon_error)

    def test_cupon_inexistente(self):
        r = calcular_carrito([LineaCarrito(self.v, 1)], codigo_cupon="NOEXISTE")
        self.assertIn("no existe", r.cupon_error)

    def test_cupon_vencido(self):
        Cupon.objects.create(
            codigo="VIEJO", tipo="porcentaje", valor=Decimal(10),
            fecha_fin=timezone.now() - timedelta(days=1),
        )
        r = calcular_carrito([LineaCarrito(self.v, 1)], codigo_cupon="VIEJO")
        self.assertIn("venció", r.cupon_error)

    def test_cupon_limite_de_usos(self):
        cupon = Cupon.objects.create(
            codigo="POCAS", tipo="porcentaje", valor=Decimal(10), max_usos=1
        )
        cupon.usos.create(email="alguien@ejemplo.com")
        r = calcular_carrito([LineaCarrito(self.v, 1)], codigo_cupon="POCAS")
        self.assertIn("límite", r.cupon_error)

    def test_cupon_con_categoria_limitada(self):
        cat = Categoria.objects.create(nombre="Edredones")
        v2 = crear_variante(nombre="Edredón")
        v2.producto.categorias.add(cat)
        cupon = Cupon.objects.create(codigo="EDREDONES", tipo="porcentaje", valor=Decimal(15))
        cupon.categorias.add(cat)
        # No aplica: el carrito es de sábanas
        r = calcular_carrito([LineaCarrito(self.v, 1)], codigo_cupon="EDREDONES")
        self.assertEqual(r.cupon_descuento, 0)
        self.assertIn("solo aplica", r.cupon_error)
        # Sí aplica si el carrito tiene edredones
        r2 = calcular_carrito([LineaCarrito(v2, 1)], codigo_cupon="EDREDONES")
        self.assertEqual(r2.cupon_descuento, Decimal(15000))

    def test_cupon_no_acumulable_elige_mejor_opcion(self):
        # Oferta automática 50% vs cupón 10% no acumulable → ganan las ofertas.
        v = crear_variante(precio=100000)
        Descuento.objects.create(
            nombre="Mitad de precio", sobre="producto", producto=v.producto,
            tipo="porcentaje", valor=Decimal(50),
        )
        Cupon.objects.create(
            codigo="NOACUM", tipo="porcentaje", valor=Decimal(10), acumulable=False
        )
        r = calcular_carrito([LineaCarrito(v, 1)], codigo_cupon="NOACUM")
        self.assertEqual(r.total, Decimal(50000))  # mandan las ofertas

    def test_cupon_no_acumulable_gana_si_es_mejor(self):
        v = crear_variante(precio=100000)
        Descuento.objects.create(
            nombre="5%", sobre="producto", producto=v.producto,
            tipo="porcentaje", valor=Decimal(5),
        )
        Cupon.objects.create(
            codigo="GRANDE", tipo="porcentaje", valor=Decimal(30), acumulable=False
        )
        r = calcular_carrito([LineaCarrito(v, 1)], codigo_cupon="GRANDE")
        self.assertEqual(r.total, Decimal(70000))  # mandó el cupón
        self.assertEqual(r.lineas[0].descuento, 0)


class AcumulacionTests(TestCase):
    def test_cupon_se_aplica_sobre_lineas_ya_descontadas(self):
        v = crear_variante(precio=100000)
        Descuento.objects.create(
            nombre="10%", sobre="producto", producto=v.producto,
            tipo="porcentaje", valor=Decimal(10),
        )
        Cupon.objects.create(codigo="OTRO10", tipo="porcentaje", valor=Decimal(10))
        r = calcular_carrito([LineaCarrito(v, 1)], codigo_cupon="OTRO10")
        # 100.000 → 90.000 (oferta) → cupón 10% = 9.000 → total 81.000
        self.assertEqual(r.total, Decimal(81000))
        self.assertEqual(r.total_descuentos, Decimal(19000))


class CuponBienvenidaTests(TestCase):
    def test_crear_bienvenida_copia_la_plantilla(self):
        Cupon.objects.create(
            codigo="BIENVENIDA10", tipo="porcentaje", valor=Decimal(10),
            monto_minimo=Decimal(80000), es_bienvenida=True,
        )
        cupon = Cupon.crear_bienvenida()
        self.assertIsNotNone(cupon)
        self.assertTrue(cupon.codigo.startswith("BIENVENIDA-"))
        self.assertNotEqual(cupon.codigo, "BIENVENIDA10")
        self.assertEqual(cupon.valor, Decimal(10))
        self.assertEqual(cupon.monto_minimo, Decimal(80000))
        self.assertEqual(cupon.max_usos, 1)
        self.assertEqual(cupon.max_usos_por_cliente, 1)
        self.assertTrue(cupon.solo_primera_compra)
        self.assertTrue(cupon.activo)
        self.assertFalse(cupon.es_bienvenida)
        # Y se puede usar en el motor
        v = crear_variante(precio=100000)
        r = calcular_carrito([LineaCarrito(v, 1)], codigo_cupon=cupon.codigo)
        self.assertEqual(r.cupon_descuento, Decimal(10000))
        self.assertEqual(r.cupon_error, "")

    def test_crear_bienvenida_codigos_unicos(self):
        Cupon.objects.create(codigo="PLANTILLA", es_bienvenida=True, valor=Decimal(10))
        c1 = Cupon.crear_bienvenida()
        c2 = Cupon.crear_bienvenida()
        self.assertNotEqual(c1.codigo, c2.codigo)

    def test_crear_bienvenida_sin_plantilla_devuelve_none(self):
        self.assertIsNone(Cupon.crear_bienvenida())
