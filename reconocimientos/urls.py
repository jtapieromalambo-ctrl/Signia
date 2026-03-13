from django.urls import path
from . import views

urlpatterns = [
    path('',      views.reconocimiento, name='reconocimiento'),
    path('feed/', views.video_feed,     name='video_feed'),
]