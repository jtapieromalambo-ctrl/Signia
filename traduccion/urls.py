from django.urls import path
from . import views

urlpatterns = [
    path('traductor/', views.buscar_video, name='traduccion'),
    path('base/', views.pagina_base, name='pagina_base'),
]