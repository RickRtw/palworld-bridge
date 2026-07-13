"""Exportador PalSchema — converte conteudo da forja em mod PalSchema (JSON).

PROVADO IN-GAME (2026-07-13): renomear itens/pals (translations pt-BR) e editar
stats de rows existentes (DT_PalMonsterParameter) aplicam no jogo, sem crash.

Este exportador cobre os tipos da forja de forma SEGURA (edita rows existentes,
nao cria itens novos — que no build WinGDK podem crashar mundos):
  - boss / pal  -> stats em DT_PalMonsterParameter + nome (DT_PalNameText)
  - item        -> raridade em DT_ItemDataTable + nome (DT_ItemNameText)
  - equipment   -> stats/raridade em DT_ItemDataTable + nome (DT_ItemNameText)
  - title / map / class: nao sao conteudo PalSchema (titulo=save via title_injector;
    map=config do servidor; class=parte do pal).

Requer PalSchema >= 0.6.0. Idioma: gera pt-BR + en.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

LANGS = ["pt-BR", "en"]

# stats absolutos de boss por tier (proven format DT_PalMonsterParameter)
TIER_STATS = {
    1: {"HP": 1500, "MeleeAttack": 150, "ShotAttack": 150, "Defense": 120, "Rarity": 5},
    2: {"HP": 2500, "MeleeAttack": 220, "ShotAttack": 220, "Defense": 170, "Rarity": 6},
    3: {"HP": 4000, "MeleeAttack": 300, "ShotAttack": 300, "Defense": 220, "Rarity": 7},
    4: {"HP": 6000, "MeleeAttack": 420, "ShotAttack": 420, "Defense": 300, "Rarity": 9},
    5: {"HP": 9000, "MeleeAttack": 600, "ShotAttack": 600, "Defense": 400, "Rarity": 10},
}
# raridade da forja -> valor numerico de Rarity do jogo
RARITY_NUM = {"comum": 1, "incomum": 2, "raro": 3, "epico": 4,
              "lendario": 5, "mitico": 6, "unico": 6, "maldicao": 5}


def _core(base: str) -> str:
    return base.replace("BOSS_", "").replace("Boss_", "")


def boss_row_name(base_pal: str) -> str:
    return "Boss_" + _core(base_pal)


class ContentPack:
    """Acumula edicoes de varios itens de conteudo e escreve UM mod PalSchema."""

    def __init__(self, mod_name: str, description: str = "Conteudo do Grid"):
        self.mod_name = mod_name
        self.description = description
        self.pal_params: dict = {}        # DT_PalMonsterParameter
        self.item_data: dict = {}         # DT_ItemDataTable
        self.item_names: dict = {}        # ITEM_NAME_<id> -> nome
        self.pal_names: dict = {}         # PAL_NAME_<id> -> nome

    # ---- adicionar cada tipo ----
    def add_boss(self, boss: dict):
        row = boss_row_name(boss["base_pal"])
        self.pal_params[row] = dict(TIER_STATS.get(boss.get("tier", 3), TIER_STATS[3]))
        self.pal_names[_core(boss["base_pal"])] = boss["name"]
        self.pal_names[row] = boss["name"]

    def add_pal(self, pal: dict):
        core = _core(pal["base_pal"])
        ivs = pal.get("ivs", {})
        self.pal_params[core] = {
            "HP": 500 + ivs.get("hp", 50) * 20,
            "MeleeAttack": 100 + ivs.get("attack", 50) * 5,
            "ShotAttack": 100 + ivs.get("attack", 50) * 5,
            "Defense": 80 + ivs.get("defense", 50) * 4,
            "Rarity": RARITY_NUM.get(pal.get("rarity", "raro"), 3),
        }
        self.pal_names[core] = pal["name"]

    def add_item(self, item: dict):
        base = item["base_item"]
        self.item_data[base] = {
            "Rarity": RARITY_NUM.get(item.get("rarity", "raro"), 3),
            "Price": int(item.get("power", 10) * 100),
        }
        self.item_names[base] = f"{item['name']} ({item.get('rarity','')})"

    def add_equipment(self, equip: dict):
        base = equip["base_equip"]
        st = equip.get("stats", {})
        row = {"Rarity": RARITY_NUM.get(equip.get("rarity", "raro"), 3)}
        if equip.get("slot") == "arma":
            row["AttackValue"] = int(st.get("poder", 100))
        row["Durability"] = float(st.get("durabilidade", 100))
        self.item_data[base] = row
        self.item_names[base] = f"{equip['name']} ({equip.get('rarity','')})"

    # ---- escrever o mod ----
    def write(self, out_dir: str | Path) -> Path:
        root = Path(out_dir) / self.mod_name
        (root / "raw").mkdir(parents=True, exist_ok=True)

        (root / "metadata.json").write_text(json.dumps({
            "name": self.mod_name, "authors": ["Grid Central"],
            "description": self.description, "version": "1.0.0",
        }, indent=2, ensure_ascii=False), encoding="utf-8")

        if self.pal_params:
            (root / "raw" / "pal_params.json").write_text(
                json.dumps({"DT_PalMonsterParameter": self.pal_params}, indent=2, ensure_ascii=False),
                encoding="utf-8")
        if self.item_data:
            (root / "raw" / "item_data.json").write_text(
                json.dumps({"DT_ItemDataTable": self.item_data}, indent=2, ensure_ascii=False),
                encoding="utf-8")

        # nomes (traducoes) em cada idioma
        if self.item_names or self.pal_names:
            for lang in LANGS:
                d = root / "translations" / lang
                d.mkdir(parents=True, exist_ok=True)
                payload = {}
                if self.item_names:
                    payload["DT_ItemNameText"] = {f"ITEM_NAME_{k}": v for k, v in self.item_names.items()}
                if self.pal_names:
                    payload["DT_PalNameText"] = {f"PAL_NAME_{k}": v for k, v in self.pal_names.items()}
                (d / "grid_names.json").write_text(
                    json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
        return root


def pack_from_forge(items=None, equipment=None, bosses=None, pals=None,
                    mod_name="GridContentPack", out_dir=".") -> Path:
    """Monta um pack a partir de listas de conteudo gerado pela forja."""
    pack = ContentPack(mod_name)
    for b in (bosses or []):
        pack.add_boss(b)
    for p in (pals or []):
        pack.add_pal(p)
    for it in (items or []):
        pack.add_item(it)
    for eq in (equipment or []):
        pack.add_equipment(eq)
    return pack.write(out_dir)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--name", default="GridContentPack")
    ap.add_argument("--bosses", type=int, default=1)
    ap.add_argument("--items", type=int, default=2)
    ap.add_argument("--equipment", type=int, default=2)
    ap.add_argument("--pals", type=int, default=1)
    args = ap.parse_args()

    from .boss_generator import generate_boss
    from .item_generator import generate_item
    from .equipment_generator import generate_equipment
    from .pal_generator import generate_pal

    root = pack_from_forge(
        bosses=[generate_boss(tier=5) for _ in range(args.bosses)],
        items=[generate_item(floor="lendario") for _ in range(args.items)],
        equipment=[generate_equipment(floor="lendario") for _ in range(args.equipment)],
        pals=[generate_pal(floor="lendario") for _ in range(args.pals)],
        mod_name=args.name, out_dir=args.out,
    )
    print(f"content pack escrito em: {root}")
    for f in sorted(Path(root).rglob("*.json")):
        print("  ", f.relative_to(root))
    return 0


if __name__ == "__main__":
    sys.exit(main())
