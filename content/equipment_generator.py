"""Gerador de EQUIPAMENTOS unicos (armas, armaduras, acessorios).

Varia equipamentos-base reais do Palworld com stats/afixos/raridade/nome + unique_id.
"""
from __future__ import annotations

from . import common as C

BASE_EQUIP = {
    "arma":      ["AssaultRifle", "HandGun", "Shotgun", "RocketLauncher",
                  "BowGun", "Sword_Common", "GrenadeLauncher"],
    "armadura":  ["PlayerEquipArmor_Cloth", "PlayerEquipArmor_Metal",
                  "PlayerEquipArmor_Refine", "PlayerEquipArmor_Dragon"],
    "acessorio": ["Accessory_HeatResist", "Accessory_ColdResist",
                  "Accessory_Movement", "Accessory_Damage"],
}

# afixos (encantamentos) que somam poder
AFFIXES = ["+Dano", "+Vida", "+Defesa", "+Velocidade", "+Peso", "+Sorte",
           "Resist. Fogo", "Resist. Gelo", "Roubo de Vida", "Critico",
           "Recarga Rapida", "Reducao de Dano"]


def generate_equipment(seed=None, slot=None, floor="raro", server_id=None) -> dict:
    r = C.rng(seed)
    slot = slot or r.choice(list(BASE_EQUIP))
    base = r.choice(BASE_EQUIP[slot])
    rarity = C.roll_rarity(r, floor=floor)
    ri = C.RARITIES.index(rarity)
    mult = C.RARITY_MULT[rarity]

    element = r.choice(C.ELEMENTS)
    name = f"{C.title(r)} {'Arma' if slot == 'arma' else 'Armadura' if slot == 'armadura' else 'Amuleto'}"

    base_stat = {"arma": 40, "armadura": 30, "acessorio": 15}[slot]
    stats = {
        "poder": round((base_stat + r.randint(0, 25)) * mult, 1),
        "durabilidade": int(100 * mult),
        "peso": round(max(0.5, 8 - ri) + r.random(), 1),
    }
    # nro de afixos cresce com a raridade
    n_affixes = 1 + ri
    affixes = r.sample(AFFIXES, k=min(n_affixes, len(AFFIXES)))
    uid = C.unique_id()

    return {
        "type": "equipment",
        "slot": slot,
        "base_equip": base,
        "unique_id": uid,
        "fingerprint": C.fingerprint(uid, base, name),
        "name": name,
        "rarity": rarity,
        "element": element,
        "stats": stats,
        "affixes": affixes,
        "tradeable_globally": ri >= C.RARITIES.index("raro"),
        **C.stamp(server_id),
    }
