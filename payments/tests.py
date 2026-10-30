"""Pruebas de la pasarela simulada: aprobado, rechazado, pendiente y ocultación."""
from decimal import Decimal

from django.test import TestCase, override_settings
from django.urls import reverse

from catalog.models import Producto, Variante
from orders.models import HistorialPedido, Pedido
from payments.models import Pago
from shipping.models import MunicipioSantander, ZonaEnvio


def crear_pedido(estado="pendiente", metodo="pasarela"):
    """Pedido mínimo para probar la pantalla de pago (sin pasar por checkout)."""
    zona = ZonaEnvio.objects.create(
        nombre="Área metropolitana de Bucaramanga",
        tarifa=Decimal(8000), envio_gratis_desde=Decimal(150000),
        tiempo_estimado="Mismo día en Bucaramanga",
    )
    municipio = MunicipioSantander.objects.create(nombre="Bucaramanga", zona=zona)
    return Pedido.objects.create(
        nombre="María Pérez",
        email="maria@ejemplo.com",
        telefono="3001112233",
        municipio=municipio,
        direccion="Cra 15 # 42-10, apto 302",
        subtotal=Decimal(200000),
        costo_envio=Decimal(0),
        total=Decimal(200000),
        metodo_pago=metodo,
        estado=estado,
    )


@override_settings(PASARELA_SIMULADA=True)
class PantallaDePagoTests(TestCase):
    """La pantalla simulada muestra el monto y registra el resultado elegido."""

    def test_aprobado_mueve_el_pedido_a_pagado_y_deja_historial(self):
        pedido = crear_pedido()
        self.client.post(
            reverse("payments:resultado", args=[pedido.numero]),
            {"resultado": "aprobado"},
        )
        pedido.refresh_from_db()
        self.assertEqual(pedido.estado, "pagado")
        self.assertTrue(
            HistorialPedido.objects.filter(
                pedido=pedido, estado="pagado", nota__icontains="Pasarela simulada",
            ).exists()
        )

    def test_rechazado_se_queda_pendiente_y_muestra_error(self):
        pedido = crear_pedido()
        respuesta = self.client.post(
            reverse("payments:resultado", args=[pedido.numero]),
            {"resultado": "rechazado"}, follow=True,
        )
        pedido.refresh_from_db()
        self.assertEqual(pedido.estado, "pendiente")
        contenido = respuesta.content.decode("utf-8", errors="ignore")
        self.assertIn("rechazado", contenido.lower())

    def test_pendiente_se_queda_pendiente_y_muestra_aviso(self):
        pedido = crear_pedido()
        respuesta = self.client.post(
            reverse("payments:resultado", args=[pedido.numero]),
            {"resultado": "pendiente"}, follow=True,
        )
        pedido.refresh_from_db()
        self.assertEqual(pedido.estado, "pendiente")
        contenido = respuesta.content.decode("utf-8", errors="ignore")
        self.assertIn("pendiente", contenido.lower())

    def test_pagina_muestra_monto_y_referencia(self):
        pedido = crear_pedido()
        respuesta = self.client.get(reverse("payments:pagar", args=[pedido.numero]))
        self.assertContains(respuesta, "$200.000")
        self.assertContains(respuesta, pedido.numero)

    def test_pedido_inexistente_da_404(self):
        respuesta = self.client.get(reverse("payments:pagar", args=["CB-999999"]))
        self.assertEqual(respuesta.status_code, 404)

    def test_pedido_pagado_no_vuelve_a_pasar_por_la_pasarela(self):
        pedido = crear_pedido(estado="pagado")
        respuesta = self.client.get(reverse("payments:pagar", args=[pedido.numero]))
        self.assertRedirects(respuesta, reverse("orders:confirmacion", args=[pedido.numero]))

    def test_el_resultado_es_solo_post(self):
        pedido = crear_pedido()
        respuesta = self.client.get(reverse("payments:resultado", args=[pedido.numero]))
        self.assertEqual(respuesta.status_code, 405)
        pedido.refresh_from_db()
        self.assertEqual(pedido.estado, "pendiente")


@override_settings(PASARELA_SIMULADA=False)
class PasarelaDesactivadaTests(TestCase):
    """Sin simulación (producción sin llaves) la pantalla se oculta."""

    def test_pagar_redirige_a_la_confirmacion(self):
        pedido = crear_pedido()
        respuesta = self.client.get(reverse("payments:pagar", args=[pedido.numero]))
        self.assertRedirects(respuesta, reverse("orders:confirmacion", args=[pedido.numero]))

    def test_el_resultado_no_cambia_el_estado(self):
        pedido = crear_pedido()
        self.client.post(
            reverse("payments:resultado", args=[pedido.numero]),
            {"resultado": "aprobado"},
        )
        pedido.refresh_from_db()
        self.assertEqual(pedido.estado, "pendiente")


class PagoAdminTests(TestCase):
    """El Pago guardado en el admin refleja el monto y el método del pedido."""

    def test_pago_se_crea_desde_el_pedido(self):
        pedido = crear_pedido(estado="pagado")
        pago = Pago.objects.create(
            pedido=pedido, metodo="pasarela", monto=pedido.total,
            estado="aprobado", referencia=pedido.numero,
        )
        self.assertIn(pedido.numero, str(pago))
        self.assertEqual(pago.comprobante_nombre, "")


def _crear_checkout_fixture():
    """Zona, municipio y variante para completar el checkout en pruebas."""
    zona = ZonaEnvio.objects.create(
        nombre="Área metropolitana de Bucaramanga",
        tarifa=Decimal(8000), envio_gratis_desde=Decimal(150000),
        tiempo_estimado="Mismo día en Bucaramanga",
    )
    municipio = MunicipioSantander.objects.create(nombre="Bucaramanga", zona=zona)
    prod = Producto.objects.create(nombre="Sábanas dobles bonitas", estado="publicado")
    variante = Variante.objects.create(
        producto=prod, precio=Decimal(100000), stock=10,
    )
    return municipio, variante


class FlujoDeCompraTests(TestCase):
    """El checkout lleva a la pasarela solo cuando el cliente la elige."""

    def _datos(self, metodo):
        return {
            "nombre": "María Pérez",
            "email": "maria@ejemplo.com",
            "telefono": "3001112233",
            "cedula": "1023456789",
            "mayor_de_edad": "on",
            "autoriza_datos": "on",
            "municipio": "Bucaramanga",
            "direccion": "Cra 15 # 42-10, apto 302",
            "barrio": "Cabecera",
            "metodo_pago": metodo,
        }

    def _comprar(self, metodo):
        _, variante = _crear_checkout_fixture()
        self.client.post(
            reverse("cart:agregar"), {"sku": variante.sku, "cantidad": 1},
            HTTP_REFERER="/tienda/",
        )
        return self.client.post(reverse("orders:checkout"), self._datos(metodo))

    @override_settings(PASARELA_SIMULADA=True)
    def test_checkout_con_pasarela_lleva_a_la_pantalla_de_pago(self):
        respuesta = self._comprar("pasarela")
        pedido = Pedido.objects.get()
        self.assertEqual(respuesta.status_code, 302)
        self.assertEqual(respuesta["Location"], reverse("payments:pagar", args=[pedido.numero]))
        self.assertEqual(pedido.estado, "pendiente")

    @override_settings(PASARELA_SIMULADA=True)
    def test_checkout_contraentrega_no_pasa_por_la_pasarela(self):
        respuesta = self._comprar("contraentrega")
        pedido = Pedido.objects.get()
        self.assertEqual(respuesta["Location"], reverse("orders:confirmacion", args=[pedido.numero]))
        self.assertEqual(pedido.estado, "preparacion")
        self.assertFalse(Pago.objects.exists())

    @override_settings(PASARELA_SIMULADA=False)
    def test_checkout_sin_pasarela_no_acepta_ese_metodo(self):
        respuesta = self._comprar("pasarela")
        # El form no ofrece pasarela: el pedido no se crea y vuelve al checkout
        self.assertEqual(respuesta.status_code, 200)
        self.assertFalse(Pedido.objects.exists())
        self.assertContains(respuesta, "pasarela no es una de las opciones")

