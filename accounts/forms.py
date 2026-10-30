"""Formularios de cuentas: registro, ingreso, perfil, direcciones y borrado."""
from django import forms
from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password

from accounts.models import Direccion, Usuario


class RegistroForm(forms.Form):
    nombre = forms.CharField(label="Nombre completo", max_length=150)
    email = forms.EmailField(label="Correo electrónico")
    celular = forms.CharField(
        label="Celular (WhatsApp)", max_length=20, required=False,
        help_text="Opcional. Lo usamos para avisarte de tu pedido por WhatsApp.",
    )
    password1 = forms.CharField(
        label="Contraseña", widget=forms.PasswordInput(
            attrs={"autocomplete": "new-password"}
        ),
    )
    password2 = forms.CharField(
        label="Repite la contraseña", widget=forms.PasswordInput(
            attrs={"autocomplete": "new-password"}
        ),
    )

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        if Usuario.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("Ya hay una cuenta con ese correo.")
        return email

    def clean_password1(self):
        password = self.cleaned_data.get("password1")
        if password:
            validate_password(password)
        return password

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("password1") and cleaned.get("password2"):
            if cleaned["password1"] != cleaned["password2"]:
                self.add_error("password2", "Las contraseñas no coinciden.")
        return cleaned

    def guardar(self):
        """Crea el usuario con el correo como nombre de usuario."""
        nombre = self.cleaned_data["nombre"].strip().split(" ", 1)
        usuario = Usuario.objects.create_user(
            username=self.cleaned_data["email"].strip().lower(),
            email=self.cleaned_data["email"],
            first_name=nombre[0],
            last_name=nombre[1] if len(nombre) > 1 else "",
            telefono=self.cleaned_data.get("celular", ""),
            password=self.cleaned_data["password1"],
        )
        return usuario


class IngresoForm(forms.Form):
    email = forms.EmailField(label="Correo electrónico")
    password = forms.CharField(
        label="Contraseña", widget=forms.PasswordInput(attrs={"autocomplete": "current-password"})
    )

    def __init__(self, request=None, *args, **kwargs):
        self.request = request
        self.usuario = None
        super().__init__(*args, **kwargs)

    def clean(self):
        cleaned = super().clean()
        email = cleaned.get("email", "").strip().lower()
        password = cleaned.get("password", "")
        if email and password:
            self.usuario = authenticate(self.request, username=email, password=password)
            if self.usuario is None:
                raise forms.ValidationError(
                    "Correo o contraseña incorrectos. Revísalos e inténtalo de nuevo."
                )
        return cleaned


class PerfilForm(forms.ModelForm):
    class Meta:
        model = Usuario
        fields = ("first_name", "last_name", "email", "telefono", "cedula")
        labels = {
            "first_name": "Nombre",
            "last_name": "Apellido",
            "email": "Correo electrónico",
            "telefono": "Celular (WhatsApp)",
            "cedula": "Cédula (opcional)",
        }
        widgets = {
            "first_name": forms.TextInput(attrs={"autocomplete": "given-name"}),
            "last_name": forms.TextInput(attrs={"autocomplete": "family-name"}),
            "email": forms.EmailInput(attrs={"autocomplete": "email"}),
            "telefono": forms.TextInput(attrs={"autocomplete": "tel"}),
        }

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        duenos = Usuario.objects.filter(email__iexact=email).exclude(pk=self.instance.pk)
        if duenos.exists():
            raise forms.ValidationError("Ya hay una cuenta con ese correo.")
        return email


class DireccionForm(forms.ModelForm):
    class Meta:
        model = Direccion
        fields = (
            "destinatario", "municipio", "barrio", "direccion",
            "indicaciones", "telefono", "predeterminada",
        )
        widgets = {
            "destinatario": forms.TextInput(attrs={"autocomplete": "name"}),
            "barrio": forms.TextInput(),
            "direccion": forms.TextInput(
                attrs={"autocomplete": "street-address", "placeholder": "Cra 15 # 42-10, apto 302"}
            ),
            "indicaciones": forms.TextInput(
                attrs={"placeholder": "Portón negro, tocar timbre 302"}
            ),
            "telefono": forms.TextInput(attrs={"autocomplete": "tel"}),
        }


class EliminarCuentaForm(forms.Form):
    password = forms.CharField(
        label="Confirma con tu contraseña",
        widget=forms.PasswordInput(attrs={"autocomplete": "current-password"}),
        help_text="Por seguridad, escribe tu contraseña para eliminar la cuenta.",
    )

    def __init__(self, usuario, *args, **kwargs):
        self.usuario = usuario
        super().__init__(*args, **kwargs)

    def clean_password(self):
        password = self.cleaned_data["password"]
        if not self.usuario.check_password(password):
            raise forms.ValidationError("La contraseña no es correcta.")
        return password
