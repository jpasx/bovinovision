@echo off
chcp 65001 >nul
title BovinoVision - Publicar no GitHub

echo ========================================================
echo   🐄 BovinoVision AI - Publicando no GitHub (jpasx)
echo ========================================================
echo.

set "PATH=%LOCALAPPDATA%\Programs\Git\cmd;%PATH%"

echo 1. Verificando autenticação no GitHub...
gh auth status >nul 2>&1
if %errorlevel% neq 0 (
    echo.
    echo [INFO] Abrindo o navegador para conectar a sua conta do GitHub...
    echo Siga as instruções na tela do navegador para autorizar o acesso.
    echo.
    gh auth login --web -p https
    gh auth setup-git
)

echo.
echo 2. Enviando código para o repositório remoto:
echo    https://github.com/jpasx/bovinovision.git
echo.

git push -u origin main

if %errorlevel% equ 0 (
    echo.
    echo ========================================================
    echo   SUCESSO! O projeto foi publicado no GitHub!
    echo   Acesse: https://github.com/jpasx/bovinovision
    echo ========================================================
) else (
    echo.
    echo [ERRO] Ocorreu uma falha no envio. Verifique suas credenciais.
)

echo.
pause
