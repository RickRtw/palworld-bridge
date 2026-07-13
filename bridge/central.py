"""Autoridade Central do grid (modelo edge NÃO-confiável).

Compõe o GlobalDB (ledger + custódia) com um registro de servidores e os
fluxos federados. Regra: NADA é real até o Central validar. O estado local
de um feudo é provisório; a custódia e a economia vivem aqui.
"""
from __future__ import annotations

import io
import contextlib
import time

from .globaldb import GlobalDB, DupeError, item_identity
from .savreader import load_gvas, write_gvas
from .saver import player_save_path, level_save_path
from .extractor import extract_player_state, INVENTORY_CONTAINERS, _uuid, _v
from .injector import inject_pal, backup_world


def _silent():
    return contextlib.redirect_stdout(io.StringIO())


def _player_container_and_guild(world_dir: str, player_id: str):
    """Do save do feudo destino: (palbox_uuid, guild_group_id) do player."""
    with _silent():
        psd = load_gvas(player_save_path(world_dir, player_id)).properties["SaveData"]["value"]
        palbox = _uuid(psd["PalStorageContainerId"])
        g = load_gvas(level_save_path(world_dir))
    guild = None
    puid = player_id.split("-")[0].lower()
    for e in g.properties["worldSaveData"]["value"]["GroupSaveDataMap"]["value"]:
        rd = e["value"].get("RawData", {}).get("value", {})
        if isinstance(rd, dict):
            for p in rd.get("players", []):
                if str(p.get("player_uid", "")).lower().startswith(puid):
                    guild = str(rd.get("group_id"))
    return palbox, guild


class CentralAuthority:
    def __init__(self, db_path: str = "central.db"):
        self.db = GlobalDB(db_path)
        self.db.db.execute("""CREATE TABLE IF NOT EXISTS servers(
            server_id TEXT PRIMARY KEY, owner TEXT, world_dir TEXT, registered_at REAL)""")
        self.db.db.commit()

    # ---- onboarding de feudo ----
    def register_server(self, server_id: str, owner: str, world_dir: str):
        self.db.db.execute(
            "INSERT INTO servers(server_id,owner,world_dir,registered_at) VALUES(?,?,?,?)"
            " ON CONFLICT(server_id) DO UPDATE SET owner=excluded.owner,world_dir=excluded.world_dir",
            (server_id, owner, world_dir, time.time()))
        self.db.db.commit()

    def servers(self) -> list[dict]:
        return [dict(r) for r in self.db.db.execute("SELECT * FROM servers").fetchall()]

    # ---- sync de um player vindo de um feudo (checkout no logout) ----
    def sync_player(self, server_id: str, world_dir: str, player_id: str, strict: bool = True) -> dict:
        """Extrai o estado do player naquele feudo e registra no central sob
        custódia do feudo. strict=True levanta DupeError no 1º conflito; strict=False
        COLETA as rejeições (útil pra flagrar um feudo trapaceiro sem abortar)."""
        rejections = []
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

        self.db.upsert_player(state, server_id)
        pals = 0
        for cid in (otomo, palbox):
            for slot in cc[cid]["Slots"]["value"]["values"]:
                entry = by_iid.get(str(slot["RawData"]["value"]["instance_id"]))
                if not entry:
                    continue
                sp = entry["value"]["RawData"]["value"]["object"]["SaveParameter"]["value"]
                if _v(sp.get("IsPlayer")):
                    continue
                try:
                    self.db.register_pal(entry, _v(sp.get("CharacterID")), _v(sp.get("Level")) or 1,
                                         player_id, server_id)
                    pals += 1
                except DupeError as e:
                    if strict:
                        raise
                    rejections.append(str(e))
        items = 0
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
                if item_identity(dyn) is None:
                    continue
                try:
                    self.db.register_item(dyn, _v(rd["item"].get("static_id")), player_id, server_id)
                    items += 1
                except DupeError as e:
                    if strict:
                        raise
                    rejections.append(str(e))
        return {"server": server_id, "pals": pals, "unique_items": items, "rejections": rejections}

    # ---- viagem entre feudos (handoff autoritativo) ----
    def travel(self, player_id: str, from_server: str, to_server: str, to_world_dir: str) -> dict:
        """Move os Pals do player de from_server -> to_server: aposenta as
        instâncias de origem, injeta no mundo destino com InstanceId novo e
        atualiza custódia. Faz backup do destino antes de escrever."""
        pals = self.db.pals_on_server(player_id, from_server)
        if not pals:
            return {"moved": 0, "note": "nenhum Pal sob custódia da origem"}
        palbox, guild = _player_container_and_guild(to_world_dir, player_id)
        with _silent():
            backup_world(to_world_dir, tag="travel_in")
            g = load_gvas(level_save_path(to_world_dir))
            moved = []
            for p in pals:
                node = self.db.transfer_pal(p["global_pal_id"], to_server)  # aposenta origem
                res = inject_pal(g, node, player_id, palbox, guild)
                self.db.register_transferred_instance(p["global_pal_id"], to_server, res["new_instance_id"])
                moved.append((p["character_id"], res["new_instance_id"]))
            write_gvas(g, level_save_path(to_world_dir))
        # custódia do player-snapshot e dos itens únicos também migra (handoff legítimo)
        self.db.db.execute("UPDATE players SET custodian_server=? WHERE player_uid=?", (to_server, player_id))
        self.db.db.execute("UPDATE legendary_items SET custodian_server=? WHERE owner_uid=? AND custodian_server=?",
                           (to_server, player_id, from_server))
        self.db.db.commit()
        return {"moved": len(moved), "to": to_server, "sample": moved[:3]}

    # ---- regra global: reset de temporada ----
    def season_reset(self):
        """Zera o progresso global (players/pals/itens). Feudos devem reidratar
        do central (zero) no próximo login. Só o central pode disparar."""
        for t in ("players", "pals", "legendary_items", "pal_instances", "transfer_log"):
            self.db.db.execute(f"DELETE FROM {t}")
        self.db.db.commit()
