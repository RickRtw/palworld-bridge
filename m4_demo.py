"""Demo M4: ingere o estado do POOT no DB global e exercita o anti-duplicação.

Cenário simulado:
  - "central"  = servidor central (endgame)
  - "clan_A"   = servidor privado de um clã
Mostra: ingestão, detecção de item duplicado, e handoff de custódia de Pal.
"""
import io, contextlib, json, os
from bridge.savreader import load_gvas
from bridge.extractor import extract_player_state, INVENTORY_CONTAINERS, _uuid, _v
from bridge.globaldb import GlobalDB, DupeError, item_identity
from bridge.saver import player_save_path

WD = "C:/palworldserver/Pal/Saved/SaveGames/0/029DD0464FC342C5962BC2B994E5BD23"
PID = "FA4200F8-0000-0000-0000-000000000000"

if os.path.exists("global.db"):
    os.remove("global.db")
db = GlobalDB("global.db")

buf = io.StringIO()
with contextlib.redirect_stdout(buf):
    state = extract_player_state(WD, PID)
    g = load_gvas(WD + "/Level.sav")
    w = g.properties["worldSaveData"]["value"]
    # indice full-entry por InstanceId
    by_iid = {str(e["key"]["InstanceId"]["value"]): e for e in w["CharacterSaveParameterMap"]["value"]}
    cc = {str(x["key"]["ID"]["value"]): x["value"] for x in w["CharacterContainerSaveData"]["value"]}
    ic = {str(x["key"]["ID"]["value"]): x["value"] for x in w["ItemContainerSaveData"]["value"]}
    # containers do player
    psd = load_gvas(player_save_path(WD, PID)).properties["SaveData"]["value"]
    otomo = _uuid(psd["OtomoCharacterContainerId"])
    palbox = _uuid(psd["PalStorageContainerId"])

# 1) ingestão do player + Pals + itens sob custódia "central"
db.upsert_player(state, "central")

pal_ids = []
for cid in (otomo, palbox):
    for slot in cc[cid]["Slots"]["value"]["values"]:
        iid = str(slot["RawData"]["value"]["instance_id"])
        entry = by_iid.get(iid)
        if not entry:
            continue
        sp = entry["value"]["RawData"]["value"]["object"]["SaveParameter"]["value"]
        if _v(sp.get("IsPlayer")):
            continue
        cid_name = _v(sp.get("CharacterID"))
        gid = db.register_pal(entry, cid_name, _v(sp.get("Level")) or 1, PID, "central")
        pal_ids.append((gid, cid_name))

leg_items = []
for key, label in INVENTORY_CONTAINERS.items():
    if key not in psd["InventoryInfo"]["value"]:
        continue
    cont = ic.get(_uuid(psd["InventoryInfo"]["value"][key]))
    if not cont:
        continue
    for slot in cont["Slots"]["value"]["values"]:
        rd = slot["RawData"]["value"]
        if not isinstance(rd, dict):
            continue
        item = rd.get("item", {})
        dyn = item.get("dynamic_id", {})
        if item_identity(dyn) is None:
            continue
        r = db.register_item(dyn, _v(item.get("static_id")), PID, "central")
        leg_items.append((_v(item.get("static_id")), item_identity(dyn)))

print("=== INGESTÃO (servidor 'central') ===")
print("stats:", db.stats())
print(f"Pals registrados: {len(pal_ids)} | itens lendários no ledger: {len(leg_items)}")
print("amostra itens únicos:", [i[0] for i in leg_items[:6]])
print()

# 2) ANTI-DUPE: clã tenta reivindicar um item lendário que o central já detém
print("=== ANTI-DUPLICAÇÃO DE ITEM ===")
victim_static, victim_key = leg_items[0]
created, local = victim_key.split(":")
fake_dyn = {"created_world_id": created, "local_id_in_created_world": local}
try:
    db.register_item(fake_dyn, victim_static, PID, "clan_A")
    print("  FALHA: dupe NÃO detectado")
except DupeError as e:
    print("  [OK] bloqueado:", e)
print()

# 3) TRANSFERÊNCIA de custódia de Pal (central -> clan_A) e reivindicação stale
print("=== CUSTÓDIA DE PAL ===")
gid, cname = pal_ids[0]
print(f"Pal {cname} [{gid[:8]}] custódia inicial = central")
node = db.transfer_pal(gid, "clan_A")
row = db.db.execute("SELECT custodian_server FROM pals WHERE global_pal_id=?", (gid,)).fetchone()
print(f"  após transfer_pal -> custódia = {row['custodian_server']} (node p/ injeção: {len(json.dumps(node,default=str))} bytes)")
try:
    # central tenta re-sincronizar o Pal que já entregou (ainda no save dele) => stale/dupe
    db.register_pal(node, cname, 1, PID, "central", global_pal_id=gid)
    print("  FALHA: re-sync stale NÃO detectado")
except DupeError as e:
    print("  [OK] re-sync do central bloqueado:", e)
print()
print("stats finais:", db.stats())
