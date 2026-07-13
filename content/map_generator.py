"""Gerador de CONFIG DE MAPA por feudo (sem terreno novo).

Cada feudo = uma fatia/config unica do mapa existente: uma regiao, com spawns,
recursos e Pals LIMITADos, dificuldade e limites proprios. Isso reforca a regra
do jogo: o feudo nao sustenta o progresso completo -> obriga a ir ao Central.

Saida: um perfil de mundo aplicavel via config do servidor + regras do mod.
"""
from __future__ import annotations

from . import common as C

# regioes-tema (fatias do mapa base) — nome + bioma
REGIONS = [
    ("Planicie Inicial", "campo"), ("Floresta Umida", "floresta"),
    ("Deserto Rachado", "deserto"), ("Tundra Palida", "neve"),
    ("Pantano Sombrio", "pantano"), ("Colinas de Ferro", "montanha"),
    ("Litoral Quebrado", "praia"), ("Vale Vulcanico", "vulcao"),
]

# Pals iniciais permitidos por bioma (limitados — o resto so no Central)
BIOME_PALS = {
    "campo":    ["LeafMomonga", "ElecPomeranian", "WindHawk"],
    "floresta": ["GrassPanda", "LeafMomonga", "ShadowCat"],
    "deserto":  ["RockGolem", "FlameBuffalo", "RedArmorBird"],
    "neve":     ["IceDeer", "BirdDragon_Ice", "WaterLizard"],
    "pantano":  ["DarkCrow", "ShadowCat", "WaterLizard"],
    "montanha": ["RockGolem", "ThunderDog", "WindHawk"],
    "praia":    ["WaterLizard", "BlueDragon", "RedArmorBird"],
    "vulcao":   ["FlameBuffalo", "BlueDragon", "ThunderDog"],
}

# recursos-base por bioma (limitados)
BIOME_RESOURCES = {
    "campo":    ["Wood", "Stone", "Fiber", "RedBerry"],
    "floresta": ["Wood", "Fiber", "Honey", "Mushroom"],
    "deserto":  ["Stone", "Sulfur", "Sand", "Bone"],
    "neve":     ["Ice", "Wood", "Wool", "Stone"],
    "pantano":  ["Fiber", "Mushroom", "Bone", "Venom"],
    "montanha": ["Stone", "Ore", "Coal", "Crystal"],
    "praia":    ["Sand", "Shell", "Fiber", "Wood"],
    "vulcao":   ["Sulfur", "Ore", "Coal", "Obsidian"],
}


def generate_map(seed=None, server_id=None, difficulty=None) -> dict:
    r = C.rng(seed)
    region, biome = r.choice(REGIONS)
    difficulty = difficulty or r.choice(["facil", "normal", "dificil"])

    # LIMITES do feudo (o que forca o jogador a ir ao Central)
    diff_mult = {"facil": 0.8, "normal": 1.0, "dificil": 1.3}[difficulty]
    limits = {
        "nivel_maximo_local": int(35 * diff_mult),      # teto de progresso no feudo
        "recursos_por_no": round(1.0 * (2 - diff_mult), 2),  # rende menos no dificil
        "pals_capturaveis": BIOME_PALS[biome],           # so estes; raros so no Central
        "recursos_disponiveis": BIOME_RESOURCES[biome],  # limitados
        "bosses_locais": 0,                              # bosses unicos so no Central
        "dungeons_unicas": 0,
        "acesso_central": "portal",                      # como sai pro Central
    }

    # config aplicavel ao servidor (subset de PalWorldSettings + regras do mod)
    server_opts = {
        "ExpRate": round(0.8 * diff_mult, 2),
        "PalCaptureRate": round(1.2 / diff_mult, 2),
        "CollectionDropRate": round(limits["recursos_por_no"], 2),
        "EnemyDropItemRate": round(0.9 * diff_mult, 2),
        "DeathPenalty": "Item" if difficulty != "dificil" else "ItemAndEquipment",
    }

    return {
        "type": "map",
        "map_id": C.unique_id(),
        "region": region,
        "biome": biome,
        "difficulty": difficulty,
        "limits": limits,
        "server_opts": server_opts,
        "descricao": f"Feudo em {region} ({biome}). Progresso limitado ao nivel "
                     f"{limits['nivel_maximo_local']}; recursos e Pals restritos — "
                     f"avance ao Mundo Central pelo portal.",
        **C.stamp(server_id),
    }
