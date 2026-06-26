from django.contrib import admin
from django.urls import path, include, re_path
from django.contrib.auth import views as auth_views
from django.conf import settings
from django.conf.urls.static import static
from django.views.static import serve
from django.http import JsonResponse
import os


def health(request):
    return JsonResponse({'status': 'ok'})


urlpatterns = [
    path('health/', health, name='health'),
    path('admin/', admin.site.urls),
    path('', include('usuarios.urls')),
    path('', include('traduccion.urls')),
    path('', include('historial.urls')),
    path('accounts/', include('allauth.urls')),
    path('reconocimientos/', include('reconocimientos.urls')),

    path('favicon.ico', serve, {
        'path': 'favicon.ico',
        'document_root': os.path.join(settings.BASE_DIR, 'static'),
    }),

    path('googleca96cff507878622.html', serve, {
        'path': 'googleca96cff507878622.html',
        'document_root': os.path.join(settings.BASE_DIR, 'static'),
    }),

    path('password-reset/',
         auth_views.PasswordResetView.as_view(template_name='registration/password_reset.html'),
         name='password_reset'),
    path('password-reset/done/',
         auth_views.PasswordResetDoneView.as_view(template_name='registration/password_reset_done.html'),
         name='password_reset_done'),
    path('password-reset/confirm/<uidb64>/<token>/',
         auth_views.PasswordResetConfirmView.as_view(template_name='registration/password_reset_confirm.html'),
         name='password_reset_confirm'),
    path('password-reset/complete/',
         auth_views.PasswordResetCompleteView.as_view(template_name='registration/password_reset_complete.html'),
         name='password_reset_complete'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
else:
    urlpatterns += [
        re_path(r'^media/(?P<path>.*)$', serve, {'document_root': settings.MEDIA_ROOT}),
    ]