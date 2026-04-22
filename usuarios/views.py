from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.core.mail import send_mail, EmailMultiAlternatives
from django.conf import settings
from .forms import RegistroForm, EditarPerfilForm
from .models import Usuario
from reconocimientos.models import VideoSeña
from traduccion.models import video as VideoTraductor
import ssl

ssl._create_default_https_context = ssl._create_unverified_context
from django.utils import timezone
from .forms import ContactoForm
from .models import MensajeContacto
from django.shortcuts import render, redirect, get_object_or_404
#para verificacion del correo
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from .models import CodigoOTP
from functools import wraps

# ── FUNCIÓN PARA VALIDAR ADMIN ─────────────────────────
def es_admin(user):
    return user.is_authenticated and user.is_superuser


# ── PANEL ADMIN PERSONALIZADO ─────────────────────────
# ajusta si los nombres son diferentes

@user_passes_test(es_admin)
def panel_admin_videos(request):
    context = {
        'videos_reconocimiento': VideoSeña.objects.all().order_by('-creado'),
        'videos_traductor':      VideoTraductor.objects.all().order_by('-id'),
        'total_reconocimiento':  VideoSeña.objects.count(),
        'total_traductor':       VideoTraductor.objects.count(),
        'mensajes_contacto':     MensajeContacto.objects.all().order_by('-fecha'),
        'total_mensajes':        MensajeContacto.objects.count(),

    }
    return render(request, 'usuarios/admin_video.html', context)

# ── INICIO ─────────────────────────────────────────────
def index(request):
    if request.user.is_authenticated:
        if request.user.is_superuser:
            return redirect('panel_admin_videos') 
        return redirigir_por_discapacidad(request.user)
    return render(request, 'usuarios/index.html')


# ── LOGIN ──────────────────────────────────────────────
def home(request):
    if request.user.is_authenticated:
        if request.user.is_superuser:
            return redirect('panel_admin_videos')  
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
            user = form.save(commit=False)  # ← cambiamos esto para no guardar aún
            user.email_verificado = False
            user.save()

            # Enviamos el OTP antes de hacer login
            enviar_otp(user)
            request.session['email_verificacion'] = user.email
            request.session['show_disability_modal'] = True  # lo conservamos para después

            messages.success(request, 'Cuenta creada. Verifica tu correo para continuar.')
            return redirect('verificar_otp')  # ← primero verificar

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
        user.delete()  # borra de la base de datos
        return redirect('index')
    return redirect('perfil')


# ── CONTACTO ───────────────────────────────────────────
def contacto(request):
    form = ContactoForm()
    observacion_enviada = False
    if request.method == 'POST':
        form = ContactoForm(request.POST)
        if form.is_valid():
            form.save()
            if form.cleaned_data.get('observacion'):
                observacion_enviada = True

                # Enviar correo al administrador
                nombre = form.cleaned_data.get('nombre')
                correo = form.cleaned_data.get('correo')
                observacion = form.cleaned_data.get('observacion')
                mensaje = form.cleaned_data.get('mensaje')

                try:
                    send_mail(
                        subject=f'Nueva queja/contacto de {nombre}',
                        message=f'Nombre: {nombre}\nCorreo: {correo}\n\nObservación:\n{observacion}\n\nMensaje:\n{mensaje}',
                        from_email=settings.DEFAULT_FROM_EMAIL,
                        recipient_list=['osorioescobardavidfelipe@gmail.com'],
                        fail_silently=True,
                    )
                except Exception:
                    pass

            else:
                return redirect('contacto')

    return render(request, 'usuarios/contacto.html', {
        'form': form,
        'observacion_enviada': observacion_enviada,
    })


# ── TRADUCTOR ──────────────────────────────────────────
@login_required
def traduccion(request):
    return render(request, 'traduccion/traductor.html')


# ── RECONOCIMIENTO ─────────────────────────────────────

def reconocimiento(request):
    return redirect('/reconocimientos/camara/')


# ── RECUPERAR CONTRASEÑA CON CÓDIGO ───────────────────

import random

def recuperar_password(request):
    if request.method == 'POST':
        email = request.POST.get('email', '').strip()

        try:
            usuario = Usuario.objects.get(email=email)
        except Usuario.DoesNotExist:
            messages.error(request, 'No existe una cuenta con ese correo.')
            return render(request, 'registration/recuperar.html')
        except Usuario.MultipleObjectsReturned:
            usuario = Usuario.objects.filter(email=email, is_active=True).first()
            if not usuario:
                messages.error(request, 'No existe una cuenta activa con ese correo.')
                return render(request, 'registration/recuperar.html')

        # ── Este bloque debe estar FUERA del try/except ──
        codigo = str(random.randint(100000, 999999))
        request.session['reset_codigo'] = codigo
        request.session['reset_email']  = email

        html_content = f"""<!DOCTYPE html>
<html>
<head><meta charset="UTF-8"></head>
<body style="margin:0;padding:0;background:#E8F3FC;font-family:Arial,sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background:#E8F3FC;padding:40px 0;">
    <tr><td align="center">
      <table width="480" cellpadding="0" cellspacing="0" style="background:white;border-radius:24px;overflow:hidden;box-shadow:0 10px 30px rgba(37,99,235,0.15);">
        <tr>
          <td style="background:linear-gradient(135deg,#2563EB,#3B82F6);padding:32px;text-align:center;">
            <h1 style="color:white;margin:0;font-size:24px;">🔑 Recuperar Contraseña</h1>
            <p style="color:#BFDBFE;margin:8px 0 0;">Signia - Comunicación sin barreras</p>
          </td>
        </tr>
        <tr>
          <td style="padding:32px;">
            <p style="color:#374151;font-size:16px;margin:0 0 24px;">Hola,</p>
            <p style="color:#374151;font-size:16px;margin:0 0 24px;">Recibimos una solicitud para restablecer tu contraseña. Usa el siguiente código:</p>
            <div style="background:#EFF6FF;border:2px dashed #2563EB;border-radius:16px;padding:24px;text-align:center;margin:0 0 24px;">
              <p style="color:#1E40AF;font-size:13px;margin:0 0 8px;letter-spacing:2px;text-transform:uppercase;">Tu código de verificación</p>
              <span style="color:#2563EB;font-size:42px;font-weight:bold;letter-spacing:12px;">{codigo}</span>
            </div>
            <p style="color:#6B7280;font-size:14px;margin:0 0 8px;">⏱ Este código es válido por <strong>10 minutos</strong>.</p>
            <p style="color:#6B7280;font-size:14px;margin:0;">Si no solicitaste este cambio, ignora este correo.</p>
          </td>
        </tr>
        <tr>
          <td style="background:#F0F7FF;padding:20px;text-align:center;">
            <p style="color:#93C5FD;font-size:12px;margin:0;">© 2026 Signia · Comunicación sin barreras 🤟</p>
          </td>
        </tr>
      </table>
    </td></tr>
  </table>
</body>
</html>"""

        email_msg = EmailMultiAlternatives(
            subject='Código para restablecer tu contraseña - Signia',
            body=f'Tu código de verificación es: {codigo}\n\nEste código es válido por 10 minutos.',
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[email],
        )
        email_msg.attach_alternative(html_content, "text/html")
        email_msg.send(fail_silently=False)

        messages.success(request, 'Código enviado a tu correo.')
        return redirect('verificar_codigo')

    return render(request, 'registration/recuperar.html')

       
 
        
def verificar_codigo(request):
    if request.method == 'POST':
        codigo_ingresado = request.POST.get('codigo', '').strip()
        codigo_guardado  = request.session.get('reset_codigo')

        if not codigo_guardado:
            messages.error(request, 'La sesión expiró. Vuelve a solicitar el código.')
            return redirect('recuperar_password')

        if codigo_ingresado == codigo_guardado:
            request.session['reset_verificado'] = True
            return redirect('nueva_password')
        else:
            messages.error(request, 'Código incorrecto. Inténtalo de nuevo.')

    return render(request, 'registration/verificar_codigo.html')


def nueva_password(request):
    if not request.session.get('reset_verificado'):
        messages.error(request, 'Debes verificar tu código primero.')
        return redirect('recuperar_password')

    if request.method == 'POST':
        password1 = request.POST.get('password1')
        password2 = request.POST.get('password2')

        if password1 != password2:
            messages.error(request, 'Las contraseñas no coinciden.')
        elif len(password1) < 8:
            messages.error(request, 'La contraseña debe tener mínimo 8 caracteres.')
        else:
            email   = request.session.get('reset_email')
            usuario = Usuario.objects.get(email=email)
            usuario.set_password(password1)
            usuario.save()

            del request.session['reset_codigo']
            del request.session['reset_email']
            del request.session['reset_verificado']

            messages.success(request, '¡Contraseña cambiada exitosamente! Ya puedes iniciar sesión.')
            return redirect('home')

    return render(request, 'registration/nueva_password.html')




from django.http import JsonResponse

@user_passes_test(es_admin)
def eliminar_mensaje_contacto(request, mensaje_id):
    from .models import MensajeContacto
    mensaje = get_object_or_404(MensajeContacto, id=mensaje_id)
    if request.method == 'POST':
        mensaje.delete()
        return JsonResponse({'ok': True})
    return JsonResponse({'ok': False, 'error': 'Método no permitido'}, status=405)

#verificacion del corrreo
def verificar_otp(request):
    email = request.session.get('email_verificacion')
    
    if not email:
        messages.error(request, 'Sesión expirada. Intenta de nuevo.')
        return redirect('solicitar_verificacion')
    
    if request.method == 'POST':
        codigo_ingresado = request.POST.get('codigo')
        
        try:
            usuario = Usuario.objects.get(email=email)
            otp = CodigoOTP.objects.filter(
                usuario=usuario,
                codigo=codigo_ingresado,
                usado=False
            ).last()
            
            if otp and otp.esta_vigente():
                otp.usado = True
                otp.save()
                usuario.email_verificado = True
                usuario.save()
                del request.session['email_verificacion']

                # Login después de verificar
                login(request, usuario, backend='django.contrib.auth.backends.ModelBackend')

                # Correo de bienvenida
                try:
                    send_mail(
                        subject='¡Bienvenido a Signia! 🤟',
                        message=f'Hola {usuario.username},\n\n¡Gracias por registrarte en Signia!\n\nEl equipo de Signia',
                        from_email=settings.DEFAULT_FROM_EMAIL,
                        recipient_list=[usuario.email],
                        fail_silently=True,
                    )
                except Exception:
                    pass

                messages.success(request, '¡Correo verificado correctamente!')
                return redirigir_por_discapacidad(usuario)
            
            else:
                messages.error(request, 'Código incorrecto o expirado.')
        
        except Usuario.DoesNotExist:
            messages.error(request, 'Usuario no encontrado.')
    
    return render(request, 'usuarios/verificar_otp.html')


def enviar_otp(usuario):
    otp = CodigoOTP.generar(usuario)
    
    asunto = 'Tu código de verificación - Signia'
    contexto = {
        'usuario': usuario,
        'codigo': otp.codigo,
    }
    
    cuerpo_texto = f'Tu código de verificación es: {otp.codigo}. Válido por 10 minutos.'
    cuerpo_html = render_to_string('usuarios/email_otp.html', contexto)
    
    correo = EmailMultiAlternatives(
        subject=asunto,
        body=cuerpo_texto,
        from_email=None,
        to=[usuario.email],
    )
    correo.attach_alternative(cuerpo_html, "text/html")
    correo.send()


# Vista 1: El usuario ingresa su correo y se le envía el OTP
def solicitar_verificacion(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        
        try:
            usuario = Usuario.objects.get(email=email)
            enviar_otp(usuario)
            request.session['email_verificacion'] = email  # guardamos el email en sesión
            messages.success(request, 'Código enviado a tu correo.')
            return redirect('verificar_otp')
        
        except Usuario.DoesNotExist:
            messages.error(request, 'No existe una cuenta con ese correo.')
    
    return render(request, 'usuarios/solicitar_verificacion.html')


# Vista 2: El usuario ingresa el código OTP
def verificar_otp(request):
    email = request.session.get('email_verificacion')
    
    if not email:
        messages.error(request, 'Sesión expirada. Intenta de nuevo.')
        return redirect('solicitar_verificacion')
    
    if request.method == 'POST':
        codigo_ingresado = request.POST.get('codigo')
        
        try:
            usuario = Usuario.objects.get(email=email)
            otp = CodigoOTP.objects.filter(
                usuario=usuario,
                codigo=codigo_ingresado,
                usado=False
            ).last()
            
            if otp and otp.esta_vigente():
                otp.usado = True
                otp.save()
                usuario.email_verificado = True  # lo activamos (lo agregamos en el siguiente paso)
                usuario.save()
                del request.session['email_verificacion']
                messages.success(request, '¡Correo verificado correctamente!')
                return redirect('home')  # cambia esto por tu vista principal
            else:
                messages.error(request, 'Código incorrecto o expirado.')
        
        except Usuario.DoesNotExist:
            messages.error(request, 'Usuario no encontrado.')
    
    return render(request, 'usuarios/verificar_otp.html')


def requiere_email_verificado(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('login')
        if not request.user.email_verificado:
            messages.warning(request, 'Debes verificar tu correo primero.')
            return redirect('solicitar_verificacion')
        return view_func(request, *args, **kwargs)
    return wrapper


# ── SELECCIONAR DISCAPACIDAD (post-Google OAuth) ───────
@login_required
def seleccionar_discapacidad(request):
    # Si ya tiene discapacidad definida, redirigir directo
    if request.user.discapacidad != 'ninguna':
        return redirigir_por_discapacidad(request.user)

    if request.method == 'POST':
        discapacidad = request.POST.get('discapacidad', 'ninguna')
        if discapacidad in ['ninguna', 'sordo', 'mudo']:
            request.user.discapacidad = discapacidad
            request.user.save()
            return redirigir_por_discapacidad(request.user)

    return render(request, 'usuarios/seleccionar_discapacidad.html')