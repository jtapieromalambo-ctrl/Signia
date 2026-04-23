from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import Usuario
from .models import MensajeContacto


class RegistroForm(UserCreationForm):
    email = forms.EmailField(required=True, label='Correo electrónico')

    DISCAPACIDAD_CHOICES = [
        ('ninguna', 'No tengo discapacidad'),
        ('sordo',   'Soy sordo (quiero texto → señas)'),
        ('mudo',    'Soy mudo (quiero señas → texto)'),
    ]

    discapacidad = forms.ChoiceField(
        choices=DISCAPACIDAD_CHOICES,
        label='¿Tienes alguna discapacidad?',
        widget=forms.RadioSelect
    )
    def clean_email(self):  # ← agregar esto
        email = self.cleaned_data.get('email')
        if Usuario.objects.filter(email=email).exists():
            raise forms.ValidationError('Ya existe una cuenta con este correo electrónico.')
        return email

    class Meta:
        model  = Usuario
        fields = ['username', 'email', 'password1', 'password2', 'discapacidad']


class EditarPerfilForm(forms.ModelForm):
    # Sobreescribimos el campo para quitar el validador de caracteres de Django
    username = forms.CharField(
        max_length=150,
        label='Nombre de usuario',
    )

    class Meta:
        model  = Usuario
        fields = ['username']

    def clean_username(self):
        username = self.cleaned_data.get('username').strip()
        if not username:
            raise forms.ValidationError('El nombre de usuario no puede estar vacío.')
        qs = Usuario.objects.filter(username=username).exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError('Este nombre de usuario ya está en uso.')
        return username


class ContactoForm(forms.ModelForm):
    class Meta:
        model = MensajeContacto
        fields = ['nombre', 'correo', 'observacion', 'mensaje']
        widgets = {
            'nombre': forms.TextInput(attrs={
                'placeholder': 'Tu nombre completo'
            }),
            'correo': forms.EmailInput(attrs={
                'placeholder': 'tucorreo@ejemplo.com'
            }),
            'observacion': forms.TextInput(attrs={
                'placeholder': 'Tu observación...'
            }),
            'mensaje': forms.Textarea(attrs={
                'placeholder': 'Escribe tu mensaje aquí...',
                'rows': 4
            }),
        }