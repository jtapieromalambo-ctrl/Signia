from allauth.socialaccount.adapter import DefaultSocialAccountAdapter

class SocialAccountAdapter(DefaultSocialAccountAdapter):

    def is_open_for_signup(self, request, sociallogin):
        email = sociallogin.account.extra_data.get('email', '')
        from .models import Usuario
        if Usuario.objects.filter(email=email, is_active=False).exists():
            from django.contrib import messages
            messages.error(request, 'Esta cuenta fue eliminada y no puede volver a registrarse.')
            return False
        return True

    def save_user(self, request, sociallogin, form=None):
        user = super().save_user(request, sociallogin, form)
        user.is_active = True
        user.save()
        return user

    def get_login_redirect_url(self, request):
        """Para usuarios que ya existían y hacen login con Google"""
        user = request.user
        if user.is_authenticated and user.discapacidad == 'ninguna':
            return '/seleccionar-discapacidad/'
        if user.discapacidad == 'sordo':
            return '/traduccion/'
        elif user.discapacidad == 'mudo':
            return '/reconocimientos/camara/'
        return '/perfil/'

    def get_signup_redirect_url(self, request):
        """Para usuarios nuevos que se registran con Google por primera vez"""
        return '/seleccionar-discapacidad/'