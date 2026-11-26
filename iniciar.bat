@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo === Sistema de Ensalamento ===

where py >nul 2>nul && (set PY=py -3) || (where python >nul 2>nul && (set PY=python) || (
  echo Python nao encontrado. Instale em https://www.python.org/downloads/ marcando "Add python.exe to PATH" e rode este arquivo de novo.
  pause
  exit /b 1
))

if not exist .venv (
  echo Criando ambiente virtual...
  %PY% -m venv .venv || (echo Falha ao criar o ambiente virtual. & pause & exit /b 1)
)
call .venv\Scripts\activate.bat

echo Instalando dependencias...
python -m pip install -q -r requirements.txt || (echo Falha ao instalar. & pause & exit /b 1)

python manage.py migrate --noinput
if not exist db.sqlite3.populado (
  python manage.py popular_exemplo && echo ok> db.sqlite3.populado
)

echo.
echo Abrindo http://127.0.0.1:8000  (usuario: admin  senha: univille2026)
echo Para encerrar, feche esta janela ou pressione Ctrl+C.
start "" http://127.0.0.1:8000
python manage.py runserver
pause
