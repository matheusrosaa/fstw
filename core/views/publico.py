"""Visualização pública do ensalamento (sem login): por curso, turma ou professor."""
from datetime import timedelta

from django.conf import settings
from django.shortcuts import get_object_or_404, render
from django.utils import timezone

from .. import models
from ..utils import DIAS_LONGOS, HORARIOS, nome_semana, segunda_da_semana


def _semana(hoje):
    segunda = segunda_da_semana(hoje)
    datas = [segunda + timedelta(days=i) for i in range(5)]
    cal = {c.data: c for c in models.DataCalendario.objects.filter(data__in=datas)}
    return segunda, datas, cal


def _publicados(segunda, **filtros):
    return (models.Ensalamento.objects.filter(data_inicio=segunda, status=models.Ensalamento.Status.PUBLICADO,
                                              ativo=True, grade__ativo=True, **filtros)
            .select_related("grade__curso", "grade__semestre"))


def _montar(request, titulo, subtitulo, caminho, ensalamentos, filtro_aula, mostrar_eventos=False, modo="curso"):
    hoje = timezone.localdate()
    segunda, datas, cal = _semana(hoje)
    ens_ids = [e.id for e in ensalamentos]
    aloc = {(a.ensalamento_id, a.aula_id): a.sala
            for a in models.Alocacao.objects.filter(ensalamento_id__in=ens_ids).select_related("sala")}
    entradas = {}
    for e in ensalamentos:
        for aula in filtro_aula(e.grade.aulas.select_related("turma", "unidade", "professor")):
            entradas.setdefault((aula.dia_semana, aula.horario), []).append(
                {"aula": aula, "sala": aloc.get((e.id, aula.id)), "curso": e.grade.curso})
    for lista in entradas.values():
        lista.sort(key=lambda x: (x["aula"].turma.ordem, x["aula"].turma.nome))
    dias = []
    for i, d in enumerate(datas):
        c = cal.get(d)
        feriado = c if c and c.feriado else None
        dias.append({
            "data": d, "nome": DIAS_LONGOS[i], "curto": DIAS_LONGOS[i].split("-")[0], "hoje": d == hoje,
            "feriado": feriado, "evento": c if (c and not c.feriado and mostrar_eventos) else None,
            "horarios": [{"texto": t, "entradas": [] if feriado else entradas.get((i, h), [])} for h, t in HORARIOS],
        })
    hoje_info = next((d for d in dias if d["hoje"]), None)
    turmas = []
    if modo == "curso":
        vistos = {}
        for lista in entradas.values():
            for x in lista:
                vistos[x["aula"].turma.id] = x["aula"].turma
        turmas = sorted(vistos.values(), key=lambda t: (t.ordem, t.nome))
        for d in dias:  # alinha as células às colunas de turmas
            for h in d["horarios"]:
                por_turma = {x["aula"].turma.id: x for x in h["entradas"]}
                h["colunas"] = [por_turma.get(t.id) for t in turmas]
    linhas_semana = [{"texto": t, "dias": [{"dia": d, "entradas": d["horarios"][i]["entradas"]} for d in dias]}
                     for i, (_, t) in enumerate(HORARIOS)]
    aba = "semana" if request.GET.get("aba") == "semana" else "hoje"
    ctx = {
        "titulo": titulo, "subtitulo": subtitulo, "caminho": caminho, "aba": aba, "modo": modo,
        "dias": dias, "linhas_semana": linhas_semana, "hoje": hoje, "hoje_info": hoje_info, "turmas": turmas,
        "semana": nome_semana(segunda), "segunda": segunda, "sabado": segunda + timedelta(days=5),
        "publicado": bool(ensalamentos), "nome_hoje": DIAS_LONGOS[hoje.weekday()],
        "atualizado": max((e.atualizado_em for e in ensalamentos), default=None),
        "link": f"{settings.SITE_PUBLICO}{caminho}",
    }
    return render(request, "publico/pagina.html", ctx)


def por_curso(request, slug):
    curso = get_object_or_404(models.Curso, slug=slug, ativo=True)
    ens = list(_publicados(segunda_da_semana(timezone.localdate()), grade__curso=curso))
    return _montar(request, curso.nome, "Ensalamento do curso", f"/p/{curso.slug}", ens,
                   lambda qs: qs.filter(turma__ativo=True), modo="curso")


def por_turma(request, slug):
    turma = get_object_or_404(models.Turma.objects.prefetch_related("cursos"), slug=slug, ativo=True)
    ens = list(_publicados(segunda_da_semana(timezone.localdate()), grade__aulas__turma=turma).distinct())
    cursos = " / ".join(c.nome for c in turma.cursos.all())
    return _montar(request, f"{turma.nome} · {turma.slug}", f"{cursos} · {turma.quantidade_alunos} alunos",
                   f"/p/t/{turma.slug}", ens, lambda qs: qs.filter(turma=turma), modo="turma")


def por_professor(request, slug):
    prof = get_object_or_404(models.Professor, slug=slug, ativo=True)
    ens = list(_publicados(segunda_da_semana(timezone.localdate()), grade__aulas__professor=prof).distinct())
    return _montar(request, f"Prof. {prof.nome}", "Ensalamento do professor · todas as turmas",
                   f"/p/p/{prof.slug}", ens, lambda qs: qs.filter(professor=prof), mostrar_eventos=True, modo="professor")
