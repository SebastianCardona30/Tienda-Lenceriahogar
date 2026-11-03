"""Pruebas del dashboard: métricas, gráficas y el panel en el admin."""
from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from catalog.models import Categoria, Producto, Variante
from dashboard import servicios
from orders.models import ItemPedido, Pedido
from promotions.models import Cupon, UsoCupon
from shipping.models import MunicipioSantander, ZonaEnvio

Usuario = get_user_model()


def crear_pedido(estado="pagado", hace_dias=0, total=Decimal(100000), **kwargs):
    """Crea un pedido de prueba y (si hace falta) lo retrocede en el tiempo."""
    zona, _ = ZonaEnvio.objects.get_or_create(
        nombre="Área metropolitana de Bucaramanga",
        defaults={"tarifa": Decimal(8000),
                  "envio_gratis_desde": Decimal(150000),
                  "tiempo_estimado": "Mismo día"},
    )
    municipio, _ = MunicipioSantander.objects.get_or_create(
        nombre="Bucaramanga", defaults={"zona": zona},
    )
    pedido = Pedido.objects.create(
        nombre="María Pérez", email="maria@ejemplo.com",
        telefono="3001112233", municipio=municipio,
        direccion="Cra 15 # 42-10", subtotal=total, total=total,
        metodo_pago="pasarela", estado=estado, **kwargs,
    )
    if hace_dias:
        # creado es auto_now_add: hay que moverlo con una consulta directa
        Pedido.objects.filter(pk=pedido.pk).update(
            creado=timezone.now() - timedelta(days=hace_dias)
        )
        pedido.refresh_from_db()
    return pedido


def crear_item(pedido, nombre="Sábanas dobles", cantidad=1,
               precio=Decimal(100000), descuento=Decimal(0), variante=None):
    return ItemPedido.objects.create(
        pedido=pedido, variante=variante, producto_nombre=nombre,
        sku="SKU-TEST", cantidad=cantidad, precio_unitario=precio,
        descuento=descuento,
    )


class VentasPorPeriodoTests(TestCase):
    def test_suma_solo_ventas_hechas_de_hoy(self):
        crear_pedido("pagado")
        crear_pedido("entregado")
        crear_pedido("cancelado")  # no cuenta
        datos = servicios.ventas_por_periodo()
        self.assertEqual(datos["hoy"]["pedidos"], 2)
        self.assertEqual(datos["hoy"]["monto"], Decimal(200000))

    def test_semana_incluye_los_ultimos_dias(self):
        crear_pedido("pagado", hace_dias=3, total=Decimal(50000))
        datos = servicios.ventas_por_periodo()
        self.assertEqual(datos["semana"]["monto"], Decimal(50000))

    def test_mes_incluye_lo_del_mes_en_curso(self):
        pedido = crear_pedido("enviado", total=Decimal(70000))
        # Primer día del mes en curso: sin importar cuándo corra la prueba
        primer_dia = timezone.localtime().replace(
            day=1, hour=0, minute=0, second=0, microsecond=0,
        )
        Pedido.objects.filter(pk=pedido.pk).update(creado=primer_dia)
        datos = servicios.ventas_por_periodo()
        self.assertEqual(datos["mes"]["monto"], Decimal(70000))

    def test_sin_ventas_devuelve_ceros(self):
        datos = servicios.ventas_por_periodo()
        self.assertEqual(datos["hoy"]["monto"], Decimal(0))
        self.assertEqual(datos["semana"]["pedidos"], 0)


class PedidosPorEstadoTests(TestCase):
    def test_trae_todos_los_estados_con_conteo(self):
        crear_pedido("pagado")
        crear_pedido("pagado")
        crear_pedido("pendiente")
        estados = servicios.pedidos_por_estado()
        # Siempre aparecen los 8 estados, aunque estén en 0
        self.assertEqual(len(estados), len(Pedido.ESTADOS))
        conteos = {e["estado"]: e["cantidad"] for e in estados}
        self.assertEqual(conteos["pagado"], 2)
        self.assertEqual(conteos["pendiente"], 1)
        self.assertEqual(conteos["cancelado"], 0)


class RequierenAccionTests(TestCase):
    def test_cuenta_por_verificar_pendientes_por_enviar(self):
        crear_pedido("por_verificar")
        crear_pedido("por_verificar")
        crear_pedido("pendiente")
        crear_pedido("pagado")
        crear_pedido("preparacion")
        crear_pedido("enviado")  # ya salió, no requiere acción
        accion = servicios.requieren_accion()
        self.assertEqual(accion["por_verificar"], 2)
        self.assertEqual(accion["pendiente_pago"], 1)
        self.assertEqual(accion["por_enviar"], 2)


class StockBajoTests(TestCase):
    def _variante(self, stock, umbral, publicado=True):
        prod = Producto.objects.create(
            nombre=f"Producto {stock}-{umbral}",
            estado="publicado" if publicado else "borrador",
        )
        return Variante.objects.create(
            producto=prod, precio=Decimal(80000), stock=stock,
            umbral_stock_bajo=umbral,
        )

    def test_lista_variantes_en_o_bajo_el_umbral(self):
        self._variante(stock=2, umbral=3)   # alerta
        self._variante(stock=3, umbral=3)   # alerta (límite)
        self._variante(stock=10, umbral=3)  # bien
        bajas = servicios.stock_bajo()
        self.assertEqual(len(bajas), 2)

    def test_no_incluye_productos_borrador(self):
        self._variante(stock=1, umbral=3, publicado=False)
        self.assertEqual(servicios.stock_bajo(), [])


class MasVendidosTests(TestCase):
    def test_ordena_por_unidades(self):
        p1 = crear_pedido("pagado")
        p2 = crear_pedido("entregado")
        crear_item(p1, nombre="Toallas", cantidad=2)
        crear_item(p1, nombre="Almohadas", cantidad=1)
        crear_item(p2, nombre="Toallas", cantidad=3)
        filas = servicios.mas_vendidos()
        self.assertEqual(filas[0]["producto_nombre"], "Toallas")
        self.assertEqual(filas[0]["unidades"], 5)
        self.assertEqual(filas[1]["producto_nombre"], "Almohadas")

    def test_calcula_monto_como_precio_por_cantidad_menos_descuento(self):
        pedido = crear_pedido("pagado")
        crear_item(pedido, cantidad=2, precio=Decimal(50000),
                   descuento=Decimal(10000))
        fila = servicios.mas_vendidos()[0]
        self.assertEqual(fila["monto"], Decimal(90000))


class IngresosYMargenTests(TestCase):
    def _variante_con_costo(self, costo):
        prod = Producto.objects.create(nombre="Sábanas", estado="publicado")
        return Variante.objects.create(
            producto=prod, precio=Decimal(100000), costo=costo, stock=5,
        )

    def test_resta_el_costo_de_las_variantes(self):
        variante = self._variante_con_costo(Decimal(60000))
        pedido = crear_pedido("pagado", total=Decimal(100000))
        crear_item(pedido, variante=variante, precio=Decimal(100000))
        datos = servicios.ingresos_y_margen()
        self.assertEqual(datos["ingresos"], Decimal(100000))
        self.assertEqual(datos["costos"], Decimal(60000))
        self.assertEqual(datos["margen"], Decimal(40000))
        self.assertFalse(datos["estimado"])

    def test_se_marca_estimado_si_falta_costo(self):
        pedido = crear_pedido("pagado", total=Decimal(100000))
        crear_item(pedido)  # variante vacía → sin costo
        datos = servicios.ingresos_y_margen()
        self.assertTrue(datos["estimado"])
        self.assertEqual(datos["margen"], Decimal(100000))


class OtrasMetricasTests(TestCase):
    def test_clientes_nuevos_excluye_al_personal(self):
        Usuario.objects.create_user(
            username="cliente@ejemplo.com", email="cliente@ejemplo.com",
            password="clave-segura-123",
        )
        Usuario.objects.create_user(
            username="dueña", email="duena@ejemplo.com",
            password="clave-segura-123", is_staff=True,
        )
        self.assertEqual(servicios.clientes_nuevos(), 1)

    def test_cupones_mas_usados(self):
        cupon = Cupon.objects.create(
            codigo="BIENVENIDA", tipo="porcentaje", valor=10,
        )
        UsoCupon.objects.create(cupon=cupon, email="a@ejemplo.com")
        UsoCupon.objects.create(cupon=cupon, email="b@ejemplo.com")
        filas = servicios.cupones_mas_usados()
        self.assertEqual(filas[0]["cupon__codigo"], "BIENVENIDA")
        self.assertEqual(filas[0]["n"], 2)

    def test_busquedas_sin_resultados_solo_sin_revisar(self):
        from catalog.models import BusquedaSinResultados

        BusquedaSinResultados.objects.create(consulta="sábanas azules")
        BusquedaSinResultados.objects.create(consulta="toallas", revisada=True)
        filas = servicios.busquedas_sin_resultados()
        self.assertEqual(len(filas), 1)
        self.assertEqual(filas[0].consulta, "sábanas azules")

    def test_ventas_por_dia_trae_14_etiquetas(self):
        crear_pedido("pagado")
        crear_pedido("pagado", hace_dias=10, total=Decimal(50000))
        serie = servicios.ventas_por_dia()
        self.assertEqual(len(serie["etiquetas"]), 14)
        self.assertEqual(len(serie["montos"]), 14)
        self.assertEqual(serie["montos"][-1], 100000.0)  # hoy
        self.assertEqual(serie["montos"][-11], 50000.0)  # hace 10 días

    def test_panel_completo_trae_todo(self):
        datos = servicios.panel_completo()
        for clave in ("ventas", "estados", "accion", "stock_bajo",
                      "mas_vendidos", "margen", "clientes_nuevos",
                      "cupones", "busquedas", "serie_ventas", "valorizado"):
            self.assertIn(clave, datos)


class PanelAdminTests(TestCase):
    """El panel se pinta en el index del admin (solo personal autenticado)."""

    def setUp(self):
        self.duena = Usuario.objects.create_user(
            username="duena", email="duena@ejemplo.com",
            password="clave-segura-123", is_staff=True, is_superuser=True,
        )

    def test_sin_sesion_redirige_al_login(self):
        respuesta = self.client.get(reverse("admin:index"))
        self.assertEqual(respuesta.status_code, 302)
        self.assertIn("/admin/login/", respuesta.url)

    def test_el_panel_se_pinta_para_el_personal(self):
        crear_pedido("pagado")
        self.client.force_login(self.duena)
        respuesta = self.client.get(reverse("admin:index"))
        self.assertEqual(respuesta.status_code, 200)
        html = respuesta.content.decode()
        self.assertIn("Ventas de hoy", html)
        self.assertIn("Inventario valorizado", html)
        self.assertIn("cb-grafica-ventas", html)
        self.assertIn("cb-grafica-estados", html)
        self.assertIn("chart.umd.min.js", html)  # Chart.js local, sin CDN
        self.assertNotIn("cdn.jsdelivr", html)

    def test_los_datos_de_las_graficas_van_en_json(self):
        crear_pedido("pagado")
        self.client.force_login(self.duena)
        html = self.client.get(reverse("admin:index")).content.decode()
        self.assertIn('"etiquetas"', html)
        self.assertIn('"montos"', html)


class ReportesTests(TestCase):
    """Reportes CSV: tipos, contenido, fechas y descarga desde el admin."""

    def setUp(self):
        self.zona, _ = ZonaEnvio.objects.get_or_create(
            nombre="Área metropolitana de Bucaramanga",
            defaults={"tarifa": Decimal(8000),
                      "envio_gratis_desde": Decimal(150000),
                      "tiempo_estimado": "Mismo día"},
        )
        self.municipio, _ = MunicipioSantander.objects.get_or_create(
            nombre="Bucaramanga", defaults={"zona": self.zona},
        )

    def _pedido(self, estado="pagado", total=Decimal(100000), hace_dias=0):
        pedido = Pedido.objects.create(
            nombre="María Pérez", email="maria@ejemplo.com",
            telefono="3001112233", municipio=self.municipio,
            direccion="Cra 15 # 42-10", subtotal=total, total=total,
            metodo_pago="pasarela", estado=estado,
        )
        if hace_dias:
            Pedido.objects.filter(pk=pedido.pk).update(
                creado=timezone.now() - timedelta(days=hace_dias)
            )
            pedido.refresh_from_db()
        return pedido

    def _item(self, pedido, nombre="Sábanas dobles", cantidad=1,
              precio=Decimal(100000), descuento=Decimal(0)):
        return ItemPedido.objects.create(
            pedido=pedido, producto_nombre=nombre, sku="SKU-1",
            cantidad=cantidad, precio_unitario=precio, descuento=descuento,
        )

    def test_todos_los_tipos_generan_encabezados(self):
        from dashboard import reportes

        for clave in reportes.TIPOS:
            titulo, encabezados, filas = reportes.generar_reporte(clave)
            self.assertTrue(titulo)
            self.assertTrue(encabezados)
            self.assertIsInstance(filas, list)

    def test_ventas_por_periodo_trae_las_ventas(self):
        from dashboard import reportes

        pedido = self._pedido()
        self._pedido(estado="cancelado")  # no cuenta
        _e, filas = reportes.ventas_por_periodo()
        self.assertEqual(len(filas), 1)
        self.assertTrue(filas[0][0].startswith("CB-"))  # número aleatorio
        self.assertEqual(filas[0][0], pedido.numero)
        self.assertEqual(filas[0][-1], 100000)  # total

    def test_ventas_por_periodo_respeta_las_fechas(self):
        from dashboard import reportes

        self._pedido(hace_dias=60)
        _e, filas = reportes.ventas_por_periodo()
        self.assertEqual(filas, [])  # fuera de los últimos 30 días
        hace60 = (timezone.localtime().date() - timedelta(days=65)).isoformat()
        _e, filas = reportes.ventas_por_periodo(desde=hace60)
        self.assertEqual(len(filas), 1)

    def test_ventas_por_producto_suma_unidades_y_monto(self):
        from dashboard import reportes

        pedido = self._pedido()
        self._item(pedido, cantidad=2, precio=Decimal(50000),
                   descuento=Decimal(10000))
        _e, filas = reportes.ventas_por_producto()
        self.assertEqual(filas[0][0], "Sábanas dobles")
        self.assertEqual(filas[0][1], 2)   # unidades
        self.assertEqual(filas[0][3], 90000)  # 50.000×2 − 10.000

    def test_ventas_por_categoria_y_proveedor(self):
        from catalog.models import Proveedor
        from dashboard import reportes

        prod = Producto.objects.create(nombre="Sábanas", estado="publicado")
        cat = Categoria.objects.create(nombre="Dormitorio")
        proveedor = Proveedor.objects.create(nombre="Textiles Andes")
        prod.categorias.add(cat)
        prod.proveedor = proveedor
        prod.save()
        variante = Variante.objects.create(
            producto=prod, precio=Decimal(100000), stock=5,
        )
        pedido = self._pedido()
        ItemPedido.objects.create(
            pedido=pedido, variante=variante, producto_nombre="Sábanas",
            sku=variante.sku, cantidad=1, precio_unitario=Decimal(100000),
        )
        _e, filas = reportes.ventas_por_categoria()
        self.assertEqual(filas[0][0], "Dormitorio")
        _e, filas = reportes.ventas_por_proveedor()
        self.assertEqual(filas[0][0], "Textiles Andes")

    def test_ventas_por_municipio(self):
        from dashboard import reportes

        self._pedido(total=Decimal(80000))
        _e, filas = reportes.ventas_por_municipio()
        self.assertEqual(filas[0][0], "Bucaramanga")
        self.assertEqual(filas[0][1], 1)
        self.assertEqual(filas[0][2], 80000)

    def test_reporte_de_cupones(self):
        from dashboard import reportes
        from promotions.models import Cupon, UsoCupon

        cupon = Cupon.objects.create(codigo="AHORRO10", tipo="valor",
                                     valor=Decimal(5000))
        UsoCupon.objects.create(cupon=cupon, email="a@ejemplo.com")
        pedido = self._pedido()
        Pedido.objects.filter(pk=pedido.pk).update(
            cupon_codigo="AHORRO10", descuento_cupon=Decimal(5000)
        )
        _e, filas = reportes.cupones_usados()
        self.assertEqual(filas[0][0], "AHORRO10")
        self.assertEqual(filas[0][1], 1)
        self.assertEqual(filas[0][2], 5000)

    def test_inventario_valorizado(self):
        from dashboard import reportes

        prod = Producto.objects.create(nombre="Toallas", estado="publicado")
        Variante.objects.create(
            producto=prod, precio=Decimal(40000), costo=Decimal(25000),
            stock=6,
        )
        _e, filas = reportes.inventario_valorizado()
        fila = next(f for f in filas if f[1] == "Toallas")
        self.assertEqual(fila[4], 6)          # stock
        self.assertEqual(fila[6], 25000)      # costo unitario
        self.assertEqual(fila[7], 150000)     # valor a costo
        self.assertEqual(fila[9], 240000)     # valor a venta

    def test_a_csv_usa_punto_y_coma_y_bom(self):
        from dashboard import reportes

        texto = reportes.a_csv(["a", "b"], [[1, "ñ"]])
        self.assertTrue(texto.startswith("﻿"))
        self.assertIn("a;b", texto)
        self.assertIn("1;ñ", texto)


class VistasReportesTests(TestCase):
    """La página y la descarga requieren sesión de personal."""

    def setUp(self):
        from django.contrib.auth import get_user_model

        Usuario = get_user_model()
        self.duena = Usuario.objects.create_user(
            username="duena", email="duena@ejemplo.com",
            password="clave-segura-123", is_staff=True, is_superuser=True,
        )
        self.cliente = Usuario.objects.create_user(
            username="cliente", email="cliente@ejemplo.com",
            password="clave-segura-123",
        )

    def test_sin_sesion_redirige_al_login(self):
        for url in ("/admin/reportes/", "/admin/reportes/csv/?tipo=cupones"):
            r = self.client.get(url)
            self.assertEqual(r.status_code, 302, url)

    def test_cliente_normal_no_ve_reportes(self):
        self.client.force_login(self.cliente)
        r = self.client.get("/admin/reportes/")
        # admin_view redirige a /admin/login/ si el usuario no es staff
        self.assertIn(r.status_code, (302, 404))
        r = self.client.get("/admin/reportes/csv/?tipo=inventario")
        self.assertIn(r.status_code, (302, 404))

    def test_pagina_lista_todos_los_tipos(self):
        from dashboard import reportes

        self.client.force_login(self.duena)
        r = self.client.get("/admin/reportes/")
        self.assertEqual(r.status_code, 200)
        for clave, (titulo, _f, _u) in reportes.TIPOS.items():
            self.assertContains(r, titulo)

    def test_descarga_el_csv_elegido(self):
        self.client.force_login(self.duena)
        r = self.client.get("/admin/reportes/csv/?tipo=inventario")
        self.assertEqual(r.status_code, 200)
        self.assertIn("text/csv", r["Content-Type"])
        self.assertIn("attachment", r["Content-Disposition"])
        cuerpo = r.content.decode("utf-8-sig")
        self.assertIn("sku", cuerpo.splitlines()[0])

    def test_tipo_desconocido_da_404(self):
        self.client.force_login(self.duena)
        r = self.client.get("/admin/reportes/csv/?tipo=inexistente")
        self.assertEqual(r.status_code, 404)

    def test_el_panel_enlaza_a_los_reportes(self):
        self.client.force_login(self.duena)
        r = self.client.get(reverse("admin:index"))
        self.assertContains(r, "Descargar reportes CSV")
