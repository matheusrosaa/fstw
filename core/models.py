"""Modelos do Sistema de Ensalamento."""
from datetime import timedelta

from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator, RegexValidator
from django.db import models
from django.db.models import Q

from .utils import DIAS, HORARIOS, HORARIO_TEXTO, DIAS_LONGOS

slug_validator = RegexValidator(
    r"^[a-z0-9]+(?:-[a-z0-9]+)*$",
    "Use apenas letras minúsculas, números e hífens (ex.: sistemas-informacao).",
)
SLUGS_RESERVADOS = {"t", "p"}


class AtivoQuerySet(models.QuerySet):
    def ativos(self):
        return self.filter(ativo=True)


class Sala(models.Model):
    class Tipo(models.TextChoices):
        SALA_AULA = "sala", "Sala de aula"
        LABORATORIO = "laboratorio", "Laboratório de informática"
        AUDITORIO = "auditorio", "Auditório"

    nome = models.CharField(
        "Nome", max_length=20, unique=True,
        validators=[RegexValidator(r"^[A-Z]-\d{3}$", "Use o formato bloco-número, ex.: C-323 ou E-215.")],
        error_messages={"unique": "Já existe uma sala com este nome."},
    )
    tipo = models.CharField("Tipo", max_length=20, choices=Tipo.choices)
    capacidade = models.PositiveIntegerField(
        "Capacidade", validators=[MinValueValidator(1, "A capacidade deve ser maior que zero.")]
    )
    descricao = models.TextField("Descrição", blank=True)
    ativo = models.BooleanField("Ativo", default=True)

    objects = AtivoQuerySet.as_manager()

    class Meta:
        ordering = ["nome"]

    def __str__(self):
        return self.nome


class Professor(models.Model):
    nome = models.CharField("Nome", max_length=120)
    email = models.EmailField("E-mail", unique=True, error_messages={"unique": "Já existe um professor com este e-mail."})
    slug = models.SlugField("Slug", max_length=60, unique=True, validators=[slug_validator],
                            error_messages={"unique": "Este slug já está em uso."})
    ativo = models.BooleanField("Ativo", default=True)

    objects = AtivoQuerySet.as_manager()

    class Meta:
        ordering = ["nome"]
        verbose_name_plural = "professores"

    def __str__(self):
        return self.nome


class Curso(models.Model):
    nome = models.CharField("Nome", max_length=120, unique=True, error_messages={"unique": "Já existe um curso com este nome."})
    sigla = models.CharField("Sigla", max_length=10, blank=True, help_text="Ex.: BSI, BES")
    slug = models.SlugField("Slug", max_length=60, unique=True, validators=[slug_validator],
                            error_messages={"unique": "Este slug já está em uso."})
    ativo = models.BooleanField("Ativo", default=True)

    objects = AtivoQuerySet.as_manager()

    class Meta:
        ordering = ["nome"]

    def __str__(self):
        return self.nome

    def clean(self):
        if self.slug in SLUGS_RESERVADOS:
            raise ValidationError({"slug": "Este slug é reservado pelo sistema. Escolha outro."})


class Semestre(models.Model):
    nome = models.CharField(
        "Nome", max_length=7, unique=True,
        validators=[RegexValidator(r"^\d{4}/0[12]$", "Use o formato ano/semestre, ex.: 2026/02.")],
        error_messages={"unique": "Já existe um semestre com este nome."},
    )
    ano = models.PositiveIntegerField("Ano")
    data_inicio = models.DateField("Data de início")
    data_fim = models.DateField("Data de fim")
    slug = models.SlugField("Slug", max_length=20, unique=True, validators=[slug_validator],
                            error_messages={"unique": "Este slug já está em uso."})
    ativo = models.BooleanField("Ativo", default=True)

    objects = AtivoQuerySet.as_manager()

    class Meta:
        ordering = ["-ano", "-nome"]

    def __str__(self):
        return self.nome

    def clean(self):
        erros = {}
        if self.nome and self.ano and not self.nome.startswith(str(self.ano)):
            erros["ano"] = "O ano deve ser o mesmo informado no nome."
        if self.data_inicio and self.data_fim and self.data_fim <= self.data_inicio:
            erros["data_fim"] = "A data de fim deve ser posterior à data de início."
        if erros:
            raise ValidationError(erros)


class DataCalendario(models.Model):
    data = models.DateField("Data", unique=True, error_messages={"unique": "Esta data já está no calendário."})
    feriado = models.BooleanField("Feriado", default=False)
    reposicao = models.BooleanField("Reposição de aula", default=False)
    descricao = models.CharField("Descrição", max_length=200)

    class Meta:
        ordering = ["data"]
        verbose_name = "data do calendário"
        verbose_name_plural = "calendário acadêmico"

    def __str__(self):
        return f"{self.data:%d/%m/%Y} – {self.descricao}"

    @property
    def dia_semana(self):
        return DIAS_LONGOS[self.data.weekday()]

    def clean(self):
        if self.feriado and self.reposicao:
            raise ValidationError({"reposicao": "Uma data não pode ser feriado e reposição de aula ao mesmo tempo."})


class Turma(models.Model):
    cursos = models.ManyToManyField(Curso, verbose_name="Cursos", related_name="turmas")
    semestre = models.ForeignKey(Semestre, verbose_name="Semestre", on_delete=models.PROTECT, related_name="turmas")
    ordem = models.PositiveIntegerField("Ordem", default=1, help_text="Posição da turma na grade (1ª coluna, 2ª coluna…)")
    nome = models.CharField("Nome", max_length=80)
    slug = models.SlugField("Slug", max_length=60, unique=True, validators=[slug_validator],
                            help_text="Usado no link público, ex.: 111-2an",
                            error_messages={"unique": "Este slug já está em uso."})
    quantidade_alunos = models.PositiveIntegerField(
        "Quantidade de alunos", validators=[MinValueValidator(1, "Informe ao menos 1 aluno.")]
    )
    descricao = models.TextField("Descrição", blank=True)
    ativo = models.BooleanField("Ativo", default=True)

    objects = AtivoQuerySet.as_manager()

    class Meta:
        ordering = ["semestre", "ordem", "nome"]

    def __str__(self):
        return self.nome


class UnidadeCurricular(models.Model):
    codigo = models.CharField(
        "Código", max_length=20, unique=True,
        validators=[RegexValidator(r"^[A-Z0-9]+(_[A-Z0-9]+)*$", "Use letras maiúsculas, números e _ (ex.: POO_II).")],
        error_messages={"unique": "Já existe uma unidade curricular com este código."},
    )
    nome = models.CharField("Nome", max_length=120)
    descricao = models.TextField("Descrição", blank=True)
    ativo = models.BooleanField("Ativo", default=True)

    objects = AtivoQuerySet.as_manager()

    class Meta:
        ordering = ["codigo"]
        verbose_name = "unidade curricular"
        verbose_name_plural = "unidades curriculares"

    def __str__(self):
        return f"{self.codigo} – {self.nome}"


class GradeHoraria(models.Model):
    curso = models.ForeignKey(Curso, verbose_name="Curso", on_delete=models.PROTECT, related_name="grades")
    semestre = models.ForeignKey(Semestre, verbose_name="Semestre", on_delete=models.PROTECT, related_name="grades")
    nome = models.CharField("Nome", max_length=80)
    ativo = models.BooleanField("Ativo", default=True)

    objects = AtivoQuerySet.as_manager()

    class Meta:
        ordering = ["-semestre__ano", "curso__nome", "nome"]
        verbose_name = "grade horária"
        verbose_name_plural = "grades horárias"
        constraints = [
            models.UniqueConstraint(fields=["curso", "semestre", "nome"], name="grade_unica_por_curso_semestre",
                                    violation_error_message="Já existe uma grade com este nome para o curso e semestre."),
        ]

    def __str__(self):
        return self.nome

    def turmas(self):
        return Turma.objects.filter(cursos=self.curso, semestre=self.semestre, ativo=True).distinct().order_by("ordem", "nome")


class Aula(models.Model):
    grade = models.ForeignKey(GradeHoraria, on_delete=models.CASCADE, related_name="aulas")
    turma = models.ForeignKey(Turma, verbose_name="Turma", on_delete=models.PROTECT, related_name="aulas")
    unidade = models.ForeignKey(UnidadeCurricular, verbose_name="Disciplina", on_delete=models.PROTECT, related_name="aulas")
    professor = models.ForeignKey(Professor, verbose_name="Professor", on_delete=models.PROTECT, related_name="aulas")
    dia_semana = models.PositiveSmallIntegerField("Dia da semana", choices=DIAS)
    horario = models.PositiveSmallIntegerField("Horário", choices=HORARIOS)

    class Meta:
        ordering = ["dia_semana", "horario", "turma__ordem"]
        constraints = [
            models.UniqueConstraint(fields=["grade", "turma", "dia_semana", "horario"], name="uma_aula_por_turma_horario",
                                    violation_error_message="Esta turma já tem aula neste dia e horário."),
        ]

    def __str__(self):
        return f"{self.unidade.codigo} · {self.turma} · {self.get_dia_semana_display()} {self.get_horario_display()}"

    @property
    def horario_texto(self):
        return HORARIO_TEXTO[self.horario]

    def clean(self):
        if not (self.professor_id and self.grade_id and self.dia_semana is not None and self.horario):
            return
        choque = (Aula.objects.filter(professor_id=self.professor_id, dia_semana=self.dia_semana, horario=self.horario,
                                      grade__semestre_id=self.grade.semestre_id, grade__ativo=True)
                  .exclude(pk=self.pk).select_related("turma").first())
        if choque:
            raise ValidationError({"professor": f"Este professor já tem aula neste horário ({choque.turma}, {choque.unidade.codigo})."})


class Ensalamento(models.Model):
    class Status(models.TextChoices):
        RASCUNHO = "rascunho", "Rascunho"
        PUBLICADO = "publicado", "Publicado"

    grade = models.ForeignKey(GradeHoraria, verbose_name="Grade horária", on_delete=models.PROTECT, related_name="ensalamentos")
    nome = models.CharField("Nome", max_length=40, help_text="Ex.: 09/11 até 14/11")
    data_inicio = models.DateField("Data de início")
    status = models.CharField("Status", max_length=10, choices=Status.choices, default=Status.RASCUNHO)
    ativo = models.BooleanField("Ativo", default=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    objects = AtivoQuerySet.as_manager()

    class Meta:
        ordering = ["-data_inicio", "grade__curso__nome"]
        constraints = [
            models.UniqueConstraint(fields=["grade", "data_inicio"], name="um_ensalamento_por_grade_semana",
                                    violation_error_message="Já existe ensalamento desta grade nesta semana."),
        ]

    def __str__(self):
        return f"{self.grade} · {self.nome}"

    @property
    def data_fim(self):
        return self.data_inicio + timedelta(days=5) if self.data_inicio else None

    @property
    def publicado(self):
        return self.status == self.Status.PUBLICADO

    def clean(self):
        if self.data_inicio and self.data_inicio.weekday() != 0:
            raise ValidationError({"data_inicio": "A data de início deve ser uma segunda-feira."})


class Alocacao(models.Model):
    """Sala informada para uma aula dentro de um ensalamento."""
    ensalamento = models.ForeignKey(Ensalamento, on_delete=models.CASCADE, related_name="alocacoes")
    aula = models.ForeignKey(Aula, on_delete=models.CASCADE, related_name="alocacoes")
    sala = models.ForeignKey(Sala, verbose_name="Sala", on_delete=models.PROTECT, related_name="alocacoes")

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["ensalamento", "aula"], name="uma_sala_por_aula"),
        ]

    def __str__(self):
        return f"{self.aula} → {self.sala}"

    @property
    def nao_comporta(self):
        return self.aula.turma.quantidade_alunos > self.sala.capacidade


def alocacoes_da_semana(segunda, dia_semana=None, horario=None):
    """Alocações de qualquer ensalamento ativo da semana iniciada em `segunda`."""
    qs = Alocacao.objects.filter(ensalamento__data_inicio=segunda, ensalamento__ativo=True)
    if dia_semana is not None:
        qs = qs.filter(aula__dia_semana=dia_semana)
    if horario is not None:
        qs = qs.filter(aula__horario=horario)
    return qs.select_related("aula__turma", "aula__unidade", "sala", "ensalamento__grade")


def choque_de_sala(sala, ensalamento, aula, ignorar_pk=None):
    """Retorna a alocação que já ocupa a sala no mesmo dia/horário da semana, ou None."""
    qs = alocacoes_da_semana(ensalamento.data_inicio, aula.dia_semana, aula.horario).filter(sala=sala)
    if ignorar_pk:
        qs = qs.exclude(pk=ignorar_pk)
    return qs.exclude(Q(ensalamento=ensalamento) & Q(aula=aula)).first()
