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
    DISCAPACIDAD_CHOICES = [
        ('ninguna', 'No tengo discapacidad'),
        ('sordo',   'Soy sordo'),
        ('mudo',    'Soy mudo'),
    ]

    discapacidad = forms.ChoiceField(
        choices=DISCAPACIDAD_CHOICES,
        label='Tipo de acceso',
        widget=forms.RadioSelect
    )

    class Meta:
        model  = Usuario
        fields = ['username', 'discapacidad']




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