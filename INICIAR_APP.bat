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

:: Verifica se as bibliotecas principais já estão instaladas
.\.venv\Scripts\python.exe -c "import PySide6, cv2, torch" >nul 2>&1
if %errorlevel% neq 0 (
    echo ======================================================
    echo  [ATENCAO] A instalacao das bibliotecas nao terminou!
    echo ======================================================
    echo  As dependencias de IA (PySide6, PyTorch, OpenCV) ainda
    echo  nao estao totalmente instaladas nesta pasta.
    echo.
    echo  O que fazer:
    echo  1. Feche esta janela.
    echo  2. De dois cliques em "INSTALAR_DEPENDENCIAS.bat".
    echo  3. Aguarde o download (~2.5 GB) ate aparecer:
    echo     "Instalacao concluida com sucesso!"
    echo ======================================================
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
