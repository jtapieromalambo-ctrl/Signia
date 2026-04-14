from django.urls import path
from . import views

urlpatterns = [
    path('',                views.index,            name='index'),
    path('login/',          views.home,             name='home'),
    path('registro/',       views.registro,         name='registro'),
    path('logout/',         views.logout_view,      name='logout'),
    path('perfil/',         views.perfil,           name='perfil'),
    path('perfil/editar/',  views.editar_perfil,    name='editar_perfil'),
    path('perfil/password/',views.cambiar_password, name='cambiar_password'),
    path('perfil/eliminar/',views.eliminar_cuenta,  name='eliminar_cuenta'),
    path('contacto/',       views.contacto,         name='contacto'),
    path('reconocimiento/', views.reconocimiento,   name='reconocimiento'),
    path('admin-videos/', views.panel_admin_videos, name='panel_admin_videos'),
    path('mensajes/eliminar/<int:mensaje_id>/', views.eliminar_mensaje_contacto, name='eliminar_mensaje_contacto'),


    # Recuperar contraseña con código
    path('recuperar/',          views.recuperar_password,  name='recuperar_password'),
    path('verificar-codigo/',   views.verificar_codigo,    name='verificar_codigo'),
    path('nueva-password/',     views.nueva_password,      name='nueva_password'),
]