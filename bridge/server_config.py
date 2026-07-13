"""Gerador do PalWorldSettings.ini a partir dos dados do dono do feudo.

Parte do fluxo de instalacao do servidor (feudo_installer). Le o
DefaultPalWorldSettings.ini que vem com o servidor e patcha as chaves
necessarias (nome, senhas, portas, REST/RCON) preservando o resto.

Feito pra ser config-driven: no futuro, mods/configs exclusivas vindas da
Central sao so mais chaves no dict `opts`.
"""
from __future__ import annotations

import re
from pathlib import Path


def _fmt(v) -> str:
    if isinstance(v, bool):
        return "True" if v else "False"
    if isinstance(v, (int, float)):
        return str(v)
    return f'"{v}"'  # string


def patch_option_settings(option_line: str, opts: dict) -> str:
    """Recebe a linha 'OptionSettings=(...)' e aplica opts (chave->valor).
    Substitui chaves existentes; acrescenta as que faltarem."""
    m = re.search(r"OptionSettings=\((.*)\)\s*$", option_line.strip())
    inner = m.group(1) if m else ""
    for key, val in opts.items():
        token = f"{key}={_fmt(val)}"
        # chave string: Key="..."  |  chave nao-string: Key=valor ate virgula/fim
        pat = re.compile(rf'(?<![A-Za-z0-9_]){re.escape(key)}=(?:"[^"]*"|[^,)]*)')
        if pat.search(inner):
            inner = pat.sub(token, inner, count=1)
        else:
            inner = inner + ("," if inner else "") + token
    return f"OptionSettings=({inner})"


def build_settings_text(default_ini_text: str, opts: dict) -> str:
    """Gera o texto final do PalWorldSettings.ini."""
    lines = default_ini_text.splitlines()
    out, patched = [], False
    for ln in lines:
        if ln.strip().startswith(";"):
            continue  # remove comentarios do Default
        if ln.strip().startswith("OptionSettings="):
            out.append(patch_option_settings(ln, opts))
            patched = True
        else:
            out.append(ln)
    if not patched:
        out.append("[/Script/Pal.PalGameWorldSettings]")
        out.append(patch_option_settings("OptionSettings=()", opts))
    return "\n".join(out).strip() + "\n"


# chaves default que todo feudo do grid precisa
GRID_REQUIRED = {
    "RESTAPIEnabled": True,
    "RCONEnabled": True,
    "RESTAPIPort": 8212,
    "RCONPort": 25575,
}


def write_server_settings(install_dir: str | Path, server_opts: dict) -> Path:
    """Escreve Pal/Saved/Config/WindowsServer/PalWorldSettings.ini.

    server_opts: ServerName, ServerDescription, AdminPassword, ServerPassword,
    PublicPort, ServerPlayerMaxNum, CoopPlayerMaxNum, etc.
    As chaves do grid (REST/RCON) sao forcadas.
    """
    install_dir = Path(install_dir)
    default_ini = install_dir / "DefaultPalWorldSettings.ini"
    base = default_ini.read_text(encoding="utf-8", errors="ignore") if default_ini.exists() \
        else "[/Script/Pal.PalGameWorldSettings]\nOptionSettings=()\n"

    opts = {**server_opts, **GRID_REQUIRED}
    text = build_settings_text(base, opts)

    cfg_dir = install_dir / "Pal" / "Saved" / "Config" / "WindowsServer"
    cfg_dir.mkdir(parents=True, exist_ok=True)
    dst = cfg_dir / "PalWorldSettings.ini"
    dst.write_text(text, encoding="utf-8")
    return dst
