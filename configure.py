"""Configurador automatico do feudo (chamado pelo setup_feudo.bat).

Faz o trabalho inteligente que .bat nao faz bem:
  - localiza a pasta do mundo (Pal/Saved/SaveGames/0/<hash>) automaticamente
  - le o AdminPassword do PalWorldSettings.ini
  - LIGA RESTAPIEnabled e RCONEnabled se estiverem desligados (avisa p/ reiniciar)
  - escreve o config.json final

Uso:
  python configure.py --server-folder "C:\\palworldserver" --server-id feudo_x --owner "ClanX"
Se --server-folder nao vier, tenta autodetectar em caminhos comuns.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).parent

COMMON_SERVER_DIRS = [
    r"C:\palworldserver",
    r"C:\steamcmd\steamapps\common\PalServer",
    r"C:\Program Files (x86)\Steam\steamapps\common\PalServer",
    r"C:\SteamLibrary\steamapps\common\PalServer",
]


def find_world_dirs(server_folder: Path) -> list[Path]:
    """Retorna as pastas de mundo (que contem Level.sav) sob o server_folder."""
    base = server_folder / "Pal" / "Saved" / "SaveGames" / "0"
    if not base.exists():
        # fallback: procura qualquer Level.sav
        return [p.parent for p in server_folder.rglob("Level.sav")]
    return [d for d in base.iterdir() if d.is_dir() and (d / "Level.sav").exists()]


def find_settings_ini(server_folder: Path) -> Path | None:
    cand = server_folder / "Pal" / "Saved" / "Config" / "WindowsServer" / "PalWorldSettings.ini"
    if cand.exists():
        return cand
    found = list(server_folder.rglob("PalWorldSettings.ini"))
    return found[0] if found else None


def read_and_fix_ini(ini_path: Path) -> tuple[str, bool]:
    """Le o AdminPassword e garante REST/RCON ligados. Retorna (senha, mexeu_no_arquivo)."""
    text = ini_path.read_text(encoding="utf-8", errors="ignore")
    m = re.search(r'AdminPassword="([^"]*)"', text)
    password = m.group(1) if m else ""

    changed = False
    for flag in ("RESTAPIEnabled", "RCONEnabled"):
        if re.search(rf"{flag}=False", text):
            text = text.replace(f"{flag}=False", f"{flag}=True")
            changed = True
    if changed:
        ini_path.write_text(text, encoding="utf-8")
    return password, changed


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--server-folder", default="")
    ap.add_argument("--server-id", required=True)
    ap.add_argument("--owner", required=True)
    ap.add_argument("--central-url", default="")
    args = ap.parse_args()

    # 1) localizar a pasta do servidor
    server_folder = Path(args.server_folder) if args.server_folder else None
    if not server_folder or not server_folder.exists():
        for c in COMMON_SERVER_DIRS:
            if Path(c).exists():
                server_folder = Path(c)
                print(f"[auto] servidor Palworld encontrado em: {server_folder}")
                break
    if not server_folder or not server_folder.exists():
        print("[ERRO] pasta do servidor Palworld nao encontrada. Passe --server-folder.")
        return 2

    # 2) localizar o mundo
    worlds = find_world_dirs(server_folder)
    if not worlds:
        print(f"[ERRO] nenhum Level.sav encontrado sob {server_folder}. O servidor ja rodou uma vez?")
        return 3
    if len(worlds) > 1:
        print("[aviso] varios mundos encontrados; usando o mais recente:")
        worlds.sort(key=lambda p: (p / "Level.sav").stat().st_mtime, reverse=True)
        for w in worlds:
            print("   -", w.name)
    world_dir = worlds[0]
    print(f"[ok] mundo: {world_dir}")

    # 3) ler ini + garantir REST/RCON
    ini = find_settings_ini(server_folder)
    password = ""
    if ini:
        password, changed = read_and_fix_ini(ini)
        print(f"[ok] PalWorldSettings.ini: {ini}")
        if changed:
            print("[IMPORTANTE] Liguei RESTAPIEnabled/RCONEnabled. REINICIE o servidor Palworld!")
        if not password:
            print("[aviso] AdminPassword vazio no ini — a REST API pode recusar auth.")
    else:
        print("[aviso] PalWorldSettings.ini nao encontrado; preencha a senha manualmente no config.json.")

    # 4) escrever config.json a partir do template
    tpl = json.loads((HERE / "config.example.json").read_text(encoding="utf-8"))
    tpl["rest_api"]["password"] = password
    tpl["save"]["world_dir"] = str(world_dir).replace("\\", "/")
    tpl["central"]["server_id"] = args.server_id
    tpl["central"]["owner"] = args.owner
    if args.central_url:
        tpl["central"]["base_url"] = args.central_url
    (HERE / "config.json").write_text(json.dumps(tpl, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"[ok] config.json escrito. server_id={args.server_id} owner={args.owner}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
