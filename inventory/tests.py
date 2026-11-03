"""Pruebas de inventario: movimientos, recepción de órdenes y valorizado."""
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.contrib.admin.sites import AdminSite
from django.test import TestCase
from django.urls import reverse

from catalog.models import Producto, Proveedor, Variante
from inventory import servicios
from inventory.admin import (
    MovimientoStockAdmin, OrdenCompraAdmin, StockBajoFilter,
    VarianteInventarioAdmin,
)
from inventory.models import MovimientoStock, OrdenCompra, OrdenCompraItem
from inventory.servicios import StockInsuficiente
from orders.models import Pedido
from orders.servicios import cambiar_estado, crear_pedido, devolver_stock
from shipping.models import MunicipioSantander, ZonaEnvio

Usuario = get_user_model()


def crear_variante(stock=10, umbral=3, costo=None, activa=True, nombre="Sábanas"):
    prod = Producto.objects.create(nombre=nombre, estado="publicado")
    return Variante.objects.create(
        producto=prod, precio=Decimal(100000), costo=costo,
        stock=stock, umbral_stock_bajo=umbral, activa=activa,
    )


class MovimientoTests(TestCase):
    """registrar_movimiento: ajusta stock y deja el registro."""

    def setUp(self):
        self.variante = crear_variante(stock=10)

    def test_entrada_suma_stock_y_registra(self):
        mov = servicios.registrar_movimiento(
            self.variante, 5, "ajuste", nota="Conteo físico",
        )
        self.variante.refresh_from_db()
        self.assertEqual(self.variante.stock, 15)
        self.assertEqual(mov.stock_resultante, 15)
        self.assertEqual(mov.motivo, "ajuste")
        self.assertEqual(MovimientoStock.objects.count(), 1)

    def test_salida_resta_stock(self):
        servicios.registrar_movimiento(self.variante, -3, "merma")
        self.variante.refresh_from_db()
        self.assertEqual(self.variante.stock, 7)

    def test_no_permite_stock_negativo(self):
        with self.assertRaises(StockInsuficiente):
            servicios.registrar_movimiento(self.variante, -11, "merma")
        self.variante.refresh_from_db()
        self.assertEqual(self.variante.stock, 10)  # no cambió
        self.assertEqual(MovimientoStock.objects.count(), 0)

    def test_anotar_ajuste_con_delta_cero_no_registra(self):
        self.assertIsNone(servicios.anotar_ajuste(self.variante, 0))
        self.assertEqual(MovimientoStock.objects.count(), 0)

    def test_anotar_ajuste_registra_el_delta(self):
        self.variante.stock = 8
        self.variante.save(update_fields=["stock"])
        mov = servicios.anotar_ajuste(self.variante, -2, nota="10 → 8")
        self.assertEqual(mov.cantidad, -2)
        self.assertEqual(mov.motivo, "ajuste")
        self.assertEqual(mov.stock_resultante, 8)


class OrdenCompraTests(TestCase):
    """Recepción de órdenes: suma stock una sola vez y deja movimientos."""

    def setUp(self):
        self.proveedor = Proveedor.objects.create(nombre="Textiles Andes")
        self.variante = crear_variante(stock=4)
        self.orden = OrdenCompra.objects.create(proveedor=self.proveedor)
        OrdenCompraItem.objects.create(
            orden=self.orden, variante=self.variante,
            cantidad=10, costo_unitario=Decimal(60000),
        )

    def test_numero_automatico(self):
        otra = OrdenCompra.objects.create(proveedor=self.proveedor)
        self.assertEqual(self.orden.numero, "OC-00001")
        self.assertEqual(otra.numero, "OC-00002")

    def test_total_se_suma_de_las_lineas(self):
        self.assertEqual(self.orden.total, Decimal(600000))

    def test_recibir_suma_stock_y_crea_movimientos(self):
        servicios.recibir_orden(self.orden)
        self.variante.refresh_from_db()
        self.assertEqual(self.variante.stock, 14)
        mov = MovimientoStock.objects.get()
        self.assertEqual(mov.motivo, "orden")
        self.assertEqual(mov.referencia, self.orden.numero)
        self.orden.refresh_from_db()
        self.assertEqual(self.orden.estado, "recibida")
        self.assertIsNotNone(self.orden.recibida)

    def test_recibir_es_idempotente(self):
        servicios.recibir_orden(self.orden)
        servicios.recibir_orden(self.orden)
        self.variante.refresh_from_db()
        self.assertEqual(self.variante.stock, 14)  # sumó una sola vez
        self.assertEqual(MovimientoStock.objects.count(), 1)


class ValorizadoTests(TestCase):
    """valorizar_inventario: cuánto vale la mercancía a costo y a precio."""

    def test_suma_stock_a_costo_y_a_precio(self):
        crear_variante(stock=5, costo=Decimal(60000), nombre="A")
        crear_variante(stock=2, costo=None, nombre="B")  # sin costo cargado
        crear_variante(stock=0, costo=Decimal(10000), nombre="C")  # sin unidades
        crear_variante(stock=3, costo=Decimal(10000), activa=False, nombre="D")

        datos = servicios.valorizar_inventario()
        self.assertEqual(datos["unidades"], 7)  # A(5) + B(2); no C ni D
        self.assertEqual(datos["valor_costo"], Decimal(300000))  # solo A
        self.assertEqual(datos["valor_venta"], Decimal(700000))  # A(5)+B(2) x 100.000
        self.assertEqual(datos["sin_costo"], 1)

    def test_sin_unidades_devuelve_ceros(self):
        datos = servicios.valorizar_inventario()
        self.assertEqual(datos["unidades"], 0)
        self.assertIsNone(datos["porcentaje"])


class VentaYDevolucionBitacoraTests(TestCase):
    """Las ventas y devoluciones dejan su movimiento en la bitácora."""

    def setUp(self):
        self.variante = crear_variante(stock=10)
        zona, _ = ZonaEnvio.objects.get_or_create(
            nombre="Área metropolitana de Bucaramanga",
            defaults={"tarifa": Decimal(8000),
                      "envio_gratis_desde": Decimal(150000),
                      "tiempo_estimado": "Mismo día"},
        )
        self.municipio, _ = MunicipioSantander.objects.get_or_create(
            nombre="Bucaramanga", defaults={"zona": zona},
        )

    def _pedido(self):
        return Pedido.objects.create(
            nombre="María Pérez", email="maria@ejemplo.com",
            telefono="3001112233", municipio=self.municipio,
            direccion="Cra 15 # 42-10", subtotal=Decimal(100000),
            total=Decimal(100000), metodo_pago="contraentrega",
            estado="preparacion",
        )

    def test_venta_deja_movimiento(self):
        from orders.models import ItemPedido

        pedido = self._pedido()
        ItemPedido.objects.create(
            pedido=pedido, variante=self.variante,
            producto_nombre=self.variante.producto.nombre,
            sku=self.variante.sku, cantidad=2,
            precio_unitario=Decimal(100000),
        )
        devolver_stock(pedido)
        mov = MovimientoStock.objects.get()
        self.assertEqual(mov.motivo, "devolucion")
        self.assertEqual(mov.cantidad, 2)
        self.assertEqual(mov.referencia, pedido.numero)

    def test_cancelar_pedido_devuelve_con_movimiento(self):
        from orders.models import ItemPedido

        pedido = self._pedido()
        ItemPedido.objects.create(
            pedido=pedido, variante=self.variante,
            producto_nombre=self.variante.producto.nombre,
            sku=self.variante.sku, cantidad=2,
            precio_unitario=Decimal(100000),
        )
        self.variante.stock = 8
        self.variante.save(update_fields=["stock"])
        cambiar_estado(pedido, "cancelado", nota="Se canceló.")
        self.variante.refresh_from_db()
        self.assertEqual(self.variante.stock, 10)
        self.assertEqual(MovimientoStock.objects.get().motivo, "devolucion")

    def test_devolver_dos_veces_no_duplica(self):
        pedido = self._pedido()
        devolver_stock(pedido)
        devolver_stock(pedido)
        self.assertEqual(MovimientoStock.objects.count(), 0)  # no había ítems


class AdminInventarioTests(TestCase):
    """El admin registra ajustes, recepciones y filtra alertas de stock."""

    def setUp(self):
        self.duena = Usuario.objects.create_user(
            username="duena", email="duena@ejemplo.com",
            password="clave-segura-123", is_staff=True, is_superuser=True,
        )
        self.site = AdminSite()

    def test_alta_de_movimiento_ajusta_stock(self):
        variante = crear_variante(stock=10)
        admin_obj = MovimientoStockAdmin(MovimientoStock, self.site)
        self.client.force_login(self.duena)
        respuesta = self.client.post(
            reverse("admin:inventory_movimientostock_add"),
            {"variante": variante.pk, "cantidad": "-2", "motivo": "merma",
             "referencia": "", "nota": "Se dañaron"},
            follow=True,
        )
        self.assertEqual(respuesta.status_code, 200)
        variante.refresh_from_db()
        self.assertEqual(variante.stock, 8)
        mov = MovimientoStock.objects.get()
        self.assertEqual(mov.motivo, "merma")
        self.assertEqual(mov.usuario, self.duena)

    def test_no_puede_dejar_stock_negativo_desde_el_form(self):
        variante = crear_variante(stock=2)
        self.client.force_login(self.duena)
        self.client.post(
            reverse("admin:inventory_movimientostock_add"),
            {"variante": variante.pk, "cantidad": "-5", "motivo": "merma",
             "referencia": "", "nota": ""},
        )
        variante.refresh_from_db()
        self.assertEqual(variante.stock, 2)  # rechazado por validación
        self.assertEqual(MovimientoStock.objects.count(), 0)

    def test_ajuste_de_stock_desde_la_lista_queda_en_bitacora(self):
        variante = crear_variante(stock=10)
        admin_obj = VarianteInventarioAdmin(Variante, self.site)
        obj = Variante.objects.get(pk=variante.pk)
        obj.stock = 7
        form = type("F", (), {"changed_data": {"stock": True}})()
        request = type("R", (), {"user": self.duena})()
        admin_obj.save_model(request, obj, form, change=True)
        mov = MovimientoStock.objects.get()
        self.assertEqual(mov.cantidad, -3)
        self.assertEqual(mov.motivo, "ajuste")
        self.assertEqual(mov.stock_resultante, 7)

    def test_accion_recibir_del_admin(self):
        from django.test import RequestFactory

        proveedor = Proveedor.objects.create(nombre="Textiles Andes")
        variante = crear_variante(stock=4)
        orden = OrdenCompra.objects.create(proveedor=proveedor)
        OrdenCompraItem.objects.create(
            orden=orden, variante=variante,
            cantidad=10, costo_unitario=Decimal(60000),
        )
        admin_obj = OrdenCompraAdmin(OrdenCompra, self.site)
        request = RequestFactory().get("/admin/")
        request.user = self.duena
        # Almacén de mensajes mínimo (no hay middleware de sesión en la prueba)
        request._messages = type(
            "M", (), {"add": lambda self, *args, **kwargs: None},
        )()
        admin_obj.accion_recibir(request, OrdenCompra.objects.filter(pk=orden.pk))
        variante.refresh_from_db()
        self.assertEqual(variante.stock, 14)

    def test_filtro_de_alerta_stock_bajo(self):
        crear_variante(stock=2, umbral=3, nombre="Bajo")
        crear_variante(stock=10, umbral=3, nombre="Sano")
        crear_variante(stock=0, umbral=3, nombre="Agotado")
        filtro = StockBajoFilter(None, {"alerta_stock": ["bajo"]}, Variante, None)
        filas = list(filtro.queryset(None, Variante.objects.all()))
        self.assertEqual([v.producto.nombre for v in filas], ["Bajo"])
        filtro = StockBajoFilter(None, {"alerta_stock": ["sin"]}, Variante, None)
        filas = list(filtro.queryset(None, Variante.objects.all()))
        self.assertEqual([v.producto.nombre for v in filas], ["Agotado"])

    def test_lista_del_admin_muestra_alertas(self):
        variante = crear_variante(stock=1, umbral=3)
        admin_obj = VarianteInventarioAdmin(Variante, self.site)
        self.assertTrue(admin_obj.alerta(variante))
        self.assertEqual(
            admin_obj.valor_en_stock(variante), "sin costo",
        )
        variante.costo = Decimal(60000)
        variante.save(update_fields=["costo"])
        self.assertEqual(
            admin_obj.valor_en_stock(variante), "$60.000",
        )

    def test_bitacora_no_se_edita_ni_se_borra(self):
        admin_obj = MovimientoStockAdmin(MovimientoStock, self.site)
        request = type("R", (), {"user": self.duena})()
        self.assertFalse(admin_obj.has_change_permission(request))
        self.assertFalse(admin_obj.has_delete_permission(request))
