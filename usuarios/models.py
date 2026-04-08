from django.contrib.auth.models import AbstractUser
from django.db import models

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
    is_deleted = models.BooleanField(default=False)
    deleted_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return self.username