from django.test import TestCase
from django.urls import reverse

from core.models import SiteConfig
from core.templatetags.format_tags import cop


class FormatoCOPTests(TestCase):
    def test_formato_colombiano(self):
        self.assertEqual(cop(89900), "$89.900")
        self.assertEqual(cop(1500000), "$1.500.000")
        self.assertEqual(cop(0), "$0")
        self.assertEqual(cop(None), "$0")
        self.assertEqual(cop("no-numero"), "$0")


class SiteConfigTests(TestCase):
    def test_es_singleton(self):
        a = SiteConfig.get()
        a.nombre_negocio = "Otra cosa"
        a.save()
        b = SiteConfig.get()
        self.assertEqual(a.pk, b.pk)
        self.assertEqual(SiteConfig.objects.count(), 1)
        self.assertEqual(b.nombre_negocio, "Otra cosa")


class PaginasTests(TestCase):
    def test_inicio_responde_200(self):
        respuesta = self.client.get(reverse("core:home"))
        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, "Ciudad Bonita")

    def test_pagina_institucional(self):
        respuesta = self.client.get(reverse("core:pagina", args=["quienes-somos"]))
        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, "Quiénes somos")

    def test_pagina_inexistente_es_404(self):
        respuesta = self.client.get("/no-existe/")
        self.assertEqual(respuesta.status_code, 404)


class WhatsAppFlotanteTests(TestCase):
    """El botón flotante lleva un mensaje wa.me prellenado según la página."""

    def setUp(self):
        config = SiteConfig.get()
        config.whatsapp = "573001112233"
        config.save()

    def test_inicio_lleva_mensaje(self):
        r = self.client.get(reverse("core:home"))
        self.assertContains(r, "wa.me/573001112233?text=")
        self.assertContains(r, "recomendaciones")

    def test_tienda_lleva_mensaje(self):
        r = self.client.get(reverse("catalog:tienda"))
        self.assertContains(r, "wa.me/573001112233?text=")
        self.assertContains(r, "recomendaciones")

    def test_ficha_lleva_mensaje_del_producto(self):
        from catalog.models import Producto, Variante
        from decimal import Decimal

        prod = Producto.objects.create(nombre="Edredón polar", estado="publicado")
        Variante.objects.create(producto=prod, precio=Decimal(120000), stock=5)
        r = self.client.get(prod.get_absolute_url())
        self.assertContains(r, "wa.me/573001112233?text=")
        self.assertContains(r, "Edred")  # el nombre viaja en el mensaje

    def test_sin_numero_no_muestra_el_boton(self):
        config = SiteConfig.get()
        config.whatsapp = ""
        config.save()
        r = self.client.get(reverse("core:home"))
        self.assertNotContains(r, "whatsapp-flotante")
