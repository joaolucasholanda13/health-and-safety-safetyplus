@echo off
setlocal EnableExtensions
chcp 65001 >nul
cd /d "%~dp0"
title Safety Plus - Diagnostico

echo ======================================================
echo             SAFETY PLUS - DIAGNOSTICO
echo ======================================================
echo.
echo Pasta atual:
echo %CD%
echo.

echo --- PYTHON ---
where py 2>nul
where python 2>nul
py -3 --version 2>nul
python --version 2>nul
for /f "delims=" %%P in ('py -3 -c "import sys; print(sys.executable)" 2^>nul') do echo Python real via py: %%P
for /f "delims=" %%P in ('python -c "import sys; print(sys.executable)" 2^>nul') do echo Python real via python: %%P

echo.
echo --- AMBIENTE LOCAL ---
if exist ".venv\Scripts\python.exe" (
  echo [OK] Modo .venv disponivel
  ".venv\Scripts\python.exe" --version
) else (
  echo [INFO] .venv nao disponivel
)
if exist ".runtime" (
  echo [OK] Modo alternativo .runtime disponivel
) else (
  echo [INFO] .runtime nao criado
)

echo.
echo --- PORTA 8000 ---
powershell -NoProfile -ExecutionPolicy Bypass -Command "$c=New-Object Net.Sockets.TcpClient; try{$c.Connect('127.0.0.1',8000); 'PORTA 8000: ABERTA'}catch{'PORTA 8000: FECHADA'}finally{$c.Close()}"

echo.
echo --- ARQUIVOS PRINCIPAIS ---
if exist "app\main.py" (echo [OK] app\main.py) else (echo [ERRO] app\main.py ausente)
if exist "requirements.txt" (echo [OK] requirements.txt) else (echo [ERRO] requirements.txt ausente)
if exist "requirements-vps.txt" (echo [OK] requirements-vps.txt - usado na VPS) else (echo [AVISO] requirements-vps.txt ausente)
if exist "storage" (echo [OK] storage) else (echo [AVISO] storage ainda nao criada)

echo.
echo Se a porta 8000 estiver FECHADA, execute INICIAR_TESTE_LOCAL.bat.
echo O novo inicializador tenta .venv e, se falhar, usa .runtime automaticamente.
echo.
pause
