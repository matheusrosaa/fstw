from django.conf import settings

from .utils import hex_para_oklch


def tema(request):
    cores = settings.TEMA_CORES
    return {
        "tema": cores,
        "tema_primaria_oklch": hex_para_oklch(cores["primaria"]),
        "site_publico": settings.SITE_PUBLICO,
        "menu_cadastros": MENU_CADASTROS,
    }


MENU_CADASTROS = [
    ("salas", "door", "Salas"), ("professores", "user", "Professores"), ("cursos", "cap", "Cursos"),
    ("semestres", "cal", "Semestres"), ("calendario", "cal", "Calendário Acadêmico"), ("turmas", "users", "Turmas"),
    ("unidades", "book", "Unidades Curriculares"), ("grades", "grid", "Grades Horárias"),
]
