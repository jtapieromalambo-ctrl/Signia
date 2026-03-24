from django.contrib import admin
from .models import video

# Register your models here.


@admin.register(video)

class VideoAdmin(admin.ModelAdmin):
    list_display = ('nombre','video')
    search_fields= ('nombre',)
