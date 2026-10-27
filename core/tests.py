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
