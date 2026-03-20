from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.conf import settings
from django.utils import timezone
from datetime import timedelta
from .forms import RegistroForm, EditarPerfilForm
from .models import Usuario, CodigoVerificacion
import httpx
import ssl


# ── ENVIAR EMAIL CON SENDGRID (sin verificación SSL) ───
def enviar_email_sendgrid(destinatario, asunto, contenido_html):
    try:
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE

        response = httpx.post(
            "https://api.sendgrid.com/v3/mail/send",
            headers={
                "Authorization": f"Bearer {settings.SENDGRID_API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "personalizations": [{"to": [{"email": destinatario}]}],
                "from": {"email": "osorioescobardavidfelipe@gmail.com", "name": "Signia"},
                "subject": asunto,
                "content": [{"type": "text/html", "value": contenido_html}]
            },
            verify=False
        )
        print(f"[EMAIL] Status: {response.status_code}")
        return response.status_code == 202
    except Exception as e:
        print(f"[EMAIL ERROR] {e}")
        return False


# ── INICIO ─────────────────────────────────────────────
def index(request):
    if request.user.is_authenticated:
        return redirigir_por_discapacidad(request.user)
    return render(request, 'usuarios/index.html')


# ── LOGIN ──────────────────────────────────────────────
def home(request):
    if request.user.is_authenticated:
        return redirigir_por_discapacidad(request.user)

    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user, backend='django.contrib.auth.backends.ModelBackend')
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

            enviar_email_sendgrid(
                user.email,
                '¡Bienvenido a Signia! 🤟',
                f"""
                <div style="font-family:Arial,sans-serif;max-width:520px;margin:0 auto;background:#f0f6ff;padding:2rem;border-radius:16px;">
                    <div style="background:linear-gradient(135deg,#2563EB,#3B82F6);padding:2rem;border-radius:12px;text-align:center;margin-bottom:1.5rem;">
                        <h1 style="color:white;font-size:1.8rem;margin:0;">🤟 ¡Bienvenido a Signia!</h1>
                    </div>
                    <p style="color:#1E293B;font-size:1rem;">Hola <strong>{user.username}</strong>,</p>
                    <p style="color:#64748B;">Tu cuenta ha sido creada exitosamente. Ya puedes acceder a todas las herramientas de traducción de lenguaje de señas.</p>
                    <p style="color:#64748B;margin-top:1.5rem;">— El equipo de Signia</p>
                </div>
                """
            )

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
    return render(request, 'usuarios/perfil.html', {'usuario': request.user})


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


# ── RECUPERAR CONTRASEÑA — PASO 1: Pedir correo ────────
def recuperar_password(request):
    if request.method == 'POST':
        email = request.POST.get('email', '').strip()

        try:
            user = Usuario.objects.get(email=email)
        except Usuario.DoesNotExist:
            request.session['recuperar_email'] = email
            return redirect('verificar_codigo')

        CodigoVerificacion.objects.filter(usuario=user, usado=False).delete()

        codigo = CodigoVerificacion.generar_codigo()
        CodigoVerificacion.objects.create(usuario=user, codigo=codigo)

        request.session['recuperar_email'] = email

        enviado = enviar_email_sendgrid(
            email,
            'Código de verificación — Signia 🔐',
            f"""
            <div style="font-family:Arial,sans-serif;max-width:520px;margin:0 auto;background:#f0f6ff;padding:2rem;border-radius:16px;">
                <div style="background:linear-gradient(135deg,#2563EB,#3B82F6);padding:2rem;border-radius:12px;text-align:center;margin-bottom:1.5rem;">
                    <h1 style="color:white;font-size:1.5rem;margin:0;">🔐 Código de Verificación</h1>
                    <p style="color:rgba(255,255,255,0.85);margin:0.5rem 0 0;">Signia — Sistema de Lenguaje de Señas</p>
                </div>
                <p style="color:#1E293B;font-size:1rem;">Hola <strong>{user.username}</strong>,</p>
                <p style="color:#64748B;">Recibimos una solicitud para restablecer tu contraseña. Usa el siguiente código:</p>
                <div style="background:white;border:2px solid #DBEAFE;border-radius:12px;padding:2rem;text-align:center;margin:1.5rem 0;">
                    <p style="color:#64748B;font-size:0.85rem;margin:0 0 0.5rem;">Tu código de verificación es:</p>
                    <span style="font-size:3rem;font-weight:900;color:#2563EB;letter-spacing:0.5rem;">{codigo}</span>
                    <p style="color:#94A3B8;font-size:0.8rem;margin:1rem 0 0;">Este código expira en <strong>15 minutos</strong></p>
                </div>
                <p style="color:#94A3B8;font-size:0.82rem;">Si no solicitaste este código, ignora este correo.</p>
                <p style="color:#64748B;margin-top:1.5rem;">— El equipo de Signia</p>
            </div>
            """
        )

        if enviado:
            print(f"[EMAIL] Código {codigo} enviado a {email}")
        else:
            print(f"[EMAIL] Falló el envío. Código: {codigo}")

        return redirect('verificar_codigo')

    return render(request, 'registration/password_reset.html')


# ── RECUPERAR CONTRASEÑA — PASO 2: Verificar código ───
def verificar_codigo(request):
    email = request.session.get('recuperar_email', '')

    if request.method == 'POST':
        codigo_ingresado = request.POST.get('codigo', '').strip()

        if not email:
            messages.error(request, 'Sesión expirada. Intenta de nuevo.')
            return redirect('recuperar_password')

        try:
            user = Usuario.objects.get(email=email)
        except Usuario.DoesNotExist:
            messages.error(request, 'Usuario no encontrado.')
            return redirect('recuperar_password')

        limite = timezone.now() - timedelta(minutes=15)
        try:
            codigo_obj = CodigoVerificacion.objects.get(
                usuario=user,
                codigo=codigo_ingresado,
                usado=False,
                creado__gte=limite
            )
            codigo_obj.usado = True
            codigo_obj.save()

            request.session['recuperar_verificado'] = True
            return redirect('nueva_password')

        except CodigoVerificacion.DoesNotExist:
            messages.error(request, 'Código incorrecto o expirado. Intenta de nuevo.')

    return render(request, 'registration/verificar_codigo.html', {'email': email})


# ── RECUPERAR CONTRASEÑA — PASO 3: Nueva contraseña ───
def nueva_password(request):
    if not request.session.get('recuperar_verificado'):
        return redirect('recuperar_password')

    email = request.session.get('recuperar_email', '')

    if request.method == 'POST':
        password1 = request.POST.get('password1', '')
        password2 = request.POST.get('password2', '')

        if password1 != password2:
            messages.error(request, 'Las contraseñas no coinciden.')
        elif len(password1) < 8:
            messages.error(request, 'La contraseña debe tener mínimo 8 caracteres.')
        else:
            try:
                user = Usuario.objects.get(email=email)
                user.set_password(password1)
                user.save()

                del request.session['recuperar_email']
                del request.session['recuperar_verificado']

                messages.success(request, 'Contraseña cambiada correctamente. Ya puedes iniciar sesión.')
                return redirect('home')
            except Usuario.DoesNotExist:
                messages.error(request, 'Error al cambiar la contraseña.')

    return render(request, 'registration/nueva_password.html')


# ── CONTACTO ───────────────────────────────────────────
def contacto(request):
    enviado = False
    if request.method == 'POST':
        nombre  = request.POST.get('nombre', '').strip()
        email   = request.POST.get('email', '').strip()
        asunto  = request.POST.get('asunto', '').strip()
        mensaje = request.POST.get('mensaje', '').strip()

        if nombre and email and asunto and mensaje:
            enviar_email_sendgrid(
                'osorioescobardavidfelipe@gmail.com',
                f'[Signia Contacto] {asunto}',
                f"""
                <div style="font-family:Arial,sans-serif;padding:1.5rem;">
                    <h2>Nuevo mensaje de contacto</h2>
                    <p><strong>Nombre:</strong> {nombre}</p>
                    <p><strong>Email:</strong> {email}</p>
                    <p><strong>Asunto:</strong> {asunto}</p>
                    <p><strong>Mensaje:</strong><br>{mensaje}</p>
                </div>
                """
            )
            enviado = True
        else:
            messages.error(request, 'Por favor completa todos los campos.')

    return render(request, 'usuarios/contacto.html', {'enviado': enviado})


# ── TRADUCTOR ──────────────────────────────────────────
def traduccion(request):
    return render(request, 'traduccion/traductor.html')


# ── RECONOCIMIENTO ─────────────────────────────────────
def reconocimiento(request):
    return render(request, 'usuarios/reconocimiento.html')