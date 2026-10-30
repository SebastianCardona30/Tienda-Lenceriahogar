def deseos(request):
    """
    Contexto global: ids de productos en la lista de deseos del cliente
    (para pintar el corazón ♥/♡ en tarjetas y fichas).
    """
    if request.user.is_authenticated:
        return {
            "deseos_ids": set(request.user.deseos.values_list("producto_id", flat=True))
        }
    return {"deseos_ids": set()}
