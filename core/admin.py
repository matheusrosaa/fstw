from django.contrib import admin

from . import models

for m in (models.Sala, models.Professor, models.Curso, models.Semestre, models.DataCalendario, models.Turma,
          models.UnidadeCurricular, models.GradeHoraria, models.Aula, models.Ensalamento, models.Alocacao):
    admin.site.register(m)

admin.site.site_header = "Ensalamento Univille – Administração"
