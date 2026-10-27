from django.urls import path

from catalog import views

app_name = "catalog"

urlpatterns = [
    path("tienda/", views.tienda, name="tienda"),
    path("ofertas/", views.ofertas, name="ofertas"),
    path("combos/", views.combos, name="combos"),
    path("combos/<slug:slug>/", views.combo, name="combo"),
    path("buscar/", views.buscar, name="buscar"),
    path("buscar/sugerencias/", views.autocomplete, name="autocomplete"),
    path("categoria/<slug:slug>/", views.categoria, name="categoria"),
    path("producto/<slug:slug>/", views.producto, name="producto"),
    path("producto/<slug:slug>/resena/", views.enviar_resena, name="enviar_resena"),
    path("suscribir/", views.suscribir, name="suscribir"),
]
