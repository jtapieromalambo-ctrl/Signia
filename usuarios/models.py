from django.db import models
from django.conf import settings
from django.contrib.auth.models import AbstractUser
import random
import string


class Usuario(AbstractUser):
    DISCAPACIDAD_CHOICES = [
        ('ninguna', 'Ninguna'),
        ('sordo',   'Sordo'),
        ('mudo',    'Mudo'),
    ]

    discapacidad = models.CharField(
        max_length=10,
        choices=DISCAPACIDAD_CHOICES,
        default='ninguna'
    )

    def __str__(self):
        return self.username


class CodigoVerificacion(models.Model):
    """Código de 6 dígitos para recuperar contraseña."""
    usuario  = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    codigo   = models.CharField(max_length=6)
    creado   = models.DateTimeField(auto_now_add=True)
    usado    = models.BooleanField(default=False)

    class Meta:
        ordering = ['-creado']

    def __str__(self):
        return f"{self.usuario.email} — {self.codigo}"

    @staticmethod
    def generar_codigo():
        return ''.join(random.choices(string.digits, k=6))