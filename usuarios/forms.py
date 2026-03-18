from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import Usuario


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