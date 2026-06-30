from allauth.socialaccount.signals import pre_social_login
from django.dispatch import receiver
from django.db.models.signals import post_migrate
from django.core.signals import request_started
from django.conf import settings


@receiver(pre_social_login)
def set_disability_modal(sender, request, sociallogin, **kwargs):
    if sociallogin.is_existing:
        user = sociallogin.user
        if user.discapacidad_seleccionada:
            request.session.pop('show_disability_modal', None)
        else:
            request.session['show_disability_modal'] = True
    else:
        request.session['show_disability_modal'] = True


def _get_local_domain():
    """Devuelve el dominio correcto según el entorno."""
    if getattr(settings, 'DEBUG', False):
        return '127.0.0.1:8000'
    return getattr(settings, 'SITE_DOMAIN', 'www.signia.click')


def _update_site():
    """Actualiza el registro Site en BD con el dominio del entorno actual."""
    try:
        from django.contrib.sites.models import Site
        domain = _get_local_domain()
        name = 'Signia Local' if settings.DEBUG else 'Signia'
        Site.objects.filter(id=settings.SITE_ID).update(domain=domain, name=name)
    except Exception:
        pass  # BD aún no lista (primera migración, etc.)


@receiver(post_migrate)
def configure_site(sender, **kwargs):
    """Tras cada migrate, sincroniza el Site con el entorno actual."""
    if sender.name != 'django.contrib.sites':
        return
    domain = _get_local_domain()
    name = 'Signia Local' if settings.DEBUG else 'Signia'
    try:
        from django.contrib.sites.models import Site
        Site.objects.update_or_create(
            id=settings.SITE_ID,
            defaults={'domain': domain, 'name': name},
        )
    except Exception:
        pass


# Actualizar el Site en la primera petición HTTP para que no sea necesario
# ejecutar migrate manualmente al cambiar de entorno (prod ↔ local).
_site_fixed = False

@receiver(request_started)
def fix_site_on_startup(sender, **kwargs):
    global _site_fixed
    if _site_fixed:
        return
    _site_fixed = True
    _update_site()