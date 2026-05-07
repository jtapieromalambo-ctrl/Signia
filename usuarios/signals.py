from allauth.socialaccount.signals import pre_social_login
from django.dispatch import receiver

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