"""Pruebas del checkout: 3 pasos, pedido, stock, cupón y volver a comprar."""
from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from catalog.models import Producto, Variante
from core.models import SiteConfig
from orders.models import HistorialPedido, ItemPedido, Pedido
from promotions.models import Cupon, UsoCupon
from shipping.models import MunicipioSantander, ZonaEnvio

Usuario = get_user_model()


def crear_variante(nombre="Sábanas dobles bonitas", precio=100000, stock=10):
    prod = Producto.objects.create(nombre=nombre, estado="publicado")
    return Variante.objects.create(producto=prod, precio=Decimal(precio), stock=stock)


class CheckoutTestCase(TestCase):
    def setUp(self):
        zona = ZonaEnvio.objects.create(
            nombre="Área metropolitana de Bucaramanga",
            tarifa=Decimal(8000), envio_gratis_desde=Decimal(150000),
            tiempo_estimado="Mismo día en Bucaramanga",
        )
        self.municipio = MunicipioSantander.objects.create(nombre="Bucaramanga", zona=zona)
        self.variante = crear_variante()
        # Un carrito con 2 unidades (subtotal 200.000 → envío gratis en metro)
        self.agregar_al_carrito(self.variante, 2)

    def agregar_al_carrito(self, variante, cantidad=1):
        self.client.post(
            reverse("cart:agregar"), {"sku": variante.sku, "cantidad": cantidad},
            HTTP_REFERER="/tienda/",
        )

    def datos(self, **extra):
        datos = {
            "nombre": "María Pérez",
            "email": "maria@ejemplo.com",
            "telefono": "3001112233",
            "cedula": "1023456789",
            "mayor_de_edad": "on",
            "autoriza_datos": "on",
            "municipio": "Bucaramanga",
            "direccion": "Cra 15 # 42-10, apto 302",
            "barrio": "Cabecera",
            "indicaciones": "Portón negro",
            "metodo_pago": "contraentrega",
        }
        datos.update(extra)
        return datos


class PasoPrevioTests(CheckoutTestCase):
    def _vaciar_carrito(self):
        session = self.client.session
        session["carrito"] = {"lineas": {}, "cupon": "", "municipio": "",
                              "guardados": []}
        session.save()

    def test_carrito_vacio_no_entra_al_checkout(self):
        self._vaciar_carrito()
        r = self.client.get(reverse("orders:checkout"))
        self.assertEqual(r.status_code, 302)
        self.assertEqual(r["Location"], reverse("cart:pagina"))

    def test_checkout_se_muestra_con_carrito(self):
        r = self.client.get(reverse("orders:checkout"))
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "Tus datos")
        self.assertContains(r, "¿A dónde llegamos?")
        self.assertContains(r, "Cómo vas a pagar")
        self.assertContains(r, "mayor de edad")  # casilla obligatoria


class ConfirmarPedidoTests(CheckoutTestCase):
    def test_invitado_puede_comprar(self):
        r = self.client.post(reverse("orders:checkout"), self.datos())
        pedido = Pedido.objects.get()
        self.assertEqual(r["Location"], reverse("orders:confirmacion",
                                               args=[pedido.numero]))
        self.assertIsNone(pedido.usuario)  # compró como invitado
        self.assertEqual(pedido.nombre, "María Pérez")
        self.assertEqual(pedido.municipio, self.municipio)
        self.assertEqual(pedido.total, Decimal(200000))  # envío gratis por umbral
        self.assertEqual(pedido.costo_envio, Decimal(0))
        # Ítems congelados
        item = pedido.items.get()
        self.assertEqual(item.cantidad, 2)
        self.assertEqual(item.precio_unitario, Decimal(100000))
        self.assertEqual(item.sku, self.variante.sku)
        # Stock descontado
        self.variante.refresh_from_db()
        self.assertEqual(self.variante.stock, 8)
        # Carrito limpio
        self.assertEqual(self.client.session["carrito"]["lineas"], {})
        # Historial
        self.assertEqual(HistorialPedido.objects.filter(pedido=pedido).count(), 1)

    def test_contraentrega_entra_en_preparacion(self):
        self.client.post(reverse("orders:checkout"),
                         self.datos(metodo_pago="contraentrega"))
        self.assertEqual(Pedido.objects.get().estado, "preparacion")

    def test_transferencia_queda_pendiente(self):
        # La transferencia solo se ofrece si el negocio tiene datos de cuenta
        config = SiteConfig.get()
        config.pago_nequi = "300 111 2233 — Lencería de Hogar [MARCADOR]"
        config.save()
        self.client.post(reverse("orders:checkout"),
                         self.datos(metodo_pago="transferencia"))
        self.assertEqual(Pedido.objects.get().estado, "pendiente")

    def test_metodo_pago_invalido_no_crea_pedido(self):
        # El formulario valida la lista de métodos; una opción inventada no pasa
        r = self.client.post(reverse("orders:checkout"),
                             self.datos(metodo_pago="tarjeta-secreta"))
        self.assertEqual(Pedido.objects.count(), 0)
        self.assertEqual(r.status_code, 200)  # vuelve al formulario con el error

    def test_falta_mayor_de_edad(self):
        r = self.client.post(reverse("orders:checkout"),
                             self.datos(mayor_de_edad=""))
        self.assertEqual(Pedido.objects.count(), 0)
        self.assertContains(r, "mayor de edad")

    def test_falta_aceptar_terminos(self):
        r = self.client.post(reverse("orders:checkout"), self.datos(autoriza_datos=""))
        self.assertEqual(Pedido.objects.count(), 0)
        self.assertContains(r, "política de datos")

    def test_municipio_fuera_de_santander(self):
        r = self.client.post(reverse("orders:checkout"),
                             self.datos(municipio="Bogotá"))
        self.assertEqual(Pedido.objects.count(), 0)
        self.assertContains(r, "Santander")

    def test_stock_insuficiente_bloquea(self):
        # El carrito tiene 2 pero alguien más compró y quedó 1
        self.variante.stock = 1
        self.variante.save()
        r = self.client.post(reverse("orders:checkout"), self.datos())
        self.assertEqual(Pedido.objects.count(), 0)
        self.assertContains(r, "solo quedan")

    def test_envio_cobrado_fuera_del_umbral(self):
        # Carrito de 100.000 (< 150.000) → cobra $8.000
        session = self.client.session
        session["carrito"] = {
            "lineas": {self.variante.sku: 1}, "cupon": "", "municipio": "Bucaramanga",
            "guardados": [],
        }
        session.save()
        self.client.post(reverse("orders:checkout"), self.datos())
        pedido = Pedido.objects.get()
        self.assertEqual(pedido.costo_envio, Decimal(8000))
        self.assertEqual(pedido.total, Decimal(108000))
        self.assertEqual(pedido.zona_nombre, "Área metropolitana de Bucaramanga")

    def test_cupon_se_registra(self):
        Cupon.objects.create(codigo="PRUEBA10", tipo="porcentaje", valor=Decimal(10))
        session = self.client.session
        session["carrito"] = {
            "lineas": {self.variante.sku: 1}, "cupon": "PRUEBA10",
            "municipio": "Bucaramanga", "guardados": [],
        }
        session.save()
        self.client.post(reverse("orders:checkout"), self.datos())
        pedido = Pedido.objects.get()
        self.assertEqual(pedido.cupon_codigo, "PRUEBA10")
        self.assertEqual(pedido.descuento_cupon, Decimal(10000))
        self.assertEqual(UsoCupon.objects.filter(cupon__codigo="PRUEBA10").count(), 1)

    def test_registro_autenticado_asocia_el_pedido(self):
        usuario = Usuario.objects.create_user(
            username="maria@ejemplo.com", email="maria@ejemplo.com",
            first_name="María", password="clave-segura-123",
        )
        self.client.force_login(usuario)
        self.client.post(reverse("orders:checkout"), self.datos())
        pedido = Pedido.objects.get()
        self.assertEqual(pedido.usuario, usuario)

    def test_pedido_requiere_carrito(self):
        session = self.client.session
        session["carrito"] = {"lineas": {}, "cupon": "", "municipio": "",
                              "guardados": []}
        session.save()
        r = self.client.post(reverse("orders:checkout"), self.datos())
        self.assertEqual(Pedido.objects.count(), 0)
        self.assertEqual(r.status_code, 200)  # vuelve al formulario con aviso


class ConfirmacionTests(CheckoutTestCase):
    def test_pagina_de_confirmacion(self):
        self.client.post(reverse("orders:checkout"), self.datos())
        pedido = Pedido.objects.get()
        r = self.client.get(reverse("orders:confirmacion", args=[pedido.numero]))
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, pedido.numero)
        self.assertContains(r, "Sábanas dobles bonitas")
        self.assertContains(r, "$200.000")

    def test_pedido_inexistente_da_404(self):
        r = self.client.get(reverse("orders:confirmacion", args=["CB-000000"]))
        self.assertEqual(r.status_code, 404)

    def test_numeros_unicos(self):
        self.client.post(reverse("orders:checkout"), self.datos())
        self.agregar_al_carrito(self.variante, 1)
        self.client.post(reverse("orders:checkout"), self.datos())
        self.assertEqual(Pedido.objects.count(), 2)
        self.assertEqual(
            Pedido.objects.values_list("numero", flat=True).count(), 2
        )


class MisPedidosTests(CheckoutTestCase):
    def test_pide_ingreso(self):
        r = self.client.get(reverse("orders:mis_pedidos"))
        self.assertEqual(r.status_code, 302)
        self.assertIn(reverse("accounts:ingreso"), r["Location"])

    def test_lista_solo_los_propios(self):
        propio = Usuario.objects.create_user(
            username="maria@ejemplo.com", email="maria@ejemplo.com",
            password="clave-segura-123",
        )
        otro = Usuario.objects.create_user(
            username="otra@ejemplo.com", email="otra@ejemplo.com", password="x-12345678"
        )
        Pedido.objects.create(
            usuario=propio, nombre="María", email="maria@ejemplo.com",
            telefono="300", municipio=self.municipio, direccion="Cra 1 # 2-3",
            total=Decimal(100000),
        )
        ajeno = Pedido.objects.create(
            usuario=otro, nombre="Otra", email="otra@ejemplo.com",
            telefono="301", municipio=self.municipio, direccion="Cra 9 # 8-7",
            total=Decimal(50000),
        )
        self.client.force_login(propio)
        r = self.client.get(reverse("orders:mis_pedidos"))
        self.assertEqual(r.status_code, 200)
        propio_p = Pedido.objects.get(usuario=propio)
        self.assertContains(r, propio_p.numero)
        self.assertNotContains(r, ajeno.numero)

    def test_volver_a_comprar(self):
        self.client.post(reverse("orders:checkout"), self.datos())
        pedido = Pedido.objects.get()
        usuario = Usuario.objects.create_user(
            username="maria@ejemplo.com", email="maria@ejemplo.com",
            password="clave-segura-123",
        )
        pedido.usuario = usuario
        pedido.save()
        self.client.force_login(usuario)
        # Vacía el carrito y repite el pedido
        session = self.client.session
        session["carrito"] = {"lineas": {}, "cupon": "", "municipio": "",
                              "guardados": []}
        session.save()
        r = self.client.post(reverse("orders:repetir", args=[pedido.numero]))
        self.assertEqual(r.status_code, 302)
        self.assertEqual(
            self.client.session["carrito"]["lineas"][self.variante.sku], 2
        )

    def test_no_repetir_pedido_ajeno(self):
        propio = Usuario.objects.create_user(
            username="maria@ejemplo.com", email="maria@ejemplo.com",
            password="clave-segura-123",
        )
        otro = Usuario.objects.create_user(
            username="otra@ejemplo.com", email="otra@ejemplo.com", password="x-12345678"
        )
        pedido = Pedido.objects.create(
            usuario=propio, nombre="María", email="maria@ejemplo.com",
            telefono="300", municipio=self.municipio, direccion="Cra 1 # 2-3",
        )
        self.client.force_login(otro)
        r = self.client.post(reverse("orders:repetir", args=[pedido.numero]))
        self.assertEqual(r.status_code, 404)


class HabeasDataPedidosTests(CheckoutTestCase):
    def test_borrar_cuenta_anonimiza_los_pedidos(self):
        usuario = Usuario.objects.create_user(
            username="maria@ejemplo.com", email="maria@ejemplo.com",
            password="clave-segura-123",
        )
        self.client.force_login(usuario)
        self.client.post(reverse("orders:checkout"), self.datos())
        pedido = Pedido.objects.get()

        self.client.post(
            reverse("accounts:eliminar_cuenta"), {"password": "clave-segura-123"}
        )
        pedido.refresh_from_db()
        # La venta se conserva…
        self.assertEqual(Pedido.objects.count(), 1)
        self.assertEqual(pedido.total, Decimal(200000))
        # …pero los datos personales no
        self.assertIsNone(pedido.usuario)
        self.assertEqual(pedido.nombre, "Cliente eliminada")
        self.assertEqual(pedido.email, "")
        self.assertEqual(pedido.telefono, "")
        self.assertEqual(pedido.direccion, "")


class ReservaDeStockTests(TestCase):
    """La reserva de stock vence y el comando cancela y devuelve inventario."""

    def setUp(self):
        zona, _ = ZonaEnvio.objects.get_or_create(
            nombre="Área metropolitana de Bucaramanga",
            defaults={"tarifa": Decimal(8000),
                      "envio_gratis_desde": Decimal(150000),
                      "tiempo_estimado": "Mismo día"},
        )
        self.municipio, _ = MunicipioSantander.objects.get_or_create(
            nombre="Bucaramanga", defaults={"zona": zona},
        )
        self.variante = crear_variante(stock=10)

    def _datos(self, metodo):
        return {
            "nombre": "María Pérez", "email": "maria@ejemplo.com",
            "telefono": "3001112233", "mayor_de_edad": "on",
            "autoriza_datos": "on", "municipio": "Bucaramanga",
            "direccion": "Cra 15 # 42-10", "metodo_pago": metodo,
        }

    def _comprar(self, metodo):
        self.client.post(
            reverse("cart:agregar"),
            {"sku": self.variante.sku, "cantidad": 2},
            HTTP_REFERER="/tienda/",
        )
        self.client.post(reverse("orders:checkout"), self._datos(metodo))
        return Pedido.objects.latest("creado")

    def test_pasarela_reserva_15_minutos(self):
        pedido = self._comprar("pasarela")
        self.assertIsNotNone(pedido.reserva_hasta)
        resta = (pedido.reserva_hasta - pedido.creado).total_seconds()
        self.assertAlmostEqual(resta, 15 * 60, delta=60)

    def test_transferencia_reserva_las_horas_del_admin(self):
        config = SiteConfig.get()
        config.pago_nequi = "Nequi: 300 111 2233"
        config.reserva_horas_transferencia = 48
        config.save()
        pedido = self._comprar("transferencia")
        resta = (pedido.reserva_hasta - pedido.creado).total_seconds()
        self.assertAlmostEqual(resta, 48 * 3600, delta=60)

    def test_contraentrega_no_reserva(self):
        pedido = self._comprar("contraentrega")
        self.assertIsNone(pedido.reserva_hasta)
        self.assertEqual(pedido.estado, "preparacion")

    def test_pagar_libera_la_reserva(self):
        from orders.servicios import cambiar_estado

        pedido = self._comprar("pasarela")
        cambiar_estado(pedido, "pagado", nota="Pago aprobado.")
        pedido.refresh_from_db()
        self.assertIsNone(pedido.reserva_hasta)

    def test_cancelar_devuelve_el_stock(self):
        from orders.servicios import cambiar_estado

        pedido = self._comprar("pasarela")
        self.variante.refresh_from_db()
        self.assertEqual(self.variante.stock, 8)
        cambiar_estado(pedido, "cancelado", nota="Vencida.")
        self.variante.refresh_from_db()
        pedido.refresh_from_db()
        self.assertEqual(self.variante.stock, 10)
        self.assertTrue(pedido.stock_devuelto)

    def test_devolver_stock_es_idempotente(self):
        from orders.servicios import cambiar_estado, devolver_stock

        pedido = self._comprar("pasarela")
        cambiar_estado(pedido, "cancelado", nota="Primera.")
        self.assertFalse(devolver_stock(pedido))  # segunda vez no devuelve nada
        self.variante.refresh_from_db()
        self.assertEqual(self.variante.stock, 10)

    def test_cancel_expired_cancela_pedidos_vencidos(self):
        from django.core.management import call_command
        from django.utils import timezone

        pedido = self._comprar("pasarela")
        Pedido.objects.filter(pk=pedido.pk).update(
            reserva_hasta=timezone.now() - timedelta(hours=1),
        )
        call_command("cancel_expired_orders")
        pedido.refresh_from_db()
        self.variante.refresh_from_db()
        self.assertEqual(pedido.estado, "cancelado")
        self.assertEqual(self.variante.stock, 10)
        self.assertTrue(
            HistorialPedido.objects.filter(
                pedido=pedido, estado="cancelado",
                nota__icontains="reserva de stock venció",
            ).exists()
        )

    def test_cancel_expired_no_toca_pagados_ni_a_tiempo(self):
        from django.core.management import call_command
        from django.utils import timezone

        pagado = self._comprar("pasarela")
        cambiar = pagado
        from orders.servicios import cambiar_estado

        cambiar_estado(cambiar, "pagado", nota="Pagado.")
        # Otro pedido aún dentro de la ventana
        session = self.client.session
        session["carrito"] = {"lineas": {}, "cupon": "", "municipio": "",
                              "guardados": []}
        session.save()
        a_tiempo = self._comprar("pasarela")
        Pedido.objects.filter(pk=pagado.pk).update(
            reserva_hasta=timezone.now() - timedelta(hours=1),
        )
        call_command("cancel_expired_orders")
        pagado.refresh_from_db()
        a_tiempo.refresh_from_db()
        self.assertEqual(pagado.estado, "pagado")
        self.assertEqual(a_tiempo.estado, "pendiente")

    def test_simular_no_cancela(self):
        from django.core.management import call_command
        from django.utils import timezone

        pedido = self._comprar("pasarela")
        Pedido.objects.filter(pk=pedido.pk).update(
            reserva_hasta=timezone.now() - timedelta(hours=1),
        )
        call_command("cancel_expired_orders", "--simular")
        pedido.refresh_from_db()
        self.variante.refresh_from_db()
        self.assertEqual(pedido.estado, "pendiente")
        self.assertEqual(self.variante.stock, 8)

    def test_release_stock_reservations_devuelve_stock_huerfano(self):
        from django.core.management import call_command

        pedido = self._comprar("pasarela")
        # Cancelado a mano desde el panel (sin pasar por cambiar_estado)
        Pedido.objects.filter(pk=pedido.pk).update(
            estado="cancelado", stock_devuelto=False,
        )
        call_command("release_stock_reservations")
        self.variante.refresh_from_db()
        pedido.refresh_from_db()
        self.assertEqual(self.variante.stock, 10)
        self.assertTrue(pedido.stock_devuelto)
        # Correrlo otra vez no duplica la devolución
        call_command("release_stock_reservations")
        self.variante.refresh_from_db()
        self.assertEqual(self.variante.stock, 10)


class SeguimientoTests(TestCase):
    """Seguimiento público por número + celular, sin cuenta y sin historial ajeno."""

    def setUp(self):
        zona, _ = ZonaEnvio.objects.get_or_create(
            nombre="Área metropolitana de Bucaramanga",
            defaults={"tarifa": Decimal(8000),
                      "envio_gratis_desde": Decimal(150000),
                      "tiempo_estimado": "Mismo día"},
        )
        municipio, _ = MunicipioSantander.objects.get_or_create(
            nombre="Bucaramanga", defaults={"zona": zona},
        )
        self.pedido = Pedido.objects.create(
            nombre="María Pérez", email="maria@ejemplo.com",
            telefono="+57 300 111 2233", municipio=municipio,
            direccion="Cra 15 # 42-10", subtotal=Decimal(200000),
            total=Decimal(200000), metodo_pago="pasarela", estado="pagado",
        )
        HistorialPedido.objects.create(
            pedido=self.pedido, estado="pagado",
            nota="Pago aprobado por la pasarela.",
        )

    def _consultar(self, numero, telefono):
        return self.client.post(
            reverse("orders:seguimiento"),
            {"numero": numero, "telefono": telefono},
        )

    def test_con_celular_correcto_muestra_el_pedido_y_su_historial(self):
        r = self._consultar(self.pedido.numero, "3001112233")
        self.assertContains(r, self.pedido.numero)
        self.assertContains(r, "Pago aprobado")
        self.assertContains(r, "Pagado")

    def test_acepta_el_celular_con_mas_formatos(self):
        r = self._consultar(self.pedido.numero, "+57 (300) 111-2233")
        self.assertContains(r, self.pedido.numero)

    def test_celular_equivocado_no_muestra_nada(self):
        r = self._consultar(self.pedido.numero, "3019998877")
        # El resultado (historial y estado) no aparece; solo el formulario
        self.assertNotContains(r, "Historial de tu pedido")
        self.assertContains(r, "No encontramos")

    def test_numero_inexistente_no_muestra_nada(self):
        r = self._consultar("CB-999999", "3001112233")
        self.assertNotContains(r, "Historial de tu pedido")
        self.assertContains(r, "No encontramos")

    def test_la_consulta_no_requiere_sesion(self):
        # Tras consultar, la sesión no guarda nada sensible del pedido
        self._consultar(self.pedido.numero, "3001112233")
        self.assertNotIn("pedido", self.client.session)

    def test_pagina_de_consulta_responde_sin_post(self):
        r = self.client.get(reverse("orders:seguimiento"))
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "Seguimiento")


class CorreosDePedidoTests(TestCase):
    """Los correos de marca salen al confirmar, al cambiar estado y al equipo."""

    def setUp(self):
        zona, _ = ZonaEnvio.objects.get_or_create(
            nombre="Área metropolitana de Bucaramanga",
            defaults={"tarifa": Decimal(8000),
                      "envio_gratis_desde": Decimal(150000),
                      "tiempo_estimado": "Mismo día"},
        )
        self.municipio, _ = MunicipioSantander.objects.get_or_create(
            nombre="Bucaramanga", defaults={"zona": zona},
        )
        self.variante = crear_variante(stock=10)
        self.config = SiteConfig.get()
        self.config.email_contacto = "tienda@ejemplo.com"
        self.config.save()

    def _datos(self, metodo="contraentrega"):
        return {
            "nombre": "María Pérez", "email": "maria@ejemplo.com",
            "telefono": "3001112233", "mayor_de_edad": "on",
            "autoriza_datos": "on", "municipio": "Bucaramanga",
            "direccion": "Cra 15 # 42-10", "metodo_pago": metodo,
        }

    def _comprar(self, metodo="contraentrega"):
        self.client.post(
            reverse("cart:agregar"),
            {"sku": self.variante.sku, "cantidad": 1},
            HTTP_REFERER="/tienda/",
        )
        self.client.post(reverse("orders:checkout"), self._datos(metodo))
        return Pedido.objects.get()

    def test_confirmacion_y_aviso_interno(self):
        from django.core import mail

        pedido = self._comprar()
        # Dos correos: confirmación al cliente y aviso al negocio
        self.assertEqual(len(mail.outbox), 2)
        asuntos = [c.subject for c in mail.outbox]
        self.assertTrue(any(pedido.numero in a for a in asuntos))
        destinatarios = [c.to[0] for c in mail.outbox]
        self.assertIn("maria@ejemplo.com", destinatarios)
        self.assertIn("tienda@ejemplo.com", destinatarios)

    def test_confirmacion_incluye_enlace_de_pago_para_pasarela(self):
        from django.core import mail

        pedido = self._comprar("pasarela")
        cliente = [c for c in mail.outbox if "maria@ejemplo.com" in c.to][0]
        self.assertIn(f"/pago/{pedido.numero}/", cliente.body)

    def test_cambio_a_pagado_avisa_al_cliente(self):
        from django.core import mail

        pedido = self._comprar()
        mail.outbox.clear()
        cambiar_estado(pedido, "pagado", nota="Pago aprobado.")
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("maria@ejemplo.com", mail.outbox[0].to)
        self.assertIn("Pagado", mail.outbox[0].subject)

    def test_cambio_a_preparacion_no_envia_correo(self):
        from django.core import mail

        pedido = self._comprar()
        mail.outbox.clear()
        cambiar_estado(pedido, "preparacion", nota="Armando.")
        self.assertEqual(len(mail.outbox), 0)

    def test_sin_email_de_contacto_no_envia_aviso(self):
        from django.core import mail

        self.config.email_contacto = ""
        self.config.save()
        self._comprar()
        destinatarios = [c.to[0] for c in mail.outbox]
        self.assertNotIn("", destinatarios)
        self.assertEqual(len(mail.outbox), 1)  # solo la confirmación al cliente
