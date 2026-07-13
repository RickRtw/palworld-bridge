@echo off
setlocal enabledelayedexpansion
chcp 65001 >nul
title Palworld Grid - Setup do Feudo
color 0A

echo ============================================================
echo    PALWORLD GRID - SETUP AUTOMATICO DO FEUDO
echo ============================================================
echo.

REM ---------- 1. Python ----------
where python >nul 2>nul
if errorlevel 1 (
  echo [ERRO] Python nao encontrado.
  echo   Instale Python 3.10+ em https://www.python.org/downloads/
  echo   IMPORTANTE: marque "Add Python to PATH" durante a instalacao.
  echo.
  pause
  exit /b 1
)
echo [OK] Python encontrado.

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

REM ---------- 4. Perguntas ----------
echo.
echo ------------------------------------------------------------
echo    CONFIGURACAO DO SEU FEUDO
echo ------------------------------------------------------------
set "SERVERID="
set /p SERVERID=ID unico do feudo (ex: feudo_mizu):
set "OWNER="
set /p OWNER=Nome do seu cla:
set "TOKEN="
set /p TOKEN=Token da API central (peca ao admin):
set "SRVFOLDER="
set /p SRVFOLDER=Pasta do servidor Palworld [Enter = autodetectar]:

if "%SERVERID%"=="" ( echo [ERRO] ID do feudo obrigatorio. & pause & exit /b 1 )
if "%TOKEN%"=="" ( echo [ERRO] Token obrigatorio. & pause & exit /b 1 )

REM ---------- 5. Ambiente + dependencias ----------
echo.
echo [..] Criando ambiente virtual e instalando dependencias...
echo      (a primeira vez pode demorar alguns minutos)
python -m venv .venv
call ".venv\Scripts\activate.bat"
python -m pip install -q --upgrade pip
python -m pip install -q -r requirements.txt
if errorlevel 1 ( echo [ERRO] Falha ao instalar dependencias base. & pause & exit /b 1 )
python -m pip install -q --no-deps "git+https://github.com/oMaN-Rod/palworld-save-tools.git@main"
if errorlevel 1 ( echo [ERRO] Falha ao instalar o parser 1.0. & pause & exit /b 1 )
echo [OK] Dependencias instaladas.

REM ---------- 6. Token no ambiente (sessao + persistente + arquivo) ----------
set "CENTRAL_API_TOKEN=%TOKEN%"
setx CENTRAL_API_TOKEN "%TOKEN%" >nul
> ".token" echo %TOKEN%

REM ---------- 7. Configurar (detecta mundo, le ini, liga REST/RCON) ----------
echo.
echo [..] Detectando o mundo e escrevendo config.json...
if "%SRVFOLDER%"=="" (
  python configure.py --server-id "%SERVERID%" --owner "%OWNER%"
) else (
  python configure.py --server-folder "%SRVFOLDER%" --server-id "%SERVERID%" --owner "%OWNER%"
)
if errorlevel 1 ( echo [ERRO] Configuracao falhou. Veja as mensagens acima. & pause & exit /b 1 )

REM ---------- 8. Registrar no grid + status ----------
echo.
echo [..] Registrando o feudo na Central...
python feudo_cli.py register
python feudo_cli.py stats

echo.
echo ============================================================
echo    SETUP CONCLUIDO!
echo.
echo    Se o setup avisou p/ REINICIAR o servidor Palworld, faca isso.
echo.
echo    Para sincronizar um jogador (no logout dele):
echo       python feudo_cli.py sync ^<PLAYER_UID^>
echo    O PLAYER_UID e o nome do arquivo em Players\ (sem .sav)
echo ============================================================
echo.
pause
