"""Calendário acadêmico: calendário anual + tabela."""
import calendar
from django.conf import settings
from django.utils import timezone

from .. import models
from .base import requer_gestor
from .crud import CALENDARIO, lista

MESES = ["Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho", "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"]


@requer_gestor
def calendario_lista(request):
    hoje = timezone.localdate()
    try:
        ano = int(request.GET.get("ano", hoje.year))
    except ValueError:
        ano = hoje.year
    datas = {d.data: d for d in models.DataCalendario.objects.filter(data__year=ano)}
    cal = calendar.Calendar(firstweekday=6)  # semana começando no domingo
    meses = []
    for m in range(1, 13):
        semanas = []
        for semana in cal.monthdatescalendar(ano, m):
            dias = []
            for d in semana:
                item = datas.get(d) if d.month == m else None
                tipo = ""
                if item:
                    tipo = "feriado" if item.feriado else ("reposicao" if item.reposicao else "evento")
                dias.append({"dia": d.day if d.month == m else "", "tipo": tipo, "item": item, "hoje": d == hoje})
            semanas.append(dias)
        meses.append({"nome": MESES[m - 1], "semanas": semanas})
    extra = {"ano": ano, "meses": meses, "ano_ant": ano - 1, "ano_prox": ano + 1,
             "calendario_url": settings.CALENDARIO_OFICIAL_URL}
    return lista(request, _cad_do_ano(ano), template="core/calendario.html", extra=extra)


def _cad_do_ano(ano):
    from dataclasses import replace
    cad = replace(CALENDARIO)
    base_qs = cad.queryset
    cad.queryset = lambda: base_qs().filter(data__year=ano)  # tabela só com o ano exibido
    return cad
