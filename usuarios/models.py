from django.contrib.auth.models import AbstractUser
from django.db import models
import random
import string
from django.utils import timezone
from datetime import timedelta


class Usuario(AbstractUser):
    # Sobreescribimos username para permitir espacios y caracteres especiales
    username = models.CharField(
        max_length=150,
        unique=True,
        validators=[],  # quitamos UnicodeUsernameValidator
    )

    DISCAPACIDAD_CHOICES = [
        ('ninguna', 'Ninguna'),
        ('sordo',   'Sordo'),
        ('mudo',    'Mudo'),
    ]

    email = models.EmailField(unique=True)
    discapacidad = models.CharField(
        max_length=10,
        choices=DISCAPACIDAD_CHOICES,
        default='ninguna'
    )
    email_verificado = models.BooleanField(default=False)
    acepto_terminos = models.BooleanField(default=False)
    fecha_aceptacion_terminos = models.DateTimeField(null=True, blank=True)
    discapacidad_seleccionada = models.BooleanField(default=False)

    def __str__(self):
        return self.username


class MensajeContacto(models.Model):
    nombre = models.CharField(max_length=200)
    correo = models.EmailField()
    observacion = models.TextField(blank=True, null=True)
    mensaje = models.TextField()
    fecha = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.nombre} - {self.correo}"

    class Meta:
        verbose_name = "Mensaje de Contacto"
        verbose_name_plural = "Mensajes de Contacto"


class CodigoOTP(models.Model):
    usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE, related_name='codigos_otp')
    codigo = models.CharField(max_length=6)
    creado_en = models.DateTimeField(auto_now_add=True)
    usado = models.BooleanField(default=False)

    def esta_vigente(self):
        return not self.usado and timezone.now() < self.creado_en + timedelta(minutes=10)

    @classmethod
    def generar(cls, usuario):
        cls.objects.filter(usuario=usuario, usado=False).update(usado=True)
        codigo = ''.join(random.choices(string.digits, k=6))
        return cls.objects.create(usuario=usuario, codigo=codigo)

    def __str__(self):
        return f"OTP {self.codigo} para {self.usuario.email}"