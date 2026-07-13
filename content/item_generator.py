"""Gerador de ITENS unicos (consumiveis, materiais, reliquias).

Varia itens-base reais do Palworld com raridade/atributos/nome + unique_id.
Itens de raridade >= 'raro' viram "unicos" rastreados na economia.
"""
from __future__ import annotations

from . import common as C

# itens-base reais do Palworld (static_id) por categoria
BASE_ITEMS = {
    "consumivel": ["SkillFruit_Random", "Medicine_HailBerry", "Nut_Muscle",
                   "PalDopingShot", "SkillCard", "StatusPoint_ReturnItem"],
    "material":   ["AncientCivilizationParts", "Ingot_High", "Cloth_High",
                   "Wood", "Paldium", "Coal", "Sulfur", "CarbonFiber"],
    "reliquia":   ["LegendarySchematic", "Relic_Ancient", "GoldCoin"],
}

# efeitos possiveis por categoria (rotulos de jogo)
ITEM_EFFECTS = {
    "consumivel": ["Cura", "Buff de Ataque", "Buff de Defesa", "Stamina", "XP Bonus", "Sorte"],
    "material":   ["Refino", "Craft Avancado", "Fortificacao"],
    "reliquia":   ["Bonus de Territorio", "Recurso Unico", "Chave de Dungeon"],
}


def generate_item(seed=None, category=None, floor="raro", server_id=None) -> dict:
    r = C.rng(seed)
    category = category or r.choice(list(BASE_ITEMS))
    base = r.choice(BASE_ITEMS[category])
    rarity = C.roll_rarity(r, floor=floor)
    mult = C.RARITY_MULT[rarity]

    name = f"{C.title(r)} — {base.replace('_', ' ')}"
    power = round((10 + r.randint(0, 20)) * mult, 1)
    effects = r.sample(ITEM_EFFECTS[category], k=min(1 + C.RARITIES.index(rarity) // 2,
                                                     len(ITEM_EFFECTS[category])))
    uid = C.unique_id()
    tradeable = C.RARITIES.index(rarity) >= C.RARITIES.index("raro")

    return {
        "type": "item",
        "category": category,
        "base_item": base,
        "unique_id": uid,
        "fingerprint": C.fingerprint(uid, base, name),
        "name": name,
        "rarity": rarity,
        "power": power,
        "effects": effects,
        "stack_max": 1 if tradeable else 999,
        "tradeable_globally": tradeable,   # so o que e raro+ entra na economia global
        **C.stamp(server_id),
    }
