"""Pruebas de notificaciones y plantillas de correo de marca."""
from decimal import Decimal

from django.core import mail
from django.test import TestCase

from core import correos
from core.models import SiteConfig
from notifications.models import PlantillaCorreo
from orders.models import Pedido
from shipping.models import MunicipioSantander, ZonaEnvio


class PlantillaCorreoTests(TestCase):
    def setUp(self):
        self.zona = ZonaEnvio.objects.create(
            nombre="Bucaramanga", tarifa=Decimal(8000),
        )
        self.municipio = MunicipioSantander.objects.create(
            nombre="Bucaramanga", zona=self.zona,
        )
        self.pedido = Pedido.objects.create(
            nombre="Laura Morales",
            email="laura@ejemplo.com",
            telefono="3001234567",
            municipio=self.municipio,
            direccion="Calle 35 # 20-10",
            total=Decimal(120000),
            estado="pagado",
        )

    def test_plantilla_personaliza_asunto(self):
        PlantillaCorreo.objects.create(
            clave="confirmacion_pedido",
            asunto="¡Gracias {{ pedido.nombre }}! Tu pedido {{ pedido.numero }} fue recibido",
            cuerpo="Estamos alistando tus prendas con mucho cariño.",
            activo=True,
        )
        correos.confirmacion_pedido(self.pedido)
        self.assertEqual(len(mail.outbox), 1)
        enviado = mail.outbox[0]
        self.assertIn("¡Gracias Laura Morales!", enviado.subject)
        self.assertIn(self.pedido.numero, enviado.subject)
        self.assertIn("Estamos alistando tus prendas con mucho cariño.", enviado.body)

    def test_plantilla_inactiva_usa_predeterminada(self):
        PlantillaCorreo.objects.create(
            clave="confirmacion_pedido",
            asunto="Asunto inactivo",
            cuerpo="Cuerpo inactivo",
            activo=False,
        )
        correos.confirmacion_pedido(self.pedido)
        self.assertEqual(len(mail.outbox), 1)
        enviado = mail.outbox[0]
        self.assertNotIn("Asunto inactivo", enviado.subject)
        self.assertIn(f"Pedido {self.pedido.numero} confirmado", enviado.subject)
