@echo off
title BovinoVision AI
cd /d "%~dp0"

echo ======================================================
echo           Iniciando o BovinoVision AI
echo ======================================================
echo.

if not exist ".venv\Scripts\python.exe" (
    echo [AVISO] O ambiente virtual Python (.venv) nao foi encontrado nesta pasta.
    echo.
    echo Por favor, execute primeiro o arquivo "INSTALAR_DEPENDENCIAS.bat".
    echo.
    pause
    exit /b 1
)

call .\.venv\Scripts\python.exe main.py
if %errorlevel% neq 0 (
    echo.
    echo Ocorreu um erro ao executar o BovinoVision AI.
    pause
)
