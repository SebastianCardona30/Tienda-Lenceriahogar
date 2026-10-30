"""Pruebas de envíos: zonas, cobertura y municipios de Santander."""
from decimal import Decimal

from django.core.management import call_command
from django.test import TestCase

from shipping.models import MunicipioSantander, ZonaEnvio, zona_para_municipio


class ZonaEnvioTests(TestCase):
    def setUp(self):
        self.zona = ZonaEnvio.objects.create(
            nombre="Área metropolitana", tarifa=8000, envio_gratis_desde=150000
        )

    def test_cobertura_sin_envio_gratis(self):
        costo, falta, gratis = self.zona.cobertura(Decimal(100000))
        self.assertEqual(costo, Decimal(8000))
        self.assertEqual(falta, Decimal(50000))
        self.assertFalse(gratis)

    def test_cobertura_con_envio_gratis(self):
        costo, falta, gratis = self.zona.cobertura(Decimal(150000))
        self.assertEqual(costo, 0)
        self.assertEqual(falta, 0)
        self.assertTrue(gratis)

    def test_zona_sin_umbral_nunca_es_gratis(self):
        zona = ZonaEnvio.objects.create(nombre="Sin umbral", tarifa=12000)
        costo, falta, gratis = zona.cobertura(Decimal(999999))
        self.assertEqual(costo, Decimal(12000))
        self.assertIsNone(falta)
        self.assertFalse(gratis)


class MunicipiosTests(TestCase):
    def test_seed_carga_los_87_municipios(self):
        call_command("seed_municipios")
        self.assertEqual(MunicipioSantander.objects.count(), 87)

    def test_seed_es_idempotente(self):
        call_command("seed_municipios")
        call_command("seed_municipios")
        self.assertEqual(MunicipioSantander.objects.count(), 87)

    def test_area_metropolitana_asignada(self):
        call_command("seed_municipios")
        muni = MunicipioSantander.objects.get(nombre="Floridablanca")
        self.assertIn("metropolitana", muni.zona.nombre.lower())
        resto = MunicipioSantander.objects.get(nombre="Málaga")
        self.assertIn("resto", resto.zona.nombre.lower())

    def test_zona_para_municipio_por_nombre(self):
        call_command("seed_municipios")
        zona = zona_para_municipio("bucaramanga")
        self.assertIsNotNone(zona)
        self.assertIn("metropolitana", zona.nombre.lower())

    def test_zona_para_municipio_desconocido(self):
        call_command("seed_municipios")
        self.assertIsNone(zona_para_municipio("Bogotá"))

    def test_todos_los_municipios_tienen_zona(self):
        call_command("seed_municipios")
        sin_zona = MunicipioSantander.objects.filter(zona__isnull=True).count()
        self.assertEqual(sin_zona, 0)
