from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import Usuario, MensajeContacto

@admin.register(Usuario)
class UsuarioAdmin(UserAdmin):
    list_display = ['username', 'email', 'is_active', 'discapacidad']
    list_editable = ['is_active']
    fieldsets = UserAdmin.fieldsets + (
        ('Signia', {'fields': ('discapacidad',)}),
    )

@admin.register(MensajeContacto)
class MensajeContactoAdmin(admin.ModelAdmin):
    list_display = ['nombre', 'correo', 'fecha']
    search_fields = ['nombre', 'correo']
    readonly_fields = ['fecha']