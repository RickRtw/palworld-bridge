"""Exploracao: abre um .sav e imprime a arvore de chaves ate certa profundidade.
Uso: python explore_sav.py <caminho.sav> [profundidade]
"""
import sys
from palworld_save_tools.gvas import GvasFile
from palworld_save_tools.palsav import decompress_sav_to_gvas
from palworld_save_tools.paltypes import PALWORLD_TYPE_HINTS, PALWORLD_CUSTOM_PROPERTIES


def load(path):
    with open(path, "rb") as f:
        raw, _ = decompress_sav_to_gvas(f.read())
    return GvasFile.read(raw, PALWORLD_TYPE_HINTS, PALWORLD_CUSTOM_PROPERTIES, allow_nan=True)


def walk(node, depth, maxd, prefix=""):
    if depth > maxd:
        return
    if isinstance(node, dict):
        for k, v in node.items():
            t = type(v).__name__
            hint = ""
            if isinstance(v, (str, int, float, bool)):
                hint = f" = {v!r}"
            elif isinstance(v, list):
                hint = f" [list len={len(v)}]"
            print(f"{prefix}{k}: {t}{hint}")
            walk(v, depth + 1, maxd, prefix + "  ")
    elif isinstance(node, list) and node:
        print(f"{prefix}[0] amostra:")
        walk(node[0], depth + 1, maxd, prefix + "  ")


if __name__ == "__main__":
    path = sys.argv[1]
    maxd = int(sys.argv[2]) if len(sys.argv) > 2 else 4
    gvas = load(path)
    walk(gvas.properties, 0, maxd)
