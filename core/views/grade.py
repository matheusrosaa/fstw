"""Grade horária: visualização em grade e cadastro das aulas."""
from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .. import forms, models
from ..utils import DIAS, HORARIOS
from .base import requer_gestor


def montar_grade(grade, celula):
    """Linhas dia×horário com uma célula por turma. `celula(aula|None, turma, dia, horario)`."""
    turmas = list(grade.turmas())
    aulas = {(a.dia_semana, a.horario, a.turma_id): a
             for a in grade.aulas.select_related("turma", "unidade", "professor")}
    linhas = []
    for d, dnome in DIAS:
        for i, (h, hnome) in enumerate(HORARIOS):
            linhas.append({
                "dia": d, "dia_nome": dnome.split("-")[0], "primeira": i == 0, "horario": h, "horario_nome": hnome,
                "celulas": [celula(aulas.get((d, h, t.id)), t, d, h) for t in turmas],
            })
    return turmas, linhas


@requer_gestor
def grade_detalhe(request, pk, form=None, aula_editando=None):
    grade = get_object_or_404(models.GradeHoraria.objects.select_related("curso", "semestre"), pk=pk)
    turmas, linhas = montar_grade(grade, lambda a, t, d, h: {"aula": a, "turma": t, "dia": d, "horario": h})
    if form is None and request.GET.get("nova"):
        form = forms.AulaForm(grade=grade, initial={
            "turma": request.GET.get("turma"), "dia_semana": request.GET.get("dia"), "horario": request.GET.get("horario")})
    ctx = {"grade": grade, "turmas": turmas, "linhas": linhas, "form": form, "aula_editando": aula_editando,
           "total_aulas": grade.aulas.count()}
    return render(request, "core/grade_detalhe.html", ctx, status=400 if form is not None and form.is_bound else 200)


@requer_gestor
def aula_editar(request, pk, aula_pk=None):
    grade = get_object_or_404(models.GradeHoraria, pk=pk)
    aula = get_object_or_404(models.Aula, pk=aula_pk, grade=grade) if aula_pk else None
    if request.method != "POST":
        form = forms.AulaForm(instance=aula, grade=grade)
        return grade_detalhe.__wrapped__(request, pk, form=form, aula_editando=aula)
    form = forms.AulaForm(request.POST, instance=aula, grade=grade)
    if form.is_valid():
        a = form.save()
        messages.success(request, f"Aula {a.unidade.codigo} {'atualizada' if aula else 'adicionada'} na grade.")
        return redirect("grade_detalhe", pk=grade.pk)
    return grade_detalhe.__wrapped__(request, pk, form=form, aula_editando=aula)


@requer_gestor
@require_POST
def aula_excluir(request, pk, aula_pk):
    aula = get_object_or_404(models.Aula, pk=aula_pk, grade_id=pk)
    desc = f"{aula.unidade.codigo} ({aula.turma}, {aula.get_dia_semana_display()} {aula.horario_texto})"
    aula.delete()
    messages.success(request, f"Aula {desc} excluída da grade.")
    return redirect("grade_detalhe", pk=pk)
