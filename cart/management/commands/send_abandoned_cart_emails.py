"""Envía el recordatorio de carrito abandonado a los clientes con cuenta.

Uso: manage.py send_abandoned_cart_emails [--horas 24] [--simular]

Busca usuarios con un carrito guardado (en su cuenta) que no han comprado
desde que lo tocaron por última vez y les manda un correo amable con un
botón para retomar la compra. No toca carritos de invitados (no tenemos
su correo).
"""
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.utils import timezone


class Command(BaseCommand):
    help = ("Envía un recordatorio a los clientes con carrito guardado que "
            "no completaron su compra.")

    def add_arguments(self, parser):
        parser.add_argument(
            "--horas", type=int, default=24,
            help="Horas mínimas desde la última vez que se tocó el carrito "
                 "(por defecto 24).",
        )
        parser.add_argument(
            "--simular", action="store_true",
            help="Muestra a quién se le enviaría sin enviar nada.",
        )

    def handle(self, *args, **opciones):
        Usuario = get_user_model()
        ahora = timezone.now()
        limite = ahora - timedelta(hours=opciones["horas"])

        candidatos = (
            Usuario.objects.filter(
                carrito_actualizado__lte=limite,
                carrito__isnull=False,
            )
            .distinct()
        )

        enviados = 0
        for usuario in candidatos:
            lineas = _lineas_del_carrito(usuario)
            if not lineas:
                continue
            # Si compró después de tocar el carrito, no avisar
            from orders.models import Pedido

            if Pedido.objects.filter(
                usuario=usuario,
                creado__gte=usuario.carrito_actualizado,
            ).exists():
                continue
            # Si ya les avisamos después de la última modificación, no repetir
            if (usuario.aviso_carrito and usuario.carrito_actualizado
                    and usuario.aviso_carrito >= usuario.carrito_actualizado):
                continue

            if opciones["simular"]:
                self.stdout.write(
                    f"Se enviaría a {usuario.email}: {len(lineas)} producto(s)."
                )
                continue

            from core import correos

            if correos.carrito_abandonado(usuario, lineas, _total(lineas)):
                usuario.aviso_carrito = ahora
                usuario.save(update_fields=["aviso_carrito"])
                enviados += 1
                self.stdout.write(f"Recordatorio enviado a {usuario.email}.")

        if opciones["simular"]:
            self.stdout.write(self.style.WARNING("Simulación: no se envió nada."))
        else:
            self.stdout.write(self.style.SUCCESS(
                f"{enviados} recordatorio(s) de carrito enviado(s)."
            ))


def _lineas_del_carrito(usuario):
    """Convierte el carrito guardado del usuario en líneas con nombre y precio."""
    from catalog.models import Variante

    datos = usuario.carrito or {}
    crudo = datos.get("lineas") or {}
    if not crudo:
        return []
    lineas = []
    for sku, cantidad in crudo.items():
        try:
            cantidad = int(cantidad)
        except (TypeError, ValueError):
            continue
        if cantidad <= 0:
            continue
        variante = (
            Variante.objects.select_related("producto")
            .filter(sku=str(sku), producto__estado="publicado")
            .first()
        )
        if variante is None:
            continue
        lineas.append({
            "nombre": variante.producto.nombre
                      + (f" ({variante.talla_label})" if variante.talla_label else ""),
            "cantidad": cantidad,
            "precio": variante.precio * cantidad,
        })
    return lineas


def _total(lineas):
    from decimal import Decimal

    return sum((l["precio"] for l in lineas), Decimal(0))
