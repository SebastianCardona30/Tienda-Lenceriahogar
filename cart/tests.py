"""Pruebas del carrito: sesión, stock, cupones, envío, WhatsApp y fusión."""
from decimal import Decimal

from django.contrib.messages import get_messages
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse

from cart import servicios
from catalog.models import Producto, Variante
from core.models import SiteConfig
from promotions.models import Cupon


def crear_variante(nombre="Sábanas dobles", precio=100000, stock=10, **kwargs):
    prod = Producto.objects.create(nombre=nombre, estado="publicado")
    return Variante.objects.create(
        producto=prod, precio=Decimal(precio), stock=stock, **kwargs
    )


def mensajes_de(response):
    return " ".join(str(m) for m in get_messages(response.wsgi_request))


class CarritoTestCase(TestCase):
    def agregar(self, variante, cantidad=1):
        return self.client.post(
            reverse("cart:agregar"),
            {"sku": variante.sku, "cantidad": cantidad},
            HTTP_REFERER="/tienda/",
        )

    def en_sesion(self):
        return self.client.session.get("carrito", {})


class SesionTests(CarritoTestCase):
    def test_agregar_persiste_en_sesion(self):
        v = crear_variante()
        r = self.agregar(v, 2)
        self.assertEqual(self.en_sesion()["lineas"][v.sku], 2)
        # Reabre el drawer en la página de origen
        self.assertIn("carrito=1", r["Location"])

    def test_agregar_sin_sku_da_error(self):
        r = self.client.post(
            reverse("cart:agregar"), {"cantidad": 1}, HTTP_REFERER="/tienda/"
        )
        self.assertIn("Elige talla", mensajes_de(r))
        self.assertEqual(self.en_sesion().get("lineas", {}), {})

    def test_agregar_respeta_stock(self):
        v = crear_variante(stock=3)
        r = self.agregar(v, 5)
        self.assertEqual(self.en_sesion()["lineas"][v.sku], 3)
        self.assertIn("solo quedan 3", mensajes_de(r))

    def test_agregar_acumula_hasta_el_stock(self):
        v = crear_variante(stock=5)
        self.agregar(v, 4)
        r = self.agregar(v, 3)
        self.assertEqual(self.en_sesion()["lineas"][v.sku], 5)
        self.assertIn("Ajustamos", mensajes_de(r))

    def test_agregar_agotado_no_entra(self):
        v = crear_variante(stock=0)
        r = self.agregar(v, 1)
        self.assertEqual(self.en_sesion().get("lineas", {}), {})
        self.assertIn("agotado", mensajes_de(r))

    def test_agregar_inexistente(self):
        r = self.client.post(
            reverse("cart:agregar"), {"sku": "NADA", "cantidad": 1},
            HTTP_REFERER="/tienda/",
        )
        self.assertIn("ya no est", mensajes_de(r))

    def test_actualizar_cantidad(self):
        v = crear_variante()
        self.agregar(v, 1)
        self.client.post(
            reverse("cart:actualizar"), {"sku": v.sku, "cantidad": 7},
            HTTP_REFERER=reverse("cart:pagina"),
        )
        self.assertEqual(self.en_sesion()["lineas"][v.sku], 7)

    def test_actualizar_mayor_que_stock_se_limita(self):
        v = crear_variante(stock=2)
        self.agregar(v, 1)
        r = self.client.post(
            reverse("cart:actualizar"), {"sku": v.sku, "cantidad": 10},
            HTTP_REFERER=reverse("cart:pagina"),
        )
        self.assertEqual(self.en_sesion()["lineas"][v.sku], 2)
        self.assertIn("solo quedan 2", mensajes_de(r))

    def test_eliminar_linea(self):
        v = crear_variante()
        self.agregar(v, 2)
        self.client.post(
            reverse("cart:eliminar"), {"sku": v.sku},
            HTTP_REFERER=reverse("cart:pagina"),
        )
        self.assertEqual(self.en_sesion().get("lineas", {}), {})

    def test_guardar_para_despues_y_restaurar(self):
        v = crear_variante()
        self.agregar(v, 2)
        self.client.post(
            reverse("cart:guardar"), {"sku": v.sku},
            HTTP_REFERER=reverse("cart:pagina"),
        )
        self.assertEqual(self.en_sesion().get("lineas", {}), {})
        self.assertEqual(self.en_sesion()["guardados"], [v.sku])
        self.client.post(
            reverse("cart:restaurar"), {"sku": v.sku},
            HTTP_REFERER=reverse("cart:pagina"),
        )
        self.assertEqual(self.en_sesion()["lineas"][v.sku], 1)
        self.assertEqual(self.en_sesion()["guardados"], [])

    def test_stepper_menos_no_borra(self):
        # El botón "−" con cantidad 1 no debe eliminar la línea
        v = crear_variante()
        self.agregar(v, 1)
        self.client.post(
            reverse("cart:actualizar"), {"sku": v.sku, "cantidad": "-1"},
            HTTP_REFERER=reverse("cart:pagina"),
        )
        self.assertEqual(self.en_sesion()["lineas"][v.sku], 1)


class PaginaTests(CarritoTestCase):
    def test_pagina_vacia(self):
        r = self.client.get(reverse("cart:pagina"))
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "Tu carrito est")

    def test_pagina_lista_productos(self):
        v = crear_variante()
        self.agregar(v, 2)
        r = self.client.get(reverse("cart:pagina"))
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "Sábanas dobles")
        self.assertContains(r, v.sku)
        self.assertContains(r, "$200.000")  # total

    def test_drawer_y_contador_en_cualquier_pagina(self):
        v = crear_variante()
        self.agregar(v, 2)
        r = self.client.get(reverse("core:home"))
        self.assertContains(r, 'id="drawer-carrito"')
        self.assertContains(r, 'encabezado__contador')
        self.assertContains(r, ">2<")

    def test_stock_insuficiente_se_ajusta_en_pantalla(self):
        v = crear_variante(precio=100000, stock=2)
        s = self.client.session
        s["carrito"] = {"lineas": {v.sku: 5}, "cupon": "", "municipio": "",
                        "guardados": []}
        s.save()
        r = self.client.get(reverse("cart:pagina"))
        self.assertContains(r, "solo quedan 2")
        self.assertContains(r, "$200.000")  # total con 2 unidades

    def test_linea_de_referencia_fantasma_se_muestra_para_quitar(self):
        s = self.client.session
        s["carrito"] = {"lineas": {"NOEXISTE": 2}, "cupon": "", "municipio": "",
                        "guardados": []}
        s.save()
        r = self.client.get(reverse("cart:pagina"))
        self.assertContains(r, "ya no est")
        self.assertContains(r, "NOEXISTE")
        self.assertContains(r, "Quitar del carrito")


class CuponVistaTests(CarritoTestCase):
    def setUp(self):
        self.v = crear_variante(precio=100000)
        Cupon.objects.create(codigo="PRUEBA10", tipo="porcentaje", valor=Decimal(10))
        self.agregar(self.v, 1)

    def test_cupon_valido_se_aplica(self):
        r = self.client.post(
            reverse("cart:cupon"), {"codigo": "prueba10"},
            HTTP_REFERER=reverse("cart:pagina"),
        )
        self.assertIn("aplicado", mensajes_de(r))
        pagina = self.client.get(reverse("cart:pagina"))
        self.assertContains(pagina, "PRUEBA10")
        self.assertContains(pagina, "$90.000")  # 100.000 - 10%

    def test_cupon_inexistente_da_error(self):
        r = self.client.post(
            reverse("cart:cupon"), {"codigo": "NOEXISTE"},
            HTTP_REFERER=reverse("cart:pagina"),
        )
        self.assertIn("no existe", mensajes_de(r))
        pagina = self.client.get(reverse("cart:pagina"))
        self.assertContains(pagina, "$100.000")

    def test_quitar_cupon(self):
        self.client.post(
            reverse("cart:cupon"), {"codigo": "PRUEBA10"},
            HTTP_REFERER=reverse("cart:pagina"),
        )
        r = self.client.post(
            reverse("cart:cupon"), {"codigo": ""},
            HTTP_REFERER=reverse("cart:pagina"),
        )
        self.assertIn("retirado", mensajes_de(r))
        pagina = self.client.get(reverse("cart:pagina"))
        self.assertContains(pagina, "$100.000")


class EnvioTests(CarritoTestCase):
    def setUp(self):
        call_command("seed_municipios")
        self.v = crear_variante(precio=100000, stock=10)
        self.agregar(self.v, 1)  # subtotal 100.000 < 150.000 (gratis metro)

    def test_municipio_calcula_envio_y_falta(self):
        r = self.client.post(
            reverse("cart:municipio"), {"municipio": "Bucaramanga"},
            HTTP_REFERER=reverse("cart:pagina"),
        )
        self.assertIn("listo", mensajes_de(r))
        pagina = self.client.get(reverse("cart:pagina"))
        self.assertContains(pagina, "$8.000")        # tarifa metro
        self.assertContains(pagina, "Te faltan")
        self.assertContains(pagina, "$50.000")       # 150.000 - 100.000
        self.assertContains(pagina, "barra-envio")

    def test_municipio_fuera_de_santander(self):
        r = self.client.post(
            reverse("cart:municipio"), {"municipio": "Bogotá"},
            HTTP_REFERER=reverse("cart:pagina"),
        )
        self.assertIn("Santander", mensajes_de(r))
        self.assertEqual(self.en_sesion().get("municipio", ""), "")

    def test_envio_gratis_por_umbral(self):
        self.agregar(self.v, 1)  # total 200.000 >= 150.000
        self.client.post(
            reverse("cart:municipio"), {"municipio": "Girón"},
            HTTP_REFERER=reverse("cart:pagina"),
        )
        pagina = self.client.get(reverse("cart:pagina"))
        self.assertContains(pagina, "Tu env")

    def test_municipio_sin_zona_avisa(self):
        from shipping.models import MunicipioSantander, ZonaEnvio

        # Municipio real pero sin zona asignada
        muni = MunicipioSantander.objects.create(nombre="Sin Zona Prueba")
        r = self.client.post(
            reverse("cart:municipio"), {"municipio": muni.nombre},
            HTTP_REFERER=reverse("cart:pagina"),
        )
        self.assertIn("listo", mensajes_de(r))
        pagina = self.client.get(reverse("cart:pagina"))
        self.assertContains(pagina, "Todav")

        # Limpieza defensiva (no debería afectar otras pruebas)
        muni.delete()

    def test_total_incluye_envio(self):
        self.client.post(
            reverse("cart:municipio"), {"municipio": "Bucaramanga"},
            HTTP_REFERER=reverse("cart:pagina"),
        )
        pagina = self.client.get(reverse("cart:pagina"))
        # 100.000 + 8.000 de envío
        self.assertContains(pagina, "$108.000")


class WhatsAppTests(CarritoTestCase):
    def setUp(self):
        config = SiteConfig.get()
        config.whatsapp = "573001112233"
        config.save()

    def test_boton_pedido_por_whatsapp(self):
        v = crear_variante(precio=100000)
        self.agregar(v, 2)
        r = self.client.get(reverse("cart:pagina"))
        self.assertContains(r, "wa.me/573001112233")
        self.assertContains(r, "Enviar mi pedido por WhatsApp")
        # El resumen viaja como texto en la URL
        self.assertContains(r, "confirmar")

    def test_drawer_tambien_tiene_whatsapp(self):
        v = crear_variante()
        self.agregar(v, 1)
        r = self.client.get(reverse("core:home"))
        self.assertContains(r, "wa.me/573001112233")


class FusionTests(TestCase):
    def test_fusiona_lineas_sumando(self):
        sesion = {"lineas": {"A": 2, "B": 1}, "cupon": "X", "municipio": "M",
                  "guardados": ["A", "C"]}
        usuario = {"lineas": {"B": 3, "D": 1}, "cupon": "", "municipio": "",
                   "guardados": ["D"]}
        r = servicios.fusionar_carrito(sesion, usuario)
        self.assertEqual(r["lineas"], {"A": 2, "B": 4, "D": 1})
        self.assertEqual(r["cupon"], "X")
        self.assertEqual(r["municipio"], "M")
        self.assertEqual(r["guardados"], ["D", "A", "C"])

    def test_fusiona_con_carritos_vacios(self):
        self.assertEqual(servicios.fusionar_carrito(None, None)["lineas"], {})
        self.assertEqual(
            servicios.fusionar_carrito({"lineas": {"A": 1}}, {})["lineas"],
            {"A": 1},
        )
        self.assertEqual(
            servicios.fusionar_carrito({}, {"lineas": {"A": 1}})["lineas"],
            {"A": 1},
        )
