from django.urls import path

from cart import views

app_name = "cart"

urlpatterns = [
    path("carrito/", views.pagina, name="pagina"),
    path("carrito/agregar/", views.agregar, name="agregar"),
    path("carrito/actualizar/", views.actualizar, name="actualizar"),
    path("carrito/eliminar/", views.eliminar, name="eliminar"),
    path("carrito/guardar/", views.guardar_para_despues, name="guardar"),
    path("carrito/restaurar/", views.restaurar, name="restaurar"),
    path("carrito/cupon/", views.cupon, name="cupon"),
    path("carrito/envio/", views.municipio, name="municipio"),
]
