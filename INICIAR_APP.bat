@echo off
title BovinoVision AI
cd /d "%~dp0"

echo ======================================================
echo           Iniciando o BovinoVision AI
echo ======================================================
echo.

if not exist ".venv\Scripts\python.exe" goto SEM_VENV

.\.venv\Scripts\python.exe -c "import PySide6, cv2, torch" >nul 2>&1
if %errorlevel% neq 0 goto FALTAM_DEPENDENCIAS

goto RODAR

:SEM_VENV
echo [AVISO] O ambiente virtual Python .venv nao foi encontrado nesta pasta.
echo.
echo Por favor, execute primeiro o arquivo "INSTALAR_DEPENDENCIAS.bat".
echo.
pause
exit /b 1

:FALTAM_DEPENDENCIAS
echo ======================================================
echo  [ATENCAO] A instalacao das bibliotecas nao terminou!
echo ======================================================
echo  As dependencias de IA ainda nao estao instaladas.
echo.
echo  O que fazer:
echo  1. Feche esta janela.
echo  2. De dois cliques em "INSTALAR_DEPENDENCIAS.bat".
echo  3. Aguarde o download ate ver a mensagem de sucesso!
echo ======================================================
echo.
pause
exit /b 1

:RODAR
call .\.venv\Scripts\python.exe main.py
if %errorlevel% neq 0 (
    echo.
    echo Ocorreu um erro ao executar o BovinoVision AI.
    pause
)
