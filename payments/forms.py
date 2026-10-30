"""Formularios de pagos: subida del comprobante de transferencia/Nequi/Daviplata."""
from django import forms

from payments.models import Pago

# Límite de tamaño del comprobante (5 MB): suficiente para una foto de la app
# del banco y pequeño para el disco gratuito.
TAMANO_MAXIMO = 5 * 1024 * 1024


class ComprobanteForm(forms.ModelForm):
    """Comprobante del pago: imagen (JPG/PNG/WebP) o PDF, con validación real."""

    # FileField en vez de ImageField: el validador nativo de Django (Pillow)
    # rechazaría los PDF antes de nuestra propia validación.
    comprobante = forms.FileField(
        label="Comprobante de pago",
        help_text="Foto o captura de la confirmación del banco, Nequi o Daviplata. "
                  "También acepta PDF. Máximo 5 MB.",
        widget=forms.ClearableFileInput(attrs={
            "accept": "image/jpeg,image/png,image/webp,application/pdf",
        }),
    )

    class Meta:
        model = Pago
        fields = ["comprobante"]

    def clean_comprobante(self):
        archivo = self.cleaned_data.get("comprobante")
        if not archivo:
            raise forms.ValidationError("Adjunta el comprobante de tu pago.")

        if archivo.size > TAMANO_MAXIMO:
            raise forms.ValidationError(
                "El archivo pesa más de 5 MB. Envía una foto más pequeña, por favor."
            )

        # El content-type del navegador no es confiable: se valida el contenido.
        cabecera = archivo.read(5)
        archivo.seek(0)
        es_pdf = cabecera.startswith(b"%PDF-")
        if not es_pdf:
            try:
                from PIL import Image

                imagen = Image.open(archivo)
                imagen.verify()  # comprueba que no esté corrupta
                archivo.seek(0)
            except Exception as exc:
                raise forms.ValidationError(
                    "Solo aceptamos imágenes (JPG, PNG o WebP) o PDF."
                ) from exc

        return archivo
