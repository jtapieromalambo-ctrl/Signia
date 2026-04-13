from django.contrib import admin
from .models import MensajeContacto



@admin.register(MensajeContacto)
class MensajeContactoAdmin(admin.ModelAdmin):
    list_display = ['nombre', 'correo', 'fecha']
    search_fields = ['nombre', 'correo']
    readonly_fields = ['fecha']