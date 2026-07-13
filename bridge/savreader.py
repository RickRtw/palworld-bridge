"""Leitor de .sav do Palworld que entende os DOIS formatos de compressao:

  - PlZ  -> zlib          (saves antigos, <= 0.5)
  - PlM  -> Oodle Kraken  (saves 0.6+ e 1.0)  via lib open-source `ooz`

Retorna um GvasFile pronto pra navegar as properties.
"""
from __future__ import annotations

import zlib
from pathlib import Path

import ooz
from loguru import logger
from palworld_save_tools.gvas import GvasFile
from palworld_save_tools.paltypes import PALWORLD_TYPE_HINTS, PALWORLD_CUSTOM_PROPERTIES

# O fork loga em DEBUG via loguru; silencia o ruido do parser.
logger.disable("palworld_save_tools")

MAGIC_ZLIB = b"PlZ"
MAGIC_OODLE = b"PlM"


def decompress_sav(data: bytes) -> bytes:
    """Header (12 bytes): [unc_len u32][cmp_len u32][magic 3][type 1] + payload."""
    unc_len = int.from_bytes(data[0:4], "little")
    cmp_len = int.from_bytes(data[4:8], "little")
    magic = data[8:11]
    save_type = data[11]
    payload = data[12:]

    if magic == MAGIC_OODLE:
        raw = ooz.decompress(payload, unc_len)
        if len(raw) != unc_len:
            raise ValueError(f"Oodle: tamanho {len(raw)} != esperado {unc_len}")
        return raw

    if magic == MAGIC_ZLIB:
        raw = zlib.decompress(payload)
        if save_type == 0x32:  # zlib duplo
            raw = zlib.decompress(raw)
        return raw

    raise ValueError(f"magic desconhecido: {magic!r} (esperado PlZ ou PlM)")


def load_gvas(path: str | Path) -> GvasFile:
    data = Path(path).read_bytes()
    raw = decompress_sav(data)
    return GvasFile.read(raw, PALWORLD_TYPE_HINTS, PALWORLD_CUSTOM_PROPERTIES, allow_nan=True)


# --- escrita (M3) ---
# Nao conseguimos comprimir em Oodle (PlM) — o pyooz prebuilt so descomprime.
# Solucao: escrever em PlZ (zlib duplo, save_type 0x32). O servidor 1.0 carrega
# PlZ por retrocompatibilidade, igual aos conversores da comunidade.
from palworld_save_tools.palsav import compress_gvas_to_sav

PLZ_DOUBLE_ZLIB = 0x32


def write_gvas(gvas: GvasFile, path: str | Path, save_type: int = PLZ_DOUBLE_ZLIB) -> None:
    raw = gvas.write(PALWORLD_CUSTOM_PROPERTIES)
    sav = compress_gvas_to_sav(raw, save_type)
    Path(path).write_bytes(sav)
