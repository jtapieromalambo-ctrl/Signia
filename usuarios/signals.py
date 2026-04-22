from allauth.socialaccount.signals import pre_social_login
from django.dispatch import receiver

@receiver(pre_social_login)
def set_disability_modal(sender, request, sociallogin, **kwargs):
    # Solo mostrar modal la primera vez (usuario nuevo con Google)
    if not sociallogin.is_existing:
        request.session['show_disability_modal'] = True