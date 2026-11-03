"""Integración opcional con Wompi (Web Checkout y Webhook).

Documentación oficial: https://docs.wompi.co/
Sandbox gratuito para pruebas. En producción Wompi cobra comisión por transacción.
Si no existen llaves (WOMPI_* en .env), el método se oculta y se usa la pasarela simulada.
Nunca se almacenan datos de tarjeta en el sistema.
"""
import hashlib
import json
import logging
import os
from decimal import Decimal
from urllib.parse import urlencode

from django.conf import settings

from orders.models import Pedido
from orders.servicios import cambiar_estado
from payments.models import Pago

logger = logging.getLogger(__name__)


def esta_configurado():
    """True si las llaves de Wompi están en el entorno."""
    pub = os.getenv("WOMPI_PUBLIC_KEY", "").strip()
    secret = (
        os.getenv("WOMPI_INTEGRITY_SECRET", "").strip()
        or os.getenv("WOMPI_EVENTS_KEY", "").strip()
    )
    return bool(pub and secret)


def obtener_llaves():
    return {
        "public_key": os.getenv("WOMPI_PUBLIC_KEY", "").strip(),
        "private_key": os.getenv("WOMPI_PRIVATE_KEY", "").strip(),
        "events_key": os.getenv("WOMPI_EVENTS_KEY", "").strip(),
        "integrity_secret": os.getenv("WOMPI_INTEGRITY_SECRET", "").strip(),
        "base_url": os.getenv("WOMPI_BASE_URL", "https://sandbox.wompi.co/v1").strip(),
        "checkout_url": os.getenv(
            "WOMPI_CHECKOUT_URL", "https://checkout.wompi.co/p/"
        ).strip(),
    }


def monto_en_centavos(total_cop):
    """COP 120.000 → 12000000 centavos."""
    if isinstance(total_cop, (int, float)):
        total_cop = Decimal(str(total_cop))
    return int(total_cop * 100)


def calcular_firma_integridad(referencia, monto_centavos, moneda="COP"):
    """Firma de integridad Wompi: SHA256(referencia + monto_centavos + moneda + secreto)."""
    llaves = obtener_llaves()
    secreto = llaves["integrity_secret"] or llaves["events_key"]
    cadena = f"{referencia}{monto_centavos}{moneda}{secreto}"
    return hashlib.sha256(cadena.encode("utf-8")).hexdigest()


def url_checkout_wompi(pedido, redirect_url=None):
    """Construye la URL de redirección directa al Web Checkout de Wompi."""
    llaves = obtener_llaves()
    centavos = monto_en_centavos(pedido.total)
    firma = calcular_firma_integridad(pedido.numero, centavos, "COP")

    params = {
        "public-key": llaves["public_key"],
        "currency": "COP",
        "amount-in-cents": centavos,
        "reference": pedido.numero,
        "signature:integrity": firma,
    }
    if redirect_url:
        params["redirect-url"] = redirect_url
    if pedido.email:
        params["customer-data:email"] = pedido.email
    if pedido.nombre:
        params["customer-data:full-name"] = pedido.nombre
    if pedido.telefono:
        params["customer-data:phone-number"] = pedido.telefono

    return f"{llaves['checkout_url']}?{urlencode(params)}"


def verificar_firma_webhook(payload, timestamp, checksum):
    """Verifica el checksum del webhook de Wompi:

    Wompi concatena las propiedades listadas en signature.properties
    con el timestamp y el secreto de eventos: SHA256(prop1 + prop2 + ... + timestamp + events_key)
    """
    llaves = obtener_llaves()
    secreto = llaves["events_key"] or llaves["integrity_secret"]
    if not secreto:
        return False

    # Extraer valores según properties
    propiedades = payload.get("signature", {}).get("properties", [])
    data = payload.get("data", {})

    valores = []
    for prop in propiedades:
        # prop puede ser tipo 'transaction.id', 'transaction.status', etc.
        partes = prop.split(".")
        actual = data
        for p in partes:
            if isinstance(actual, dict):
                actual = actual.get(p)
            else:
                actual = None
                break
        if actual is not None:
            valores.append(str(actual))

    cadena = "".join(valores) + str(timestamp) + secreto
    esperado = hashlib.sha256(cadena.encode("utf-8")).hexdigest()
    return checksum == esperado


def procesar_webhook(payload):
    """Procesa el evento de transacción de Wompi de forma idempotente."""
    evento = payload.get("event")
    if evento != "transaction.updated":
        return {"procesado": False, "motivo": f"Evento ignorado: {evento}"}

    transaccion = payload.get("data", {}).get("transaction", {})
    referencia = transaccion.get("reference")
    estado_wompi = transaccion.get("status")  # APPROVED, DECLINED, VOIDED, ERROR
    tx_id = transaccion.get("id")
    monto_centavos = transaccion.get("amount_in_cents", 0)
    monto_cop = Decimal(monto_centavos) / Decimal(100)

    if not referencia:
        return {"procesado": False, "motivo": "Falta referencia"}

    try:
        pedido = Pedido.objects.get(numero=referencia)
    except Pedido.DoesNotExist:
        return {"procesado": False, "motivo": f"Pedido {referencia} no existe"}

    # Registrar el pago en la app payments
    pago, _creado = Pago.objects.get_or_create(
        pedido=pedido,
        referencia=f"wompi_{tx_id}",
        defaults={
            "metodo": "pasarela",
            "monto": monto_cop,
            "estado": "aprobado" if estado_wompi == "APPROVED" else "rechazado",
        },
    )

    if estado_wompi == "APPROVED":
        pago.estado = "aprobado"
        pago.save(update_fields=["estado", "actualizado"])
        if pedido.estado != "pagado":
            cambiar_estado(
                pedido,
                "pagado",
                nota=f"Pago Wompi aprobado (tx: {tx_id}).",
            )
        return {"procesado": True, "estado": "pagado", "pedido": pedido.numero}

    elif estado_wompi in ("DECLINED", "ERROR", "VOIDED"):
        pago.estado = "rechazado"
        pago.save(update_fields=["estado", "actualizado"])
        return {"procesado": True, "estado": "rechazado", "pedido": pedido.numero}

    return {"procesado": True, "estado": estado_wompi, "pedido": pedido.numero}
