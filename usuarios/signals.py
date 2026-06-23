from allauth.socialaccount.signals import pre_social_login
from django.dispatch import receiver
from django.db.models.signals import post_migrate
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


@receiver(post_migrate)
def configure_site(sender, **kwargs):
    if sender.name != 'django.contrib.sites':
        return
    from django.contrib.sites.models import Site
    domain = getattr(settings, 'SITE_DOMAIN', 'www.signia.click')
    Site.objects.update_or_create(
        id=settings.SITE_ID,
        defaults={'domain': domain, 'name': 'Signia'},
    )