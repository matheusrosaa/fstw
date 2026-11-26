#!/usr/bin/env bash
# Cria o ambiente, instala, carrega dados de exemplo e inicia o sistema.
set -e
cd "$(dirname "$0")"
PY=$(command -v python3 || command -v python || true)
[ -z "$PY" ] && { echo "Python 3.11+ nao encontrado. Instale em https://www.python.org/downloads/"; exit 1; }
[ -d .venv ] || "$PY" -m venv .venv
source .venv/bin/activate
python -m pip install -q -r requirements.txt
python manage.py migrate --noinput
if [ ! -f .populado ]; then python manage.py popular_exemplo && touch .populado; fi
echo "Abra http://127.0.0.1:8000  (usuario: admin  senha: univille2026)"
python manage.py runserver
