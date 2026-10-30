"""Devuelve al inventario el stock de pedidos cancelados o devueltos.

Uso: manage.py release_stock_reservations

Red de seguridad: si un pedido se canceló o devolvió sin pasar por el
servicio (por ejemplo editando el estado a mano en el panel), esta tarea
recupera su stock. Es idempotente: nunca devuelve una reserva dos veces.
"""
from django.core.management.base import BaseCommand

from orders.models import Pedido
from orders.servicios import devolver_stock


class Command(BaseCommand):
    help = ("Devuelve al inventario el stock de pedidos cancelados o "
            "devueltos que aún no lo habían devuelto.")

    def add_arguments(self, parser):
        parser.add_argument(
            "--simular", action="store_true",
            help="Muestra lo que se devolvería sin tocar nada.",
        )

    def handle(self, *args, **opciones):
        pendientes = (
            Pedido.objects.filter(estado__in=("cancelado", "devuelto"),
                                  stock_devuelto=False)
            .prefetch_related("items")
        )

        if opciones["simular"]:
            for pedido in pendientes:
                unidades = sum(i.cantidad for i in pedido.items.all())
                self.stdout.write(
                    f"Se devolverían {unidades} unidad(es) de {pedido.numero}."
                )
            self.stdout.write(self.style.WARNING(
                f"Simulación: {pendientes.count()} pedido(s) devolverían stock."
            ))
            return

        devueltos = 0
        for pedido in pendientes:
            unidades = sum(i.cantidad for i in pedido.items.all())
            if devolver_stock(pedido):
                self.stdout.write(
                    f"{pedido.numero}: {unidades} unidad(es) de vuelta al stock."
                )
                devueltos += 1

        self.stdout.write(self.style.SUCCESS(
            f"{devueltos} pedido(s) con stock devuelto al inventario."
        ))
