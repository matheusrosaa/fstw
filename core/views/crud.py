"""CRUD genérico: listagem com busca/filtros/ordenação, adicionar, editar e desativar."""
from dataclasses import dataclass, field
from typing import Callable

from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import path, reverse
from django.views.decorators.http import require_POST

from .. import forms, models
from .base import requer_gestor


@dataclass
class Coluna:
    titulo: str
    valor: str | Callable  # atributo (aceita a__b) ou função(obj)
    ordem: str | None = None  # campo de ordenação
    tipo: str = "texto"  # texto | forte | ativo | status | data
    largura: str = ""


@dataclass
class Filtro:
    nome: str
    rotulo: str
    opcoes: Callable  # () -> [(valor, texto)]
    campo: str = ""  # lookup do ORM; padrão = nome


@dataclass
class Cadastro:
    chave: str  # usado nas URLs e nomes de rota
    model: type
    form_class: type
    singular: str
    plural: str
    artigo: str  # "a" ou "o"
    subtitulo: str
    icone: str
    busca: list = field(default_factory=lambda: ["nome"])
    filtros: list = field(default_factory=list)
    ordens: list = field(default_factory=list)  # [(campo, texto)]
    colunas: list = field(default_factory=list)
    regras: list = field(default_factory=list)
    acoes: list = field(default_factory=list)  # [(texto, nome_da_rota)] extras por linha
    desativavel: bool = True
    excluivel: bool = False
    descricao_obj: Callable = str
    select_related: tuple = ()
    prefetch: tuple = ()

    @property
    def rota(self):
        return f"{self.chave}_lista"

    def queryset(self):
        qs = self.model.objects.all()
        if self.select_related:
            qs = qs.select_related(*self.select_related)
        if self.prefetch:
            qs = qs.prefetch_related(*self.prefetch)
        return qs


def opcoes_ativo():
    return [("sim", "Ativos"), ("nao", "Inativos")]


def _valor(obj, col):
    if callable(col.valor):
        return col.valor(obj)
    v = obj
    for parte in col.valor.split("__"):
        v = getattr(v, parte)
        if callable(v):
            v = v()
    return v


def lista(request, cad: Cadastro, template="crud/lista.html", extra=None):
    total_geral = cad.model.objects.count()
    qs = cad.queryset()
    q = request.GET.get("q", "").strip()
    if q:
        cond = Q()
        for f in cad.busca:
            cond |= Q(**{f"{f}__icontains": q})
        qs = qs.filter(cond)
    filtros_ativos = []
    for f in cad.filtros:
        v = request.GET.get(f.nome, "")
        opcoes = f.opcoes()
        if v:
            if f.nome == "ativo":
                qs = qs.filter(ativo=(v == "sim"))
            else:
                qs = qs.filter(**{f.campo or f.nome: v})
        filtros_ativos.append({"nome": f.nome, "rotulo": f.rotulo, "opcoes": [(str(a), b) for a, b in opcoes], "valor": v})
    ordens_validas = {o for o, _ in cad.ordens} | {c.ordem for c in cad.colunas if c.ordem} | {f"-{c.ordem}" for c in cad.colunas if c.ordem}
    ordem = request.GET.get("ordem") or (cad.ordens[0][0] if cad.ordens else None)
    if ordem in ordens_validas:
        qs = qs.order_by(ordem, "pk")
    qs = qs.distinct()
    pagina = Paginator(qs, 10).get_page(request.GET.get("pagina"))
    linhas = [{"obj": o, "celulas": [{"col": c, "valor": _valor(o, c)} for c in cad.colunas]} for o in pagina]
    params = request.GET.copy()
    params.pop("pagina", None)
    ctx = {
        "cad": cad, "pagina": pagina, "linhas": linhas, "q": q, "filtros": filtros_ativos,
        "ordem": ordem, "total_geral": total_geral, "params": params.urlencode(),
        "filtrando": bool(q or any(f["valor"] for f in filtros_ativos)),
        "url_novo": reverse(f"{cad.chave}_novo"),
    }
    ctx.update(extra or {})
    return render(request, template, ctx)


def formulario(request, cad: Cadastro, pk=None, initial=None):
    obj = get_object_or_404(cad.model, pk=pk) if pk else None
    form = cad.form_class(request.POST or None, instance=obj, initial=initial)
    if request.method == "POST" and form.is_valid():
        obj = form.save()
        acao = "atualizad" if pk else "cadastrad"
        messages.success(request, f"{cad.singular.capitalize()} {cad.descricao_obj(obj)} {acao}{cad.artigo} com sucesso.")
        destino = request.POST.get("proximo")
        if destino and destino.startswith("/"):
            return redirect(destino)
        return redirect(cad.rota)
    return render(request, "crud/form.html", {"cad": cad, "form": form, "obj": obj, "editando": bool(pk)})


@require_POST
def alternar_ativo(request, cad: Cadastro, pk):
    obj = get_object_or_404(cad.model, pk=pk)
    obj.ativo = not obj.ativo
    obj.save(update_fields=["ativo"])
    estado = "reativad" if obj.ativo else "desativad"
    messages.success(request, f"{cad.singular.capitalize()} {cad.descricao_obj(obj)} {estado}{cad.artigo}.")
    return redirect(request.POST.get("proximo") or cad.rota)


@require_POST
def excluir(request, cad: Cadastro, pk):
    if not cad.excluivel:
        raise Http404
    obj = get_object_or_404(cad.model, pk=pk)
    desc = cad.descricao_obj(obj)
    obj.delete()
    messages.success(request, f"{cad.singular.capitalize()} {desc} excluíd{cad.artigo}.")
    return redirect(cad.rota)


def rotas(cad: Cadastro, view_lista=None):
    c = cad.chave
    return [
        path(f"{c}/", requer_gestor(view_lista or (lambda r: lista(r, cad))), name=f"{c}_lista"),
        path(f"{c}/novo/", requer_gestor(lambda r: formulario(r, cad)), name=f"{c}_novo"),
        path(f"{c}/<int:pk>/editar/", requer_gestor(lambda r, pk: formulario(r, cad, pk)), name=f"{c}_editar"),
        path(f"{c}/<int:pk>/ativo/", requer_gestor(lambda r, pk: alternar_ativo(r, cad, pk)), name=f"{c}_ativo"),
        path(f"{c}/<int:pk>/excluir/", requer_gestor(lambda r, pk: excluir(r, cad, pk)), name=f"{c}_excluir"),
    ]


# ------------------------------------------------------------------ cadastros
def _choices(model_field):
    return lambda: list(model_field.choices)


SALAS = Cadastro(
    "salas", models.Sala, forms.SalaForm, "sala", "salas", "a",
    "Gerencie as salas, laboratórios e auditórios usados no ensalamento.", "door",
    busca=["nome", "descricao"],
    filtros=[Filtro("tipo", "Tipo", _choices(models.Sala.Tipo)), Filtro("ativo", "Ativo", opcoes_ativo)],
    ordens=[("nome", "Nome (A–Z)"), ("-capacidade", "Maior capacidade"), ("capacidade", "Menor capacidade")],
    colunas=[Coluna("Nome", "nome", "nome", "forte"), Coluna("Tipo", "get_tipo_display", "tipo"),
             Coluna("Capacidade", lambda o: f"{o.capacidade} lugares", "capacidade"),
             Coluna("Descrição", lambda o: o.descricao or "—"), Coluna("Ativo", "ativo", "ativo", "ativo")],
    regras=["O nome segue o padrão bloco-número (C-323).", "Salas não podem ser excluídas, apenas desativadas.",
            "Salas inativas não aparecem para o ensalamento."],
)

PROFESSORES = Cadastro(
    "professores", models.Professor, forms.ProfessorForm, "professor", "professores", "o",
    "Cadastre os professores e o slug usado no link público do ensalamento.", "user",
    busca=["nome", "email", "slug"], filtros=[Filtro("ativo", "Ativo", opcoes_ativo)],
    ordens=[("nome", "Nome (A–Z)"), ("-nome", "Nome (Z–A)")],
    colunas=[Coluna("Nome", "nome", "nome", "forte"), Coluna("E-mail", "email", "email"),
             Coluna("Slug", lambda o: f"/p/p/{o.slug}", "slug"), Coluna("Ativo", "ativo", "ativo", "ativo")],
    regras=["O e-mail e o slug devem ser únicos.", "O slug forma o link público: /p/p/slug.",
            "Professores não podem ser excluídos, apenas desativados."],
)

CURSOS = Cadastro(
    "cursos", models.Curso, forms.CursoForm, "curso", "cursos", "o",
    "Cadastre os cursos e o slug usado no link público do ensalamento.", "cap",
    busca=["nome", "sigla", "slug"], filtros=[Filtro("ativo", "Ativo", opcoes_ativo)],
    ordens=[("nome", "Nome (A–Z)"), ("-nome", "Nome (Z–A)")],
    colunas=[Coluna("Nome", "nome", "nome", "forte"), Coluna("Sigla", lambda o: o.sigla or "—", "sigla"),
             Coluna("Slug", lambda o: f"/p/{o.slug}", "slug"), Coluna("Ativo", "ativo", "ativo", "ativo")],
    regras=["O nome e o slug devem ser únicos.", "O slug forma o link público: /p/slug.",
            "Cursos não podem ser excluídos, apenas desativados."],
)

SEMESTRES = Cadastro(
    "semestres", models.Semestre, forms.SemestreForm, "semestre", "semestres", "o",
    "Defina os semestres letivos e o período de cada um.", "cal",
    busca=["nome", "slug"],
    filtros=[Filtro("ano", "Ano", lambda: [(a, a) for a in models.Semestre.objects.values_list("ano", flat=True).distinct().order_by("-ano")]),
             Filtro("ativo", "Ativo", opcoes_ativo)],
    ordens=[("-nome", "Mais recente"), ("nome", "Mais antigo")],
    colunas=[Coluna("Nome", "nome", "nome", "forte"), Coluna("Ano", "ano", "ano"),
             Coluna("Início", "data_inicio", "data_inicio", "data"), Coluna("Fim", "data_fim", "data_fim", "data"),
             Coluna("Ativo", "ativo", "ativo", "ativo")],
    regras=["O nome segue o formato 2026/02.", "A data de fim deve ser posterior à de início.",
            "Semestres não podem ser excluídos, apenas desativados."],
)

CALENDARIO = Cadastro(
    "calendario", models.DataCalendario, forms.DataCalendarioForm, "data", "datas", "a",
    "Feriados, reposições de aula e datas importantes do ano letivo.", "cal",
    busca=["descricao"], ordens=[("data", "Data")],
    colunas=[Coluna("Data", "data", "data", "data"), Coluna("Dia da semana", "dia_semana"),
             Coluna("Descrição", "descricao", None, "forte"),
             Coluna("Tipo", lambda o: "Feriado" if o.feriado else ("Reposição de aula" if o.reposicao else "Evento"), None, "tipo_cal")],
    regras=["Feriados ocultam o ensalamento do dia na página pública.",
            "Eventos aparecem apenas na página pública dos professores.", "Cada data pode ser cadastrada uma vez."],
    desativavel=False, excluivel=True, descricao_obj=lambda o: f"{o.data:%d/%m/%Y}",
)

TURMAS = Cadastro(
    "turmas", models.Turma, forms.TurmaForm, "turma", "turmas", "a",
    "Turmas de cada semestre, com cursos e quantidade de alunos.", "users",
    busca=["nome", "slug", "descricao"],
    filtros=[Filtro("curso", "Curso", lambda: list(models.Curso.objects.values_list("id", "nome")), "cursos__id"),
             Filtro("semestre", "Semestre", lambda: list(models.Semestre.objects.values_list("id", "nome")), "semestre_id"),
             Filtro("ativo", "Ativo", opcoes_ativo)],
    ordens=[("ordem", "Ordem"), ("nome", "Nome (A–Z)"), ("-quantidade_alunos", "Mais alunos")],
    colunas=[Coluna("Nome", "nome", "nome", "forte"),
             Coluna("Cursos", lambda o: ", ".join(c.sigla or c.nome for c in o.cursos.all())),
             Coluna("Semestre", "semestre", "semestre__nome"), Coluna("Ordem", "ordem", "ordem"),
             Coluna("Alunos", "quantidade_alunos", "quantidade_alunos"), Coluna("Ativo", "ativo", "ativo", "ativo")],
    regras=["Uma turma pode pertencer a mais de um curso (ex.: BES e BSI).",
            "A ordem define a coluna da turma na grade.", "O slug forma o link público: /p/t/slug."],
    select_related=("semestre",), prefetch=("cursos",),
)

UNIDADES = Cadastro(
    "unidades", models.UnidadeCurricular, forms.UnidadeCurricularForm, "unidade curricular", "unidades curriculares", "a",
    "Disciplinas usadas nas grades horárias.", "book",
    busca=["codigo", "nome", "descricao"], filtros=[Filtro("ativo", "Ativo", opcoes_ativo)],
    ordens=[("codigo", "Código (A–Z)"), ("nome", "Nome (A–Z)")],
    colunas=[Coluna("Código", "codigo", "codigo", "forte"), Coluna("Nome", "nome", "nome"),
             Coluna("Ativo", "ativo", "ativo", "ativo")],
    regras=["O código é único e usa letras maiúsculas e _ (POO_II).",
            "Unidades não podem ser excluídas, apenas desativadas."],
    descricao_obj=lambda o: o.codigo,
)

GRADES = Cadastro(
    "grades", models.GradeHoraria, forms.GradeHorariaForm, "grade horária", "grades horárias", "a",
    "Monte as aulas de cada curso e semestre.", "grid",
    busca=["nome", "curso__nome"],
    filtros=[Filtro("curso", "Curso", lambda: list(models.Curso.objects.values_list("id", "nome")), "curso_id"),
             Filtro("semestre", "Semestre", lambda: list(models.Semestre.objects.values_list("id", "nome")), "semestre_id"),
             Filtro("ativo", "Ativo", opcoes_ativo)],
    ordens=[("-semestre__nome", "Semestre (mais recente)"), ("curso__nome", "Curso (A–Z)")],
    colunas=[Coluna("Curso", "curso", "curso__nome", "forte"), Coluna("Semestre", "semestre", "semestre__nome"),
             Coluna("Nome", "nome", "nome"), Coluna("Aulas", lambda o: o.aulas.count()),
             Coluna("Ativo", "ativo", "ativo", "ativo")],
    regras=["Cada curso e semestre podem ter várias grades com nomes diferentes.",
            "As turmas da grade são as do mesmo curso e semestre.",
            "Um professor não pode ter duas aulas no mesmo horário."],
    acoes=[("Abrir grade", "grade_detalhe")], select_related=("curso", "semestre"),
)

ENSALAMENTOS = Cadastro(
    "ensalamentos", models.Ensalamento, forms.EnsalamentoForm, "ensalamento", "ensalamentos", "o",
    "Informe as salas de cada semana da grade horária.", "door",
    busca=["nome", "grade__nome", "grade__curso__nome"],
    filtros=[Filtro("curso", "Curso", lambda: list(models.Curso.objects.values_list("id", "nome")), "grade__curso_id"),
             Filtro("status", "Status", _choices(models.Ensalamento.Status)), Filtro("ativo", "Ativo", opcoes_ativo)],
    ordens=[("-data_inicio", "Início (mais recente)"), ("data_inicio", "Início (mais antigo)")],
    colunas=[Coluna("Curso", "grade__curso", "grade__curso__nome", "forte"), Coluna("Nome", "nome", "nome", "forte"),
             Coluna("Data de início", "data_inicio", "data_inicio", "data"), Coluna("Data de fim", "data_fim", None, "data"),
             Coluna("Status", "status", "status", "status"), Coluna("Ativo", "ativo", "ativo", "ativo")],
    regras=["A data de início deve ser sempre uma segunda-feira.", "A data de fim é o sábado da mesma semana.",
            "Cada grade pode ter apenas um ensalamento por semana."],
    acoes=[("Abrir ensalamento", "ensalamento_detalhe")], select_related=("grade__curso",),
)

TODOS = [SALAS, PROFESSORES, CURSOS, SEMESTRES, CALENDARIO, TURMAS, UNIDADES, GRADES, ENSALAMENTOS]
