from django.db import models
from django.conf import settings


class Traduccion(models.Model):
    """Guarda cada traducción de texto a señas realizada por un usuario."""

    usuario  = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='traducciones'
    )
    texto    = models.TextField(default='')              # Texto que el usuario escribió
    fecha    = models.DateTimeField(auto_now_add=True) # Cuándo se hizo la traducción

    class Meta:
        ordering = ['-fecha']
        verbose_name = 'Traducción'
        verbose_name_plural = 'Traducciones'

    def __str__(self):
        return f"{self.usuario} — {self.texto[:40]} ({self.fecha:%d/%m/%Y})"