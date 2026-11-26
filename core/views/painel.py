"""Login e dashboard."""
from datetime import timedelta

from django.contrib.auth import views as auth_views
from django.shortcuts import render
from django.utils import timezone

from .. import models
from ..utils import DIAS, HORARIOS, nome_semana, segunda_da_semana
from .base import requer_gestor


class Login(auth_views.LoginView):
    template_name = "registration/login.html"
    redirect_authenticated_user = True


def semestre_atual(hoje):
    s = models.Semestre.objects.ativos().filter(data_inicio__lte=hoje, data_fim__gte=hoje).first()
    return s or models.Semestre.objects.ativos().first()


@requer_gestor
def dashboard(request):
    hoje = timezone.localdate()
    segunda = segunda_da_semana(hoje)
    semestre = semestre_atual(hoje)
    labs = list(models.Sala.objects.ativos().filter(tipo=models.Sala.Tipo.LABORATORIO))
    ocupados = {(a.aula.dia_semana, a.aula.horario, a.sala_id) for a in models.alocacoes_da_semana(segunda)}
    series = []
    for h, texto in HORARIOS:
        livres = [sum(1 for lab in labs if (d, h, lab.id) not in ocupados) for d, _ in DIAS]
        series.append({"rotulo": texto, "valores": livres})
    por_tipo = [{"rotulo": t.label, "valor": models.Sala.objects.ativos().filter(tipo=t.value).count()} for t in models.Sala.Tipo]
    proximas = models.DataCalendario.objects.filter(data__gte=hoje, data__lte=hoje + timedelta(days=60))[:6]
    ctx = {
        "semestre": semestre, "semana": nome_semana(segunda), "segunda": segunda,
        "dias": [d.split("-")[0] for _, d in DIAS], "series": series, "total_labs": len(labs),
        "por_tipo": por_tipo, "proximas": proximas, "hoje": hoje,
    }
    return render(request, "core/dashboard.html", ctx)
