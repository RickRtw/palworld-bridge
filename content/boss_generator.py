"""Gerador de BOSS UNICO (sem modelagem 3D).

Cria um boss variando parametros de Pals que JA existem no jogo: espécie-base
(prefixo BOSS_ quando ha), escala, atributos, moveset, passivas, drops e nome.
Cada boss ganha um ID unico rastreavel (encaixa na economia anti-duplicacao).

Saida: um dict/JSON com a definicao do boss. Quem faz o boss APARECER no jogo e
o mod UE4SS (spawn_boss.lua), que le essa definicao.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import random
import sys
import time
import uuid
from pathlib import Path

# Especies-base com variante de boss no jogo (CharacterID reais do Palworld).
BASE_BOSSES = [
    "BOSS_BlueDragon", "BOSS_BirdDragon", "BOSS_BirdDragon_Ice",
    "BOSS_ThunderDragon", "BOSS_KingBahamut_Dragon", "BOSS_GrassPanda",
    "BOSS_DarkCrow", "BOSS_LilyQueen", "BOSS_HadesBird", "BOSS_VolcanicMonster",
    "BOSS_NightLady", "BOSS_SakuraSaurus", "BOSS_CatMage", "BOSS_WhiteTiger",
]

# temas de elemento -> movesets tipicos (EPalWazaID reais)
ELEMENT_THEMES = {
    "Fogo":    ["EPalWazaID::FlareTornado", "EPalWazaID::Flamethrower", "EPalWazaID::FireBall"],
    "Gelo":    ["EPalWazaID::IcicleThrow", "EPalWazaID::IceBlade", "EPalWazaID::BlizzardSpike"],
    "Raio":    ["EPalWazaID::LineLightning", "EPalWazaID::ThunderStrike", "EPalWazaID::ElecWave"],
    "Sombra":  ["EPalWazaID::ShadowBall", "EPalWazaID::DarkWave", "EPalWazaID::GhostFlame"],
    "Dragao":  ["EPalWazaID::DragonBreath", "EPalWazaID::DragonWave", "EPalWazaID::DragonCannon"],
    "Agua":    ["EPalWazaID::HydroPump", "EPalWazaID::AquaBurst", "EPalWazaID::BubbleShot"],
}

# passivas fortes (PassiveSkillList reais)
STRONG_PASSIVES = ["Legend", "PowerfulResistant_Up_2", "ElementBoost_Fire_2",
                   "Rare", "Deadly", "MusuoModel"]

# pedacos de nome pra gerar titulos unicos
PREFIX = ["Rei", "Senhor", "Devorador", "Guardiao", "Arauto", "Tirano", "Colosso", "Profeta"]
EPITETH = ["das Cinzas", "do Abismo", "da Tempestade", "Eterno", "Carmesim",
           "do Vazio", "das Sombras", "Ancestral", "da Ruina", "Imortal"]

# possiveis drops (static_id reais + slot pra item unico gerado)
COMMON_DROPS = ["Gold", "PalSphere_Master", "AncientCivilizationParts",
                "SkillFruit_Random", "Ingot_High", "LegendarySchematic"]


def _rng(seed=None):
    return random.Random(seed if seed is not None else time.time_ns())


def generate_boss(seed=None, tier=3, server_id=None) -> dict:
    """Gera um boss unico. tier 1..5 escala a dificuldade/recompensa."""
    r = _rng(seed)
    tier = max(1, min(5, tier))

    base = r.choice(BASE_BOSSES)
    element = r.choice(list(ELEMENT_THEMES))
    name = f"{r.choice(PREFIX)} {base.replace('BOSS_', '')} {r.choice(EPITETH)}"

    # atributos escalam com o tier
    level = 30 + tier * 12 + r.randint(0, 8)          # ~42..102
    hp_mult = round(2.0 + tier * 1.5 + r.random(), 2)  # vida inflada
    atk_mult = round(1.5 + tier * 0.8 + r.random(), 2)
    scale = round(1.4 + tier * 0.25 + r.random() * 0.3, 2)  # tamanho imponente

    moves = ELEMENT_THEMES[element][:]
    passives = r.sample(STRONG_PASSIVES, k=min(2 + tier // 2, len(STRONG_PASSIVES)))

    drops = r.sample(COMMON_DROPS, k=min(2 + tier, len(COMMON_DROPS)))
    # 1 item unico "cunhado" (entra na economia com dynamic_id)
    unique_item = {
        "static_id": "LegendaryBossDrop",
        "unique_id": str(uuid.uuid4()),
        "name": f"Reliquia de {name}",
        "rarity": "lendario",
    }

    boss_id = str(uuid.uuid4())
    fingerprint = hashlib.sha1(f"{boss_id}{base}{name}".encode()).hexdigest()[:12]

    return {
        "type": "boss",
        "boss_id": boss_id,
        "fingerprint": fingerprint,
        "name": name,
        "tier": tier,
        "element": element,
        "base_pal": base,
        "level": level,
        "scale": scale,
        "hp_multiplier": hp_mult,
        "attack_multiplier": atk_mult,
        "moves": moves,
        "passives": passives,
        "drops": drops,
        "unique_item": unique_item,
        "minted_by": server_id or "central",
        "minted_at": time.time(),
    }


def to_lua(boss: dict) -> str:
    """Emite a definicao do boss como tabela Lua (o mod UE4SS da require nisso)."""
    def lua_list(xs):
        return "{" + ", ".join(f'"{x}"' for x in xs) + "}"
    return (
        "-- gerado por boss_generator.py — NAO editar a mao\n"
        "return {\n"
        f'  boss_id = "{boss["boss_id"]}",\n'
        f'  name = "{boss["name"]}",\n'
        f'  base_pal = "{boss["base_pal"]}",\n'
        f'  level = {boss["level"]},\n'
        f'  scale = {boss["scale"]},\n'
        f'  hp_multiplier = {boss["hp_multiplier"]},\n'
        f'  attack_multiplier = {boss["attack_multiplier"]},\n'
        f'  moves = {lua_list(boss["moves"])},\n'
        f'  passives = {lua_list(boss["passives"])},\n'
        f'  drops = {lua_list(boss["drops"])},\n'
        "}\n"
    )


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tier", type=int, default=3)
    ap.add_argument("--seed", type=int, default=None)
    ap.add_argument("--server", default="central")
    ap.add_argument("--out", default="")
    ap.add_argument("--lua", default="", help="tambem emite a def em Lua nesse caminho")
    args = ap.parse_args()

    boss = generate_boss(seed=args.seed, tier=args.tier, server_id=args.server)
    text = json.dumps(boss, indent=2, ensure_ascii=False)
    if args.out:
        Path(args.out).write_text(text, encoding="utf-8")
        print(f"boss salvo em {args.out}")
    if args.lua:
        Path(args.lua).write_text(to_lua(boss), encoding="utf-8")
        print(f"def Lua salva em {args.lua}")
    print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
