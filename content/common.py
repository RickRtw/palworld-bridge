"""Base compartilhada dos geradores de conteudo (sem modelagem 3D).

Tudo aqui e "parametrico": varia o que o jogo JA tem (IDs reais do Palworld) —
stats, raridade, nome, classe. Cada peca gerada ganha um ID unico rastreavel que
encaixa na economia anti-duplicacao (dynamic_id / unique_id).
"""
from __future__ import annotations

import hashlib
import random
import time
import uuid

# ---- raridade: pesos e multiplicadores ----
RARITIES = ["comum", "incomum", "raro", "epico", "lendario", "mitico"]
RARITY_WEIGHT = [40, 28, 18, 9, 4, 1]          # sorteio ponderado
RARITY_MULT = {                                 # escala de poder por raridade
    "comum": 1.0, "incomum": 1.25, "raro": 1.6,
    "epico": 2.1, "lendario": 3.0, "mitico": 4.2,
}

# ---- pecas de nome (geram titulos unicos, PT-BR) ----
NAME_PREFIX = ["Rei", "Senhor", "Devorador", "Guardiao", "Arauto", "Tirano",
               "Colosso", "Profeta", "Algoz", "Ceifador", "Patriarca", "Oraculo"]
NAME_EPITETH = ["das Cinzas", "do Abismo", "da Tempestade", "Eterno", "Carmesim",
                "do Vazio", "das Sombras", "Ancestral", "da Ruina", "Imortal",
                "do Trovao", "da Aurora", "Sangrento", "do Alem", "de Ferro"]
ADJ = ["Flamejante", "Gelido", "Sombrio", "Radiante", "Corrompido", "Sagrado",
       "Venenoso", "Tempestuoso", "Espectral", "Dourado", "Primordial", "Selvagem"]

ELEMENTS = ["Fogo", "Gelo", "Raio", "Sombra", "Dragao", "Agua", "Terra", "Planta", "Neutro"]


def rng(seed=None):
    return random.Random(seed if seed is not None else time.time_ns())


def roll_rarity(r, floor=None):
    """Sorteia raridade ponderada. floor = raridade minima (ex: 'raro')."""
    rar = r.choices(RARITIES, weights=RARITY_WEIGHT, k=1)[0]
    if floor and RARITIES.index(rar) < RARITIES.index(floor):
        rar = floor
    return rar


def unique_id():
    return str(uuid.uuid4())


def fingerprint(*parts):
    return hashlib.sha1("".join(map(str, parts)).encode()).hexdigest()[:12]


def title(r, kind="epic"):
    """Gera um nome unico. kind: 'epic' (Prefixo X Epiteto) ou 'adj' (Adj X)."""
    if kind == "adj":
        return f"{r.choice(ADJ)}"
    return f"{r.choice(NAME_PREFIX)} {r.choice(NAME_EPITETH)}"


def stamp(server_id=None):
    """Metadados comuns de cunhagem (quem/quando)."""
    return {"minted_by": server_id or "central", "minted_at": time.time()}
