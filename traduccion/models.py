# ✅ DESPUÉS (correcto)
from django.db import models
from django.conf import settings

class Traduccion(models.Model):
    usuario   = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    # Apunta al modelo de usuario que defina settings.py
    # sea el de Django por defecto o uno personalizado

    seña      = models.CharField(max_length=10)
    palabra   = models.CharField(max_length=100)
    confianza = models.IntegerField()
    fecha     = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-fecha']

    def __str__(self):
        return f"{self.usuario} — {self.palabra} ({self.fecha})"