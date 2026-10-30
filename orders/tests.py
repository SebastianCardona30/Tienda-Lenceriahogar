"""Pruebas del checkout: 3 pasos, pedido, stock, cupón y volver a comprar."""
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from catalog.models import Producto, Variante
from core.models import SiteConfig
from orders.models import HistorialPedido, ItemPedido, Pedido
from promotions.models import Cupon, UsoCupon
from shipping.models import MunicipioSantander, ZonaEnvio

Usuario = get_user_model()


def crear_variante(nombre="Sábanas dobles bonitas", precio=100000, stock=10):
    prod = Producto.objects.create(nombre=nombre, estado="publicado")
    return Variante.objects.create(producto=prod, precio=Decimal(precio), stock=stock)


class CheckoutTestCase(TestCase):
    def setUp(self):
        zona = ZonaEnvio.objects.create(
            nombre="Área metropolitana de Bucaramanga",
            tarifa=Decimal(8000), envio_gratis_desde=Decimal(150000),
            tiempo_estimado="Mismo día en Bucaramanga",
        )
        self.municipio = MunicipioSantander.objects.create(nombre="Bucaramanga", zona=zona)
        self.variante = crear_variante()
        # Un carrito con 2 unidades (subtotal 200.000 → envío gratis en metro)
        self.agregar_al_carrito(self.variante, 2)

    def agregar_al_carrito(self, variante, cantidad=1):
        self.client.post(
            reverse("cart:agregar"), {"sku": variante.sku, "cantidad": cantidad},
            HTTP_REFERER="/tienda/",
        )

    def datos(self, **extra):
        datos = {
            "nombre": "María Pérez",
            "email": "maria@ejemplo.com",
            "telefono": "3001112233",
            "cedula": "1023456789",
            "mayor_de_edad": "on",
            "autoriza_datos": "on",
            "municipio": "Bucaramanga",
            "direccion": "Cra 15 # 42-10, apto 302",
            "barrio": "Cabecera",
            "indicaciones": "Portón negro",
            "metodo_pago": "contraentrega",
        }
        datos.update(extra)
        return datos


class PasoPrevioTests(CheckoutTestCase):
    def _vaciar_carrito(self):
        session = self.client.session
        session["carrito"] = {"lineas": {}, "cupon": "", "municipio": "",
                              "guardados": []}
        session.save()

    def test_carrito_vacio_no_entra_al_checkout(self):
        self._vaciar_carrito()
        r = self.client.get(reverse("orders:checkout"))
        self.assertEqual(r.status_code, 302)
        self.assertEqual(r["Location"], reverse("cart:pagina"))

    def test_checkout_se_muestra_con_carrito(self):
        r = self.client.get(reverse("orders:checkout"))
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "Tus datos")
        self.assertContains(r, "¿A dónde llegamos?")
        self.assertContains(r, "Cómo vas a pagar")
        self.assertContains(r, "mayor de edad")  # casilla obligatoria


class ConfirmarPedidoTests(CheckoutTestCase):
    def test_invitado_puede_comprar(self):
        r = self.client.post(reverse("orders:checkout"), self.datos())
        pedido = Pedido.objects.get()
        self.assertEqual(r["Location"], reverse("orders:confirmacion",
                                               args=[pedido.numero]))
        self.assertIsNone(pedido.usuario)  # compró como invitado
        self.assertEqual(pedido.nombre, "María Pérez")
        self.assertEqual(pedido.municipio, self.municipio)
        self.assertEqual(pedido.total, Decimal(200000))  # envío gratis por umbral
        self.assertEqual(pedido.costo_envio, Decimal(0))
        # Ítems congelados
        item = pedido.items.get()
        self.assertEqual(item.cantidad, 2)
        self.assertEqual(item.precio_unitario, Decimal(100000))
        self.assertEqual(item.sku, self.variante.sku)
        # Stock descontado
        self.variante.refresh_from_db()
        self.assertEqual(self.variante.stock, 8)
        # Carrito limpio
        self.assertEqual(self.client.session["carrito"]["lineas"], {})
        # Historial
        self.assertEqual(HistorialPedido.objects.filter(pedido=pedido).count(), 1)

    def test_contraentrega_entra_en_preparacion(self):
        self.client.post(reverse("orders:checkout"),
                         self.datos(metodo_pago="contraentrega"))
        self.assertEqual(Pedido.objects.get().estado, "preparacion")

    def test_transferencia_queda_pendiente(self):
        # La transferencia solo se ofrece si el negocio tiene datos de cuenta
        config = SiteConfig.get()
        config.pago_nequi = "300 111 2233 — Lencería de Hogar [MARCADOR]"
        config.save()
        self.client.post(reverse("orders:checkout"),
                         self.datos(metodo_pago="transferencia"))
        self.assertEqual(Pedido.objects.get().estado, "pendiente")

    def test_metodo_pago_invalido_no_crea_pedido(self):
        # El formulario valida la lista de métodos; una opción inventada no pasa
        r = self.client.post(reverse("orders:checkout"),
                             self.datos(metodo_pago="tarjeta-secreta"))
        self.assertEqual(Pedido.objects.count(), 0)
        self.assertEqual(r.status_code, 200)  # vuelve al formulario con el error

    def test_falta_mayor_de_edad(self):
        r = self.client.post(reverse("orders:checkout"),
                             self.datos(mayor_de_edad=""))
        self.assertEqual(Pedido.objects.count(), 0)
        self.assertContains(r, "mayor de edad")

    def test_falta_aceptar_terminos(self):
        r = self.client.post(reverse("orders:checkout"), self.datos(autoriza_datos=""))
        self.assertEqual(Pedido.objects.count(), 0)
        self.assertContains(r, "política de datos")

    def test_municipio_fuera_de_santander(self):
        r = self.client.post(reverse("orders:checkout"),
                             self.datos(municipio="Bogotá"))
        self.assertEqual(Pedido.objects.count(), 0)
        self.assertContains(r, "Santander")

    def test_stock_insuficiente_bloquea(self):
        # El carrito tiene 2 pero alguien más compró y quedó 1
        self.variante.stock = 1
        self.variante.save()
        r = self.client.post(reverse("orders:checkout"), self.datos())
        self.assertEqual(Pedido.objects.count(), 0)
        self.assertContains(r, "solo quedan")

    def test_envio_cobrado_fuera_del_umbral(self):
        # Carrito de 100.000 (< 150.000) → cobra $8.000
        session = self.client.session
        session["carrito"] = {
            "lineas": {self.variante.sku: 1}, "cupon": "", "municipio": "Bucaramanga",
            "guardados": [],
        }
        session.save()
        self.client.post(reverse("orders:checkout"), self.datos())
        pedido = Pedido.objects.get()
        self.assertEqual(pedido.costo_envio, Decimal(8000))
        self.assertEqual(pedido.total, Decimal(108000))
        self.assertEqual(pedido.zona_nombre, "Área metropolitana de Bucaramanga")

    def test_cupon_se_registra(self):
        Cupon.objects.create(codigo="PRUEBA10", tipo="porcentaje", valor=Decimal(10))
        session = self.client.session
        session["carrito"] = {
            "lineas": {self.variante.sku: 1}, "cupon": "PRUEBA10",
            "municipio": "Bucaramanga", "guardados": [],
        }
        session.save()
        self.client.post(reverse("orders:checkout"), self.datos())
        pedido = Pedido.objects.get()
        self.assertEqual(pedido.cupon_codigo, "PRUEBA10")
        self.assertEqual(pedido.descuento_cupon, Decimal(10000))
        self.assertEqual(UsoCupon.objects.filter(cupon__codigo="PRUEBA10").count(), 1)

    def test_registro_autenticado_asocia_el_pedido(self):
        usuario = Usuario.objects.create_user(
            username="maria@ejemplo.com", email="maria@ejemplo.com",
            first_name="María", password="clave-segura-123",
        )
        self.client.force_login(usuario)
        self.client.post(reverse("orders:checkout"), self.datos())
        pedido = Pedido.objects.get()
        self.assertEqual(pedido.usuario, usuario)

    def test_pedido_requiere_carrito(self):
        session = self.client.session
        session["carrito"] = {"lineas": {}, "cupon": "", "municipio": "",
                              "guardados": []}
        session.save()
        r = self.client.post(reverse("orders:checkout"), self.datos())
        self.assertEqual(Pedido.objects.count(), 0)
        self.assertEqual(r.status_code, 200)  # vuelve al formulario con aviso


class ConfirmacionTests(CheckoutTestCase):
    def test_pagina_de_confirmacion(self):
        self.client.post(reverse("orders:checkout"), self.datos())
        pedido = Pedido.objects.get()
        r = self.client.get(reverse("orders:confirmacion", args=[pedido.numero]))
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, pedido.numero)
        self.assertContains(r, "Sábanas dobles bonitas")
        self.assertContains(r, "$200.000")

    def test_pedido_inexistente_da_404(self):
        r = self.client.get(reverse("orders:confirmacion", args=["CB-000000"]))
        self.assertEqual(r.status_code, 404)

    def test_numeros_unicos(self):
        self.client.post(reverse("orders:checkout"), self.datos())
        self.agregar_al_carrito(self.variante, 1)
        self.client.post(reverse("orders:checkout"), self.datos())
        self.assertEqual(Pedido.objects.count(), 2)
        self.assertEqual(
            Pedido.objects.values_list("numero", flat=True).count(), 2
        )


class MisPedidosTests(CheckoutTestCase):
    def test_pide_ingreso(self):
        r = self.client.get(reverse("orders:mis_pedidos"))
        self.assertEqual(r.status_code, 302)
        self.assertIn(reverse("accounts:ingreso"), r["Location"])

    def test_lista_solo_los_propios(self):
        propio = Usuario.objects.create_user(
            username="maria@ejemplo.com", email="maria@ejemplo.com",
            password="clave-segura-123",
        )
        otro = Usuario.objects.create_user(
            username="otra@ejemplo.com", email="otra@ejemplo.com", password="x-12345678"
        )
        Pedido.objects.create(
            usuario=propio, nombre="María", email="maria@ejemplo.com",
            telefono="300", municipio=self.municipio, direccion="Cra 1 # 2-3",
            total=Decimal(100000),
        )
        ajeno = Pedido.objects.create(
            usuario=otro, nombre="Otra", email="otra@ejemplo.com",
            telefono="301", municipio=self.municipio, direccion="Cra 9 # 8-7",
            total=Decimal(50000),
        )
        self.client.force_login(propio)
        r = self.client.get(reverse("orders:mis_pedidos"))
        self.assertEqual(r.status_code, 200)
        propio_p = Pedido.objects.get(usuario=propio)
        self.assertContains(r, propio_p.numero)
        self.assertNotContains(r, ajeno.numero)

    def test_volver_a_comprar(self):
        self.client.post(reverse("orders:checkout"), self.datos())
        pedido = Pedido.objects.get()
        usuario = Usuario.objects.create_user(
            username="maria@ejemplo.com", email="maria@ejemplo.com",
            password="clave-segura-123",
        )
        pedido.usuario = usuario
        pedido.save()
        self.client.force_login(usuario)
        # Vacía el carrito y repite el pedido
        session = self.client.session
        session["carrito"] = {"lineas": {}, "cupon": "", "municipio": "",
                              "guardados": []}
        session.save()
        r = self.client.post(reverse("orders:repetir", args=[pedido.numero]))
        self.assertEqual(r.status_code, 302)
        self.assertEqual(
            self.client.session["carrito"]["lineas"][self.variante.sku], 2
        )

    def test_no_repetir_pedido_ajeno(self):
        propio = Usuario.objects.create_user(
            username="maria@ejemplo.com", email="maria@ejemplo.com",
            password="clave-segura-123",
        )
        otro = Usuario.objects.create_user(
            username="otra@ejemplo.com", email="otra@ejemplo.com", password="x-12345678"
        )
        pedido = Pedido.objects.create(
            usuario=propio, nombre="María", email="maria@ejemplo.com",
            telefono="300", municipio=self.municipio, direccion="Cra 1 # 2-3",
        )
        self.client.force_login(otro)
        r = self.client.post(reverse("orders:repetir", args=[pedido.numero]))
        self.assertEqual(r.status_code, 404)


class HabeasDataPedidosTests(CheckoutTestCase):
    def test_borrar_cuenta_anonimiza_los_pedidos(self):
        usuario = Usuario.objects.create_user(
            username="maria@ejemplo.com", email="maria@ejemplo.com",
            password="clave-segura-123",
        )
        self.client.force_login(usuario)
        self.client.post(reverse("orders:checkout"), self.datos())
        pedido = Pedido.objects.get()

        self.client.post(
            reverse("accounts:eliminar_cuenta"), {"password": "clave-segura-123"}
        )
        pedido.refresh_from_db()
        # La venta se conserva…
        self.assertEqual(Pedido.objects.count(), 1)
        self.assertEqual(pedido.total, Decimal(200000))
        # …pero los datos personales no
        self.assertIsNone(pedido.usuario)
        self.assertEqual(pedido.nombre, "Cliente eliminada")
        self.assertEqual(pedido.email, "")
        self.assertEqual(pedido.telefono, "")
        self.assertEqual(pedido.direccion, "")
