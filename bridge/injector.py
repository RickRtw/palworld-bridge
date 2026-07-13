"""Injeção inversa (Milestone 3): escreve estado de volta nos .sav do servidor.

REGRAS DE SEGURANÇA (não negociáveis):
  1. O servidor DEVE estar PARADO. O Palworld carrega o save no boot e
     sobrescreve no shutdown; escrever com ele no ar = perda de dados.
  2. SEMPRE fazer backup antes de escrever (backup_world).
  3. Escrevemos em PlZ (zlib) — o servidor 1.0 carrega por retrocompat.

Escopo atual (seguro): atributos escalares do player (tech points, level/exp).
Injeção de Pals cross-server (remapeamento de UUID) fica pra uma fase posterior.
"""
from __future__ import annotations

import copy
import shutil
import uuid as _uuid
from datetime import datetime
from pathlib import Path

from palworld_save_tools.archive import UUID

from .savreader import load_gvas, write_gvas
from .saver import player_save_path, level_save_path

ZERO_UUID = "00000000-0000-0000-0000-000000000000"


def _new_iid() -> UUID:
    return UUID.from_str(str(_uuid.uuid4()))


def backup_world(world_dir: str, tag: str = "inject") -> Path:
    """Copia Level.sav + Players/ pra uma pasta timestampada. Retorna o destino."""
    src = Path(world_dir)
    ts = datetime.now().strftime("%Y.%m.%d-%H.%M.%S")
    dst = src / "backup" / f"bridge_{tag}_{ts}"
    (dst / "Players").mkdir(parents=True, exist_ok=True)
    shutil.copy2(src / "Level.sav", dst / "Level.sav")
    for p in (src / "Players").glob("*.sav"):
        shutil.copy2(p, dst / "Players" / p.name)
    return dst


def _v(node):
    return node["value"] if isinstance(node, dict) and "value" in node else node


# ---- patches escalares no Player.sav ----

def set_tech_points(world_dir: str, player_id: str, points: int, boss_points: int | None = None) -> dict:
    """Ajusta TechnologyPoint (e opcionalmente bossTechnologyPoint) no Player.sav."""
    path = player_save_path(world_dir, player_id)
    g = load_gvas(path)
    sd = g.properties["SaveData"]["value"]
    before = _v(sd["TechnologyPoint"])
    sd["TechnologyPoint"]["value"] = points
    if boss_points is not None and "bossTechnologyPoint" in sd:
        sd["bossTechnologyPoint"]["value"] = boss_points
    write_gvas(g, path)
    return {"field": "TechnologyPoint", "before": before, "after": points}


# ---- patches no Level.sav (stats do personagem do player) ----

def _find_player_character(world_gvas, instance_id: str):
    w = world_gvas.properties["worldSaveData"]["value"]
    for e in w["CharacterSaveParameterMap"]["value"]:
        if str(e["key"]["InstanceId"]["value"]) == instance_id:
            return e["value"]["RawData"]["value"]["object"]["SaveParameter"]["value"]
    return None


def set_player_level(world_dir: str, instance_id: str, level: int, exp: int | None = None) -> dict:
    """Ajusta Level/Exp do personagem do player dentro do Level.sav."""
    path = level_save_path(world_dir)
    g = load_gvas(path)
    sp = _find_player_character(g, instance_id)
    if sp is None:
        raise ValueError(f"personagem {instance_id} nao encontrado no Level.sav")
    before = {"level": _v(_v(sp.get("Level"))), "exp": _v(sp.get("Exp"))}
    if "Level" in sp:
        # Level costuma vir aninhado {'value': {'value': N}}
        node = sp["Level"]
        if isinstance(node.get("value"), dict) and "value" in node["value"]:
            node["value"]["value"] = level
        else:
            node["value"] = level
    if exp is not None and "Exp" in sp:
        sp["Exp"]["value"] = exp
    write_gvas(g, path)
    return {"field": "Level/Exp", "before": before, "after": {"level": level, "exp": exp}}


# ---- injeção de Pal com remapeamento de UUID (M3b) ----

def inject_pal(world_gvas, source_entry, target_player_uid: str,
               target_palbox_uuid: str, guild_group_id: str) -> dict:
    """Insere um Pal (source_entry = entrada crua do CharacterSaveParameterMap)
    no Palbox de um player, gerando InstanceId NOVO e atualizando as 4 refs:
      1. CharacterSaveParameterMap  (nova entrada)
      2. SaveParameter.OwnerPlayerUId + SlotId (container+indice)
      3. CharacterContainerSaveData[palbox].Slots + reserva de indice
      4. GroupSaveDataMap[guild].individual_character_handle_ids
    Opera IN-PLACE no world_gvas. Retorna {new_instance_id, slot_index}.
    """
    w = world_gvas.properties["worldSaveData"]["value"]
    chars = w["CharacterSaveParameterMap"]["value"]
    cc = {str(x["key"]["ID"]["value"]): x["value"] for x in w["CharacterContainerSaveData"]["value"]}
    box = cc[target_palbox_uuid]

    new_iid = _new_iid()
    owner = UUID.from_str(target_player_uid)

    # indice livre no Palbox (Slots so guarda ocupados; capacidade = SlotNum)
    used = {s["SlotIndex"]["value"] for s in box["Slots"]["value"]["values"]}
    slotnum = box["SlotNum"]["value"]
    free = next(i for i in range(slotnum) if i not in used)

    # 1) clona a entrada e troca o InstanceId
    entry = copy.deepcopy(source_entry)
    entry["key"]["InstanceId"]["value"] = new_iid
    entry["key"]["PlayerUId"]["value"] = UUID.from_str(ZERO_UUID)
    rdv = entry["value"]["RawData"]["value"]
    rdv["group_id"] = UUID.from_str(guild_group_id)

    # 2) dono + SlotId apontando pro Palbox alvo
    sp = rdv["object"]["SaveParameter"]["value"]
    sp["OwnerPlayerUId"]["value"] = owner
    slotid = sp["SlotId"]["value"]
    slotid["ContainerId"]["value"]["ID"]["value"] = UUID.from_str(target_palbox_uuid)
    slotid["SlotIndex"]["value"] = free
    chars.append(entry)

    # 3) slot no container (copia estrutura de um slot existente)
    slot = copy.deepcopy(box["Slots"]["value"]["values"][0])
    slot["SlotIndex"]["value"] = free
    slot["RawData"]["value"]["player_uid"] = UUID.from_str(ZERO_UUID)
    slot["RawData"]["value"]["instance_id"] = new_iid
    box["Slots"]["value"]["values"].append(slot)

    # 4) handle na guilda
    for e in w["GroupSaveDataMap"]["value"]:
        rd = e["value"].get("RawData", {}).get("value", {})
        if isinstance(rd, dict) and str(rd.get("group_id")) == guild_group_id:
            rd["individual_character_handle_ids"].append({"guid": owner, "instance_id": new_iid})
            break

    return {"new_instance_id": str(new_iid), "slot_index": free}


def find_pal_entry(world_gvas, instance_id: str):
    """Acha a entrada crua de um Pal pelo InstanceId (pra usar como fonte)."""
    for e in world_gvas.properties["worldSaveData"]["value"]["CharacterSaveParameterMap"]["value"]:
        if str(e["key"]["InstanceId"]["value"]) == instance_id:
            return e
    return None


def revalidate_noop(world_dir: str) -> dict:
    """Reescreve Level.sav SEM alterar dados (decode->encode PlZ).

    Usado pra validar que o servidor aceita nosso formato de escrita, sem
    mexer em nada do jogo. Faz backup antes.
    """
    backup = backup_world(world_dir, tag="noop")
    path = level_save_path(world_dir)
    g = load_gvas(path)
    write_gvas(g, path)
    return {"backup": str(backup), "rewrote": str(path)}
