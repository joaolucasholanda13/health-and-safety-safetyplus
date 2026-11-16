@echo off
setlocal EnableExtensions
chcp 65001 >nul
cd /d "%~dp0"
title Safety Plus - Servidor Direto

set "PY_RUN="
if exist ".venv\Scripts\python.exe" (
    set "PY_RUN=%CD%\.venv\Scripts\python.exe"
) else (
    set "PY_EXE="
    for /f "delims=" %%P in ('py -3 -c "import sys; print(sys.executable)" 2^>nul') do if not defined PY_EXE set "PY_EXE=%%P"
    if not defined PY_EXE for /f "delims=" %%P in ('python -c "import sys; print(sys.executable)" 2^>nul') do if not defined PY_EXE set "PY_EXE=%%P"
    if defined PY_EXE if exist ".runtime" (
        set "PYTHONPATH=%CD%\.runtime;%CD%"
        set "PY_RUN=%PY_EXE%"
    )
)

if not defined PY_RUN (
  echo [ERRO] Ambiente local ainda nao preparado.
  echo Execute primeiro INICIAR_TESTE_LOCAL.bat.
  echo.
  pause
  exit /b 1
)

set "ADMIN_USER=admin"
set "ADMIN_PASSWORD=admin123"
set "ADMIN_NAME=Administrador"
set "APP_SECRET=teste-local-troque-em-producao"
set "SECURE_COOKIES=false"
set "DATABASE_URL=sqlite:///./storage/checklist_serena.db"

start "" /min powershell -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -Command "$ok=$false; for($i=0;$i -lt 30;$i++){try{$c=New-Object Net.Sockets.TcpClient; $c.Connect('127.0.0.1',8000); $c.Close(); $ok=$true; break}catch{Start-Sleep -Seconds 1}}; if($ok){Start-Process 'http://127.0.0.1:8000'}"

"%PY_RUN%" -m uvicorn app.main:app --host 127.0.0.1 --port 8000
pause
