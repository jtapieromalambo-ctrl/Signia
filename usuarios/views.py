from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.core.mail import send_mail
from django.conf import settings
from .forms import RegistroForm, EditarPerfilForm
from .models import Usuario
from reconocimientos.models import VideoSeña


# ── FUNCIÓN PARA VALIDAR ADMIN ─────────────────────────
def es_admin(user):
    return user.is_authenticated and user.is_superuser


# ── PANEL ADMIN PERSONALIZADO ─────────────────────────
# ajusta si los nombres son diferentes

@user_passes_test(es_admin)
def panel_admin_videos(request):
    context = {
        'videos_reconocimiento': VideoSeña.objects.all().order_by('-creado'),
        'videos_traductor':      [],
        'total_reconocimiento':  VideoSeña.objects.count(),
        'total_traductor':       0,
    }
    return render(request, 'usuarios/admin_video.html', context)

# ── INICIO ─────────────────────────────────────────────
def index(request):
    if request.user.is_authenticated:
        if request.user.is_superuser:
            return redirect('panel_admin_videos')  # 🔥 CAMBIO
        return redirigir_por_discapacidad(request.user)
    return render(request, 'usuarios/index.html')


# ── LOGIN ──────────────────────────────────────────────
def home(request):
    if request.user.is_authenticated:
        if request.user.is_superuser:
            return redirect('panel_admin_videos')  # 🔥 CAMBIO
        return redirigir_por_discapacidad(request.user)

    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user, backend='django.contrib.auth.backends.ModelBackend')

            # 🔥 CAMBIO AQUÍ
            if user.is_superuser:
                return redirect('panel_admin_videos')

            request.session['show_disability_modal'] = True
            return redirigir_por_discapacidad(user)
        else:
            messages.error(request, 'Usuario o contraseña incorrectos.')

    return render(request, 'usuarios/home.html')


# ── REGISTRO ───────────────────────────────────────────
def registro(request):
    if request.user.is_authenticated:
        return redirigir_por_discapacidad(request.user)

    if request.method == 'POST':
        form = RegistroForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user, backend='django.contrib.auth.backends.ModelBackend')

            try:
                send_mail(
                    subject='¡Bienvenido a Signia! 🤟',
                    message=f'Hola {user.username},\n\n¡Gracias por registrarte en Signia!\n\n— El equipo de Signia',
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[user.email],
                    fail_silently=True,
                )
            except Exception:
                pass

            request.session['show_disability_modal'] = True
            return redirigir_por_discapacidad(user)
    else:
        form = RegistroForm()

    return render(request, 'usuarios/registro.html', {'form': form})


# ── LOGOUT ─────────────────────────────────────────────
def logout_view(request):
    logout(request)
    return redirect('index')


# ── REDIRECCIÓN POR DISCAPACIDAD ───────────────────────
def redirigir_por_discapacidad(user):
    if user.discapacidad == 'sordo':
        return redirect('traduccion')
    elif user.discapacidad == 'mudo':
        return redirect('reconocimiento')
    else:
        return redirect('perfil')


# ── PERFIL ─────────────────────────────────────────────
@login_required
def perfil(request):
    return render(request, 'usuarios/perfil.html', {
        'usuario': request.user,
    })


# ── EDITAR PERFIL ──────────────────────────────────────
@login_required
def editar_perfil(request):
    if request.method == 'POST':
        form = EditarPerfilForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Perfil actualizado correctamente.')
            return redirect('perfil')
    else:
        form = EditarPerfilForm(instance=request.user)

    return render(request, 'usuarios/editar_perfil.html', {
        'form': form,
        'usuario': request.user
    })


# ── CAMBIAR CONTRASEÑA ─────────────────────────────────
@login_required
def cambiar_password(request):
    if request.method == 'POST':
        password_actual = request.POST.get('password_actual')
        password_nueva  = request.POST.get('password_nueva')
        password_nueva2 = request.POST.get('password_nueva2')

        user = authenticate(request, username=request.user.username, password=password_actual)

        if user is None:
            messages.error(request, 'La contraseña actual es incorrecta.')
        elif password_nueva != password_nueva2:
            messages.error(request, 'Las contraseñas nuevas no coinciden.')
        elif len(password_nueva) < 8:
            messages.error(request, 'La nueva contraseña debe tener mínimo 8 caracteres.')
        else:
            user.set_password(password_nueva)
            user.save()
            update_session_auth_hash(request, user)
            messages.success(request, 'Contraseña cambiada correctamente.')
            return redirect('perfil')

    return render(request, 'usuarios/cambiar_password.html')


# ── ELIMINAR CUENTA ────────────────────────────────────
@login_required
def eliminar_cuenta(request):
    if request.method == 'POST':
        user = request.user
        logout(request)
        user.delete()
        return redirect('index')
    return redirect('perfil')


# ── CONTACTO ───────────────────────────────────────────
def contacto(request):
    enviado = False
    if request.method == 'POST':
        nombre  = request.POST.get('nombre', '').strip()
        email   = request.POST.get('email', '').strip()
        asunto  = request.POST.get('asunto', '').strip()
        mensaje = request.POST.get('mensaje', '').strip()

        if nombre and email and asunto and mensaje:
            print(f"[CONTACTO] De: {nombre} <{email}> | Asunto: {asunto}\n{mensaje}")
            enviado = True
        else:
            messages.error(request, 'Por favor completa todos los campos.')

    return render(request, 'usuarios/contacto.html', {'enviado': enviado})


# ── TRADUCTOR ──────────────────────────────────────────
def traduccion(request):
    return render(request, 'traduccion/traductor.html')


# ── RECONOCIMIENTO ─────────────────────────────────────
def reconocimiento(request):
    return redirect('/reconocimientos/camara/')