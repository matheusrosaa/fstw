"""Regras do ensalamento: situação das salas e cópia entre semanas."""
from django.db import transaction

from .models import Alocacao, Ensalamento, Sala, alocacoes_da_semana
from .utils import nome_semana


def situacao_salas(ensalamento, aula):
    """Lista de dicts com a situação de cada sala ativa para a aula:
    'livre', 'nao_comporta' (livre, mas pequena) ou 'ocupada'."""
    ocupadas = {
        a.sala_id: a
        for a in alocacoes_da_semana(ensalamento.data_inicio, aula.dia_semana, aula.horario)
        if not (a.ensalamento_id == ensalamento.id and a.aula_id == aula.id)
    }
    alunos = aula.turma.quantidade_alunos
    lista = []
    for sala in Sala.objects.ativos():
        oc = ocupadas.get(sala.id)
        if oc:
            estado = "ocupada"
            texto = f"{oc.aula.turma} · {oc.aula.unidade.codigo}"
            if oc.ensalamento.grade_id != ensalamento.grade_id:
                texto += f" ({oc.ensalamento.grade})"
        elif alunos > sala.capacidade:
            estado, texto = "nao_comporta", "Livre · não comporta"
        else:
            estado, texto = "livre", "Livre"
        lista.append({"sala": sala, "estado": estado, "texto": texto})
    return lista


def simular_copia(origem, segunda):
    """Calcula o que acontece ao copiar `origem` para a semana de `segunda`."""
    ocupadas = {(a.aula.dia_semana, a.aula.horario, a.sala_id): a for a in alocacoes_da_semana(segunda)}
    copiadas, choques = [], []
    for aloc in origem.alocacoes.select_related("aula__turma", "aula__unidade", "sala"):
        chave = (aloc.aula.dia_semana, aloc.aula.horario, aloc.sala_id)
        if not aloc.sala.ativo:
            choques.append((aloc, "sala desativada"))
        elif chave in ocupadas:
            oc = ocupadas[chave]
            choques.append((aloc, f"{aloc.sala} ocupada em {oc.ensalamento.grade}"))
        else:
            copiadas.append(aloc)
    total = origem.grade.aulas.count()
    return {
        "nome": nome_semana(segunda),
        "copiadas": copiadas,
        "choques": choques,
        "sem_sala": total - len(copiadas) - len(choques),
    }


@transaction.atomic
def copiar_ensalamento(origem, segunda):
    sim = simular_copia(origem, segunda)
    novo = Ensalamento.objects.create(grade=origem.grade, nome=sim["nome"], data_inicio=segunda,
                                      status=Ensalamento.Status.RASCUNHO, ativo=True)
    Alocacao.objects.bulk_create([Alocacao(ensalamento=novo, aula=a.aula, sala=a.sala) for a in sim["copiadas"]])
    return novo, sim
