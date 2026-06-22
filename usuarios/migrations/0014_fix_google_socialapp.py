from django.db import migrations
from django.conf import settings


def fix_google_socialapp(apps, schema_editor):
    """
    Elimina registros duplicados de Google en SocialApp y garantiza
    que quede exactamente uno con las credenciales correctas.
    """
    try:
        SocialApp = apps.get_model('socialaccount', 'SocialApp')
        Site = apps.get_model('sites', 'Site')
    except LookupError:
        return

    client_id = getattr(settings, '_GOOGLE_CLIENT_ID', '') or ''
    secret = getattr(settings, '_GOOGLE_CLIENT_SECRET', '') or ''

    # Intentar leer desde variables de entorno directamente
    import os
    client_id = os.environ.get('GOOGLE_CLIENT_ID', client_id)
    secret = os.environ.get('GOOGLE_CLIENT_SECRET', secret)

    google_apps = list(SocialApp.objects.filter(provider='google').order_by('id'))

    if len(google_apps) > 1:
        # Conservar solo el primero, borrar el resto
        keeper = google_apps[0]
        for app in google_apps[1:]:
            app.delete()
        # Actualizar credenciales si están disponibles
        if client_id:
            keeper.client_id = client_id
        if secret:
            keeper.secret = secret
        keeper.save()
    elif len(google_apps) == 1:
        app = google_apps[0]
        if client_id:
            app.client_id = client_id
        if secret:
            app.secret = secret
        app.save()
    else:
        # No existe ninguno — crear uno nuevo si hay credenciales
        if client_id and secret:
            site_id = getattr(settings, 'SITE_ID', 1)
            app = SocialApp.objects.create(
                provider='google',
                name='Google',
                client_id=client_id,
                secret=secret,
            )
            try:
                site = Site.objects.get(id=site_id)
                app.sites.add(site)
            except Site.DoesNotExist:
                pass


class Migration(migrations.Migration):

    dependencies = [
        ('usuarios', '0013_usuario_discapacidad_seleccionada'),
        ('socialaccount', '0001_initial'),
        ('sites', '0002_alter_domain_unique'),
    ]

    operations = [
        migrations.RunPython(fix_google_socialapp, migrations.RunPython.noop),
    ]
