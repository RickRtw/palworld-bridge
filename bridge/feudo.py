"""Fluxos do lado do feudo: montar o payload de sync e executar viagem.

Lê os saves locais (M2/M3b) e conversa com a API Central via CentralClient.
"""
from __future__ import annotations

import io
import contextlib

import orjson
from palworld_save_tools.json_tools import _orjson_default

from .savreader import load_gvas, write_gvas
from .saver import player_save_path, level_save_path
from .extractor import extract_player_state, INVENTORY_CONTAINERS, _uuid, _v
from .injector import inject_pal, backup_world
from .title_injector import apply_title
from .central_client import CentralClient


def _jsonable(node) -> dict:
    """Serializa um nó GVAS cru -> dict JSON-safe (UUID->str, bytes->base64)."""
    return orjson.loads(orjson.dumps(node, default=_orjson_default))


def _silent():
    return contextlib.redirect_stdout(io.StringIO())


def build_sync_payload(world_dir: str, player_id: str, server_id: str, strict: bool = False) -> dict:
    """Monta o corpo do POST /v1/sync a partir dos saves locais do feudo."""
    with _silent():
        state = extract_player_state(world_dir, player_id)
        g = load_gvas(level_save_path(world_dir))
        w = g.properties["worldSaveData"]["value"]
        by_iid = {str(e["key"]["InstanceId"]["value"]): e for e in w["CharacterSaveParameterMap"]["value"]}
        cc = {str(x["key"]["ID"]["value"]): x["value"] for x in w["CharacterContainerSaveData"]["value"]}
        ic = {str(x["key"]["ID"]["value"]): x["value"] for x in w["ItemContainerSaveData"]["value"]}
        psd = load_gvas(player_save_path(world_dir, player_id)).properties["SaveData"]["value"]
        otomo = _uuid(psd["OtomoCharacterContainerId"])
        palbox = _uuid(psd["PalStorageContainerId"])

    pals = []
    for cid in (otomo, palbox):
        for slot in cc[cid]["Slots"]["value"]["values"]:
            entry = by_iid.get(str(slot["RawData"]["value"]["instance_id"]))
            if not entry:
                continue
            sp = entry["value"]["RawData"]["value"]["object"]["SaveParameter"]["value"]
            if _v(sp.get("IsPlayer")):
                continue
            pals.append({
                "instance_id": str(entry["key"]["InstanceId"]["value"]),
                "character_id": _v(sp.get("CharacterID")),
                "level": _v(sp.get("Level")) or 1,
                "raw_node": _jsonable(entry),
            })

    items = []
    for key in INVENTORY_CONTAINERS:
        if key not in psd["InventoryInfo"]["value"]:
            continue
        cont = ic.get(_uuid(psd["InventoryInfo"]["value"][key]))
        if not cont:
            continue
        for slot in cont["Slots"]["value"]["values"]:
            rd = slot["RawData"]["value"]
            if not isinstance(rd, dict):
                continue
            dyn = rd.get("item", {}).get("dynamic_id", {})
            local = str(dyn.get("local_id_in_created_world", ""))
            if not local or local == "00000000-0000-0000-0000-000000000000":
                continue
            items.append({
                "created_world_id": str(dyn.get("created_world_id")),
                "local_id_in_created_world": local,
                "static_id": _v(rd["item"].get("static_id")),
            })

    a = state["attributes"]
    return {
        "server_id": server_id,
        "player_uid": state["player_id"],
        "nickname": a.get("nickname"),
        "level": a.get("level"),
        "exp": a.get("exp"),
        "payload": state,
        "pals": pals,
        "items": items,
        "strict": strict,
    }


def sync_to_central(client: CentralClient, world_dir: str, player_id: str, server_id: str) -> dict:
    """Logout: extrai o estado e envia pro Central."""
    return client.sync(build_sync_payload(world_dir, player_id, server_id))


def apply_pending_titles(client: CentralClient, world_dir: str, player_id: str) -> dict:
    """Aplica os títulos concedidos pela Central no save do player (buff + nome).
    ATENÇÃO: servidor Palworld deve estar PARADO (edita Level.sav). Faz backup.
    Fluxo: busca pendentes -> apply_title -> confirma na Central."""
    pending = client.pending_titles(player_id)
    if not pending:
        return {"applied": 0}
    results = []
    first = True
    for p in pending:
        with _silent():
            rep = apply_title(world_dir, player_id, p["title"],
                              do_backup=first, show_on_name=True)
        client.title_applied(p["id"])
        results.append({"name": p["name"], "buffs": rep["applied"],
                        "display": (rep.get("display") or {}).get("after"),
                        "ignored": rep["ignored"]})
        first = False
    return {"applied": len(results), "titles": results}


def travel_in(client: CentralClient, world_dir: str, player_id: str,
              from_server: str, to_server: str) -> dict:
    """Chega no feudo destino: pega os Pals do Central, injeta no save local e confirma.
    Descobre palbox+guilda do player no mundo destino."""
    resp = client.travel(player_id, from_server, to_server)
    pals = resp.get("pals", [])
    if not pals:
        return {"injected": 0}
    with _silent():
        psd = load_gvas(player_save_path(world_dir, player_id)).properties["SaveData"]["value"]
        palbox = _uuid(psd["PalStorageContainerId"])
        g = load_gvas(level_save_path(world_dir))
        # guilda do player no destino
        guild = None
        puid = player_id.split("-")[0].lower()
        for e in g.properties["worldSaveData"]["value"]["GroupSaveDataMap"]["value"]:
            rd = e["value"].get("RawData", {}).get("value", {})
            if isinstance(rd, dict):
                for p in rd.get("players", []):
                    if str(p.get("player_uid", "")).lower().startswith(puid):
                        guild = str(rd.get("group_id"))
        backup_world(world_dir, tag="travel_in")
        injected = []
        for p in pals:
            res = inject_pal(g, p["raw_node"], player_id, palbox, guild)
            injected.append({"global_pal_id": p["global_pal_id"],
                             "new_instance_id": res["new_instance_id"]})
        write_gvas(g, level_save_path(world_dir))
    client.travel_confirm(to_server, injected)
    return {"injected": len(injected)}
