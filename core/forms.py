"""Formulários com estilo DaisyUI."""
from django import forms

from . import models


class EstiloMixin:
    """Aplica classes DaisyUI aos widgets e marca campos com erro."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for campo in self.fields.values():
            w = campo.widget
            if isinstance(campo, forms.ModelChoiceField) and not isinstance(campo, forms.ModelMultipleChoiceField):
                if campo.empty_label is not None and campo.empty_label.startswith("---"):
                    campo.empty_label = "Selecione"
            elif isinstance(campo, forms.ChoiceField):
                campo.choices = [("", "Selecione") if v == "" else (v, t) for v, t in campo.choices]
            if isinstance(w, forms.CheckboxInput):
                w.attrs["class"] = "toggle toggle-primary"
            elif isinstance(w, forms.CheckboxSelectMultiple):
                w.attrs["class"] = "checkbox checkbox-primary checkbox-sm"
            elif isinstance(w, (forms.Select, forms.SelectMultiple)):
                w.attrs["class"] = "select select-bordered w-full"
            elif isinstance(w, forms.Textarea):
                w.attrs["rows"] = 3
                w.attrs["class"] = "textarea textarea-bordered w-full"
            else:
                w.attrs["class"] = "input input-bordered w-full"

    def full_clean(self):
        super().full_clean()
        for nome in self.errors:
            if nome in self.fields:
                w = self.fields[nome].widget
                w.attrs["class"] = w.attrs.get("class", "") + " input-error select-error textarea-error"
                w.attrs["aria-invalid"] = "true"


DATA = forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d")


class SalaForm(EstiloMixin, forms.ModelForm):
    class Meta:
        model = models.Sala
        fields = ["nome", "tipo", "capacidade", "descricao", "ativo"]
        widgets = {"nome": forms.TextInput(attrs={"placeholder": "Ex.: C-323"}),
                   "capacidade": forms.NumberInput(attrs={"placeholder": "Ex.: 40", "min": 1})}

    def clean_nome(self):
        return self.cleaned_data["nome"].strip().upper()


class ProfessorForm(EstiloMixin, forms.ModelForm):
    class Meta:
        model = models.Professor
        fields = ["nome", "email", "slug", "ativo"]
        widgets = {"nome": forms.TextInput(attrs={"placeholder": "Nome completo"}),
                   "email": forms.EmailInput(attrs={"placeholder": "nome@univille.br"}),
                   "slug": forms.TextInput(attrs={"placeholder": "Ex.: dornel"})}
        help_texts = {"slug": "Usado no link público do professor."}


class CursoForm(EstiloMixin, forms.ModelForm):
    class Meta:
        model = models.Curso
        fields = ["nome", "sigla", "slug", "ativo"]
        widgets = {"nome": forms.TextInput(attrs={"placeholder": "Ex.: Sistemas de Informação"}),
                   "slug": forms.TextInput(attrs={"placeholder": "Ex.: bsi"})}
        help_texts = {"slug": "Usado no link público do curso."}


class SemestreForm(EstiloMixin, forms.ModelForm):
    class Meta:
        model = models.Semestre
        fields = ["nome", "ano", "data_inicio", "data_fim", "slug", "ativo"]
        widgets = {"nome": forms.TextInput(attrs={"placeholder": "Ex.: 2026/02"}),
                   "data_inicio": DATA, "data_fim": DATA,
                   "slug": forms.TextInput(attrs={"placeholder": "Ex.: 2026-02"})}


class DataCalendarioForm(EstiloMixin, forms.ModelForm):
    class Meta:
        model = models.DataCalendario
        fields = ["data", "descricao", "feriado", "reposicao"]
        widgets = {"data": DATA, "descricao": forms.TextInput(attrs={"placeholder": "Ex.: Proclamação da República"})}


class TurmaForm(EstiloMixin, forms.ModelForm):
    class Meta:
        model = models.Turma
        fields = ["cursos", "semestre", "ordem", "nome", "slug", "quantidade_alunos", "descricao", "ativo"]
        widgets = {"cursos": forms.CheckboxSelectMultiple,
                   "nome": forms.TextInput(attrs={"placeholder": "Ex.: Turma 2ª fase"}),
                   "slug": forms.TextInput(attrs={"placeholder": "Ex.: 111-2an"})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["cursos"].queryset = models.Curso.objects.ativos()
        self.fields["semestre"].queryset = models.Semestre.objects.ativos()


class UnidadeCurricularForm(EstiloMixin, forms.ModelForm):
    class Meta:
        model = models.UnidadeCurricular
        fields = ["codigo", "nome", "descricao", "ativo"]
        widgets = {"codigo": forms.TextInput(attrs={"placeholder": "Ex.: POO_II"}),
                   "nome": forms.TextInput(attrs={"placeholder": "Ex.: Programação Orientada a Objetos II"})}

    def clean_codigo(self):
        return self.cleaned_data["codigo"].strip().upper()


class GradeHorariaForm(EstiloMixin, forms.ModelForm):
    class Meta:
        model = models.GradeHoraria
        fields = ["curso", "semestre", "nome", "ativo"]
        widgets = {"nome": forms.TextInput(attrs={"placeholder": "Ex.: BSI – Noturno 2026/02"})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["curso"].queryset = models.Curso.objects.ativos()
        self.fields["semestre"].queryset = models.Semestre.objects.ativos()


class AulaForm(EstiloMixin, forms.ModelForm):
    class Meta:
        model = models.Aula
        fields = ["turma", "dia_semana", "horario", "unidade", "professor"]

    def __init__(self, *args, grade=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.instance.grade = grade
        self.fields["turma"].queryset = grade.turmas()
        self.fields["unidade"].queryset = models.UnidadeCurricular.objects.ativos()
        self.fields["professor"].queryset = models.Professor.objects.ativos()
        for f in self.fields.values():
            f.empty_label = "Selecione"

    def validate_unique(self):
        # inclui a grade (que não é campo do formulário) na checagem de aula repetida
        try:
            self.instance.validate_constraints()
        except forms.ValidationError as e:
            self._update_errors(e)


class EnsalamentoForm(EstiloMixin, forms.ModelForm):
    class Meta:
        model = models.Ensalamento
        fields = ["grade", "nome", "data_inicio", "status", "ativo"]
        widgets = {"nome": forms.TextInput(attrs={"placeholder": "Ex.: 09/11 até 14/11"}), "data_inicio": DATA}
        help_texts = {"grade": "O curso e o semestre vêm da grade escolhida.", "data_inicio": "Sempre uma segunda-feira."}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["grade"].queryset = models.GradeHoraria.objects.ativos().select_related("curso", "semestre")
        self.fields["grade"].empty_label = "Selecione a grade horária"


class AlocacaoForm(forms.Form):
    sala = forms.ModelChoiceField(queryset=models.Sala.objects.ativos(), required=False, empty_label="Sem sala")


class CopiarForm(EstiloMixin, forms.Form):
    data_destino = forms.DateField(label="Segunda-feira de destino", widget=DATA)

    def __init__(self, *args, ensalamento=None, **kwargs):
        self.ensalamento = ensalamento
        super().__init__(*args, **kwargs)

    def clean_data_destino(self):
        d = self.cleaned_data["data_destino"]
        if d.weekday() != 0:
            raise forms.ValidationError("A data de destino deve ser uma segunda-feira.")
        if d == self.ensalamento.data_inicio:
            raise forms.ValidationError("Escolha uma semana diferente da original.")
        if models.Ensalamento.objects.filter(grade=self.ensalamento.grade, data_inicio=d).exists():
            raise forms.ValidationError("Já existe ensalamento desta grade nesta semana.")
        return d


from django.contrib.auth.forms import PasswordChangeForm  # noqa: E402


class SenhaForm(EstiloMixin, PasswordChangeForm):
    pass
