from django.urls import path
from . import views

urlpatterns = [
    path('',         views.home,         name='home'),
    path('registro/', views.registro,    name='registro'),
    path('logout/',   views.logout_view, name='logout'),
    path('perfil/',   views.perfil,      name='perfil'),
    path("contacto/", views.contacto, name="contacto"),
]