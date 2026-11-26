"""Testes das regras de negócio do ensalamento. Rode: python manage.py test"""
from datetime import date, timedelta
from unittest import mock

from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse

from . import forms, models as m, services
from .utils import segunda_da_semana

HOJE = date(2026, 11, 18)  # quarta-feira


@mock.patch("django.utils.timezone.localdate", return_value=HOJE)
class RegrasTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        with mock.patch("django.utils.timezone.localdate", return_value=HOJE):
            call_command("popular_exemplo", senha="senha-teste-123", stdout=open("/dev/null", "w"))
        cls.segunda = segunda_da_semana(HOJE)
        cls.ens = m.Ensalamento.objects.get(grade__curso__slug="bsi", data_inicio=cls.segunda)

    def setUp(self):
        self.client.login(username="admin", password="senha-teste-123")

    # --- acesso
    def test_login_obrigatorio(self, _):
        self.client.logout()
        r = self.client.get(reverse("salas_lista"))
        self.assertRedirects(r, "/login/?next=/salas/")

    def test_login_com_erro_mostra_mensagem(self, _):
        self.client.logout()
        r = self.client.post("/login/", {"username": "admin", "password": "errada"})
        self.assertContains(r, "Usuário ou senha inválidos")

    def test_usuario_sem_perfil_recebe_403(self, _):
        self.client.logout()
        self.client.login(username="aluno", password="senha-teste-123")
        r = self.client.get(reverse("dashboard"))
        self.assertEqual(r.status_code, 403)
        self.assertContains(r, "Acesso não autorizado", status_code=403)

    def test_pagina_inexistente_404(self, _):
        self.assertEqual(self.client.get("/nao-existe/").status_code, 404)

    # --- cadastros
    def test_sala_nome_invalido_e_capacidade(self, _):
        r = self.client.post(reverse("salas_novo"), {"nome": "sala 1", "tipo": "sala", "capacidade": 0})
        self.assertContains(r, "Use o formato bloco-número")
        self.assertContains(r, "Não foi possível salvar a sala")

    def test_sala_duplicada(self, _):
        r = self.client.post(reverse("salas_novo"), {"nome": "C-101", "tipo": "sala", "capacidade": 30})
        self.assertContains(r, "Já existe uma sala com este nome.")

    def test_desativar_sala_nao_exclui(self, _):
        sala = m.Sala.objects.get(nome="E-310")
        self.client.post(reverse("salas_ativo", args=[sala.pk]))
        sala.refresh_from_db()
        self.assertFalse(sala.ativo)
        self.assertTrue(m.Sala.objects.filter(pk=sala.pk).exists())

    def test_semestre_datas_invertidas(self, _):
        r = self.client.post(reverse("semestres_novo"), {"nome": "2027/01", "ano": 2027, "data_inicio": "2027-06-01",
                                                         "data_fim": "2027-02-01", "slug": "2027-01", "ativo": "on"})
        self.assertContains(r, "A data de fim deve ser posterior à data de início.")

    def test_curso_slug_reservado(self, _):
        r = self.client.post(reverse("cursos_novo"), {"nome": "Teste", "slug": "t"})
        self.assertContains(r, "Este slug é reservado")

    def test_professor_com_choque_de_horario_na_grade(self, _):
        grade = self.ens.grade
        sergio = m.Professor.objects.get(slug="sergio")
        turma = m.Turma.objects.get(slug="111-3an")
        # Sergio já dá aula na segunda 18:55 (Turma 2ª fase); tentar outra aula no mesmo horário
        aula = m.Aula.objects.get(grade=grade, turma=turma, dia_semana=0, horario=1)
        f = forms.AulaForm({"turma": turma.pk, "dia_semana": 0, "horario": 1, "unidade": aula.unidade_id,
                            "professor": sergio.pk}, instance=aula, grade=grade)
        self.assertFalse(f.is_valid())
        self.assertIn("já tem aula neste horário", f.errors["professor"][0])

    def test_turma_com_duas_aulas_no_mesmo_horario(self, _):
        grade = self.ens.grade
        turma = m.Turma.objects.get(slug="111-1an")
        f = forms.AulaForm({"turma": turma.pk, "dia_semana": 0, "horario": 1, "unidade": m.UnidadeCurricular.objects.get(codigo="IHC").pk,
                            "professor": m.Professor.objects.get(slug="mel").pk}, grade=grade)
        self.assertFalse(f.is_valid())
        self.assertIn("Esta turma já tem aula neste dia e horário.", str(f.errors))

    # --- ensalamento
    def test_data_inicio_deve_ser_segunda(self, _):
        r = self.client.post(reverse("ensalamentos_novo"), {"grade": self.ens.grade_id, "nome": "x",
                                                            "data_inicio": "2026-11-11", "status": "rascunho", "ativo": "on"})
        self.assertContains(r, "A data de início deve ser uma segunda-feira.")

    def test_um_ensalamento_por_grade_por_semana(self, _):
        r = self.client.post(reverse("ensalamentos_novo"), {"grade": self.ens.grade_id, "nome": "x",
                                                            "data_inicio": self.segunda.isoformat(), "status": "rascunho", "ativo": "on"})
        self.assertContains(r, "Já existe ensalamento desta grade nesta semana.")

    def test_data_fim_e_sabado(self, _):
        self.assertEqual(self.ens.data_fim.weekday(), 5)

    def test_choque_de_sala_bloqueia(self, _):
        # Terça 20:50, Turma 1ª fase está sem sala; C-324 está com a Turma 2ª fase no mesmo horário
        aula = m.Aula.objects.get(grade=self.ens.grade, dia_semana=1, horario=2, turma__slug="111-1an")
        c324 = m.Sala.objects.get(nome="C-324")
        r = self.client.post(reverse("ensalamento_informar_sala", args=[self.ens.pk, aula.pk]), {"sala": c324.pk}, follow=True)
        self.assertContains(r, "já está ocupada neste horário")
        self.assertFalse(self.ens.alocacoes.filter(aula=aula).exists())

    def test_choque_com_outra_grade_na_mesma_semana(self, _):
        prox = self.segunda + timedelta(days=7)
        bes = m.Ensalamento.objects.get(grade__curso__slug="bes", data_inicio=prox)
        novo = m.Ensalamento.objects.create(grade=self.ens.grade, nome="x", data_inicio=prox)
        aula = m.Aula.objects.get(grade=self.ens.grade, dia_semana=1, horario=1, turma__slug="111-1an")
        choque = m.choque_de_sala(m.Sala.objects.get(nome="C-101"), novo, aula)
        self.assertIsNotNone(choque)
        self.assertEqual(choque.ensalamento, bes)

    def test_sala_pequena_apenas_avisa(self, _):
        aula = m.Aula.objects.get(grade=self.ens.grade, dia_semana=1, horario=2, turma__slug="111-1an")  # 38 alunos
        e216 = m.Sala.objects.get(nome="E-216")  # 24 lugares, livre neste horário
        r = self.client.post(reverse("ensalamento_informar_sala", args=[self.ens.pk, aula.pk]), {"sala": e216.pk}, follow=True)
        self.assertContains(r, "38 alunos para 24 lugares")
        self.assertTrue(self.ens.alocacoes.filter(aula=aula, sala=e216).exists())

    def test_situacao_das_salas(self, _):
        aula = m.Aula.objects.get(grade=self.ens.grade, dia_semana=1, horario=2, turma__slug="111-1an")
        sit = {s["sala"].nome: s["estado"] for s in services.situacao_salas(self.ens, aula)}
        self.assertEqual(sit["C-324"], "ocupada")
        self.assertEqual(sit["E-216"], "nao_comporta")
        self.assertEqual(sit["C-101"], "livre")

    def test_copia_pula_choques(self, _):
        prox = self.segunda + timedelta(days=7)
        novo, sim = services.copiar_ensalamento(self.ens, prox)
        self.assertEqual(len(sim["copiadas"]), 24)
        self.assertEqual(len(sim["choques"]), 2)
        self.assertEqual(sim["sem_sala"], 4)
        self.assertEqual(novo.alocacoes.count(), 24)
        self.assertEqual(novo.status, "rascunho")
        self.assertEqual(novo.nome, f"{prox:%d/%m} até {prox + timedelta(days=5):%d/%m}")

    def test_copia_exige_segunda(self, _):
        r = self.client.get(reverse("ensalamento_copiar_previa", args=[self.ens.pk]), {"data": "2026-11-25"})
        self.assertEqual(r.json(), {"ok": False, "erro": "A data de destino deve ser uma segunda-feira."})

    # --- página pública
    def test_publico_curso_hoje(self, _):
        r = self.client.get("/p/bsi/")
        self.assertContains(r, "Quarta-feira, 18/11/2026")
        self.assertContains(r, "MATD")

    def test_publico_feriado(self, _):
        with mock.patch("django.utils.timezone.localdate", return_value=date(2026, 11, 20)):
            r = self.client.get("/p/t/111-2an/")
        self.assertContains(r, "Dia da Consciência Negra")
        self.assertContains(r, "O ensalamento não é exibido em feriados")

    def test_eventos_so_para_professor(self, _):
        evento = "Último dia para publicação das notas do bimestre"
        self.assertContains(self.client.get("/p/p/sergio/"), evento)
        self.assertNotContains(self.client.get("/p/bsi/"), evento)
        self.assertNotContains(self.client.get("/p/t/111-2an/?aba=semana"), evento)

    def test_rascunho_nao_aparece_no_publico(self, _):
        self.ens.status = m.Ensalamento.Status.RASCUNHO
        self.ens.save()
        self.assertContains(self.client.get("/p/bsi/"), "ainda não foi publicado")

    def test_publico_sem_login(self, _):
        self.client.logout()
        self.assertEqual(self.client.get("/p/p/sergio/?aba=semana").status_code, 200)
