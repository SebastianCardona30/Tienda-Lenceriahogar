def carrito(request):
    """
    Contexto global: resumen del carrito (contador del encabezado,
    drawer lateral y página del carrito).

    Con el carrito vacío no hace consultas a la base de datos.
    """
    from cart.servicios import resumen

    return {"carrito_ui": resumen(request)}
