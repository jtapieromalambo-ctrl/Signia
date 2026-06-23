from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from allauth.socialaccount.models import SocialApp
from django.conf import settings


class SocialAccountAdapter(DefaultSocialAccountAdapter):

    def get_app(self, request, provider, client_id=None):
        config = settings.SOCIALACCOUNT_PROVIDERS.get(provider, {}).get('APP', {})
        if config and config.get('client_id'):
            app = SocialApp(
                provider=provider,
                client_id=config['client_id'],
                secret=config.get('secret', ''),
                key=config.get('key', ''),
            )
            app.pk = 0
            return app
        return super().get_app(request, provider, client_id=client_id)


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
        user = request.user
        if user.is_authenticated and not user.discapacidad_seleccionada:
            return '/seleccionar-discapacidad/'
        if user.discapacidad in ['sordo', 'mudo']:
            return '/reconocimientos/camara/'
        return '/traduccion/'

    def get_signup_redirect_url(self, request):
        return '/seleccionar-discapacidad/'