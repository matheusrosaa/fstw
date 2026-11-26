from django.contrib.auth import views as auth_views
from django.contrib.auth.decorators import login_required
from django.urls import path
from django.views.generic import RedirectView

from .views import calendario, crud, ensalamento, grade, painel, publico
from .forms import SenhaForm

urlpatterns = [
    path("", RedirectView.as_view(pattern_name="dashboard", permanent=False)),
    path("login/", painel.Login.as_view(), name="login"),
    path("sair/", auth_views.LogoutView.as_view(), name="logout"),
    path("perfil/", login_required(auth_views.PasswordChangeView.as_view(template_name="registration/perfil.html", success_url="/perfil/?ok=1", form_class=SenhaForm)), name="perfil"),
    path("dashboard/", painel.dashboard, name="dashboard"),
    # grade horária e aulas
    path("grades/<int:pk>/", grade.grade_detalhe, name="grade_detalhe"),
    path("grades/<int:pk>/aulas/nova/", grade.aula_editar, name="aula_nova"),
    path("grades/<int:pk>/aulas/<int:aula_pk>/", grade.aula_editar, name="aula_editar"),
    path("grades/<int:pk>/aulas/<int:aula_pk>/excluir/", grade.aula_excluir, name="aula_excluir"),
    # ensalamento
    path("ensalamentos/<int:pk>/", ensalamento.ensalamento_detalhe, name="ensalamento_detalhe"),
    path("ensalamentos/<int:pk>/aulas/<int:aula_pk>/salas/", ensalamento.salas_da_aula, name="ensalamento_salas"),
    path("ensalamentos/<int:pk>/aulas/<int:aula_pk>/sala/", ensalamento.informar_sala, name="ensalamento_informar_sala"),
    path("ensalamentos/<int:pk>/copiar/previa/", ensalamento.copiar_previa, name="ensalamento_copiar_previa"),
    path("ensalamentos/<int:pk>/copiar/", ensalamento.copiar, name="ensalamento_copiar"),
    path("ensalamentos/<int:pk>/preview/", ensalamento.preview, name="ensalamento_preview"),
    # público (sem login)
    path("p/t/<slug:slug>/", publico.por_turma, name="publico_turma"),
    path("p/p/<slug:slug>/", publico.por_professor, name="publico_professor"),
    path("p/<slug:slug>/", publico.por_curso, name="publico_curso"),
]

for cad in crud.TODOS:
    urlpatterns += crud.rotas(cad, view_lista=calendario.calendario_lista.__wrapped__ if cad.chave == "calendario" else None)
