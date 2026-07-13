"""Gerador de TITULOS — buffs/debuffs com raridade, obtencao e requisitos.

Um titulo modifica atributos do jogador (buff e/ou debuff), tem uma raridade
(comum..unico + maldicao), uma FORMA de obtencao e REQUISITOS de conquista.
Maldicoes sao titulos de saldo negativo (risco/desafio).
"""
from __future__ import annotations

from . import common as C

# raridades proprias de titulo (inclui unico e maldicao)
TITLE_RARITIES = ["comum", "raro", "epico", "lendario", "unico", "maldicao"]
TITLE_WEIGHT = [45, 25, 15, 8, 4, 3]
# quanto poder de buff cada raridade concede
TITLE_POWER = {"comum": 1.0, "raro": 2.0, "epico": 3.5,
               "lendario": 5.0, "unico": 7.0, "maldicao": 4.0}

# atributos que um titulo pode modificar (rotulos de jogo)
STATS = ["Ataque", "Defesa", "Vida", "Stamina", "Velocidade", "Peso",
         "Sorte", "Captura de Pal", "XP", "Dano a Bosses", "Reducao de Dano",
         "Cura Recebida", "Velocidade de Craft", "Roubo de Vida"]

# como se GANHA um titulo (metodo de obtencao)
ACQUISITION = {
    "kill_boss":     "Derrotar um boss unico no Mundo Central",
    "pvp_streak":    "Vencer uma sequencia de duelos PvP",
    "clan_war":      "Vencer uma guerra de clas",
    "explore":       "Descobrir areas raras do Mundo Central",
    "collect":       "Colecionar um conjunto de itens unicos",
    "survive":       "Sobreviver a um evento de alto risco",
    "territory":     "Conquistar/defender territorio",
    "mint_event":    "Concedido pela organizacao em evento especial",
    "curse_trigger": "Ativado ao pegar um item/area amaldicoada",
}

# titulos-modelo por tema (nome + vies)
TITLE_THEMES = [
    ("Matador de Bosses", "kill_boss", ["Dano a Bosses", "Ataque"]),
    ("Senhor da Guerra", "clan_war", ["Ataque", "Reducao de Dano"]),
    ("Explorador Lendario", "explore", ["Velocidade", "Sorte"]),
    ("Guardiao do Territorio", "territory", ["Defesa", "Vida"]),
    ("Mestre Domador", "collect", ["Captura de Pal", "XP"]),
    ("Sobrevivente", "survive", ["Vida", "Cura Recebida"]),
    ("Duelista", "pvp_streak", ["Ataque", "Velocidade"]),
    ("Artesao Supremo", "collect", ["Velocidade de Craft", "Sorte"]),
]

# maldicoes: buff pequeno + debuff pesado (risco vs recompensa)
CURSE_THEMES = [
    ("Marca do Abismo", ["Dano a Bosses"], ["Vida", "Defesa"]),
    ("Fome Eterna", ["Ataque"], ["Stamina", "Cura Recebida"]),
    ("Peso das Sombras", ["Roubo de Vida"], ["Velocidade", "Peso"]),
    ("Pacto Sangrento", ["Ataque", "Roubo de Vida"], ["Vida"]),
]


def _mods(r, stats, power, sign=+1, spread=0.4):
    """Gera modificadores de atributo (%) para uma lista de stats.
    power ~1..7; escala pra faixas de jogo saudaveis (comum ~+5%, unico ~+35%)."""
    out = {}
    for s in stats:
        base = power * (2.0 + r.random() * spread * 4)   # ~ power*2..power*3.6
        out[s] = round(sign * base, 1)                   # em %
    return out


def _requirements(r, method, rarity):
    """Gera requisitos de conquista coerentes com o metodo e a raridade."""
    tough = C.RARITIES.index(rarity) if rarity in C.RARITIES else TITLE_RARITIES.index(rarity)
    n = 1 + tough
    table = {
        "kill_boss":  {"bosses_derrotados": 1 + tough * 2, "tier_minimo": min(5, 1 + tough)},
        "pvp_streak": {"vitorias_seguidas": 3 + tough * 3},
        "clan_war":   {"guerras_vencidas": 1 + tough},
        "explore":    {"areas_raras": 2 + tough * 2},
        "collect":    {"itens_unicos": 3 + tough * 2},
        "survive":    {"eventos_sobrevividos": 1 + tough},
        "territory":  {"territorios_mantidos_dias": 3 + tough * 4},
        "mint_event": {"concedido_por": "organizacao"},
        "curse_trigger": {"gatilho": "item_ou_area_amaldicoada"},
    }
    return table.get(method, {"acoes": n})


def generate_title(seed=None, force_rarity=None, server_id=None) -> dict:
    r = C.rng(seed)
    rarity = force_rarity or r.choices(TITLE_RARITIES, weights=TITLE_WEIGHT, k=1)[0]
    power = TITLE_POWER[rarity]

    if rarity == "maldicao":
        base_name, buff_stats, debuff_stats = r.choice(CURSE_THEMES)
        name = f"{base_name}"
        method = "curse_trigger"
        buffs = _mods(r, buff_stats, power * 0.8, sign=+1)
        debuffs = _mods(r, debuff_stats, power * 1.3, sign=-1)   # debuff domina
    else:
        base_name, method, buff_stats = r.choice(TITLE_THEMES)
        # titulos raros+ podem ter um pequeno debuff (trade-off)
        name = f"{base_name} {C.title(r)}" if rarity in ("lendario", "unico") else base_name
        buffs = _mods(r, buff_stats, power, sign=+1)
        debuffs = {}
        if C.RARITY_MULT.get(rarity, 1) and rarity in ("epico", "lendario", "unico") and r.random() < 0.4:
            debuffs = _mods(r, [r.choice([s for s in STATS if s not in buff_stats])], power * 0.5, sign=-1)

    return {
        "type": "title",
        "title_id": C.unique_id(),
        "name": name,
        "rarity": rarity,
        "is_curse": rarity == "maldicao",
        "buffs": buffs,          # {stat: +%}
        "debuffs": debuffs,      # {stat: -%}
        "acquisition_method": method,
        "acquisition_desc": ACQUISITION.get(method, "Conquista especial"),
        "requirements": _requirements(r, method, rarity),
        "tradeable_globally": rarity in ("lendario", "unico"),  # so os mais raros
        **C.stamp(server_id),
    }
