from django.urls import path
from . import views

urlpatterns = [
    path('traductor/', views.traductor, name='traductor'),
]