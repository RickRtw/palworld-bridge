"""Resolve o arquivo .sav de um player e forca/aguarda o Save no disco.

O nome do arquivo em Players/ e o PlayerUID em hex, sem hifens, uppercase,
com padding de zeros ate 32 chars. Ex: playerId "FA4200F8-0000-0000-0000-000000000000"
vira "FA4200F8000000000000000000000000.sav".
"""
from __future__ import annotations

import time
from pathlib import Path


def normalize_uid(player_id: str) -> str:
    """Converte o playerId da REST API no nome-base do arquivo .sav."""
    hexstr = player_id.replace("-", "").strip().upper()
    return hexstr.ljust(32, "0")[:32]


def player_save_path(world_dir: str, player_id: str) -> Path:
    return Path(world_dir) / "Players" / f"{normalize_uid(player_id)}.sav"


def level_save_path(world_dir: str) -> Path:
    return Path(world_dir) / "Level.sav"


def _mtime(p: Path) -> float:
    return p.stat().st_mtime if p.exists() else 0.0


def force_save_and_wait(rest_client, world_dir: str, player_id: str, timeout_secs: float) -> Path | None:
    """Dispara /save e espera o .sav do player mudar no disco.

    Retorna o Path do save atualizado, ou None se estourou o timeout.
    """
    save_file = player_save_path(world_dir, player_id)
    level_file = level_save_path(world_dir)
    before_player = _mtime(save_file)
    before_level = _mtime(level_file)

    rest_client.save()

    deadline = time.time() + timeout_secs
    while time.time() < deadline:
        if _mtime(save_file) > before_player or _mtime(level_file) > before_level:
            # pequeno respiro pra garantir que a escrita terminou
            time.sleep(1.0)
            return save_file if save_file.exists() else None
        time.sleep(1.0)
    return save_file if save_file.exists() else None
