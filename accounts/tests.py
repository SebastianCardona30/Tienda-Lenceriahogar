"""Pruebas de cuentas: acceso, fusión del carrito, direcciones, deseos y Habeas Data."""
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.contrib.messages import get_messages
from django.core import mail
from django.test import TestCase
from django.urls import reverse

from accounts.models import Deseo, Direccion
from catalog.models import Categoria, Producto, Variante
from shipping.models import MunicipioSantander

Usuario = get_user_model()


def crear_producto(nombre="Sábanas dobles bonitas", precio=100000):
    prod = Producto.objects.create(nombre=nombre, estado="publicado")
    Variante.objects.create(producto=prod, precio=Decimal(precio), stock=10)
    return prod


def mensajes_de(response):
    return " ".join(str(m) for m in get_messages(response.wsgi_request))


class BaseCuentas(TestCase):
    def setUp(self):
        self.usuario = Usuario.objects.create_user(
            username="maria@ejemplo.com",
            email="maria@ejemplo.com",
            first_name="María",
            last_name="Pérez",
            password="clave-segura-123",
        )
        self.municipio = MunicipioSantander.objects.create(nombre="Bucaramanga")


class RegistroTests(BaseCuentas):
    def test_registro_crea_cuenta_y_entra(self):
        r = self.client.post(
            reverse("accounts:registro"),
            {
                "nombre": "Ana Gómez",
                "email": "ana@ejemplo.com",
                "celular": "3001112233",
                "password1": "clave-segura-456",
                "password2": "clave-segura-456",
            },
        )
        self.assertEqual(r.status_code, 302)
        self.assertEqual(r["Location"], reverse("accounts:panel"))
        ana = Usuario.objects.get(email="ana@ejemplo.com")
        self.assertEqual(ana.first_name, "Ana")
        self.assertEqual(ana.last_name, "Gómez")
        self.assertEqual(ana.telefono, "3001112233")
        self.assertEqual(ana.username, "ana@ejemplo.com")  # el correo es el usuario
        self.assertTrue(ana.check_password("clave-segura-456"))
        # Quedó dentro
        self.assertEqual(int(self.client.session["_auth_user_id"]), ana.pk)

    def test_registro_con_correo_repetido_da_error(self):
        r = self.client.post(
            reverse("accounts:registro"),
            {
                "nombre": "María Duplicada",
                "email": "maria@ejemplo.com",
                "password1": "clave-segura-456",
                "password2": "clave-segura-456",
            },
        )
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "Ya hay una cuenta con ese correo.")
        self.assertEqual(Usuario.objects.count(), 1)

    def test_registro_contrasenas_no_coinciden(self):
        r = self.client.post(
            reverse("accounts:registro"),
            {
                "nombre": "Ana Gómez",
                "email": "ana@ejemplo.com",
                "password1": "clave-segura-456",
                "password2": "otra-clave-789",
            },
        )
        self.assertContains(r, "Las contraseñas no coinciden.")

    def test_registro_debil_da_error(self):
        r = self.client.post(
            reverse("accounts:registro"),
            {
                "nombre": "Ana Gómez",
                "email": "ana@ejemplo.com",
                "password1": "123",
                "password2": "123",
            },
        )
        self.assertEqual(r.status_code, 200)
        self.assertEqual(Usuario.objects.count(), 1)  # no se creó

    def test_registro_autenticado_redirige_al_panel(self):
        self.client.force_login(self.usuario)
        r = self.client.get(reverse("accounts:registro"))
        self.assertEqual(r["Location"], reverse("accounts:panel"))

    def test_registro_con_next_respeta_la_ruta(self):
        r = self.client.post(
            reverse("accounts:registro") + "?next=/tienda/",
            {
                "nombre": "Ana Gómez",
                "email": "ana@ejemplo.com",
                "password1": "clave-segura-456",
                "password2": "clave-segura-456",
            },
        )
        self.assertEqual(r["Location"], "/tienda/")

    def test_registro_next_malo_no_hace_open_redirect(self):
        r = self.client.post(
            reverse("accounts:registro") + "?next=//ejemplo.com/malo",
            {
                "nombre": "Ana Gómez",
                "email": "ana@ejemplo.com",
                "password1": "clave-segura-456",
                "password2": "clave-segura-456",
            },
        )
        self.assertEqual(r["Location"], reverse("accounts:panel"))


class IngresoTests(BaseCuentas):
    def test_ingreso_correcto(self):
        r = self.client.post(
            reverse("accounts:ingreso"),
            {"email": "maria@ejemplo.com", "password": "clave-segura-123"},
        )
        self.assertEqual(r["Location"], reverse("accounts:panel"))
        self.assertEqual(
            int(self.client.session["_auth_user_id"]), self.usuario.pk
        )

    def test_ingreso_contrasena_mala(self):
        r = self.client.post(
            reverse("accounts:ingreso"),
            {"email": "maria@ejemplo.com", "password": "equivocada"},
        )
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "incorrectos")
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_ingreso_con_next_respeta_la_ruta(self):
        r = self.client.post(
            reverse("accounts:ingreso") + "?next=/cuenta/deseos/",
            {"email": "maria@ejemplo.com", "password": "clave-segura-123"},
        )
        self.assertEqual(r["Location"], "/cuenta/deseos/")

    def test_ingreso_fusiona_el_carrito(self):
        prod = crear_producto()
        sku = prod.variantes.first().sku
        # El invitado tenía 2 en la sesión
        s = self.client.session
        s["carrito"] = {"lineas": {sku: 2}, "cupon": "", "municipio": "Bucaramanga",
                        "guardados": []}
        s.save()
        # La cuenta tenía 3 del mismo producto
        self.usuario.carrito = {"lineas": {sku: 3}, "cupon": "", "municipio": "",
                                "guardados": []}
        self.usuario.save()

        self.client.post(
            reverse("accounts:ingreso"),
            {"email": "maria@ejemplo.com", "password": "clave-segura-123"},
        )
        carrito = self.client.session["carrito"]
        self.assertEqual(carrito["lineas"][sku], 5)  # 2 + 3
        self.assertEqual(carrito["municipio"], "Bucaramanga")  # gana el de la sesión

    def test_salir_no_duplica_el_carrito_al_volver(self):
        prod = crear_producto()
        sku = prod.variantes.first().sku
        self.client.post(
            reverse("accounts:ingreso"),
            {"email": "maria@ejemplo.com", "password": "clave-segura-123"},
        )
        # Agrega algo estando dentro
        self.client.post(reverse("cart:agregar"), {"sku": sku, "cantidad": 2},
                         HTTP_REFERER="/tienda/")
        # Sale y vuelve a entrar
        self.client.post(reverse("accounts:salir"))
        self.client.post(
            reverse("accounts:ingreso"),
            {"email": "maria@ejemplo.com", "password": "clave-segura-123"},
        )
        carrito = self.client.session["carrito"]
        self.assertEqual(carrito["lineas"][sku], 2)  # sigue siendo 2, no 4


class PanelTests(BaseCuentas):
    def test_paginas_de_cuenta_piden_ingreso(self):
        for url in ("accounts:panel", "accounts:datos", "orders:mis_pedidos",
                    "accounts:direcciones", "accounts:deseos",
                    "accounts:eliminar_cuenta"):
            r = self.client.get(reverse(url))
            self.assertEqual(r.status_code, 302, url)
            self.assertIn(reverse("accounts:ingreso"), r["Location"])

    def test_paginas_de_cuenta_se_muestran(self):
        self.client.force_login(self.usuario)
        for url in ("accounts:panel", "accounts:datos", "orders:mis_pedidos",
                    "accounts:direcciones", "accounts:deseos",
                    "accounts:eliminar_cuenta"):
            r = self.client.get(reverse(url))
            self.assertEqual(r.status_code, 200, url)

    def test_mis_datos_se_actualizan(self):
        self.client.force_login(self.usuario)
        r = self.client.post(
            reverse("accounts:datos"),
            {"first_name": "María", "last_name": "Pérez",
             "email": "nuevo@ejemplo.com", "telefono": "3009998877",
             "cedula": "1023456789"},
        )
        self.assertEqual(r.status_code, 302)
        self.usuario.refresh_from_db()
        self.assertEqual(self.usuario.email, "nuevo@ejemplo.com")
        self.assertEqual(self.usuario.telefono, "3009998877")

    def test_encabezado_cambia_segun_sesion(self):
        r = self.client.get(reverse("core:home"))
        self.assertContains(r, reverse("accounts:ingreso"))
        self.client.force_login(self.usuario)
        r = self.client.get(reverse("core:home"))
        self.assertContains(r, reverse("accounts:panel"))


class DireccionesTests(BaseCuentas):
    def _datos(self, **extra):
        datos = {
            "destinatario": "María Pérez",
            "municipio": self.municipio.pk,
            "barrio": "Cabecera",
            "direccion": "Cra 15 # 42-10, apto 302",
            "indicaciones": "Portón negro, tocar timbre 302",
            "telefono": "3001112233",
        }
        datos.update(extra)
        return datos

    def test_crear_direccion(self):
        self.client.force_login(self.usuario)
        r = self.client.post(reverse("accounts:direcciones"),
                             self._datos(predeterminada=True))
        self.assertEqual(r.status_code, 302)
        d = self.usuario.direcciones.get()
        self.assertEqual(d.municipio, self.municipio)
        self.assertTrue(d.predeterminada)

    def test_solo_una_predeterminada(self):
        self.client.force_login(self.usuario)
        self.client.post(reverse("accounts:direcciones"),
                         self._datos(predeterminada=True))
        otra = MunicipioSantander.objects.create(nombre="Girón")
        self.client.post(
            reverse("accounts:direcciones"),
            self._datos(municipio=otra.pk, predeterminada=True),
        )
        self.assertEqual(
            self.usuario.direcciones.filter(predeterminada=True).count(), 1
        )

    def test_editar_direccion_propia(self):
        self.client.force_login(self.usuario)
        d = Direccion.objects.create(
            usuario=self.usuario, destinatario="María",
            municipio=self.municipio, direccion="Cra 1 # 2-3",
        )
        r = self.client.post(
            reverse("accounts:editar_direccion", args=[d.pk]),
            self._datos(barrio="Centro"),
        )
        self.assertEqual(r.status_code, 302)
        d.refresh_from_db()
        self.assertEqual(d.barrio, "Centro")

    def test_no_editar_direccion_ajena(self):
        otra = Usuario.objects.create_user(
            username="otra@ejemplo.com", email="otra@ejemplo.com", password="x-12345678"
        )
        d = Direccion.objects.create(
            usuario=otra, destinatario="Otra", municipio=self.municipio,
            direccion="Cra 9 # 8-7",
        )
        self.client.force_login(self.usuario)
        r = self.client.get(reverse("accounts:editar_direccion", args=[d.pk]))
        self.assertEqual(r.status_code, 404)

    def test_eliminar_direccion(self):
        self.client.force_login(self.usuario)
        d = Direccion.objects.create(
            usuario=self.usuario, destinatario="María",
            municipio=self.municipio, direccion="Cra 1 # 2-3",
        )
        self.client.post(reverse("accounts:eliminar_direccion", args=[d.pk]))
        self.assertEqual(self.usuario.direcciones.count(), 0)

    def test_eliminar_cuenta_borra_las_direcciones(self):
        self.client.force_login(self.usuario)
        Direccion.objects.create(
            usuario=self.usuario, destinatario="María",
            municipio=self.municipio, direccion="Cra 1 # 2-3",
        )
        self.client.post(
            reverse("accounts:eliminar_cuenta"), {"password": "clave-segura-123"}
        )
        self.assertEqual(Usuario.objects.count(), 0)
        self.assertEqual(Direccion.objects.count(), 0)


class DeseosTests(BaseCuentas):
    def setUp(self):
        super().setUp()
        self.producto = crear_producto()

    def test_anonimo_va_al_ingreso(self):
        r = self.client.post(reverse("accounts:alternar_deseo"),
                             {"producto": self.producto.pk})
        self.assertEqual(r.status_code, 302)
        self.assertIn(reverse("accounts:ingreso"), r["Location"])
        self.assertEqual(Deseo.objects.count(), 0)

    def test_autenticado_agrega_y_quita(self):
        self.client.force_login(self.usuario)
        r = self.client.post(reverse("accounts:alternar_deseo"),
                             {"producto": self.producto.pk},
                             HTTP_REFERER=self.producto.get_absolute_url())
        self.assertEqual(Deseo.objects.filter(usuario=self.usuario).count(), 1)
        # El corazón se pinta ♥ en la página
        pagina = self.client.get(self.producto.get_absolute_url())
        self.assertContains(pagina, "Guardado en mis deseos")
        # El segundo toque lo quita
        self.client.post(reverse("accounts:alternar_deseo"),
                         {"producto": self.producto.pk},
                         HTTP_REFERER=self.producto.get_absolute_url())
        self.assertEqual(Deseo.objects.count(), 0)

    def test_producto_inexistente_da_404(self):
        self.client.force_login(self.usuario)
        r = self.client.post(reverse("accounts:alternar_deseo"), {"producto": 999999})
        self.assertEqual(r.status_code, 404)

    def test_pagina_de_deseos_lista_los_favoritos(self):
        self.client.force_login(self.usuario)
        Deseo.objects.create(usuario=self.usuario, producto=self.producto)
        r = self.client.get(reverse("accounts:deseos"))
        self.assertContains(r, "Sábanas dobles bonitas")

    def test_tarjeta_muestra_el_corazon(self):
        prod = crear_producto("Edredón bonito")
        cat = Categoria.objects.create(nombre="Edredones", slug="edredones")
        prod.categorias.add(cat)
        r = self.client.get(cat.get_absolute_url())
        self.assertContains(r, "tarjeta-producto__deseo")
        self.assertContains(r, "Guardar en mis deseos")


class RecuperarTests(BaseCuentas):
    def test_envia_correo_con_enlace(self):
        r = self.client.post(
            reverse("accounts:recuperar"), {"email": "maria@ejemplo.com"}
        )
        self.assertEqual(r.status_code, 302)
        self.assertEqual(r["Location"], "/cuenta/recuperar/enviado/")
        self.assertEqual(len(mail.outbox), 1)
        correo = mail.outbox[0]
        self.assertIn("maria@ejemplo.com", correo.to)
        self.assertIn("Recupera tu contraseña", correo.subject)
        self.assertIn("/cuenta/recuperar/", correo.body)
        self.assertIn("/cuenta/recuperar/", correo.body)  # enlace completo

    def test_correo_inexistente_no_filtra_nada(self):
        r = self.client.post(
            reverse("accounts:recuperar"), {"email": "nadie@ejemplo.com"}
        )
        self.assertEqual(r.status_code, 302)
        self.assertEqual(len(mail.outbox), 0)  # sin correo, sin filtrar cuentas

    def test_paginas_de_recuperacion_se_muestran(self):
        self.assertEqual(
            self.client.get(reverse("accounts:recuperar")).status_code, 200
        )
        self.assertEqual(
            self.client.get(reverse("accounts:recuperar_enviado")).status_code, 200
        )
        self.assertEqual(
            self.client.get(reverse("accounts:recuperar_listo")).status_code, 200
        )


class HabeasDataTests(BaseCuentas):
    def test_eliminar_cuenta_pide_contraseña(self):
        self.client.force_login(self.usuario)
        r = self.client.post(
            reverse("accounts:eliminar_cuenta"), {"password": "equivocada"}
        )
        self.assertContains(r, "La contraseña no es correcta.")
        self.assertEqual(Usuario.objects.count(), 1)

    def test_eliminar_cuenta_borra_todo_en_cascada(self):
        prod = crear_producto()
        Deseo.objects.create(usuario=self.usuario, producto=prod)
        Direccion.objects.create(
            usuario=self.usuario, destinatario="María",
            municipio=self.municipio, direccion="Cra 1 # 2-3",
        )
        self.usuario.carrito = {"lineas": {"X": 1}, "cupon": "", "municipio": "",
                                "guardados": []}
        self.usuario.save()

        self.client.force_login(self.usuario)
        r = self.client.post(
            reverse("accounts:eliminar_cuenta"), {"password": "clave-segura-123"}
        )
        self.assertEqual(r["Location"], "/")
        self.assertEqual(Usuario.objects.count(), 0)
        self.assertEqual(Direccion.objects.count(), 0)
        self.assertEqual(Deseo.objects.count(), 0)
        # Y quedó fuera de sesión
        self.assertNotIn("_auth_user_id", self.client.session)
        # El mensaje de confirmación se muestra en el inicio
        pagina = self.client.get(reverse("core:home"))
        self.assertContains(pagina, "fueron eliminados")
