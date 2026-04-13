from django.contrib.auth.models import AbstractUser
from django.db import models

class Usuario(AbstractUser):
    DISCAPACIDAD_CHOICES = [
        ('ninguna', 'Ninguna'),
        ('sordo',   'Sordo'),
        ('mudo',    'Mudo'),
    ]

    email = models.EmailField(unique=True)  # ← agregado

    discapacidad = models.CharField(
        max_length=10,
        choices=DISCAPACIDAD_CHOICES,
        default='ninguna'
    )

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