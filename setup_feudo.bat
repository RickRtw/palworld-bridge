@echo off
setlocal enabledelayedexpansion
chcp 65001 >nul
title Palworld Grid - Setup do Feudo
color 0A

echo ============================================================
echo    PALWORLD GRID - SETUP AUTOMATICO DO FEUDO
echo ============================================================
echo.

REM ---------- 1. Python 3.12 (instala se faltar) ----------
set "PY="
where python >nul 2>nul && set "PY=python"
REM ignora o alias "stub" da Microsoft Store (abre a loja e nao roda)
if defined PY ( python -c "import sys" >nul 2>nul || set "PY=" )

if not defined PY (
  echo [..] Python nao encontrado. Instalando Python 3.12 automaticamente...
  where winget >nul 2>nul
  if not errorlevel 1 (
    winget install -e --id Python.Python.3.12 --silent --accept-source-agreements --accept-package-agreements
  ) else (
    echo [..] winget indisponivel. Baixando o instalador oficial do Python...
    powershell -NoProfile -Command "try { Invoke-WebRequest -Uri 'https://www.python.org/ftp/python/3.12.8/python-3.12.8-amd64.exe' -OutFile '%TEMP%\python-3.12-amd64.exe' } catch { exit 1 }"
    if errorlevel 1 ( echo [ERRO] Falha ao baixar o Python. Instale manual em python.org e rode de novo. & pause & exit /b 1 )
    "%TEMP%\python-3.12-amd64.exe" /quiet InstallAllUsers=0 PrependPath=1 Include_test=0
  )
  REM o PATH nao atualiza na sessao atual: localiza o python recem-instalado
  where python >nul 2>nul && set "PY=python"
  if not defined PY if exist "%LOCALAPPDATA%\Programs\Python\Python312\python.exe" set "PY=%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
  if not defined PY if exist "%LOCALAPPDATA%\Programs\Python\Python313\python.exe" set "PY=%LOCALAPPDATA%\Programs\Python\Python313\python.exe"
  if not defined PY (
    echo [ERRO] Python foi instalado mas nao localizei o executavel.
    echo   FECHE esta janela e rode o setup_feudo.bat de novo (o PATH ja estara atualizado).
    pause
    exit /b 1
  )
)
echo [OK] Python: %PY%

REM ---------- 2. Git (necessario p/ o parser 1.0) ----------
where git >nul 2>nul
if errorlevel 1 (
  echo [..] Git nao encontrado. Tentando instalar via winget...
  winget install --id Git.Git -e --silent --accept-source-agreements --accept-package-agreements
  where git >nul 2>nul
  if errorlevel 1 (
    echo [ERRO] Nao consegui instalar o Git automaticamente.
    echo   Instale manualmente em https://git-scm.com/download/win e rode de novo.
    pause
    exit /b 1
  )
)
echo [OK] Git disponivel.

REM ---------- 3. Localizar / baixar o bridge ----------
set "SELFDIR=%~dp0"
if exist "%SELFDIR%bridge\central_client.py" (
  set "APPDIR=%SELFDIR%"
  echo [OK] Bridge ja presente nesta pasta.
) else (
  echo [..] Baixando o bridge do GitHub...
  set "ZIP=%TEMP%\palworld-bridge.zip"
  powershell -NoProfile -Command "try { Invoke-WebRequest -Uri 'https://github.com/RickRtw/palworld-bridge/archive/refs/heads/main.zip' -OutFile '%ZIP%' } catch { exit 1 }"
  if errorlevel 1 ( echo [ERRO] Falha ao baixar o repositorio. & pause & exit /b 1 )
  powershell -NoProfile -Command "Expand-Archive -Force '%ZIP%' '%SELFDIR%_bridge'"
  set "APPDIR=%SELFDIR%_bridge\palworld-bridge-main\"
  echo [OK] Bridge baixado.
)
cd /d "%APPDIR%"

REM ---------- 4. Ambiente + dependencias ----------
echo.
echo [..] Criando ambiente virtual e instalando dependencias...
echo      (a primeira vez pode demorar alguns minutos)
"%PY%" -m venv .venv
call ".venv\Scripts\activate.bat"
python -m pip install -q --upgrade pip
python -m pip install -q -r requirements.txt
if errorlevel 1 ( echo [ERRO] Falha ao instalar dependencias base. & pause & exit /b 1 )
python -m pip install -q --no-deps "git+https://github.com/oMaN-Rod/palworld-save-tools.git@main"
if errorlevel 1 ( echo [ERRO] Falha ao instalar o parser 1.0. & pause & exit /b 1 )
echo [OK] Dependencias instaladas.

REM ---------- 5. Instalador completo (servidor + config + grid) ----------
echo.
echo [..] Iniciando o instalador do feudo...
echo      (vai baixar o Palworld Dedicated Server via SteamCMD - VARIOS GB)
echo.
python feudo_installer.py
if errorlevel 1 ( echo [ERRO] O instalador do feudo falhou. Veja as mensagens acima. & pause & exit /b 1 )

echo.
pause
