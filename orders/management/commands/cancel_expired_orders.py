"""Cancela pedidos sin pago cuya reserva de stock venció y devuelve el stock.

Uso: manage.py cancel_expired_orders [--simular]

Pensado para cron/Tareas programadas del hosting (costo $0, sin Celery).
"""
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from orders.models import Pedido
from orders.servicios import cambiar_estado


class Command(BaseCommand):
    help = ("Cancela los pedidos que no pagaron a tiempo (pasarela o "
            "transferencia), devuelve su stock al inventario y deja el "
            "motivo en el historial.")

    def add_arguments(self, parser):
        parser.add_argument(
            "--simular", action="store_true",
            help="Muestra lo que se cancelaría sin tocar nada.",
        )
        parser.add_argument(
            "--margen-minutos", type=int, default=5,
            help="Minutos extra después de la fecha de reserva antes de "
                 "cancelar (por seguridad, por defecto 5).",
        )

    def handle(self, *args, **opciones):
        margen = timezone.now() - timedelta(minutes=opciones["margen_minutos"])
        vencidos = (
            Pedido.objects.filter(reserva_hasta__lte=margen)
            .exclude(estado__in=("pagado", "preparacion", "enviado",
                                 "entregado", "cancelado", "devuelto"))
            .select_related("municipio")
        )

        if opciones["simular"]:
            for pedido in vencidos:
                self.stdout.write(
                    f"Se cancelaría {pedido.numero} ({pedido.get_estado_display()}, "
                    f"reserva venció el {pedido.reserva_hasta:%d/%m/%Y %H:%M})."
                )
            self.stdout.write(self.style.WARNING(
                f"Simulación: {vencidos.count()} pedido(s) se cancelarían."
            ))
            return

        cancelados = 0
        for pedido in vencidos:
            cambiar_estado(
                pedido, "cancelado",
                nota="El pago no llegó a tiempo y la reserva de stock venció. "
                     "Si ya pagaste, escríbenos por WhatsApp y lo reactivamos.",
            )
            self.stdout.write(f"Cancelado {pedido.numero} (stock devuelto).")
            cancelados += 1

        self.stdout.write(self.style.SUCCESS(
            f"{cancelados} pedido(s) cancelado(s) por reserva vencida."
        ))
