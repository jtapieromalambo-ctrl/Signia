from django.contrib import admin
from django.contrib import messages
from .models import VideoSeña
from .scripts.train_model import train_and_save
import os


def entrenar_modelo(modeladmin, request, queryset):
    landmarks_dir = os.path.join('reconocimientos', 'models', 'landmarks')
    model_path = os.path.join('reconocimientos', 'models', 'model.pkl')

    try:
        metricas = train_and_save(landmarks_dir, model_path)
        messages.success(
            request,
            f"✅ Modelo entrenado exitosamente. "
            f"Accuracy: {metricas['accuracy']:.2%} | "
            f"Clases: {', '.join(metricas['clases'])} | "
            f"Muestras: {metricas['total_muestras']}"
        )
    except ValueError as e:
        messages.error(request, f"❌ Error de datos: {e}")
    except Exception as e:
        messages.error(request, f"❌ Error inesperado: {e}")


entrenar_modelo.short_description = "🤖 Entrenar modelo con videos procesados"


@admin.register(VideoSeña)
class VideoSeñaAdmin(admin.ModelAdmin):
    list_display = ['label', 'procesado', 'procesando', 'creado']
    list_filter = ['procesado', 'procesando', 'label']
    search_fields = ['label']
    actions = [entrenar_modelo]
    readonly_fields = ['creado', 'procesado', 'procesando']