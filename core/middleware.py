"""
Middleware de sesión: cierra la cuenta del usuario cuando pasa un rato
sin actividad (pestaña olvidada, computador prestado, etc.).
"""
import time

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import logout
from django.shortcuts import redirect
from django.urls import reverse


class SesionPorInactividad:
    """Cierra la sesión de los usuarios autenticados tras X minutos sin actividad.

    - Solo aplica a usuarios con sesión iniciada: el carrito de invitado no se
      toca (no hay credenciales que proteger).
    - La marca de última actividad vive en la sesión del servidor; el navegador
      solo lleva la cookie de sesión httpOnly.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if self._vencida(request):
            logout(request)
            # Petición de HTMX: responde 401 sin rellenar el fragmento con la
            # página de ingreso; la próxima navegación normal sí redirige.
            if request.headers.get("HX-Request"):
                from django.http import HttpResponse

                return HttpResponse(status=401)
            messages.warning(
                request,
                "Cerramos tu sesión por inactividad. Inicia de nuevo para continuar.",
            )
            return redirect(reverse("accounts:ingreso"))
        self._registrar_actividad(request)
        return self.get_response(request)

    def _vencida(self, request):
        usuario = getattr(request, "user", None)
        if usuario is None or not usuario.is_authenticated:
            return False
        ultimo = request.session.get("ultima_actividad")
        if ultimo is None:
            return False  # primera petición tras iniciar sesión: solo se marca
        limite = getattr(settings, "SESION_INACTIVIDAD_MINUTOS", 30) * 60
        return (time.time() - ultimo) > limite

    @staticmethod
    def _registrar_actividad(request):
        usuario = getattr(request, "user", None)
        if usuario is not None and usuario.is_authenticated:
            request.session["ultima_actividad"] = time.time()
