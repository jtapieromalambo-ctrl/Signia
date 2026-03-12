from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .forms import RegistroForm


# ── LOGIN ──────────────────────────────────────────────
def home(request):
    """Vista principal: muestra el formulario de login."""
    if request.user.is_authenticated:
        return redirigir_por_discapacidad(request.user)

    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)
            return redirigir_por_discapacidad(user)
        else:
            messages.error(request, 'Usuario o contraseña incorrectos.')

    return render(request, 'usuarios/home.html')


# ── REGISTRO ───────────────────────────────────────────
def registro(request):
    """Registro de nuevo usuario con campo discapacidad."""
    if request.user.is_authenticated:
        return redirigir_por_discapacidad(request.user)

    if request.method == 'POST':
        form = RegistroForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirigir_por_discapacidad(user)
    else:
        form = RegistroForm()

    return render(request, 'usuarios/registro.html', {'form': form})


# ── LOGOUT ─────────────────────────────────────────────
def logout_view(request):
    logout(request)
    return redirect('home')


# ── REDIRECCIÓN POR DISCAPACIDAD ───────────────────────
def redirigir_por_discapacidad(user):
    """Redirige al módulo correcto según la discapacidad del usuario."""
    if user.discapacidad == 'sordo':
        return redirect('traduccion')   # texto → avatar señas
    elif user.discapacidad == 'mudo':
        return redirect('reconocimiento')  # cámara → texto
    else:
        return redirect('perfil')  # usuario sin discapacidad


# ── PERFIL ─────────────────────────────────────────────
@login_required
def perfil(request):
    return render(request, 'usuarios/perfil.html', {'usuario': request.user})