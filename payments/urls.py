from django.urls import path

from payments import views

app_name = "payments"

urlpatterns = [
    path("pago/<str:numero>/", views.pagar, name="pagar"),
    path("pago/<str:numero>/resultado/", views.registrar_resultado, name="resultado"),
    path("pago/<str:numero>/comprobante/", views.comprobante, name="comprobante"),
]
