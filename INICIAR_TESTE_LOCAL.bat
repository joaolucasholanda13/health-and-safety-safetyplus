@echo off
setlocal EnableExtensions EnableDelayedExpansion
chcp 65001 >nul
cd /d "%~dp0"
title Safety Plus - Servidor Local

cls
echo ======================================================
echo          SAFETY PLUS - TESTE LOCAL
echo ======================================================
echo.
echo Pasta do sistema:
echo %CD%
echo.

REM ======================================================
REM 1) Localiza um Python REAL (nao apenas o launcher/shim)
REM ======================================================
set "PY_EXE="
for /f "delims=" %%P in ('py -3 -c "import sys; print(sys.executable)" 2^>nul') do if not defined PY_EXE set "PY_EXE=%%P"
if not defined PY_EXE (
    for /f "delims=" %%P in ('python -c "import sys; print(sys.executable)" 2^>nul') do if not defined PY_EXE set "PY_EXE=%%P"
)
if not defined PY_EXE (
    for /f "delims=" %%P in ('python3 -c "import sys; print(sys.executable)" 2^>nul') do if not defined PY_EXE set "PY_EXE=%%P"
)

if not defined PY_EXE goto :erro_python
if not exist "%PY_EXE%" goto :erro_python

"%PY_EXE%" -c "import sys; raise SystemExit(0 if sys.version_info >= (3,11) else 1)" >nul 2>nul
if errorlevel 1 goto :erro_versao

echo [OK] Python encontrado:
echo      %PY_EXE%
"%PY_EXE%" --version

REM ======================================================
REM 2) Tenta .venv. Se o Windows/Python bloquear, usa .runtime
REM    local sem precisar de ambiente virtual.
REM ======================================================
set "PY_RUN="
set "RUNTIME_MODE="
set "VENV_LOG=%TEMP%\safety_plus_venv.log"

if exist ".venv\Scripts\python.exe" (
    set "PY_RUN=%CD%\.venv\Scripts\python.exe"
    set "RUNTIME_MODE=venv"
    goto :runtime_pronto
)

if exist ".venv" rmdir /s /q ".venv" >nul 2>nul

echo.
echo [1/4] Preparando ambiente do Safety Plus...
"%PY_EXE%" -m venv "%CD%\.venv" >"%VENV_LOG%" 2>&1

if exist ".venv\Scripts\python.exe" (
    set "PY_RUN=%CD%\.venv\Scripts\python.exe"
    set "RUNTIME_MODE=venv"
    echo [OK] Ambiente virtual criado.
    goto :runtime_pronto
)

echo [AVISO] O Windows nao conseguiu criar o .venv.
echo         O Safety Plus vai usar o modo local alternativo.
echo         Seus arquivos e banco NAO serao apagados.
if exist ".venv" rmdir /s /q ".venv" >nul 2>nul

set "RUNTIME_DIR=%CD%\.runtime"
if not exist "%RUNTIME_DIR%" mkdir "%RUNTIME_DIR%"
set "PYTHONPATH=%RUNTIME_DIR%;%CD%"
set "PY_RUN=%PY_EXE%"
set "RUNTIME_MODE=local"

:runtime_pronto
REM ======================================================
REM 3) Dependencias
REM ======================================================
echo.
echo [2/4] Verificando dependencias...

REM Verifica todos os requisitos e suas versoes, inclusive pacotes adicionados
REM depois que o ambiente foi criado. O pip fornece o parser de requirements.
set "DEPS_OK=1"
"%PY_RUN%" -c "import sys; from pathlib import Path; from importlib.metadata import version; from pip._vendor.packaging.requirements import Requirement; reqs=[Requirement(s.strip()) for s in Path(sys.argv[1]).read_text(encoding='utf-8-sig').splitlines() if s.strip() and not s.lstrip().startswith('#')]; raise SystemExit(0 if all((r.marker is not None and not r.marker.evaluate()) or r.specifier.contains(version(r.name),prereleases=True) for r in reqs) else 1)" "%CD%\requirements.txt" >nul 2>nul
if errorlevel 1 set "DEPS_OK=0"
"%PY_RUN%" -c "import fastapi,uvicorn,jinja2,sqlalchemy,multipart,fitz,psycopg,itsdangerous,cryptography,reportlab,pywebpush,qrcode,openpyxl" >nul 2>nul
if errorlevel 1 set "DEPS_OK=0"

if "%DEPS_OK%"=="0" (
    "%PY_RUN%" -m pip --version >nul 2>nul
    if errorlevel 1 "%PY_RUN%" -m ensurepip --upgrade
    if errorlevel 1 goto :erro_pip
    if /I "%RUNTIME_MODE%"=="venv" (
        "%PY_RUN%" -m pip install --disable-pip-version-check -r "%CD%\requirements.txt"
    ) else (
        "%PY_RUN%" -m pip install --disable-pip-version-check --upgrade --target "%CD%\.runtime" -r "%CD%\requirements.txt"
    )
    if errorlevel 1 goto :erro_pip
)

"%PY_RUN%" -m pip check
if errorlevel 1 goto :erro_pip
"%PY_RUN%" -c "import fastapi,uvicorn,jinja2,sqlalchemy,multipart,fitz,psycopg,itsdangerous,cryptography,reportlab,pywebpush,qrcode,openpyxl" >nul 2>nul
if errorlevel 1 goto :erro_pip

echo [OK] Dependencias prontas. Modo: %RUNTIME_MODE%

REM ======================================================
REM 4) Configuracao local
REM ======================================================
set "ADMIN_USER=admin"
set "ADMIN_PASSWORD=admin123"
set "ADMIN_NAME=Administrador"
set "APP_SECRET=teste-local-troque-em-producao"
set "SECURE_COOKIES=false"
set "DATABASE_URL=sqlite:///./storage/checklist_serena.db"

if not exist "%CD%\storage" mkdir "%CD%\storage"
if not exist "%CD%\storage\pdfs" mkdir "%CD%\storage\pdfs"
if not exist "%CD%\storage\signatures" mkdir "%CD%\storage\signatures"

echo.
echo [3/4] Preparando banco de dados...
"%PY_RUN%" -m app.init_db
if errorlevel 1 goto :erro_app

REM Se a porta ja estiver aberta, apenas abre o navegador
powershell -NoProfile -ExecutionPolicy Bypass -Command "$c=New-Object Net.Sockets.TcpClient; try{$c.Connect('127.0.0.1',8000); exit 0}catch{exit 1}finally{$c.Close()}" >nul 2>nul
if not errorlevel 1 (
    echo.
    echo [OK] O servidor ja esta em execucao.
    start "" "http://127.0.0.1:8000"
    echo.
    pause
    exit /b 0
)

echo.
echo [4/4] Iniciando servidor...
echo.
echo IMPORTANTE: esta janela agora sera a janela do servidor.
echo NAO feche enquanto estiver usando o sistema.
echo.
echo Login inicial:
echo   Usuario: admin
echo   Senha:   admin123
echo.
echo O navegador sera aberto automaticamente quando o servidor responder.
echo ======================================================
echo.

start "" /min powershell -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -Command "$ok=$false; for($i=0;$i -lt 60;$i++){try{$c=New-Object Net.Sockets.TcpClient; $c.Connect('127.0.0.1',8000); $c.Close(); $ok=$true; break}catch{Start-Sleep -Seconds 1}}; if($ok){Start-Process 'http://127.0.0.1:8000'}"

"%PY_RUN%" -m uvicorn app.main:app --host 127.0.0.1 --port 8000
set "RC=%ERRORLEVEL%"

echo.
if not "%RC%"=="0" (
    echo [ERRO] O servidor foi encerrado com codigo %RC%.
    echo Execute DIAGNOSTICO.bat e envie uma foto da tela se precisar.
) else (
    echo Servidor encerrado.
)
echo.
pause
exit /b %RC%

:erro_python
echo.
echo [ERRO] Nao foi encontrado um Python 3 funcional neste computador.
echo Instale Python 3.11 ou superior pelo site python.org e marque Add Python to PATH.
echo Depois execute este arquivo novamente.
echo.
pause
exit /b 1

:erro_versao
echo.
echo [ERRO] A versao do Python encontrada e antiga.
echo Instale Python 3.11 ou superior.
echo.
pause
exit /b 1

:erro_pip
echo.
echo [ERRO] Falha ao instalar as dependencias do Safety Plus.
echo Verifique a conexao com a internet e tente novamente.
echo Se continuar, execute DIAGNOSTICO.bat e envie uma foto da tela.
echo.
pause
exit /b 1

:erro_app
echo.
echo [ERRO] O banco de dados nao foi inicializado.
echo A mensagem acima mostra o motivo do erro.
echo.
pause
exit /b 1
