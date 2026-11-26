"""Ensalamento: grade com salas, validações, cópia para outra semana e preview."""
from django.contrib import messages
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .. import forms, models, services
from ..utils import DIAS_LONGOS, proxima_segunda
from .base import requer_gestor
from .grade import montar_grade


def _carregar(pk):
    return get_object_or_404(models.Ensalamento.objects.select_related("grade__curso", "grade__semestre"), pk=pk)


def _linhas(ens):
    aloc = {a.aula_id: a for a in ens.alocacoes.select_related("sala", "aula__turma")}

    def celula(aula, turma, d, h):
        a = aloc.get(aula.id) if aula else None
        return {"aula": aula, "turma": turma, "alocacao": a, "nao_comporta": bool(a and a.nao_comporta)}

    return montar_grade(ens.grade, celula)


@requer_gestor
def ensalamento_detalhe(request, pk):
    ens = _carregar(pk)
    turmas, linhas = _linhas(ens)
    total = ens.grade.aulas.count()
    informadas = ens.alocacoes.count()
    ctx = {
        "ens": ens, "turmas": turmas, "linhas": linhas, "total": total, "informadas": informadas,
        "percentual": round(100 * informadas / total) if total else 0,
        "destino_padrao": proxima_segunda(ens.data_inicio),
    }
    return render(request, "core/ensalamento_detalhe.html", ctx)


@requer_gestor
def salas_da_aula(request, pk, aula_pk):
    """JSON com a situação de cada sala para a aula (usado pela janela 'Informar sala')."""
    ens = _carregar(pk)
    aula = get_object_or_404(models.Aula.objects.select_related("turma", "unidade", "professor"), pk=aula_pk, grade=ens.grade)
    atual = ens.alocacoes.filter(aula=aula).values_list("sala_id", flat=True).first()
    return JsonResponse({
        "aula": {"turma": aula.turma.nome, "alunos": aula.turma.quantidade_alunos,
                 "disciplina": f"{aula.unidade.codigo} – {aula.unidade.nome}", "professor": aula.professor.nome,
                 "quando": f"{DIAS_LONGOS[aula.dia_semana]}, {aula.horario_texto}"},
        "atual": atual,
        "salas": [{"id": s["sala"].id, "nome": s["sala"].nome, "tipo": s["sala"].get_tipo_display(),
                   "capacidade": s["sala"].capacidade, "estado": s["estado"], "texto": s["texto"]}
                  for s in services.situacao_salas(ens, aula)],
    })


@requer_gestor
@require_POST
def informar_sala(request, pk, aula_pk):
    ens = _carregar(pk)
    aula = get_object_or_404(models.Aula.objects.select_related("turma", "unidade"), pk=aula_pk, grade=ens.grade)
    form = forms.AlocacaoForm(request.POST)
    if not form.is_valid():
        messages.error(request, "Selecione uma sala válida.")
        return redirect("ensalamento_detalhe", pk=pk)
    sala = form.cleaned_data["sala"]
    atual = ens.alocacoes.filter(aula=aula).first()
    if sala is None:
        if atual:
            atual.delete()
            messages.success(request, f"Sala removida da aula {aula.unidade.codigo} ({aula.turma}).")
        return redirect("ensalamento_detalhe", pk=pk)
    choque = models.choque_de_sala(sala, ens, aula, ignorar_pk=atual.pk if atual else None)
    if choque:
        messages.error(request, f"{sala} já está ocupada neste horário por {choque.aula.turma} ({choque.aula.unidade.codigo}). "
                                f"Escolha outra sala para evitar choque.")
        return redirect("ensalamento_detalhe", pk=pk)
    if atual:
        atual.sala = sala
        atual.save(update_fields=["sala"])
    else:
        models.Alocacao.objects.create(ensalamento=ens, aula=aula, sala=sala)
    ens.save(update_fields=["atualizado_em"])
    msg = f"Sala {sala} informada para {aula.unidade.codigo} ({aula.turma}, {DIAS_LONGOS[aula.dia_semana].lower()} {aula.horario_texto})."
    if aula.turma.quantidade_alunos > sala.capacidade:
        messages.warning(request, msg + f" Atenção: {aula.turma.quantidade_alunos} alunos para {sala.capacidade} lugares.")
    else:
        messages.success(request, msg)
    return redirect("ensalamento_detalhe", pk=pk)


@requer_gestor
def copiar_previa(request, pk):
    ens = _carregar(pk)
    form = forms.CopiarForm({"data_destino": request.GET.get("data")}, ensalamento=ens)
    if not form.is_valid():
        return JsonResponse({"ok": False, "erro": form.errors["data_destino"][0]})
    sim = services.simular_copia(ens, form.cleaned_data["data_destino"])
    return JsonResponse({
        "ok": True, "nome": sim["nome"], "copiadas": len(sim["copiadas"]), "sem_sala": sim["sem_sala"],
        "choques": [f"{DIAS_LONGOS[a.aula.dia_semana]} {a.aula.horario_texto[:5]} · {a.aula.turma} ({motivo})"
                    for a, motivo in sim["choques"]],
    })


@requer_gestor
@require_POST
def copiar(request, pk):
    ens = _carregar(pk)
    form = forms.CopiarForm(request.POST, ensalamento=ens)
    if not form.is_valid():
        messages.error(request, form.errors["data_destino"][0])
        return redirect("ensalamento_detalhe", pk=pk)
    novo, sim = services.copiar_ensalamento(ens, form.cleaned_data["data_destino"])
    texto = f"Ensalamento {novo.nome} criado em rascunho com {len(sim['copiadas'])} aulas com sala."
    if sim["choques"]:
        messages.warning(request, texto + f" {len(sim['choques'])} aulas ficaram sem sala por choque de horário.")
    else:
        messages.success(request, texto)
    return redirect("ensalamento_detalhe", pk=novo.pk)


@requer_gestor
def preview(request, pk):
    ens = _carregar(pk)
    turmas, linhas = _linhas(ens)
    return render(request, "core/ensalamento_preview.html", {"ens": ens, "turmas": turmas, "linhas": linhas})
