"""Controle de acesso e páginas de erro."""
from functools import wraps

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import render


def requer_gestor(view):
    """Exige login e perfil de gestor (is_staff). Sem perfil → 403 'acesso não autorizado'."""
    @wraps(view)
    @login_required
    def _v(request, *args, **kwargs):
        if not request.user.is_staff:
            raise PermissionDenied
        return view(request, *args, **kwargs)
    return _v


def erro_404(request, exception=None):
    return render(request, "erros/404.html", status=404)


def erro_403(request, exception=None):
    return render(request, "erros/403.html", status=403)
