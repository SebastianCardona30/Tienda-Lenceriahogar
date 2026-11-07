import time

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


class PaginaLegalTests(TestCase):
    """Páginas institucionales y legales editables desde el admin."""

    def test_pagina_legal_desde_base_de_datos(self):
        from core.models import PaginaLegal

        PaginaLegal.objects.create(
            slug="terminos",
            titulo="Términos y Condiciones Ciudad Bonita 2026",
            bajada="Términos vigentes para compras en Santander.",
            contenido="<p>Todos los productos tienen garantía legal de 3 meses.</p>",
            publicada=True,
        )
        r = self.client.get(reverse("core:pagina", args=["terminos"]))
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "Términos y Condiciones Ciudad Bonita 2026")
        self.assertContains(r, "garantía legal de 3 meses")

    def test_pagina_legal_despublicada_hace_fallback(self):
        from core.models import PaginaLegal

        PaginaLegal.objects.create(
            slug="quienes-somos",
            titulo="Título Despublicado",
            contenido="Contenido oculto",
            publicada=False,
        )
        r = self.client.get(reverse("core:pagina", args=["quienes-somos"]))
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "Quiénes somos")  # fallback del diccionario
        self.assertNotContains(r, "Título Despublicado")

    def test_siteconfig_analitica_opcional(self):
        config = SiteConfig.get()
        config.ga4_id = "G-TEST12345"
        config.meta_pixel_id = "987654321"
        config.save()
        config.refresh_from_db()
        self.assertEqual(config.ga4_id, "G-TEST12345")
        self.assertEqual(config.meta_pixel_id, "987654321")


class SEOTests(TestCase):
    """Pruebas de sitemap.xml, robots.txt y Open Graph."""

    def test_robots_txt(self):
        r = self.client.get("/robots.txt")
        self.assertEqual(r.status_code, 200)
        self.assertIn("text/plain", r["Content-Type"])
        self.assertContains(r, "User-agent: *")
        self.assertContains(r, "Disallow: /admin/")
        self.assertContains(r, "/sitemap.xml")

    def test_sitemap_xml(self):
        from catalog.models import Categoria, Producto

        cat = Categoria.objects.create(nombre="Almohadas", activa=True)
        Producto.objects.create(nombre="Almohada Memory Foam", estado="publicado")

        r = self.client.get("/sitemap.xml")
        self.assertEqual(r.status_code, 200)
        self.assertIn("xml", r["Content-Type"])
        self.assertContains(r, "<urlset")
        self.assertContains(r, "/tienda/")
        self.assertContains(r, cat.get_absolute_url())


class TextosLegalesYCookiesTests(TestCase):
    def test_paginas_legales_tienen_contenido_y_nota_profesional(self):
        for slug in ("terminos", "privacidad", "cambios-y-devoluciones", "cookies"):
            r = self.client.get(reverse("core:pagina", args=[slug]))
            self.assertEqual(r.status_code, 200, f"Error en página {slug}")
            self.assertContains(r, "profesional del derecho")

    def test_retracto_5_dias_habiles_presente(self):
        r = self.client.get(reverse("core:pagina", args=["cambios-y-devoluciones"]))
        self.assertContains(r, "cinco (5) días hábiles")

    def test_banner_cookies_en_base(self):
        r = self.client.get(reverse("core:home"))
        self.assertContains(r, "cb-banner-cookies")
        self.assertContains(r, "Solo necesarias")
        self.assertContains(r, "Aceptar todas")


class BackupDBTests(TestCase):
    def test_backup_db_ejecuta_y_crea_carpeta(self):
        import os
        import tempfile
        from django.core.management import call_command

        with tempfile.TemporaryDirectory() as tmpdir:
            call_command("backup_db", destino=tmpdir)
            archivos = list(os.walk(tmpdir))
            # Se creó al menos la subcarpeta backup_*
            self.assertTrue(len(archivos) > 0)


class SesionPorInactividadTests(TestCase):
    """La sesión se cierra si el usuario deja de usar la tienda un rato."""

    def setUp(self):
        from django.contrib.auth import get_user_model

        Usuario = get_user_model()
        self.usuario = Usuario.objects.create_user(
            username="prueba_inactiva", password="Clave-Prueba-123"
        )

    def _login(self):
        self.client.force_login(self.usuario)

    def _envejecer_sesion(self, minutos=31):
        sesion = self.client.session
        sesion["ultima_actividad"] = time.time() - (minutos * 60)
        sesion.save()

    def test_sesion_vencida_cierra_y_redirige(self):
        self._login()
        self._envejecer_sesion()
        r = self.client.get(reverse("core:home"))
        self.assertEqual(r.status_code, 302)
        self.assertEqual(r["Location"], reverse("accounts:ingreso"))
        self.assertFalse(r.wsgi_request.user.is_authenticated)
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_sesion_vencida_muestra_aviso(self):
        self._login()
        self._envejecer_sesion()
        r = self.client.get(reverse("core:home"), follow=True)
        self.assertContains(r, "inactividad")

    def test_sesion_reciente_sigue_viva(self):
        self._login()
        r = self.client.get(reverse("core:home"))
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.wsgi_request.user.is_authenticated)

    def test_invitado_no_pierde_su_sesion(self):
        # El carrito de invitado no tiene credenciales: no se debe cerrar
        sesion = self.client.session
        sesion["ultima_actividad"] = time.time() - (31 * 60)
        sesion["marca_prueba"] = "ok"
        sesion.save()
        r = self.client.get(reverse("core:home"))
        self.assertEqual(r.status_code, 200)
        self.assertEqual(self.client.session.get("marca_prueba"), "ok")

    def test_peticion_htmx_recibe_401_sin_redireccion(self):
        self._login()
        self._envejecer_sesion()
        r = self.client.get(reverse("core:home"), HTTP_HX_REQUEST="true")
        self.assertEqual(r.status_code, 401)
        self.assertNotIn("_auth_user_id", self.client.session)



