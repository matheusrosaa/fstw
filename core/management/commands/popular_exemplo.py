"""Popula o banco com dados de exemplo (os mesmos dos protótipos).

Uso: python manage.py popular_exemplo [--senha SENHA]
As datas do ensalamento são calculadas a partir de hoje, para a página pública sempre ter a semana atual.
"""
from datetime import date, timedelta

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from core import models as m
from core.utils import nome_semana, segunda_da_semana

SALAS = [("C-101", "sala", 45), ("C-102", "sala", 50), ("C-323", "sala", 40), ("C-324", "sala", 35),
         ("E-215", "laboratorio", 30), ("E-216", "laboratorio", 24), ("E-310", "laboratorio", 28), ("A-001", "auditorio", 120)]

PROFESSORES = ["Sabrina", "Sergio", "Leanderson", "Dornel", "Lucia", "Priscila", "José Raul", "Mel", "Romão", "Marcelo P."]

UNIDADES = {
    "DEW": "Desenvolvimento Web", "FENS_I": "Fundamentos de Engenharia de Software", "APC_I": "Algoritmos e Programação I",
    "APC_II": "Algoritmos e Programação II", "MATD": "Matemática Discreta", "IHC": "Interface Homem-Computador",
    "APSI_I": "Análise e Projeto de Sistemas I", "APSI_II": "Análise e Projeto de Sistemas II",
    "VDE_I": "Vivências de Extensão I", "ESTCP": "Estatística para Computação", "BD_I": "Banco de Dados I",
    "BD_II": "Banco de Dados II", "POO_I": "Programação Orientada a Objetos I", "ARC_I": "Arquitetura de Computadores",
    "VEII_PI": "Vivências de Extensão II – Projeto Integrador I",
}

# grade[dia][horário][turma] = (unidade, professor)
SA, SE, LE, DO, LU, PR, JR, ME, RO, MP = PROFESSORES
GRADE = [
    [[("DEW", SA), ("APSI_I", SE), ("POO_I", LE)], [("FENS_I", SE), ("VDE_I", RO), ("ARC_I", MP)]],
    [[("APC_I", SA), ("APSI_I", SE), ("BD_II", DO)], [("DEW", SA), ("VDE_I", RO), ("POO_I", LE)]],
    [[("MATD", LU), ("ESTCP", PR), ("BD_II", DO)], [("MATD", LU), ("BD_I", JR), ("APSI_II", SE)]],
    [[("IHC", ME), ("APC_II", LE), ("VEII_PI", RO)], [("FENS_I", SE), ("ESTCP", PR), ("VEII_PI", RO)]],
    [[("IHC", ME), ("BD_I", JR), ("APSI_II", SE)], [("APC_I", SA), ("APC_II", LE), ("ARC_I", MP)]],
]
SALAS_GRADE = [
    [["E-215", "C-324", "C-323"], ["C-101", "C-324", None]],
    [["C-101", "C-324", None], [None, "C-324", "C-323"]],
    [["C-102", "C-324", "C-323"], ["C-102", "E-216", "C-323"]],
    [["C-101", "C-324", "A-001"], ["C-101", "C-324", "A-001"]],
    [["C-101", None, "C-323"], ["C-101", "C-324", "C-323"]],
]
TURMAS = [("Turma 1ª fase", "111-1an", 38), ("Turma 2ª fase", "111-2an", 32), ("Turma 3ª fase", "111-3an", 40)]

FERIADOS_2026 = [
    (date(2026, 1, 1), "Confraternização Universal"), (date(2026, 2, 16), "Carnaval"), (date(2026, 2, 17), "Carnaval"),
    (date(2026, 3, 9), "Aniversário de Joinville"), (date(2026, 4, 3), "Sexta-feira Santa"), (date(2026, 4, 21), "Tiradentes"),
    (date(2026, 5, 1), "Dia do Trabalho"), (date(2026, 6, 4), "Corpus Christi"), (date(2026, 9, 7), "Independência do Brasil"),
    (date(2026, 10, 12), "Nossa Senhora Aparecida"), (date(2026, 11, 2), "Finados"), (date(2026, 11, 15), "Proclamação da República"),
    (date(2026, 11, 20), "Dia da Consciência Negra"), (date(2026, 12, 25), "Natal"),
]


class Command(BaseCommand):
    help = "Cria dados de exemplo (salas, professores, cursos, grade e ensalamentos)."

    def add_arguments(self, parser):
        parser.add_argument("--senha", default="univille2026", help="Senha dos usuários de exemplo")

    @transaction.atomic
    def handle(self, *args, senha, **opts):
        User = get_user_model()
        if not User.objects.filter(username="admin").exists():
            User.objects.create_superuser("admin", "admin@exemplo.edu.br", senha, first_name="Administrador")
        if not User.objects.filter(username="aluno").exists():
            User.objects.create_user("aluno", "aluno@exemplo.edu.br", senha, first_name="Aluno")  # sem perfil de gestor

        salas = {n: m.Sala.objects.get_or_create(nome=n, defaults={"tipo": t, "capacidade": c})[0] for n, t, c in SALAS}
        profs = {}
        for nome in PROFESSORES:
            slug = nome.lower().replace(" ", "-").replace(".", "").replace("é", "e").replace("ã", "a")
            profs[nome] = m.Professor.objects.get_or_create(slug=slug, defaults={"nome": nome, "email": f"{slug}@exemplo.edu.br"})[0]
        ucs = {c: m.UnidadeCurricular.objects.get_or_create(codigo=c, defaults={"nome": n})[0] for c, n in UNIDADES.items()}

        bsi = m.Curso.objects.get_or_create(slug="bsi", defaults={"nome": "Sistemas de Informação", "sigla": "BSI"})[0]
        bes = m.Curso.objects.get_or_create(slug="bes", defaults={"nome": "Engenharia de Software", "sigla": "BES"})[0]
        sem = m.Semestre.objects.get_or_create(nome="2026/02", defaults={
            "ano": 2026, "data_inicio": date(2026, 8, 3), "data_fim": date(2026, 12, 12), "slug": "2026-02"})[0]

        turmas = []
        for i, (nome, slug, qtd) in enumerate(TURMAS, start=1):
            t, _ = m.Turma.objects.get_or_create(slug=slug, defaults={"nome": nome, "semestre": sem, "ordem": i, "quantidade_alunos": qtd})
            t.cursos.add(bsi)
            turmas.append(t)
        t_bes, _ = m.Turma.objects.get_or_create(slug="121-1an", defaults={"nome": "BES 1ª fase", "semestre": sem, "ordem": 1, "quantidade_alunos": 42})
        t_bes.cursos.add(bes)

        for d, desc in FERIADOS_2026:
            m.DataCalendario.objects.get_or_create(data=d, defaults={"descricao": desc, "feriado": True})

        hoje = timezone.localdate()
        segunda = segunda_da_semana(hoje)
        # eventos de exemplo nesta semana (aparecem só na página pública dos professores)
        for dias, desc in [(2, "Último dia para publicação das notas do bimestre"), (3, "Reunião pedagógica do curso")]:
            d = segunda + timedelta(days=dias)
            m.DataCalendario.objects.get_or_create(data=d, defaults={"descricao": desc})

        grade, _ = m.GradeHoraria.objects.get_or_create(curso=bsi, semestre=sem, nome="BSI – Noturno 2026/02")
        aulas = {}
        for d, horarios in enumerate(GRADE):
            for h, linha in enumerate(horarios, start=1):
                for ti, (uc, prof) in enumerate(linha):
                    aulas[(d, h, ti)] = m.Aula.objects.get_or_create(
                        grade=grade, turma=turmas[ti], dia_semana=d, horario=h,
                        defaults={"unidade": ucs[uc], "professor": profs[prof]})[0]

        grade_bes, _ = m.GradeHoraria.objects.get_or_create(curso=bes, semestre=sem, nome="BES – Noturno 2026/02")
        aula_bes1 = m.Aula.objects.get_or_create(grade=grade_bes, turma=t_bes, dia_semana=1, horario=1,
                                                 defaults={"unidade": ucs["APC_I"], "professor": profs["Priscila"]})[0]
        aula_bes2 = m.Aula.objects.get_or_create(grade=grade_bes, turma=t_bes, dia_semana=3, horario=1,
                                                 defaults={"unidade": ucs["MATD"], "professor": profs["Lucia"]})[0]

        def ensalar(semana, status, alocar=True):
            e, criado = m.Ensalamento.objects.get_or_create(grade=grade, data_inicio=semana,
                                                            defaults={"nome": nome_semana(semana), "status": status})
            if criado and alocar:
                for (d, h, ti), aula in aulas.items():
                    sala = SALAS_GRADE[d][h - 1][ti]
                    if sala:
                        m.Alocacao.objects.create(ensalamento=e, aula=aula, sala=salas[sala])
            return e

        ensalar(segunda - timedelta(days=7), m.Ensalamento.Status.PUBLICADO)
        ensalar(segunda, m.Ensalamento.Status.PUBLICADO)
        # semana seguinte: BES já usa C-101 (terça 18:55) e A-001 (quinta 18:55) → a cópia de BSI mostra 2 choques
        prox = segunda + timedelta(days=7)
        e_bes, criado = m.Ensalamento.objects.get_or_create(grade=grade_bes, data_inicio=prox,
                                                            defaults={"nome": nome_semana(prox), "status": "rascunho"})
        if criado:
            m.Alocacao.objects.create(ensalamento=e_bes, aula=aula_bes1, sala=salas["C-101"])
            m.Alocacao.objects.create(ensalamento=e_bes, aula=aula_bes2, sala=salas["A-001"])

        self.stdout.write(self.style.SUCCESS(
            f"Dados de exemplo criados. Usuários: admin (gestor) e aluno (sem permissão), senha: {senha}"))
