from django.shortcuts import render
from django.contrib.auth.decorators import login_required


def traductor(request):
    return render(request, 'traduccion/traductor.html')