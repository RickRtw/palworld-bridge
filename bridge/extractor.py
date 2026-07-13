"""Extrator do estado completo de um player (Milestone 2).

Junta as duas fontes:
  - Players/<UID>.sav : IDs dos containers (inventario, party, Palbox) + tech/quests
  - Level.sav         : conteudo real (itens, Pals, stats) indexado por UUID

Saida: dict JSON-safe pronto pra persistir no DB global.
"""
from __future__ import annotations

from pathlib import Path

from .savreader import load_gvas
from .saver import player_save_path, level_save_path

# rotulos amigaveis dos containers de inventario do player
INVENTORY_CONTAINERS = {
    "CommonContainerId": "common",
    "EssentialContainerId": "essential",
    "WeaponLoadOutContainerId": "weapons",
    "PlayerEquipArmorContainerId": "armor",
    "FoodEquipContainerId": "food",
}


def _v(node):
    """Desembrulha recursivamente {'value': X} / {'values': [...]} e
    converte UUIDs/enums/bytes em str. Retorna algo JSON-safe."""
    if isinstance(node, dict):
        if "value" in node:
            return _v(node["value"])
        if "values" in node:
            return [_v(i) for i in node["values"]]
        return {k: _v(x) for k, x in node.items()}
    if isinstance(node, list):
        return [_v(i) for i in node]
    if isinstance(node, (str, int, float, bool)) or node is None:
        return node
    return str(node)  # UUID, enum, bytes, etc.


def _uuid(container_id_node) -> str:
    """De um *ContainerId (StructProperty) extrai o UUID interno como str."""
    return str(container_id_node["value"]["ID"]["value"])


_jsonsafe = _v


class WorldIndex:
    """Carrega o Level.sav uma vez e indexa por UUID/InstanceId."""

    def __init__(self, world_dir: str):
        self.world_dir = world_dir
        g = load_gvas(level_save_path(world_dir))
        w = g.properties["worldSaveData"]["value"]
        self.item_containers = {
            str(e["key"]["ID"]["value"]): e["value"]
            for e in w["ItemContainerSaveData"]["value"]
        }
        self.char_containers = {
            str(e["key"]["ID"]["value"]): e["value"]
            for e in w["CharacterContainerSaveData"]["value"]
        }
        self.characters = {
            str(e["key"]["InstanceId"]["value"]): e["value"]
            for e in w["CharacterSaveParameterMap"]["value"]
        }

    # ---- itens ----
    def read_item_container(self, uuid: str) -> list[dict]:
        cont = self.item_containers.get(uuid)
        if not cont:
            return []
        out = []
        for slot in cont["Slots"]["value"]["values"]:
            rd = slot["RawData"]["value"]
            if not isinstance(rd, dict):
                continue
            item = rd.get("item", {})
            static_id = item.get("static_id", "None")
            if static_id in ("None", None) or rd.get("count", 0) == 0:
                continue
            out.append({
                "slot": rd.get("slot_index"),
                "static_id": static_id,
                "count": rd.get("count"),
                "dynamic_id": _jsonsafe(item.get("dynamic_id")),
            })
        return out

    # ---- Pals ----
    def read_pal(self, instance_id: str) -> dict | None:
        ch = self.characters.get(instance_id)
        if not ch:
            return None
        sp = ch["RawData"]["value"]["object"]["SaveParameter"]["value"]
        if _v(sp.get("IsPlayer")) is True:
            return None  # nao e Pal, e o proprio player
        return {
            "instance_id": instance_id,
            "character_id": _v(sp.get("CharacterID")),
            "gender": _v(sp.get("Gender")),
            "level": _v(sp.get("Level")) or 1,
            "exp": _v(sp.get("Exp")) or 0,
            "rank": _v(sp.get("Rank")) or 1,
            "rank_hp": _v(sp.get("Rank_HP")),
            "rank_attack": _v(sp.get("Rank_Attack")),
            "rank_defence": _v(sp.get("Rank_Defence")),
            "talent_hp": _v(sp.get("Talent_HP")),
            "talent_shot": _v(sp.get("Talent_Shot")),
            "talent_defense": _v(sp.get("Talent_Defense")),
            "moves": _jsonsafe(_v(sp.get("EquipWaza")) or []),
            "passives": _jsonsafe(_v(sp.get("PassiveSkillList")) or []),
            "owner_uid": _jsonsafe(_v(sp.get("OwnerPlayerUId"))),
            "friendship": _v(sp.get("FriendshipPoint")),
        }

    def read_pal_container(self, uuid: str) -> list[dict]:
        cont = self.char_containers.get(uuid)
        if not cont:
            return []
        out = []
        for slot in cont["Slots"]["value"]["values"]:
            rd = slot["RawData"]["value"]
            iid = str(rd.get("instance_id"))
            pal = self.read_pal(iid)
            if pal:
                pal["slot"] = rd.get("slot_index")
                out.append(pal)
        return out


def extract_player_state(world_dir: str, player_id: str, world: WorldIndex | None = None) -> dict:
    """Estado completo do player a partir do seu .sav + Level.sav."""
    world = world or WorldIndex(world_dir)
    g = load_gvas(player_save_path(world_dir, player_id))
    sd = g.properties["SaveData"]["value"]

    player_instance = str(sd["IndividualId"]["value"]["InstanceId"]["value"])
    pc = world.characters.get(player_instance, {})
    sp = pc.get("RawData", {}).get("value", {}).get("object", {}).get("SaveParameter", {}).get("value", {}) if pc else {}

    # inventario
    inv_info = sd["InventoryInfo"]["value"]
    inventory = {
        label: world.read_item_container(_uuid(inv_info[key]))
        for key, label in INVENTORY_CONTAINERS.items()
        if key in inv_info
    }

    # Pals: party (Otomo) + Palbox (storage)
    party = world.read_pal_container(_uuid(sd["OtomoCharacterContainerId"]))
    palbox = world.read_pal_container(_uuid(sd["PalStorageContainerId"]))

    return {
        "player_id": str(_v(sd.get("PlayerUId"))),
        "instance_id": player_instance,
        "attributes": {
            "nickname": _v(sp.get("NickName")),
            "level": _v(sp.get("Level")) or 1,
            "exp": _v(sp.get("Exp")) or 0,
            "full_stomach": _v(sp.get("FullStomach")),
            "status_points": _jsonsafe(_v(sp.get("GotStatusPointList")) or []),
            "ex_status_points": _jsonsafe(_v(sp.get("GotExStatusPointList")) or []),
        },
        "technology": {
            "points": _v(sd.get("TechnologyPoint")),
            "boss_points": _v(sd.get("bossTechnologyPoint")),
            "unlocked_recipes": _jsonsafe(_v(sd.get("UnlockedRecipeTechnologyNames")) or []),
        },
        "inventory": inventory,
        "pals": {"party": party, "palbox": palbox},
    }
