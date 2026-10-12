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

python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERRO] O Python nao foi encontrado no seu computador!
    echo.
    echo Por favor, baixe e instale o Python 3.11 ou 3.12 em:
    echo https://www.python.org/downloads/
    echo.
    echo ATENCAO: Durante a instalacao, marque a opcao:
    echo "[x] Add python.exe to PATH"
    echo.
    pause
    exit /b 1
)

echo [1/5] Criando ambiente virtual isolado (.venv)...
if not exist ".venv" (
    python -m venv .venv
)

echo [2/5] Atualizando gerenciador de pacotes...
call .\.venv\Scripts\python.exe -m pip install --upgrade pip

echo.
echo [3/5] Verificando placa de video NVIDIA para aceleracao GPU...
where nvidia-smi >nul 2>&1
if %errorlevel% equ 0 (
    echo Placa NVIDIA detectada. Baixando PyTorch com aceleracao GPU (CUDA 12.4)...
    echo (Aguarde o download da barra de progresso, cerca de 2.5 GB...)
    call .\.venv\Scripts\python.exe -m pip install torch torchvision --index-url https://download.pytorch.org/whl/cu124
) else (
    echo Nenhuma placa NVIDIA detectada. Baixando PyTorch otimizado para CPU...
    echo (Aguarde o download, cerca de 200 MB...)
    call .\.venv\Scripts\python.exe -m pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu
)

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
