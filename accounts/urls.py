from django.contrib.auth import views as auth_views
from django.urls import path

from accounts import views

app_name = "accounts"

urlpatterns = [
    # Acceso
    path("cuenta/registro/", views.registro, name="registro"),
    path("cuenta/ingreso/", views.ingreso, name="ingreso"),
    path("cuenta/salir/", views.salir, name="salir"),
    # Panel
    path("cuenta/", views.panel, name="panel"),
    path("cuenta/datos/", views.mis_datos, name="datos"),
    path("cuenta/direcciones/", views.direcciones, name="direcciones"),
    path("cuenta/direcciones/<int:pk>/editar/", views.editar_direccion, name="editar_direccion"),
    path("cuenta/direcciones/<int:pk>/eliminar/", views.eliminar_direccion, name="eliminar_direccion"),
    path("cuenta/deseos/", views.deseos, name="deseos"),
    path("cuenta/eliminar/", views.eliminar_cuenta, name="eliminar_cuenta"),
    # Lista de deseos (botón corazón desde cualquier página)
    path("deseos/alternar/", views.alternar_deseo, name="alternar_deseo"),
    # Recuperar contraseña por correo (en desarrollo el correo va a consola)
    path(
        "cuenta/recuperar/",
        auth_views.PasswordResetView.as_view(
            template_name="accounts/recuperar.html",
            email_template_name="accounts/email/recuperar.txt",
            subject_template_name="accounts/email/asunto_recuperar.txt",
            success_url="/cuenta/recuperar/enviado/",
        ),
        name="recuperar",
    ),
    path(
        "cuenta/recuperar/enviado/",
        auth_views.PasswordResetDoneView.as_view(
            template_name="accounts/recuperar_enviado.html",
        ),
        name="recuperar_enviado",
    ),
    path(
        "cuenta/recuperar/<uidb64>/<token>/",
        auth_views.PasswordResetConfirmView.as_view(
            template_name="accounts/recuperar_nueva.html",
            success_url="/cuenta/recuperar/listo/",
        ),
        name="recuperar_confirmar",
    ),
    path(
        "cuenta/recuperar/listo/",
        auth_views.PasswordResetCompleteView.as_view(
            template_name="accounts/recuperar_listo.html",
        ),
        name="recuperar_listo",
    ),
]
