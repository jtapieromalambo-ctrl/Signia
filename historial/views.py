from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from .models import EntradaHistorial


@login_required
def historial(request):
    tipo_filtro = request.GET.get('tipo', '')
    entradas = EntradaHistorial.objects.filter(usuario=request.user)
    if tipo_filtro in ['traduccion', 'reconocimiento']:
        entradas = entradas.filter(tipo=tipo_filtro)
    paginator = Paginator(entradas, 15)
    page = request.GET.get('page')
    entradas = paginator.get_page(page)
    return render(request, 'historial/historial.html', {
        'entradas': entradas,
        'tipo_filtro': tipo_filtro,
    })


@login_required
def eliminar_entrada(request, entrada_id):
    # Solo permite eliminar entradas del usuario actual
    entrada = get_object_or_404(EntradaHistorial, id=entrada_id, usuario=request.user)
    if request.method == 'POST':
        entrada.delete()
    return redirect('historial')