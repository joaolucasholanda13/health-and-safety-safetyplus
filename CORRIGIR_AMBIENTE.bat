@echo off
setlocal EnableExtensions
chcp 65001 >nul
cd /d "%~dp0"
title Safety Plus - Corrigir Ambiente

echo ======================================================
echo          SAFETY PLUS - CORRIGIR AMBIENTE
echo ======================================================
echo.
echo Este processo remove apenas os componentes Python locais:
echo   .venv e .runtime
echo.
echo Seus documentos, PDFs, assinaturas e banco em storage
echo NAO serao apagados.
echo.
pause

if exist ".venv" rmdir /s /q ".venv"
if exist ".runtime" rmdir /s /q ".runtime"

echo.
echo Componentes locais removidos.
echo O inicializador sera aberto novamente.
echo.
call INICIAR_TESTE_LOCAL.bat
