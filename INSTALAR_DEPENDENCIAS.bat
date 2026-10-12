@echo off
title Instalador do BovinoVision AI
cd /d "%~dp0"

echo ======================================================
echo       Instalacao de Dependencias - BovinoVision AI
echo ======================================================
echo.
echo [!] AVISO: As bibliotecas de Inteligencia Artificial (PyTorch)
echo     possuem cerca de 2.5 GB. O download costuma levar de 3 a 8 minutos.
echo.
echo     Por favor, NAO FECHE esta janela preta ate ver a mensagem:
echo     "Instalacao concluida com sucesso!"
echo ======================================================
echo.

set "PY_EXE="

:: 1. Tenta comando python direto no PATH
python --version >nul 2>&1
if %errorlevel% equ 0 set "PY_EXE=python"
if defined PY_EXE goto PYTHON_ENCONTRADO

:: 2. Tenta o Launcher oficial do Windows (py.exe)
py -3 --version >nul 2>&1
if %errorlevel% equ 0 set "PY_EXE=py -3"
if defined PY_EXE goto PYTHON_ENCONTRADO

:: 3. Procura automaticamente na pasta padrao do usuario (AppData\Local\Programs\Python)
for /d %%D in ("%LOCALAPPDATA%\Programs\Python\Python3*") do (
    if exist "%%D\python.exe" set "PY_EXE=%%D\python.exe"
)
if defined PY_EXE goto PYTHON_ENCONTRADO

:: 4. Procura em Program Files
for /d %%D in ("%ProgramFiles%\Python3*") do (
    if exist "%%D\python.exe" set "PY_EXE=%%D\python.exe"
)
if defined PY_EXE goto PYTHON_ENCONTRADO

echo ======================================================
echo [ERRO] O Python nao foi encontrado no seu computador!
echo ======================================================
echo.
echo O instalador do Python precisa que a opcao PATH esteja ativa.
echo.
echo Como resolver em 30 segundos:
echo 1. Abra novamente o instalador do Python que voce baixou.
echo 2. Clique em "Modify" (ou reinstale).
echo 3. Avance ate a tela que tem:
echo    "[x] Add Python to environment variables"
echo    e marque essa opcao!
echo.
echo Ou baixe em: https://www.python.org/downloads/
echo ======================================================
echo.
pause
exit /b 1

:PYTHON_ENCONTRADO
echo [OK] Python localizado com sucesso!
echo.

echo [1/5] Criando ambiente virtual isolado (.venv)...
if not exist ".venv" "%PY_EXE%" -m venv .venv

echo [2/5] Atualizando gerenciador de pacotes...
call .\.venv\Scripts\python.exe -m pip install --upgrade pip

echo.
echo [3/5] Verificando placa de video NVIDIA para aceleracao GPU...
where nvidia-smi >nul 2>&1
if %errorlevel% equ 0 goto COM_GPU
goto SEM_GPU

:COM_GPU
echo Placa NVIDIA detectada. Baixando PyTorch com aceleracao GPU CUDA 12.4...
echo Aguarde o download da barra de progresso, cerca de 2.5 GB...
call .\.venv\Scripts\python.exe -m pip install torch torchvision --index-url https://download.pytorch.org/whl/cu124
goto DEPOIS_TORCH

:SEM_GPU
echo Nenhuma placa NVIDIA detectada. Baixando PyTorch otimizado para CPU...
echo Aguarde o download, cerca de 200 MB...
call .\.venv\Scripts\python.exe -m pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu
goto DEPOIS_TORCH

:DEPOIS_TORCH
if %errorlevel% neq 0 (
    echo.
    echo [ERRO] Ocorreu uma falha ao baixar o PyTorch. Verifique sua conexao com a internet.
    pause
    exit /b 1
)

echo.
echo [4/5] Instalando bibliotecas do projeto (PySide6, OpenCV, Ultralytics)...
call .\.venv\Scripts\python.exe -m pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo.
    echo [ERRO] Falha ao instalar as dependencias complementares.
    pause
    exit /b 1
)

echo.
echo [5/5] Verificando modelos de Inteligencia Artificial...
if not exist "models\bovinos_aereo.pt" (
    echo Baixando modelo aereo especializado de bovinos...
    call .\.venv\Scripts\python.exe -c "import urllib.request, os; os.makedirs('models', exist_ok=True); urllib.request.urlretrieve('https://huggingface.co/nsagatov1/cattle-detection-yolov8/resolve/main/best.pt', 'models/bovinos_aereo.pt')"
    echo Modelo baixado com sucesso!
) else (
    echo Modelo aereo ja presente na pasta models/.
)

echo.
echo ======================================================
echo           Instalacao concluida com sucesso!
echo ======================================================
echo Agora voce ja pode abrir o aplicativo clicando em:
echo              "INICIAR_APP.bat"
echo ======================================================
echo.
pause
