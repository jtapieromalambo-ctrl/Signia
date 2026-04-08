from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from allauth.exceptions import ImmediateHttpResponse
from django.shortcuts import redirect
from django.contrib import messages
from django.contrib.auth import get_user_model

User = get_user_model()

class SocialAccountAdapter(DefaultSocialAccountAdapter):
    def pre_social_login(self, request, sociallogin):
        # Verificar si el email ya existió y fue eliminado
        email = sociallogin.account.extra_data.get('email', '')
        
        if email:
            try:
                user = User.objects.get(email=email)
                if user.is_deleted:  # o not user.is_active
                    messages.error(
                        request,
                        'Esta cuenta fue eliminada. Debes crear una cuenta nueva para ingresar.'
                    )
                    raise ImmediateHttpResponse(redirect('registro'))
            except User.DoesNotExist:
                pass