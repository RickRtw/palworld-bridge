"""DB global + anti-duplicação (Milestone 4).

SQLite local (portável pra Postgres/Supabase depois). Guarda:
  - snapshot completo do player (JSON)
  - Pals canônicos com CUSTÓDIA (um Pal só pode estar ativo em 1 servidor)
  - ledger de itens únicos/lendários por `dynamic_id` (anti-dupe)

Modelo de integridade:
  - Item único = (created_world_id, local_id_in_created_world). Itens
    empilháveis (PalSphere etc.) têm dynamic_id zerado e NÃO entram no ledger.
  - Se dois servidores reivindicam o mesmo dynamic_id => DUPLICAÇÃO.
  - Pal = global_pal_id estável (atribuído no 1º sync). Custódia muda em
    transferência legítima; reivindicação por servidor sem custódia => stale/dupe.
"""
from __future__ import annotations

import sqlite3
import time
import uuid
from pathlib import Path

import orjson
from palworld_save_tools.json_tools import _orjson_default

ZERO = "00000000-0000-0000-0000-000000000000"


# ---- serialização de nós GVAS crus (lossless) ----

def serialize_node(node) -> bytes:
    return orjson.dumps(node, default=_orjson_default)


def deserialize_node(blob: bytes) -> dict:
    return orjson.loads(blob)


def item_identity(dynamic_id: dict) -> str | None:
    """Chave global de um item único. None se for empilhável (dyn_id zerado)."""
    if not isinstance(dynamic_id, dict):
        return None
    local = str(dynamic_id.get("local_id_in_created_world", ZERO))
    if local == ZERO:
        return None
    created = str(dynamic_id.get("created_world_id", ZERO))
    return f"{created}:{local}"


class DupeError(Exception):
    """Reivindicação conflitante detectada (mesmo item/Pal em outro servidor)."""


class GlobalDB:
    def __init__(self, path: str = "global.db"):
        self.db = sqlite3.connect(path)
        self.db.row_factory = sqlite3.Row
        self._schema()

    def _schema(self):
        self.db.executescript("""
        CREATE TABLE IF NOT EXISTS players (
            player_uid TEXT PRIMARY KEY,
            nickname TEXT, level INT, exp INT,
            custodian_server TEXT,
            payload BLOB,
            updated_at REAL
        );
        CREATE TABLE IF NOT EXISTS pals (
            global_pal_id TEXT PRIMARY KEY,
            character_id TEXT, level INT,
            owner_uid TEXT,
            custodian_server TEXT,
            origin_server TEXT,
            current_instance_id TEXT,
            raw_node BLOB,
            active INT DEFAULT 1,
            updated_at REAL
        );
        CREATE TABLE IF NOT EXISTS legendary_items (
            dynamic_id TEXT PRIMARY KEY,
            static_id TEXT,
            owner_uid TEXT,
            custodian_server TEXT,
            first_seen_server TEXT,
            updated_at REAL
        );
        CREATE TABLE IF NOT EXISTS transfer_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            entity_type TEXT, entity_id TEXT,
            from_server TEXT, to_server TEXT, ts REAL
        );
        -- titulos concedidos pela Central (buffs aplicados no save pelo bridge).
        CREATE TABLE IF NOT EXISTS granted_titles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            player_uid TEXT, title_name TEXT, rarity TEXT,
            title_json TEXT, granted_by TEXT,
            applied INTEGER DEFAULT 0, granted_at REAL
        );
        -- rastreia CADA instancia fisica de um Pal num servidor.
        -- 'active' = existe legitimamente ali; 'retired' = ja saiu (viajou).
        -- Uma (server, instance_id) 'retired' que reaparece = tentativa de dupe.
        CREATE TABLE IF NOT EXISTS pal_instances (
            server TEXT, instance_id TEXT,
            global_pal_id TEXT, status TEXT,
            updated_at REAL,
            PRIMARY KEY (server, instance_id)
        );
        """)
        self.db.commit()

    # ---- player ----
    def upsert_player(self, state: dict, server: str):
        a = state["attributes"]
        self.db.execute(
            "INSERT INTO players(player_uid,nickname,level,exp,custodian_server,payload,updated_at)"
            " VALUES(?,?,?,?,?,?,?)"
            " ON CONFLICT(player_uid) DO UPDATE SET"
            " nickname=excluded.nickname,level=excluded.level,exp=excluded.exp,"
            " custodian_server=excluded.custodian_server,payload=excluded.payload,updated_at=excluded.updated_at",
            (state["player_id"], a.get("nickname"), a.get("level"), a.get("exp"),
             server, serialize_node(state), time.time()),
        )
        self.db.commit()

    # ---- itens (anti-dupe) ----
    def register_item(self, dynamic_id: dict, static_id: str, owner_uid: str, server: str) -> str:
        """Registra/atualiza um item único. Levanta DupeError se outro servidor o detém.
        Retorna: 'new' | 'refresh' (mesmo servidor)."""
        key = item_identity(dynamic_id)
        if key is None:
            return "stackable"
        row = self.db.execute("SELECT custodian_server FROM legendary_items WHERE dynamic_id=?", (key,)).fetchone()
        if row and row["custodian_server"] != server:
            raise DupeError(f"item {static_id} [{key}] já custodiado por {row['custodian_server']}, "
                            f"mas {server} tentou reivindicar (DUPLICAÇÃO)")
        first = server if not row else self.db.execute(
            "SELECT first_seen_server FROM legendary_items WHERE dynamic_id=?", (key,)).fetchone()["first_seen_server"]
        self.db.execute(
            "INSERT INTO legendary_items(dynamic_id,static_id,owner_uid,custodian_server,first_seen_server,updated_at)"
            " VALUES(?,?,?,?,?,?)"
            " ON CONFLICT(dynamic_id) DO UPDATE SET owner_uid=excluded.owner_uid,"
            " custodian_server=excluded.custodian_server,updated_at=excluded.updated_at",
            (key, static_id, owner_uid, server, first, time.time()),
        )
        self.db.commit()
        return "new" if not row else "refresh"

    # ---- rastreio de instâncias físicas ----
    def instance_status(self, server: str, instance_id: str):
        r = self.db.execute("SELECT status,global_pal_id FROM pal_instances WHERE server=? AND instance_id=?",
                            (server, instance_id)).fetchone()
        return (r["status"], r["global_pal_id"]) if r else (None, None)

    def _record_instance(self, server: str, instance_id: str, gid: str, status: str):
        self.db.execute(
            "INSERT INTO pal_instances(server,instance_id,global_pal_id,status,updated_at) VALUES(?,?,?,?,?)"
            " ON CONFLICT(server,instance_id) DO UPDATE SET status=excluded.status,"
            " global_pal_id=excluded.global_pal_id,updated_at=excluded.updated_at",
            (server, instance_id, gid, status, time.time()))

    # ---- Pals (custódia) ----
    def register_pal(self, raw_entry: dict, character_id: str, level: int,
                     owner_uid: str, server: str, global_pal_id: str | None = None) -> str:
        """Registra um Pal sob custódia deste servidor.
        - Se a (server, instance_id) já foi APOSENTADA (o Pal viajou) => DupeError.
        - Se o global_pal_id existe sob outro servidor => DupeError.
        Reusa o gid da instância ativa se já conhecida (idempotente)."""
        iid = str(raw_entry["key"]["InstanceId"]["value"])
        status, known_gid = self.instance_status(server, iid)
        if status == "retired":
            raise DupeError(f"Pal {character_id} (instância {iid[:8]} em {server}) já VIAJOU; "
                            f"re-sincronização = tentativa de duplicação")
        other = self.db.execute("SELECT server FROM pal_instances WHERE instance_id=?"
                                " AND status='active' AND server<>? LIMIT 1", (iid, server)).fetchone()
        if other:
            raise DupeError(f"Pal {character_id} (instância {iid[:8]}) já ativo em "
                            f"{other['server']}; {server} não pode reivindicar (DUPLICAÇÃO)")
        gid = global_pal_id or known_gid or str(uuid.uuid4())
        row = self.db.execute("SELECT custodian_server FROM pals WHERE global_pal_id=?", (gid,)).fetchone()
        if row and row["custodian_server"] != server:
            raise DupeError(f"Pal {character_id} [{gid[:8]}] custodiado por {row['custodian_server']}, "
                            f"{server} não pode reivindicar sem transferência")
        self._record_instance(server, iid, gid, "active")
        self.db.execute(
            "INSERT INTO pals(global_pal_id,character_id,level,owner_uid,custodian_server,origin_server,"
            "current_instance_id,raw_node,active,updated_at) VALUES(?,?,?,?,?,?,?,?,1,?)"
            " ON CONFLICT(global_pal_id) DO UPDATE SET level=excluded.level,owner_uid=excluded.owner_uid,"
            " custodian_server=excluded.custodian_server,current_instance_id=excluded.current_instance_id,"
            " raw_node=excluded.raw_node,updated_at=excluded.updated_at",
            (gid, character_id, level, owner_uid, server, server, iid,
             serialize_node(raw_entry), time.time()),
        )
        self.db.commit()
        return gid

    def transfer_pal(self, global_pal_id: str, to_server: str) -> dict:
        """Handoff de custódia legítimo. APOSENTA a instância de origem (fecha o
        buraco do re-sync) e retorna o raw_node pra injeção no destino."""
        row = self.db.execute(
            "SELECT custodian_server,current_instance_id,raw_node FROM pals WHERE global_pal_id=?",
            (global_pal_id,)).fetchone()
        if not row:
            raise DupeError(f"Pal {global_pal_id} inexistente")
        frm = row["custodian_server"]
        # a instância física que fica no save de origem vira 'retired'
        if row["current_instance_id"]:
            self._record_instance(frm, row["current_instance_id"], global_pal_id, "retired")
        self.db.execute("UPDATE pals SET custodian_server=?,updated_at=? WHERE global_pal_id=?",
                        (to_server, time.time(), global_pal_id))
        self.db.execute("INSERT INTO transfer_log(entity_type,entity_id,from_server,to_server,ts)"
                        " VALUES('pal',?,?,?,?)", (global_pal_id, frm, to_server, time.time()))
        self.db.commit()
        return deserialize_node(row["raw_node"])

    def register_transferred_instance(self, global_pal_id: str, to_server: str, new_instance_id: str):
        """Após injetar o Pal no destino (novo InstanceId), registra a instância ativa."""
        self._record_instance(to_server, new_instance_id, global_pal_id, "active")
        self.db.execute("UPDATE pals SET current_instance_id=?,updated_at=? WHERE global_pal_id=?",
                        (new_instance_id, time.time(), global_pal_id))
        self.db.commit()

    def pals_on_server(self, owner_uid: str, server: str) -> list[dict]:
        rows = self.db.execute(
            "SELECT global_pal_id,character_id,current_instance_id FROM pals"
            " WHERE owner_uid=? AND custodian_server=? AND active=1", (owner_uid, server)).fetchall()
        return [dict(r) for r in rows]

    # ---- títulos (concessão pela Central) ----
    def grant_title(self, player_uid: str, title: dict, server: str) -> int:
        cur = self.db.execute(
            "INSERT INTO granted_titles(player_uid,title_name,rarity,title_json,granted_by,applied,granted_at)"
            " VALUES(?,?,?,?,?,0,?)",
            (player_uid, title.get("name"), title.get("rarity"),
             serialize_node(title).decode("utf-8"), server, time.time()))
        self.db.commit()
        return cur.lastrowid

    def pending_titles(self, player_uid: str) -> list[dict]:
        rows = self.db.execute(
            "SELECT id,title_name,title_json FROM granted_titles"
            " WHERE player_uid=? AND applied=0", (player_uid,)).fetchall()
        return [{"id": r["id"], "name": r["title_name"],
                 "title": deserialize_node(r["title_json"].encode("utf-8"))} for r in rows]

    def mark_title_applied(self, title_id: int):
        self.db.execute("UPDATE granted_titles SET applied=1 WHERE id=?", (title_id,))
        self.db.commit()

    def player_titles(self, player_uid: str) -> list[dict]:
        rows = self.db.execute(
            "SELECT title_name,rarity,applied FROM granted_titles WHERE player_uid=?",
            (player_uid,)).fetchall()
        return [dict(r) for r in rows]

    def stats(self) -> dict:
        c = self.db.execute
        return {
            "players": c("SELECT COUNT(*) n FROM players").fetchone()["n"],
            "pals": c("SELECT COUNT(*) n FROM pals").fetchone()["n"],
            "legendary_items": c("SELECT COUNT(*) n FROM legendary_items").fetchone()["n"],
            "transfers": c("SELECT COUNT(*) n FROM transfer_log").fetchone()["n"],
        }
