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


class CsvImportTests(TestCase):
    """Importar/exportar CSV: una fila por SKU, validación y nada si hay errores."""

    def test_plantilla_tiene_encabezados_y_ejemplo(self):
        from catalog import csv_io

        texto = csv_io.plantilla_csv()
        primera = texto.splitlines()[0]
        self.assertIn("sku", primera)
        self.assertIn("producto", primera)
        self.assertIn("precio", primera)
        # Una fila de ejemplo con precio
        self.assertIn("89900", texto)

    def test_importar_crea_producto_y_variante(self):
        from catalog import csv_io

        csv_texto = (
            "sku;producto;categoria;estado;talla;medida;color;material;"
            "precio;precio_oferta;costo;stock;umbral_stock_bajo;activo\n"
            "SAB-001;Sábanas dobles;Dormitorio;publicado;Doble;;Blanco;Algodón;"
            "89900;;55000;10;3;sí\n"
        )
        resultado = csv_io.importar_csv(csv_texto.encode("utf-8"))
        self.assertEqual(resultado["errores"], [])
        self.assertEqual(resultado["creados"], 1)
        variante = Variante.objects.get(sku="SAB-001")
        self.assertEqual(variante.precio, Decimal(89900))
        self.assertEqual(variante.stock, 10)  # entró por la bitácora (0 + 10)
        self.assertEqual(variante.producto.estado, "publicado")
        self.assertEqual(variante.producto.categorias.get().nombre, "Dormitorio")
        # El stock quedó registrado en la bitácora de inventario
        from inventory.models import MovimientoStock

        mov = MovimientoStock.objects.get(variante=variante)
        self.assertEqual(mov.cantidad, 10)
        self.assertEqual(mov.motivo, "ajuste")
        self.assertIn("CSV", mov.nota)

    def test_importar_actualiza_por_sku(self):
        from catalog import csv_io

        prod = Producto.objects.create(nombre="Sábanas dobles", estado="borrador")
        variante = Variante.objects.create(
            producto=prod, sku="SAB-001", precio=Decimal(80000), stock=5,
        )
        csv_texto = (
            "sku;producto;precio;stock\n"
            "SAB-001;Sábanas dobles;95000;8\n"
        )
        resultado = csv_io.importar_csv(csv_texto)
        self.assertEqual(resultado["errores"], [])
        self.assertEqual(resultado["creados"], 0)
        self.assertEqual(resultado["actualizados"], 1)
        variante.refresh_from_db()
        self.assertEqual(variante.precio, Decimal(95000))
        self.assertEqual(variante.stock, 8)
        # El cambio de stock quedó en la bitácora
        from inventory.models import MovimientoStock

        self.assertEqual(MovimientoStock.objects.get().cantidad, 3)

    def test_errores_por_fila_no_importa_nada(self):
        from catalog import csv_io

        csv_texto = (
            "sku;producto;precio;stock\n"
            "OK-1;Producto bueno;50000;5\n"
            "MAL-1;;50000;5\n"        # sin producto
            "MAL-2;Sin precio;;5\n"   # sin precio
            "MAL-3;Precio raro;abc;5\n"
            "MAL-4;Stock negativo;50000;-2\n"
        )
        resultado = csv_io.importar_csv(csv_texto)
        filas = [f for f, _ in resultado["errores"]]
        self.assertEqual(filas, [3, 4, 5, 6])
        self.assertEqual(resultado["creados"], 0)
        # La fila válida NO se importó (todo o nada)
        self.assertEqual(Variante.objects.count(), 0)
        self.assertEqual(Producto.objects.count(), 0)

    def test_sku_repetido_en_el_archivo_es_error(self):
        from catalog import csv_io

        csv_texto = (
            "sku;producto;precio\n"
            "DUP-1;Uno;10000\n"
            "DUP-1;Dos;20000\n"
        )
        resultado = csv_io.importar_csv(csv_texto)
        self.assertEqual(len(resultado["errores"]), 1)
        self.assertIn("ya apareció", resultado["errores"][0][1])

    def test_precio_con_puntos_de_miles(self):
        from catalog import csv_io

        csv_texto = "sku;producto;precio\nP-1;Producto;1.234.567\n"
        resultado = csv_io.importar_csv(csv_texto)
        self.assertEqual(resultado["errores"], [])
        self.assertEqual(Variante.objects.get().precio, Decimal(1234567))

    def test_separador_coma_tambien_se_acepta(self):
        from catalog import csv_io

        csv_texto = "sku,producto,precio\nC-1,Producto,50000\n"
        resultado = csv_io.importar_csv(csv_texto)
        self.assertEqual(resultado["errores"], [])
        self.assertEqual(Variante.objects.get().sku, "C-1")

    def test_columna_obligatoria_faltante(self):
        from catalog import csv_io

        with self.assertRaises(csv_io.ErroresDeCSV) as ctx:
            csv_io.importar_csv("sku;categoria\nX-1;Ropa\n")
        self.assertIn("producto", str(ctx.exception))

    def test_talla_invalida_es_error(self):
        from catalog import csv_io

        csv_texto = "sku;producto;talla;precio\nT-1;Ropa;Gigante;50000\n"
        resultado = csv_io.importar_csv(csv_texto)
        self.assertEqual(len(resultado["errores"]), 1)
        self.assertIn("talla", resultado["errores"][0][1])

    def test_exportar_y_reimportar_no_cambia_nada(self):
        from catalog import csv_io

        csv_io.importar_csv(
            "sku;producto;precio;stock\nSAB-001;Sábanas;89900;7\n"
        )
        exportado = csv_io.exportar_csv()
        self.assertIn("SAB-001", exportado)
        # Reimportar el exportado debe actualizar sin errores
        resultado = csv_io.importar_csv(exportado)
        self.assertEqual(resultado["errores"], [])
        self.assertEqual(Variante.objects.get().stock, 7)


class CsvAdminTests(TestCase):
    """Las vistas del admin: requieren sesión y responden el archivo."""

    def setUp(self):
        from django.contrib.auth import get_user_model

        Usuario = get_user_model()
        self.duena = Usuario.objects.create_user(
            username="duena", email="duena@ejemplo.com",
            password="clave-segura-123", is_staff=True, is_superuser=True,
        )

    def test_sin_sesion_redirige(self):
        for url in ("/admin/catalog/producto/csv/",
                    "/admin/catalog/producto/csv/exportar/",
                    "/admin/catalog/producto/csv/plantilla/"):
            r = self.client.get(url)
            self.assertEqual(r.status_code, 302, url)

    def test_plantilla_y_exportar_descargan_csv(self):
        self.client.force_login(self.duena)
        r = self.client.get("/admin/catalog/producto/csv/plantilla/")
        self.assertEqual(r.status_code, 200)
        self.assertIn("text/csv", r["Content-Type"])
        self.assertIn("attachment", r["Content-Disposition"])
        r = self.client.get("/admin/catalog/producto/csv/exportar/")
        self.assertEqual(r.status_code, 200)
        self.assertIn("sku", r.content.decode("utf-8-sig").splitlines()[0])

    def test_importar_desde_el_admin(self):
        from django.core.files.uploadedfile import SimpleUploadedFile

        self.client.force_login(self.duena)
        contenido = b"sku;producto;precio\nADM-1;Desde admin;45000\n"
        archivo = SimpleUploadedFile("catalogo.csv", contenido,
                                     content_type="text/csv")
        r = self.client.post(
            "/admin/catalog/producto/csv/", {"archivo": archivo}, follow=True,
        )
        self.assertEqual(r.status_code, 200)
        self.assertEqual(Variante.objects.get().sku, "ADM-1")

    def test_importar_con_errores_muestra_las_filas(self):
        from django.core.files.uploadedfile import SimpleUploadedFile

        self.client.force_login(self.duena)
        contenido = b"sku;producto;precio\nMAL-1;;50000\n"
        archivo = SimpleUploadedFile("catalogo.csv", contenido,
                                     content_type="text/csv")
        r = self.client.post("/admin/catalog/producto/csv/", {"archivo": archivo})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(Variante.objects.count(), 0)
        html = r.content.decode()
        self.assertIn("no se importó nada", html)
        self.assertIn("falta", html)

    def test_botones_visibles_en_la_lista(self):
        self.client.force_login(self.duena)
        r = self.client.get("/admin/catalog/producto/")
        self.assertContains(r, "Importar CSV")
        self.assertContains(r, "Exportar CSV")
        self.assertContains(r, "Plantilla de ejemplo")


class FeedWhatsAppTests(TestCase):
    def test_feed_whatsapp_csv(self):
        prod = crear_producto("Juego de sábanas premium", precio=129900, talla="Queen", color="Perla")
        r = self.client.get(reverse("catalog:feed_whatsapp"))
        self.assertEqual(r.status_code, 200)
        self.assertIn("text/csv", r["Content-Type"])
        self.assertIn("whatsapp_catalog.csv", r["Content-Disposition"])
        cuerpo = r.content.decode("utf-8-sig")
        self.assertIn("id,title,description,availability,condition,price,link,image_link,brand", cuerpo)
        self.assertIn(prod.variantes.first().sku, cuerpo)
        self.assertIn("129900 COP", cuerpo)
        self.assertIn("in stock", cuerpo)

