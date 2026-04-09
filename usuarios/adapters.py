from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from allauth.exceptions import ImmediateHttpResponse
from django.shortcuts import redirect
from django.contrib import messages
from django.contrib.auth import get_user_model

User = get_user_model()

class SocialAccountAdapter(DefaultSocialAccountAdapter):
    def pre_social_login(self, request, sociallogin):
        email = sociallogin.account.extra_data.get('email', '')
        
        if email:
            user = User.objects.filter(email=email).first()
            if user and user.is_deleted:
                messages.error(
                    request,
                    'Esta cuenta fue eliminada. Debes crear una cuenta nueva para ingresar.'
                )
                raise ImmediateHttpResponse(redirect('registro'))