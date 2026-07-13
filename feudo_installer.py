"""Instalador completo do feudo (chamado pelo setup_feudo.bat).

Faz TUDO na máquina do clã:
  1. pergunta os dados do servidor + do grid
  2. baixa o SteamCMD e instala o Palworld Dedicated Server
  3. escreve o PalWorldSettings.ini (nome/senhas/portas + REST/RCON)
  4. sobe o servidor e espera o save aparecer
  5. escreve o config.json do bridge e registra o feudo na Central

Rodar dentro do venv do bridge (com deps instaladas). Requer internet.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
import urllib.request
import zipfile
from pathlib import Path

HERE = Path(__file__).parent
STEAMCMD_URL = "https://steamcdn-a.akamaihd.net/client/installer/steamcmd.zip"
PALWORLD_APPID = "2394010"
CENTRAL_URL_DEFAULT = "http://d11k35y3n9lwh44dsticgbgu.178.18.251.2.sslip.io"


def ask(label, default=""):
    sfx = f" [{default}]" if default else ""
    v = input(f"  {label}{sfx}: ").strip()
    return v or default


def download(url, dst: Path):
    print(f"  baixando {url} ...")
    urllib.request.urlretrieve(url, dst)


def install_steamcmd(base: Path) -> Path:
    scmd_dir = base / "steamcmd"
    scmd = scmd_dir / "steamcmd.exe"
    if scmd.exists():
        print("  [ok] SteamCMD ja presente.")
        return scmd
    scmd_dir.mkdir(parents=True, exist_ok=True)
    zip_path = base / "steamcmd.zip"
    download(STEAMCMD_URL, zip_path)
    with zipfile.ZipFile(zip_path) as z:
        z.extractall(scmd_dir)
    zip_path.unlink(missing_ok=True)
    print("  [ok] SteamCMD instalado.")
    return scmd


def install_server(scmd: Path, install_dir: Path):
    print("\n[..] Baixando/instalando o Palworld Dedicated Server via SteamCMD.")
    print("     Isso baixa VARIOS GB e pode demorar bastante. Aguarde...\n")
    cmd = [str(scmd), "+force_install_dir", str(install_dir),
           "+login", "anonymous", "+app_update", PALWORLD_APPID, "validate", "+quit"]
    subprocess.run(cmd, check=True)
    exe = install_dir / "PalServer.exe"
    if not exe.exists():
        raise SystemExit("[ERRO] PalServer.exe nao encontrado apos a instalacao.")
    print("  [ok] Servidor instalado.")


def start_server(install_dir: Path):
    exe = install_dir / "PalServer.exe"
    print("\n[..] Subindo o servidor pela 1a vez (gera o mundo)...")
    subprocess.Popen(
        [str(exe), "-useperfthreads", "-NoAsyncLoadingThread", "-UseMultithreadForDS"],
        cwd=str(install_dir),
    )


def wait_for_world(install_dir: Path, timeout=300) -> Path | None:
    base = install_dir / "Pal" / "Saved" / "SaveGames" / "0"
    print("[..] Esperando o servidor criar o mundo (ate 5 min)...")
    deadline = time.time() + timeout
    while time.time() < deadline:
        if base.exists():
            worlds = [d for d in base.iterdir() if d.is_dir() and (d / "Level.sav").exists()]
            if worlds:
                worlds.sort(key=lambda p: (p / "Level.sav").stat().st_mtime, reverse=True)
                print(f"  [ok] mundo criado: {worlds[0].name}")
                return worlds[0]
        time.sleep(5)
    return None


def main() -> int:
    print("=" * 60)
    print("   INSTALADOR DO FEUDO — Palworld Grid")
    print("=" * 60)

    print("\n--- Dados do servidor ---")
    install_dir = Path(ask("Pasta de instalacao do servidor", r"C:\PalworldServer"))
    server_name = ask("Nome do servidor", "Feudo do Cla")
    server_desc = ask("Descricao (opcional)", "")
    admin_pw = ask("Senha de ADMIN (obrigatoria)", "")
    while not admin_pw:
        admin_pw = ask("Senha de ADMIN (obrigatoria)", "")
    server_pw = ask("Senha de entrada dos players (vazio = aberto)", "")
    public_port = int(ask("Porta publica do jogo", "8211") or "8211")
    max_players = int(ask("Max de players", "16") or "16")

    print("\n--- Dados do grid (Central) ---")
    server_id = ask("ID unico do feudo (ex: feudo_mizu)", "")
    while not server_id:
        server_id = ask("ID unico do feudo (ex: feudo_mizu)", "")
    owner = ask("Nome do cla", "Cla")
    central_url = ask("URL da Central", CENTRAL_URL_DEFAULT)
    token = os.environ.get("CENTRAL_API_TOKEN") or ask("Token da API central", "")
    while not token:
        token = ask("Token da API central", "")

    install_dir.mkdir(parents=True, exist_ok=True)

    # 1) SteamCMD + servidor
    scmd = install_steamcmd(install_dir)
    install_server(scmd, install_dir)

    # 2) config do servidor
    from bridge.server_config import write_server_settings
    ini = write_server_settings(install_dir, {
        "ServerName": server_name,
        "ServerDescription": server_desc,
        "AdminPassword": admin_pw,
        "ServerPassword": server_pw,
        "PublicPort": public_port,
        "ServerPlayerMaxNum": max_players,
        "CoopPlayerMaxNum": max_players,
    })
    print(f"  [ok] config do servidor: {ini}")

    # 3) sobe e espera o mundo
    start_server(install_dir)
    world = wait_for_world(install_dir)
    if not world:
        print("[aviso] o mundo ainda nao apareceu. O servidor pode estar baixando/abrindo.")
        print("        Rode depois:  python feudo_cli.py register  e  sync <uid>")
        return 0

    # 4) config do bridge
    tpl = json.loads((HERE / "config.example.json").read_text(encoding="utf-8"))
    tpl["rest_api"]["password"] = admin_pw
    tpl["save"]["world_dir"] = str(world).replace("\\", "/")
    tpl["central"]["base_url"] = central_url
    tpl["central"]["server_id"] = server_id
    tpl["central"]["owner"] = owner
    (HERE / "config.json").write_text(json.dumps(tpl, indent=2, ensure_ascii=False), encoding="utf-8")
    (HERE / ".token").write_text(token, encoding="utf-8")
    print("  [ok] config.json do bridge escrito.")

    # 5) registra na Central
    print("\n[..] Registrando o feudo na Central...")
    from bridge.central_client import CentralClient
    c = CentralClient(central_url, token)
    if not c.health():
        print("[aviso] Central nao respondeu ao health. Verifique a URL/token.")
    else:
        print("  register:", c.register_server(server_id, owner, central_url))
        print("  stats   :", c.stats())

    print("\n" + "=" * 60)
    print("   FEUDO PRONTO E NO GRID!")
    print(f"   Servidor: {install_dir}\\PalServer.exe (ja rodando)")
    print("   Sincronizar um player:  python feudo_cli.py sync <PLAYER_UID>")
    print("=" * 60)
    return 0


if __name__ == "__main__":
    sys.exit(main())
