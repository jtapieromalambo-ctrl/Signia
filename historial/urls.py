from django.urls import path
from . import views

urlpatterns = [
    path('historial/', views.historial, name='historial'),
    path('historial/eliminar/<int:entrada_id>/', views.eliminar_entrada, name='eliminar_entrada'),  


    # Usuario borra TODO su historial (DELETE /api/history/clear/)
    path("historial/clear/", views.clear_all_history, name="clear_my_history"),
 
    # Admin borra TODO el historial de un usuario (DELETE /api/history/clear/3/)
    path("historial/clear/<int:user_id>/", views.clear_all_history, name="clear_user_history"),

]