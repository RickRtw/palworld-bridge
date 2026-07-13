"""Gerador de PALS unicos (variantes de especies existentes) + CLASSES unicas.

Sem modelagem: varia especie-base real (cor/escala/atributos/skills/nome/classe).
Uma "classe unica" e um conjunto de bonus + titulo que define o arquetipo do Pal.
"""
from __future__ import annotations

from . import common as C

# especies-base reais do Palworld (CharacterID)
BASE_PALS = [
    "BirdDragon", "BirdDragon_Ice", "RedArmorBird", "LeafMomonga", "ElecPomeranian",
    "BlueDragon", "GrassPanda", "DarkCrow", "FlameBuffalo", "IceDeer",
    "ThunderDog", "WaterLizard", "RockGolem", "WindHawk", "ShadowCat",
]

# moves por elemento (EPalWazaID reais/plausiveis)
ELEMENT_MOVES = {
    "Fogo":  ["EPalWazaID::FlareTornado", "EPalWazaID::Flamethrower", "EPalWazaID::FireBall"],
    "Gelo":  ["EPalWazaID::IcicleThrow", "EPalWazaID::IceBlade", "EPalWazaID::BlizzardSpike"],
    "Raio":  ["EPalWazaID::LineLightning", "EPalWazaID::ThunderStrike", "EPalWazaID::ElecWave"],
    "Sombra":["EPalWazaID::ShadowBall", "EPalWazaID::DarkWave", "EPalWazaID::GhostFlame"],
    "Dragao":["EPalWazaID::DragonBreath", "EPalWazaID::DragonWave", "EPalWazaID::DragonCannon"],
    "Agua":  ["EPalWazaID::HydroPump", "EPalWazaID::AquaBurst", "EPalWazaID::BubbleShot"],
}
PASSIVES = ["Legend", "Rare", "Deadly", "PowerfulResistant_Up_2",
            "Swift", "ElementBoost_Fire_2", "Musou"]

# ---- classes unicas (arquetipos) ----
# cada classe = titulo + vies de atributo + tag de habilidade
CLASSES = {
    "Berserker":   {"atk": 1.6, "hp": 1.1, "def": 0.8, "tag": "furia_ao_perder_vida"},
    "Sentinela":   {"atk": 0.8, "hp": 1.5, "def": 1.7, "tag": "escudo_de_guilda"},
    "Arcano":      {"atk": 1.4, "hp": 0.9, "def": 0.9, "tag": "dano_elemental_x2"},
    "Cacador":     {"atk": 1.3, "hp": 1.0, "def": 1.0, "tag": "critico_aumentado"},
    "Curandeiro":  {"atk": 0.7, "hp": 1.3, "def": 1.2, "tag": "cura_aliados"},
    "Sombra":      {"atk": 1.5, "hp": 0.85, "def": 0.85, "tag": "furtividade"},
    "Colosso":     {"atk": 1.2, "hp": 1.8, "def": 1.4, "tag": "esmagar_estruturas"},
}


def generate_class(seed=None, server_id=None) -> dict:
    """Gera uma CLASSE unica (arquetipo) — pode ser usada solta ou dentro de um Pal."""
    r = C.rng(seed)
    cname = r.choice(list(CLASSES))
    spec = CLASSES[cname]
    return {
        "type": "class",
        "class_id": C.unique_id(),
        "class_name": cname,
        "title": f"{cname} {C.title(r)}",
        "atk_bias": spec["atk"],
        "hp_bias": spec["hp"],
        "def_bias": spec["def"],
        "ability_tag": spec["tag"],
    }


def generate_pal(seed=None, floor="raro", server_id=None) -> dict:
    r = C.rng(seed)
    base = r.choice(BASE_PALS)
    element = r.choice(list(ELEMENT_MOVES))
    rarity = C.roll_rarity(r, floor=floor)
    ri = C.RARITIES.index(rarity)
    mult = C.RARITY_MULT[rarity]

    cls = generate_class(seed=r.randint(0, 10**9))
    name = f"{C.ADJ[r.randrange(len(C.ADJ))]} {base} {C.title(r)}"

    # atributos base * raridade * vies de classe
    ivs = {
        "hp": min(100, int(50 * mult * cls["hp_bias"]) + r.randint(0, 20)),
        "attack": min(100, int(50 * mult * cls["atk_bias"]) + r.randint(0, 20)),
        "defense": min(100, int(50 * mult * cls["def_bias"]) + r.randint(0, 20)),
    }
    moves = ELEMENT_MOVES[element][:]
    passives = r.sample(PASSIVES, k=min(2 + ri // 2, len(PASSIVES)))
    scale = round(1.0 + ri * 0.15 + r.random() * 0.2, 2)

    uid = C.unique_id()
    return {
        "type": "pal",
        "base_pal": base,
        "unique_id": uid,
        "fingerprint": C.fingerprint(uid, base, name),
        "name": name,
        "rarity": rarity,
        "element": element,
        "class": cls,
        "scale": scale,
        "ivs": ivs,
        "moves": moves,
        "passives": passives,
        "tradeable_globally": ri >= C.RARITIES.index("raro"),
        **C.stamp(server_id),
    }
