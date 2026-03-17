from django.db import models
from django.conf import settings


class Reconocimiento(models.Model):
    """Guarda cada seña reconocida por la cámara y su traducción a texto."""

    usuario   = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='reconocimientos'
    )
    seña      = models.CharField(max_length=100)       # Seña detectada (ej: "Hola", "Gracias")
    confianza = models.FloatField(default=0.0)         # Nivel de confianza 0.0 - 1.0
    fecha     = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-fecha']
        verbose_name = 'Reconocimiento'
        verbose_name_plural = 'Reconocimientos'

    def __str__(self):
        return f"{self.usuario} — {self.seña} ({self.confianza:.0%}) — {self.fecha:%d/%m/%Y}"