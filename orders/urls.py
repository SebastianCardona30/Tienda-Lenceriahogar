from django.urls import path

from orders import views

app_name = "orders"

urlpatterns = [
    path("checkout/", views.checkout, name="checkout"),
    path("pedido/<str:numero>/confirmacion/", views.confirmacion, name="confirmacion"),
    path("seguimiento/", views.seguimiento, name="seguimiento"),
    path("cuenta/pedidos/", views.mis_pedidos, name="mis_pedidos"),
    path("pedido/<str:numero>/repetir/", views.repetir, name="repetir"),
]
