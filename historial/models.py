from django.db import models
from django.conf import settings


class EntradaHistorial(models.Model):
    """Registra toda actividad del usuario: traducciones y reconocimientos."""

    TIPO_CHOICES = [
        ('traduccion',     'Traducción texto → señas'),
        ('reconocimiento', 'Reconocimiento señas → texto'),
    ]

    usuario  = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='historial'
    )
    tipo     = models.CharField(max_length=20, choices=TIPO_CHOICES)
    contenido = models.TextField()                     # El texto traducido o la seña reconocida
    fecha    = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-fecha']
        verbose_name = 'Entrada de historial'
        verbose_name_plural = 'Historial'

    def __str__(self):
        return f"{self.usuario} — {self.get_tipo_display()} — {self.fecha:%d/%m/%Y %H:%M}"