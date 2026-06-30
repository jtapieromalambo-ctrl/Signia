from django.core.management.base import BaseCommand
from django.conf import settings


class Command(BaseCommand):
    help = 'Configura Site y SocialApp de Google desde variables de entorno'

    def handle(self, *args, **options):
        from django.contrib.sites.models import Site
        from allauth.socialaccount.models import SocialApp

        domain = getattr(settings, 'SITE_DOMAIN', 'www.signia.click')
        site, _ = Site.objects.update_or_create(
            id=settings.SITE_ID,
            defaults={'domain': domain, 'name': 'Signia'},
        )
        self.stdout.write(f'Site: {site.domain}')

        client_id = getattr(settings, 'SOCIALACCOUNT_PROVIDERS', {}).get('google', {}).get('APP', {}).get('client_id', '')
        secret = getattr(settings, 'SOCIALACCOUNT_PROVIDERS', {}).get('google', {}).get('APP', {}).get('secret', '')

        if not client_id or not secret:
            self.stderr.write('GOOGLE_CLIENT_ID o GOOGLE_CLIENT_SECRET no configurados')
            return

        app, created = SocialApp.objects.update_or_create(
            provider='google',
            defaults={
                'name': 'Google',
                'client_id': client_id,
                'secret': secret,
            },
        )
        app.sites.add(site)
        action = 'Creado' if created else 'Actualizado'
        self.stdout.write(f'{action} SocialApp Google: {app.client_id[:20]}...')
        self.stdout.write(self.style.SUCCESS('OAuth configurado correctamente'))
