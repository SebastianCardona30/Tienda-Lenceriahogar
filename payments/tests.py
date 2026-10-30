"""Pruebas de la pasarela simulada: aprobado, rechazado, pendiente y ocultación."""
from decimal import Decimal

from django.test import TestCase, override_settings
from django.urls import reverse

from catalog.models import Producto, Variante
from core.models import SiteConfig
from orders.models import HistorialPedido, Pedido
from payments.models import Pago
from shipping.models import MunicipioSantander, ZonaEnvio


def crear_pedido(estado="pendiente", metodo="pasarela"):
    """Pedido mínimo para probar la pantalla de pago (sin pasar por checkout)."""
    zona, _ = ZonaEnvio.objects.get_or_create(
        nombre="Área metropolitana de Bucaramanga",
        defaults={
            "tarifa": Decimal(8000), "envio_gratis_desde": Decimal(150000),
            "tiempo_estimado": "Mismo día en Bucaramanga",
        },
    )
    municipio, _ = MunicipioSantander.objects.get_or_create(
        nombre="Bucaramanga", defaults={"zona": zona},
    )
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
    zona, _ = ZonaEnvio.objects.get_or_create(
        nombre="Área metropolitana de Bucaramanga",
        defaults={
            "tarifa": Decimal(8000), "envio_gratis_desde": Decimal(150000),
            "tiempo_estimado": "Mismo día en Bucaramanga",
        },
    )
    municipio, _ = MunicipioSantander.objects.get_or_create(
        nombre="Bucaramanga", defaults={"zona": zona},
    )
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


def _archivo_imagen(nombre="comprobante.png", tamano=2048):
    """Imagen PNG válida generada en memoria con Pillow."""
    from io import BytesIO

    from PIL import Image
    from django.core.files.uploadedfile import SimpleUploadedFile

    if nombre.lower().endswith(".pdf"):
        contenido = b"%PDF-1.4\n" + b"0" * 300
        return SimpleUploadedFile(nombre, contenido, content_type="application/pdf")

    buffer = BytesIO()
    Image.new("RGB", (32, 32), "white").save(buffer, format="PNG")
    contenido = buffer.getvalue() + b"0" * max(0, tamano - len(buffer.getvalue()))
    return SimpleUploadedFile(nombre, contenido, content_type="image/png")


def _configurar_medios():
    """Publica un medio de pago manual (marcador, no dato real)."""
    config = SiteConfig.get()
    config.pago_nequi = "Nequi: 300 111 2233 — [TITULAR]"
    config.save()
    return config


class ComprobanteDeTransferenciaTests(TestCase):
    """Transferencia/Nequi/Daviplata: el cliente sube comprobante y queda por verificar."""

    def setUp(self):
        _configurar_medios()
        self.pedido = crear_pedido(estado="pendiente", metodo="transferencia")
        self.url = reverse("payments:comprobante", args=[self.pedido.numero])

    def test_la_pagina_muestra_los_datos_de_la_cuenta(self):
        respuesta = self.client.get(self.url)
        self.assertContains(respuesta, "Nequi: 300 111 2233")

    def test_subir_comprobante_valido_pasa_a_por_verificar(self):
        respuesta = self.client.post(
            self.url, {"comprobante": _archivo_imagen()},
            follow=True,
        )
        self.pedido.refresh_from_db()
        self.assertEqual(self.pedido.estado, "por_verificar")
        self.assertTrue(
            HistorialPedido.objects.filter(
                pedido=self.pedido, estado="por_verificar",
            ).exists()
        )
        self.assertContains(respuesta, "revisando")
        pago = Pago.objects.get()
        self.assertEqual(pago.monto, self.pedido.total)
        self.assertTrue(pago.comprobante)

    def test_acepta_pdf(self):
        self.client.post(self.url, {"comprobante": _archivo_imagen("pagos.pdf")})
        self.pedido.refresh_from_db()
        self.assertEqual(self.pedido.estado, "por_verificar")

    def test_archivo_que_no_es_imagen_ni_pdf_no_pasa(self):
        from django.core.files.uploadedfile import SimpleUploadedFile

        archivo = SimpleUploadedFile("malicioso.txt", b"no soy imagen",
                                     content_type="text/plain")
        respuesta = self.client.post(self.url, {"comprobante": archivo})
        self.pedido.refresh_from_db()
        self.assertEqual(self.pedido.estado, "pendiente")
        self.assertContains(respuesta, "Solo aceptamos")
        self.assertFalse(Pago.objects.exists())

    def test_archivo_mas_grande_de_5mb_no_pasa(self):
        archivo = _archivo_imagen("grande.png", tamano=6 * 1024 * 1024)
        respuesta = self.client.post(self.url, {"comprobante": archivo})
        self.pedido.refresh_from_db()
        self.assertEqual(self.pedido.estado, "pendiente")
        self.assertContains(respuesta, "5 MB")

    def test_reemplazar_comprobante_no_duplica_pagos(self):
        self.client.post(self.url, {"comprobante": _archivo_imagen()})
        self.client.post(self.url, {"comprobante": _archivo_imagen("otro.png")})
        self.assertEqual(Pago.objects.count(), 1)

    def test_pedido_de_otro_metodo_no_muestra_comprobante(self):
        otro = crear_pedido(estado="pendiente", metodo="pasarela")
        respuesta = self.client.get(
            reverse("payments:comprobante", args=[otro.numero]), follow=True,
        )
        self.assertContains(respuesta, "no espera comprobante")

    def test_pedido_pagado_no_recibe_comprobante(self):
        self.pedido.estado = "pagado"
        self.pedido.save()
        respuesta = self.client.get(self.url, follow=True)
        self.assertContains(respuesta, "ya fue pagado")

    def test_sin_datos_de_cuenta_no_ofrece_transferencia(self):
        config = SiteConfig.get()
        config.pago_nequi = ""
        config.pago_daviplata = ""
        config.pago_transferencia = ""
        config.save()
        respuesta = self.client.get(self.url, follow=True)
        self.assertContains(respuesta, "no está habilitada")

    def test_checkout_sin_datos_no_ofrece_transferencia(self):
        config = SiteConfig.get()
        config.pago_nequi = ""
        config.save()
        _, variante = _crear_checkout_fixture()
        self.client.post(
            reverse("cart:agregar"), {"sku": variante.sku, "cantidad": 1},
            HTTP_REFERER="/tienda/",
        )
        respuesta = self.client.post(
            reverse("orders:checkout"),
            {
                "nombre": "María Pérez", "email": "maria@ejemplo.com",
                "telefono": "3001112233", "mayor_de_edad": "on",
                "autoriza_datos": "on", "municipio": "Bucaramanga",
                "direccion": "Cra 15 # 42-10", "metodo_pago": "transferencia",
            },
        )
        self.assertContains(respuesta, "transferencia no es una de las opciones")


class AccionesDelAdminTests(TestCase):
    """Aprobar o rechazar un pago con un clic mueve el pedido correspondiente."""

    def _request(self):
        from django.contrib.auth import get_user_model
        from django.test import RequestFactory

        usuario = get_user_model().objects.create_superuser(
            "admin", "admin@ejemplo.com", "clave12345",
        )
        peticion = RequestFactory().post("/")
        peticion.user = usuario
        # El request de prueba no pasa por el middleware de mensajes;
        # CookieStorage no necesita sesión (evita el fallback).
        from django.contrib.messages.storage.cookie import CookieStorage

        peticion._messages = CookieStorage(peticion)
        return peticion

    def test_aprobar_pasa_el_pedido_a_pagado(self):
        from django.contrib import admin

        pedido = crear_pedido(estado="por_verificar", metodo="transferencia")
        pago = Pago.objects.create(
            pedido=pedido, metodo="transferencia", monto=pedido.total,
            estado="pendiente",
        )
        accion = admin.site._registry[Pago].aprobar_pagos
        accion(self._request(), Pago.objects.filter(pk=pago.pk))
        pago.refresh_from_db()
        pedido.refresh_from_db()
        self.assertEqual(pago.estado, "aprobado")
        self.assertEqual(pedido.estado, "pagado")

    def test_rechazar_vuelve_el_pedido_a_pendiente(self):
        from django.contrib import admin

        pedido = crear_pedido(estado="por_verificar", metodo="transferencia")
        pago = Pago.objects.create(
            pedido=pedido, metodo="transferencia", monto=pedido.total,
            estado="pendiente",
        )
        accion = admin.site._registry[Pago].rechazar_pagos
        accion(self._request(), Pago.objects.filter(pk=pago.pk))
        pago.refresh_from_db()
        pedido.refresh_from_db()
        self.assertEqual(pago.estado, "rechazado")
        self.assertEqual(pedido.estado, "pendiente")
        self.assertTrue(
            HistorialPedido.objects.filter(
                pedido=pedido, estado="pendiente", nota__icontains="rechazado",
            ).exists()
        )

