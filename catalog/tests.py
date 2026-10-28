"""Pruebas del catálogo: búsqueda, filtros, ficha, ofertas y seed_demo."""
from decimal import Decimal

from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse

from catalog.filters import aplicar_busqueda, aplicar_filtros, aplicar_orden, queryset_base
from catalog.models import Categoria, Producto, Variante
from catalog.search import busqueda_tolerante, expandir_consulta, normalizar_texto
from promotions.models import Cupon


def crear_producto(nombre, precio=100000, oferta=None, talla="Queen", color="Blanco",
                   stock=10, **kwargs):
    prod = Producto.objects.create(nombre=nombre, estado="publicado", **kwargs)
    Variante.objects.create(
        producto=prod, precio=Decimal(precio),
        precio_oferta=Decimal(oferta) if oferta else None,
        talla=talla, color=color, stock=stock,
    )
    return prod


class NormalizacionTests(TestCase):
    def test_quita_tildes_y_mayusculas(self):
        self.assertEqual(normalizar_texto("Sábanas Reina"), "sabanas reina")
        self.assertEqual(normalizar_texto("  EDREDÓN   plumón "), "edredon plumon")
        self.assertEqual(normalizar_texto(""), "")


class SinonimosTests(TestCase):
    def test_expande_consulta(self):
        from catalog.models import Sinonimo

        Sinonimo.objects.create(palabras="edredón, cubrelecho, plumón")
        resultado = expandir_consulta("edredón", [Sinonimo.objects.get().lista()])
        self.assertIn("edredon", resultado)
        self.assertIn("cubrelecho", resultado)
        self.assertIn("plumon", resultado)


class ToleranciaTests(TestCase):
    def test_encuentra_por_rapidez_de_ortografia(self):
        candidatos = ["edredon doble plumon", "juego de sabanas 400 hilos"]
        self.assertIn("edredon doble plumon", busqueda_tolerante("edreon", candidatos))
        self.assertEqual(busqueda_tolerante("xyzabc", candidatos), [])


class BusquedaTests(TestCase):
    def setUp(self):
        self.prod = crear_producto("Juego de sábanas 400 hilos", oferta=160000)

    def test_busca_sin_tildes(self):
        qs = aplicar_busqueda(queryset_base(), "sabanas")
        self.assertIn(self.prod, qs)

    def test_busca_con_tildes(self):
        qs = aplicar_busqueda(queryset_base(), "sábanas")
        self.assertIn(self.prod, qs)

    def test_registra_busquedas_vacias(self):
        from catalog.models import BusquedaSinResultados

        aplicar_busqueda(queryset_base(), "producto que no existe xyz")
        self.assertTrue(BusquedaSinResultados.objects.filter(consulta__icontains="xyz").exists())


class FiltrosTests(TestCase):
    def setUp(self):
        self.sabana = crear_producto("Sábanas Queen", oferta=None, talla="Queen", color="Blanco")
        self.edredon = crear_producto("Edredón en oferta", precio=200000, oferta=150000,
                                      talla="Doble", color="Gris")
        self.agotado = crear_producto("Producto agotado", precio=300000, stock=0, talla="King", color="Azul")

    def test_filtro_en_oferta(self):
        qs, activos = aplicar_filtros(queryset_base(), {"oferta": "1"})
        self.assertIn(self.edredon, qs)
        self.assertNotIn(self.sabana, qs)
        self.assertEqual(len(activos), 1)

    def test_filtro_talla(self):
        qs, _ = aplicar_filtros(queryset_base(), {"talla": "Queen"})
        self.assertIn(self.sabana, qs)
        self.assertNotIn(self.edredon, qs)

    def test_filtro_disponible_excluye_agotado(self):
        qs, _ = aplicar_filtros(queryset_base(), {"disponible": "1"})
        self.assertNotIn(self.agotado, qs)

    def test_orden_por_precio(self):
        qs = aplicar_orden(queryset_base(), "menor-precio")
        self.assertEqual(list(qs)[0], self.sabana)


class PrecioTests(TestCase):
    def test_precio_final_y_ahorro(self):
        prod = crear_producto("Sábanas en oferta", precio=100000, oferta=80000)
        variante = prod.variantes.first()
        self.assertEqual(variante.precio_final, Decimal(80000))
        self.assertEqual(variante.ahorro_pct, 20)
        self.assertEqual(prod.precio_tachado, Decimal(100000))
        self.assertEqual(prod.ahorro_pct, 20)
        self.assertTrue(prod.tiene_oferta)

    def test_oferta_mayor_o_igual_se_ignora(self):
        prod = crear_producto("Oferta mal hecha", precio=100000, oferta=100000)
        self.assertIsNone(prod.variantes.first().precio_oferta)


class VistasTests(TestCase):
    def setUp(self):
        self.prod = crear_producto("Sábanas dobles bonitas", oferta=90000)
        self.cat = Categoria.objects.create(nombre="Sábanas", slug="sabanas")
        self.prod.categorias.add(self.cat)
        self.prod.save()

    def test_tienda_lista_productos(self):
        r = self.client.get(reverse("catalog:tienda"))
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "Sábanas dobles bonitas")

    def test_ficha_de_producto(self):
        r = self.client.get(self.prod.get_absolute_url())
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "Sábanas dobles bonitas")
        self.assertContains(r, "application/ld+json")  # schema.org

    def test_ficha_con_foto_sin_miniatura_no_cae(self):
        # Regresión: las fotos marcador (SVG) no generan miniatura; la ficha debe
        # servir la foto principal en vez de fallar con ValueError.
        from catalog.models import FotoProducto

        FotoProducto.objects.create(producto=self.prod, imagen="productos/marcador.svg")
        r = self.client.get(self.prod.get_absolute_url())
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "productos/marcador.svg")

    def test_categoria(self):
        r = self.client.get(self.cat.get_absolute_url())
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "Sábanas dobles bonitas")

    def test_busqueda_vacia_sin_resultados_no_revienta(self):
        r = self.client.get(reverse("catalog:buscar"), {"q": "zzzznoexiste"})
        self.assertEqual(r.status_code, 200)

    def test_autocomplete_htmx(self):
        r = self.client.get(reverse("catalog:autocomplete"), {"q": "sabanas"},
                            headers={"hx-request": "true"})
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "Sábanas dobles bonitas")

    def test_inicio_muestra_secciones(self):
        r = self.client.get(reverse("core:home"))
        self.assertContains(r, "Ofertas de la semana")
        self.assertContains(r, "Categorías")

    def test_requiere_inicio_de_sesion_para_admin(self):
        r = self.client.get("/admin/")
        self.assertEqual(r.status_code, 302)


class SeedDemoTests(TestCase):
    def test_seed_crea_datos(self):
        call_command("seed_demo")
        self.assertGreaterEqual(Categoria.objects.filter(padre=None).count(), 8)
        self.assertGreaterEqual(Producto.objects.filter(estado="publicado").count(), 40)
        self.assertGreaterEqual(Variante.objects.count(), 50)
        # Se puede ejecutar dos veces sin duplicar
        call_command("seed_demo")
        self.assertGreaterEqual(Producto.objects.filter(estado="publicado").count(), 40)


class SuscripcionTests(TestCase):
    def test_suscripcion_genera_cupon_unico(self):
        Cupon.objects.create(codigo="BIENVENIDA10", es_bienvenida=True, valor=Decimal(10))
        r = self.client.post(reverse("catalog:suscribir"), {"email": "persona@ejemplo.com"})
        self.assertEqual(r.status_code, 302)
        cupon = Cupon.objects.exclude(codigo="BIENVENIDA10").get()
        self.assertTrue(cupon.codigo.startswith("BIENVENIDA-"))
        self.assertEqual(cupon.max_usos, 1)
        # El código se muestra en el mensaje de confirmación
        from django.contrib.messages import get_messages

        textos = " ".join(str(m) for m in get_messages(r.wsgi_request))
        self.assertIn(cupon.codigo, textos)

    def test_suscripcion_repetida_no_duplica_cupones(self):
        Cupon.objects.create(codigo="BIENVENIDA10", es_bienvenida=True, valor=Decimal(10))
        url = reverse("catalog:suscribir")
        self.client.post(url, {"email": "persona@ejemplo.com"})
        r = self.client.post(url, {"email": "persona@ejemplo.com"})
        self.assertEqual(Cupon.objects.exclude(codigo="BIENVENIDA10").count(), 1)
        from django.contrib.messages import get_messages

        textos = " ".join(str(m) for m in get_messages(r.wsgi_request))
        self.assertIn("ya estaba suscrito", textos)

    def test_suscripcion_sin_plantilla_no_falla(self):
        r = self.client.post(reverse("catalog:suscribir"), {"email": "otra@ejemplo.com"})
        self.assertEqual(r.status_code, 302)
        self.assertEqual(Cupon.objects.count(), 0)

    def test_suscripcion_email_invalido(self):
        r = self.client.post(reverse("catalog:suscribir"), {"email": "no-es-correo"})
        self.assertEqual(r.status_code, 302)
        self.assertEqual(Cupon.objects.count(), 0)
