from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.contrib.auth import get_user_model
from django.views.decorators.http import require_http_methods
from .models import EntradaHistorial   # <-- se importa, no se define aquí

User = get_user_model()


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
    entrada = get_object_or_404(EntradaHistorial, id=entrada_id, usuario=request.user)
    if request.method == 'POST':
        entrada.delete()
    return redirect('historial')


@login_required
def clear_all_history(request, user_id=None):
    if request.method != 'POST':
        return JsonResponse({"error": "Método no permitido"}, status=405)

    if user_id:
        if not request.user.is_staff:
            return JsonResponse({"error": "No autorizado"}, status=403)
        target_user = get_object_or_404(User, id=user_id)
        deleted_count, _ = EntradaHistorial.objects.filter(usuario=target_user).delete()
        return JsonResponse({
            "message": f"Historial de {target_user.username} eliminado",
            "deleted": deleted_count,
        })

    deleted_count, _ = EntradaHistorial.objects.filter(usuario=request.user).delete()
    return JsonResponse({
        "message": "Historial eliminado correctamente",
        "deleted": deleted_count,
    })