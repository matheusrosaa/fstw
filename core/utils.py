"""Funções auxiliares: dias, horários, semanas e cores."""
import math
from datetime import date, timedelta

DIAS = [(0, "Segunda-feira"), (1, "Terça-feira"), (2, "Quarta-feira"), (3, "Quinta-feira"), (4, "Sexta-feira")]
DIAS_CURTOS = ["Segunda", "Terça", "Quarta", "Quinta", "Sexta", "Sábado", "Domingo"]
DIAS_LONGOS = ["Segunda-feira", "Terça-feira", "Quarta-feira", "Quinta-feira", "Sexta-feira", "Sábado", "Domingo"]

HORARIOS = [(1, "18:55 – 20:35"), (2, "20:50 – 22:30")]
HORARIO_TEXTO = dict(HORARIOS)


def segunda_da_semana(d: date) -> date:
    """Segunda-feira da semana de `d`. No domingo, considera a semana seguinte."""
    if d.weekday() == 6:
        return d + timedelta(days=1)
    return d - timedelta(days=d.weekday())


def proxima_segunda(d: date) -> date:
    return d + timedelta(days=7 - d.weekday())


def nome_semana(inicio: date) -> str:
    fim = inicio + timedelta(days=5)
    return f"{inicio:%d/%m} até {fim:%d/%m}"


# --- cores: hex -> oklch (o DaisyUI 4 usa oklch nas variáveis de tema) ----

def _lin(c):
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def hex_para_oklch(hexcor: str) -> str:
    h = hexcor.lstrip("#")
    r, g, b = (_lin(int(h[i:i + 2], 16) / 255) for i in (0, 2, 4))
    l_ = 0.4122214708 * r + 0.5363325363 * g + 0.0514459929 * b
    m_ = 0.2119034982 * r + 0.6806995451 * g + 0.1073969566 * b
    s_ = 0.0883024619 * r + 0.2817188376 * g + 0.6299787005 * b
    l_, m_, s_ = (math.copysign(abs(v) ** (1 / 3), v) for v in (l_, m_, s_))
    L = 0.2104542553 * l_ + 0.7936177850 * m_ - 0.0040720468 * s_
    A = 1.9779984951 * l_ - 2.4285922050 * m_ + 0.4505937099 * s_
    B = 0.0259040371 * l_ + 0.7827717662 * m_ - 0.8086757660 * s_
    C = math.hypot(A, B)
    H = math.degrees(math.atan2(B, A)) % 360
    return f"{L * 100:.2f}% {C:.4f} {H:.2f}"
