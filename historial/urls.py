from django.urls import path
from . import views

urlpatterns = [
    path('historial/', views.historial, name='historial'),
    path('historial/eliminar/<int:entrada_id>/', views.eliminar_entrada, name='eliminar_entrada'),  
]