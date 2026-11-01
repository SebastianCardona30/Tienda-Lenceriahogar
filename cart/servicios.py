"""
Carrito de compras: persistencia en sesión y resumen para las vistas.

El carrito vive en la sesión del navegador con esta forma:
    {"lineas": {"SKU": cantidad}, "cupon": "CODIGO",
     "municipio": "Nombre", "guardados": ["SKU", ...]}

Todo el dinero se calcula en promotions/engine.py (en el servidor);
aquí solo se arma el resumen y los mensajes para la plantilla.
"""
import json

from promotions.engine import LineaCarrito, calcular_carrito

CLAVE = "carrito"

VACIO = {"lineas": {}, "cupon": "", "municipio": "", "guardados": []}


def leer(request):
    """Devuelve el carrito de la sesión con la estructura garantizada."""
    datos = request.session.get(CLAVE) or {}
    lineas = {}
    for sku, cantidad in (datos.get("lineas") or {}).items():
        try:
            cantidad = int(cantidad)
        except (TypeError, ValueError):
            continue
        if cantidad > 0:
            lineas[str(sku)] = cantidad
    return {
        "lineas": lineas,
        "cupon": str(datos.get("cupon") or "").strip().upper(),
        "municipio": str(datos.get("municipio") or "").strip(),
        "guardados": [str(s) for s in (datos.get("guardados") or [])],
    }


def guardar(request, datos):
    """Escribe el carrito en la sesión y, si hay sesión de cliente, en la cuenta."""
    from django.utils import timezone

    request.session[CLAVE] = datos
    request.session.modified = True
    usuario = getattr(request, "user", None)
    if usuario is not None and usuario.is_authenticated:
        usuario.carrito = datos
        # Marca la hora para el recordatorio de carrito abandonado
        usuario.carrito_actualizado = timezone.now()
        usuario.save(update_fields=["carrito", "carrito_actualizado"])


def agregar_linea(request, sku, cantidad):
    datos = leer(request)
    datos["lineas"][sku] = datos["lineas"].get(sku, 0) + max(1, int(cantidad))
    guardar(request, datos)


def actualizar_linea(request, sku, cantidad):
    datos = leer(request)
    if cantidad <= 0:
        datos["lineas"].pop(sku, None)
    else:
        datos["lineas"][sku] = int(cantidad)
    guardar(request, datos)


def eliminar_linea(request, sku):
    datos = leer(request)
    datos["lineas"].pop(sku, None)
    guardar(request, datos)


def guardar_para_despues(request, sku):
    """Quita la línea del carrito y la deja en 'guardados'."""
    datos = leer(request)
    datos["lineas"].pop(sku, None)
    if sku not in datos["guardados"]:
        datos["guardados"].append(sku)
    guardar(request, datos)


def restaurar(request, sku):
    """Devuelve un producto guardado al carrito (cantidad 1)."""
    datos = leer(request)
    datos["guardados"] = [s for s in datos["guardados"] if s != sku]
    if sku not in datos["lineas"]:
        datos["lineas"][sku] = 1
    guardar(request, datos)


def set_cupon(request, codigo):
    datos = leer(request)
    datos["cupon"] = (codigo or "").strip().upper()
    guardar(request, datos)


def quitar_cupon(request):
    set_cupon(request, "")


def set_municipio(request, municipio):
    datos = leer(request)
    datos["municipio"] = (municipio or "").strip()
    guardar(request, datos)


def fusionar_carrito(carrito_sesion, carrito_usuario):
    """
    Fusiona el carrito de invitado (sesión) con el del usuario al iniciar
    sesión. Suma cantidades de las líneas repetidas, une los guardados y
    conserva el cupón/municipio de la sesión si los hay.

    Función pura (sin request): recibe y devuelve dicts con la misma forma.
    """
    sesion = carrito_sesion or {}
    usuario = carrito_usuario or {}
    lineas = dict(usuario.get("lineas") or {})
    for sku, cantidad in (sesion.get("lineas") or {}).items():
        try:
            cantidad = int(cantidad)
        except (TypeError, ValueError):
            continue
        if cantidad > 0:
            lineas[str(sku)] = lineas.get(str(sku), 0) + cantidad
    guardados = list(usuario.get("guardados") or [])
    for sku in sesion.get("guardados") or []:
        if sku not in guardados:
            guardados.append(sku)
    return {
        "lineas": lineas,
        "cupon": (sesion.get("cupon") or usuario.get("cupon") or "").strip().upper(),
        "municipio": sesion.get("municipio") or usuario.get("municipio") or "",
        "guardados": guardados,
    }


# ------------------------------------------------------------------ resumen

def _texto_whatsapp(resumen):
    """Resumen del carrito en texto plano para enviar por WhatsApp."""
    partes = ["Hola, quiero confirmar este pedido:"]
    for l in resumen.lineas:
        nombre = l.variante.producto.nombre
        partes.append(
            f"- {l.cantidad} x {nombre} ({l.variante.talla_label}) "
            f"- ${int(l.subtotal):,}".replace(",", ".")
        )
    partes.append(f"Subtotal: ${int(resumen.subtotal):,}".replace(",", "."))
    if resumen.total_descuentos:
        partes.append(
            f"Descuentos: -${int(resumen.total_descuentos):,}".replace(",", ".")
        )
    if resumen.cupon_error:
        partes.append(f"Nota: {resumen.cupon_error}")
    return "\n".join(partes) + "\n\n¿Me confirmas disponibilidad y envío?"


def resumen(request):
    """
    Resumen completo del carrito para plantillas (contexto global).

    Devuelve un dict con: items, lineas, totales, cupón, avisos de stock,
    envío por municipio, barra de envío gratis y texto para WhatsApp.
    """
    from catalog.models import Variante
    from shipping.models import zona_para_municipio

    datos = leer(request)
    avisos = []
    lineas = []
    no_disponibles = []

    # Una sola consulta para todas las líneas del carrito
    variantes = {
        v.sku: v
        for v in Variante.objects.select_related("producto").filter(
            sku__in=list(datos["lineas"])
        )
    }

    for sku, cantidad in datos["lineas"].items():
        variante = variantes.get(sku)
        if variante is None:
            no_disponibles.append(
                {"sku": sku, "cantidad": cantidad, "variante": None,
                 "motivo": "ya no está disponible"}
            )
            avisos.append(
                f"La referencia {sku} ya no está disponible; no se incluye en el total."
            )
            continue
        if not variante.disponible:
            no_disponibles.append(
                {"sku": sku, "cantidad": cantidad, "variante": variante,
                 "motivo": "está agotado por ahora"}
            )
            avisos.append(
                f"{variante.producto.nombre} está agotado por ahora; "
                "no se incluye en el total."
            )
            continue
        if cantidad > variante.stock:
            avisos.append(
                f"De {variante.producto.nombre} solo quedan {variante.stock} unidades; "
                "ajustamos la cantidad."
            )
            cantidad = variante.stock
        lineas.append(LineaCarrito(variante, cantidad))

    calculado = calcular_carrito(
        lineas,
        codigo_cupon=datos["cupon"] or None,
        usuario=getattr(request, "user", None),
    )

    # ---------- Envío estimado por municipio ----------
    envio = None
    if datos["municipio"]:
        zona = zona_para_municipio(datos["municipio"])
        if zona is None:
            avisos.append(
                f"Todavía no enviamos a {datos['municipio']}; elige otro municipio "
                "o escríbenos por WhatsApp para ayudarte."
            )
        else:
            costo, falta, gratis = zona.cobertura(calculado.subtotal)
            progreso = 0
            if gratis:
                progreso = 100
            elif zona.envio_gratis_desde:
                progreso = min(
                    100, int(calculado.subtotal * 100 / zona.envio_gratis_desde)
                )
            envio = {
                "municipio": datos["municipio"],
                "zona": zona,
                "costo": costo,
                "falta": falta,
                "gratis": gratis,
                "progreso": progreso,
            }

    # ---------- Guardados ("guardar para después") ----------
    guardados = []
    if datos["guardados"]:
        en_carrito = set(datos["lineas"])
        skus = [s for s in datos["guardados"] if s not in en_carrito]
        guardados = list(
            Variante.objects.select_related("producto").filter(sku__in=skus)
        )

    items = sum(l.cantidad for l in calculado.lineas)
    total = calculado.total
    if envio and not envio["gratis"]:
        total = total + envio["costo"]

    return {
        "vacio": not calculado.lineas and not no_disponibles,
        "items": items,
        "lineas": calculado.lineas,
        "lineas_no_disponibles": no_disponibles,
        "guardados": guardados,
        "avisos": avisos,
        # Totales
        "subtotal": calculado.subtotal,
        "subtotal_publicado": calculado.subtotal_publicado,
        "subtotal_base": calculado.subtotal_base,
        "descuento_ofertas": calculado.descuento_ofertas,
        "cupon": calculado.cupon,
        "cupon_codigo": datos["cupon"],
        "cupon_descuento": calculado.cupon_descuento,
        "cupon_error": calculado.cupon_error,
        "cupon_aviso": calculado.cupon_aviso,
        "total_descuentos": calculado.total_descuentos,
        "total": total,
        # Envío
        "municipio": datos["municipio"],
        "envio": envio,
        # Mensajes
        "whatsapp_texto": _texto_whatsapp(calculado) if calculado.lineas else "",
    }
