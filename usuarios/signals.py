from allauth.socialaccount.signals import social_account_updated, pre_social_login
from django.dispatch import receiver

@receiver(pre_social_login)
def set_disability_modal(sender, request, sociallogin, **kwargs):
    request.session['show_disability_modal'] = True