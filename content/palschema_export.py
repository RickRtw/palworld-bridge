"""Exportador PalSchema — converte conteudo da forja em mod PalSchema (JSON).

PalSchema carrega arquivos de dados na inicializacao (nao crasha, e verificavel
pelo log [PS]). E o caminho robusto de distribuir conteudo unico pros feudos.

Estrutura gerada:
  <out>/<ModName>/metadata.json
  <out>/<ModName>/raw/<arquivo>.json   -> edita DT_PalMonsterParameter etc.

Edita a tabela DT_PalMonsterParameter. A versao boss/alpha de um Pal e a linha
"Boss_<Nome>" (ex: Boss_BlueDragon). Stats sao valores ABSOLUTOS.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# valores absolutos de stats por tier (boss fica forte de verdade)
TIER_STATS = {
    1: {"HP": 1500, "MeleeAttack": 150, "ShotAttack": 150, "Defense": 120, "Rarity": 5},
    2: {"HP": 2500, "MeleeAttack": 220, "ShotAttack": 220, "Defense": 170, "Rarity": 6},
    3: {"HP": 4000, "MeleeAttack": 300, "ShotAttack": 300, "Defense": 220, "Rarity": 7},
    4: {"HP": 6000, "MeleeAttack": 420, "ShotAttack": 420, "Defense": 300, "Rarity": 9},
    5: {"HP": 9000, "MeleeAttack": 600, "ShotAttack": 600, "Defense": 400, "Rarity": 10},
}


def boss_row_name(base_pal: str) -> str:
    """'BOSS_BlueDragon' / 'BlueDragon' -> 'Boss_BlueDragon' (linha alpha do jogo)."""
    core = base_pal.replace("BOSS_", "").replace("Boss_", "")
    return "Boss_" + core


# idiomas a gerar (o jogo usa a linguagem do sistema; pt-BR e o alvo, en de fallback).
# APRENDIZADO: traducao SO aplica se estiver na pasta do idioma ativo do jogo.
LANGS = ["pt-BR", "en"]


def write_item_names(root: Path, item_name_map: dict):
    """Renomeia itens (chave = ITEM_NAME_<ItemId>) em TODOS os idiomas de LANGS.
    Requer PalSchema >= 0.6.0. Verificavel abrindo o inventario."""
    payload = {"DT_ItemNameText": {f"ITEM_NAME_{iid}": name
                                   for iid, name in item_name_map.items()}}
    for lang in LANGS:
        d = root / "translations" / lang
        d.mkdir(parents=True, exist_ok=True)
        (d / "grid_names.json").write_text(
            json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def write_pal_names(root: Path, pal_name_map: dict):
    """Renomeia Pals (chave = PAL_NAME_<PalId>) em todos os idiomas."""
    payload = {"DT_PalNameText": {f"PAL_NAME_{pid}": name
                                  for pid, name in pal_name_map.items()}}
    for lang in LANGS:
        d = root / "translations" / lang
        d.mkdir(parents=True, exist_ok=True)
        (d / "grid_pal_names.json").write_text(
            json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def export_boss(boss: dict, out_dir: str | Path, mod_name: str | None = None) -> Path:
    mod_name = mod_name or ("GridBoss_" + boss["fingerprint"])
    root = Path(out_dir) / mod_name
    (root / "raw").mkdir(parents=True, exist_ok=True)

    # metadata
    (root / "metadata.json").write_text(json.dumps({
        "name": mod_name,
        "authors": ["Grid Central"],
        "description": f"Boss unico: {boss['name']}",
        "version": "1.0.0",
    }, indent=2, ensure_ascii=False), encoding="utf-8")

    # edit de stats na linha boss
    row = boss_row_name(boss["base_pal"])
    stats = TIER_STATS.get(boss.get("tier", 3), TIER_STATS[3])
    table_edit = {"DT_PalMonsterParameter": {row: dict(stats)}}
    (root / "raw" / "boss_stats.json").write_text(
        json.dumps(table_edit, indent=2, ensure_ascii=False), encoding="utf-8")

    # nome unico do boss (pt-BR + en), visivel no jogo
    core = boss["base_pal"].replace("BOSS_", "").replace("Boss_", "")
    write_pal_names(root, {core: boss["name"], row: boss["name"]})

    return root


def export_pal(pal: dict, out_dir: str | Path, mod_name: str | None = None) -> Path:
    """Exporta um Pal unico (variante buffada) como edit de DT_PalMonsterParameter."""
    mod_name = mod_name or ("GridPal_" + pal["fingerprint"])
    root = Path(out_dir) / mod_name
    (root / "raw").mkdir(parents=True, exist_ok=True)
    (root / "metadata.json").write_text(json.dumps({
        "name": mod_name, "authors": ["Grid Central"],
        "description": f"Pal unico: {pal['name']}", "version": "1.0.0",
    }, indent=2, ensure_ascii=False), encoding="utf-8")

    core = pal["base_pal"].replace("BOSS_", "").replace("Boss_", "")
    ivs = pal.get("ivs", {})
    edit = {"DT_PalMonsterParameter": {core: {
        "HP": 500 + ivs.get("hp", 50) * 20,
        "MeleeAttack": 100 + ivs.get("attack", 50) * 5,
        "ShotAttack": 100 + ivs.get("attack", 50) * 5,
        "Defense": 80 + ivs.get("defense", 50) * 4,
    }}}
    (root / "raw" / "pal_stats.json").write_text(
        json.dumps(edit, indent=2, ensure_ascii=False), encoding="utf-8")
    return root


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="BlueDragon", help="Pal base (ex: BlueDragon)")
    ap.add_argument("--tier", type=int, default=5)
    ap.add_argument("--out", required=True, help="pasta de saida (PalSchema/mods)")
    ap.add_argument("--name", default="", help="nome do mod")
    args = ap.parse_args()

    from .boss_generator import generate_boss
    boss = generate_boss(tier=args.tier)
    boss["base_pal"] = "BOSS_" + args.base  # forca o base pedido
    boss["name"] = f"Boss Teste {args.base} T{args.tier}"
    root = export_boss(boss, args.out, args.name or None)
    print(f"mod PalSchema escrito em: {root}")
    print("linha editada:", boss_row_name(boss["base_pal"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
