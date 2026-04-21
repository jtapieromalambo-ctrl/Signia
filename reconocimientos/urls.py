from django.urls import path
from . import views

urlpatterns = [
    # ── Reconocimiento ────────────────────────────────────────────
    path('camara/',        views.camara,        name='camara'),
    path('predecir/',      views.predecir,      name='predecir'),
    path('detectar_mano/', views.detectar_mano, name='detectar_mano'),

    # ── Panel admin ───────────────────────────────────────────────
    path('admin-videos/', views.admin_videos, name='admin_videos'),

    # Reconocimiento: subir y eliminar
    path('admin-videos/reconocimiento/subir/',
         views.reconocimiento_subir, name='reconocimiento_subir'),
    path('admin-videos/reconocimiento/eliminar/<int:video_id>/',
         views.reconocimiento_eliminar, name='reconocimiento_eliminar'),

    # Traductor: CRUD completo
    path('admin-videos/traductor/crear/',
         views.traductor_crear, name='traductor_crear'),
    path('admin-videos/traductor/editar/<int:video_id>/',
         views.traductor_editar, name='traductor_editar'),
    path('admin-videos/traductor/eliminar/<int:video_id>/',
         views.traductor_eliminar, name='traductor_eliminar'),

    # ✅ ESTAS DOS FALTAN — agrégalas aquí:
    path('admin-videos/entrenar/',
         views.entrenar_modelo, name='entrenar_modelo'),
    path('admin-videos/entrenar/estado/',
         views.estado_entrenamiento, name='estado_entrenamiento'),

    # Señas entrenadas con efectividad
    path('admin-videos/senas-entrenadas/',
         views.senas_entrenadas, name='senas_entrenadas'),
]