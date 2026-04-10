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