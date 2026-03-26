from django.db import models


class VideoSeña(models.Model):
    label = models.CharField(max_length=100, verbose_name="Seña")
    video = models.FileField(upload_to='video_señas/', verbose_name="Video")
    creado = models.DateTimeField(auto_now_add=True)
    procesando = models.BooleanField(default=False, verbose_name="Procesando")
    procesado = models.BooleanField(default=False, verbose_name="Procesado") 

    class Meta:
        verbose_name = "Video de Seña"
        verbose_name_plural = "Videos de Señas"

    def __str__(self):
        return f"{self.label} - {self.creado.strftime('%d/%m/%Y')}"