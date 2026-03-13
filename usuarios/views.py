from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .forms import RegistroForm


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
            login(request, user)
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
            login(request, user)
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


# ── CONTACTO ───────────────────────────────────────────
def contacto(request):
    if request.method == 'POST':
        nombre = request.POST.get('nombre')
        email = request.POST.get('email')
        asunto = request.POST.get('asunto')
        mensaje = request.POST.get('mensaje')
        print(nombre, email, asunto, mensaje)
    return render(request, 'usuarios/contacto.html')


# ── TRADUCTOR ──────────────────────────────────────────
@login_required
def traduccion(request):
    return render(request, 'usuarios/traduccion.html', {'usuario': request.user})


# ── RECONOCIMIENTO ─────────────────────────────────────
@login_required
def reconocimiento(request):
    return render(request, 'usuarios/reconocimiento.html', {'usuario': request.user})