from django.shortcuts import render
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
