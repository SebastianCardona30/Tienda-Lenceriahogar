"""Formulario del checkout (una sola página con 3 pasos)."""
from django import forms

from shipping.models import MunicipioSantander

# Casillas de verificación (mayor de edad y tratamiento de datos)
class _Casilla(forms.CheckboxInput):
    template_name = "orders/_casilla.html"


class CheckoutForm(forms.Form):
    # ---------- Paso 1: datos ----------
    nombre = forms.CharField(label="Nombre de quien recibe", max_length=120)
    email = forms.EmailField(label="Correo electrónico")
    telefono = forms.CharField(
        label="Celular (WhatsApp)", max_length=20,
        help_text="Lo usamos para confirmar tu pedido y avisarte del envío.",
    )
    cedula = forms.CharField(
        label="Cédula", max_length=20, required=False,
        help_text="Opcional. La piden algunas transportadoras.",
    )
    mayor_de_edad = forms.BooleanField(
        label="Confirmo que soy mayor de edad", required=True,
        error_messages={"required": "Debes confirmar que eres mayor de edad."},
    )
    autoriza_datos = forms.BooleanField(
        label="Acepto los términos y la política de tratamiento de datos",
        required=True,
        error_messages={"required": "Debes aceptar los términos y la política de datos."},
    )

    # ---------- Paso 2: envío ----------
    municipio = forms.ChoiceField(label="Municipio de entrega (Santander)")
    direccion = forms.CharField(
        label="Dirección", max_length=160,
        help_text="Calle, número y apartamento. Ej.: Cra 15 # 42-10, apto 302",
    )
    barrio = forms.CharField(label="Barrio", max_length=80, required=False)
    indicaciones = forms.CharField(
        label="Indicaciones para la entrega", max_length=200, required=False,
        help_text="Ej.: portón negro, tocar el timbre 302.",
    )

    # ---------- Paso 3: pago ----------
    metodo_pago = forms.ChoiceField(
        label="Método de pago",
        choices=[("contraentrega", "Contraentrega — pagas al recibir"),
                 ("transferencia", "Transferencia / Nequi / Daviplata")],
        widget=forms.RadioSelect,
        initial="contraentrega",
    )

    def __init__(self, *args, usuario=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.usuario = usuario
        # La pasarela en línea solo aparece si está habilitada (ver settings)
        from django.conf import settings

        if getattr(settings, "PASARELA_SIMULADA", False):
            self.fields["metodo_pago"].choices = [
                ("pasarela", "Tarjeta, PSE o Nequi — pago en línea"),
            ] + list(self.fields["metodo_pago"].choices)
            self.fields["metodo_pago"].initial = "pasarela"
        municipios = MunicipioSantander.objects.order_by("nombre")
        self.fields["municipio"].choices = [("", "Elige tu municipio…")] + [
            (m.nombre, m.nombre) for m in municipios
        ]
        # Autocompletar desde la cuenta o la dirección predeterminada
        if usuario and usuario.is_authenticated:
            inicial = {
                "nombre": usuario.get_full_name().strip(),
                "email": usuario.email,
                "telefono": usuario.telefono,
                "cedula": usuario.cedula,
            }
            predeterminada = usuario.direccion_predeterminada
            if predeterminada:
                inicial.update({
                    "municipio": predeterminada.municipio.nombre,
                    "direccion": predeterminada.direccion,
                    "barrio": predeterminada.barrio,
                    "indicaciones": predeterminada.indicaciones,
                })
            for campo, valor in inicial.items():
                if valor and not self.is_bound:
                    self.fields[campo].initial = valor
