from django.urls import path
from . import views

urlpatterns = [
    path('',                views.index,           name='index'),
    path('login/',          views.home,            name='home'),
    path('registro/',       views.registro,        name='registro'),
    path('logout/',         views.logout_view,     name='logout'),
    path('perfil/',         views.perfil,          name='perfil'),
    path('perfil/editar/',  views.editar_perfil,   name='editar_perfil'),
    path('perfil/password/',views.cambiar_password,name='cambiar_password'),
    path('contacto/',       views.contacto,        name='contacto'),
    path('reconocimiento/', views.reconocimiento,  name='reconocimiento'),
]