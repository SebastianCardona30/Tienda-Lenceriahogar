"""Vistas de reportes del negocio (solo personal autenticado)."""
from django.http import Http404, HttpResponse
from django.shortcuts import render

from dashboard import reportes


def _sin_permiso(request):
    """True si el usuario no puede ver reportes (no es del personal)."""
    return not (request.user.is_active and request.user.is_staff)


def pagina_reportes(request):
    """Lista de reportes con filtros de fechas (todos menos inventario)."""
    if _sin_permiso(request):
        raise Http404
    tipos = [
        {"clave": clave, "titulo": titulo, "usa_fechas": usa_fechas}
        for clave, (titulo, _funcion, usa_fechas) in reportes.TIPOS.items()
    ]
    contexto = {
        "tipos": tipos,
        "desde": request.GET.get("desde", ""),
        "hasta": request.GET.get("hasta", ""),
    }
    return render(request, "dashboard/reportes.html", contexto)


def descargar_reporte(request):
    """Genera el CSV solicitado y lo descarga."""
    if _sin_permiso(request):
        raise Http404
    tipo = request.GET.get("tipo", "")
    if tipo not in reportes.TIPOS:
        raise Http404
    desde = request.GET.get("desde", "") or None
    hasta = request.GET.get("hasta", "") or None

    titulo, encabezados, filas = reportes.generar_reporte(tipo, desde, hasta)
    contenido = reportes.a_csv(encabezados, filas)
    respuesta = HttpResponse(contenido, content_type="text/csv; charset=utf-8")
    respuesta["Content-Disposition"] = (
        f'attachment; filename="{reportes.nombre_archivo(tipo, desde, hasta)}"'
    )
    return respuesta
