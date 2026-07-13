"""Simulação do grid federado (edge NÃO-confiável) numa máquina só.

Monta 2 feudos (cópias do mundo real) + 1 Central e exercita:
  1. onboarding de feudos
  2. sync autoritativo de player
  3. viagem A -> B com handoff (injeção real no save de B)
  4. anti-cheat: feudo A tenta re-sincronizar Pals que já viajaram -> bloqueado
  5. regra global: reset de temporada
NÃO toca no servidor vivo.
"""
import io, contextlib, os, shutil
from pathlib import Path

from bridge.central import CentralAuthority
from bridge.extractor import extract_player_state

REAL = "C:/palworldserver/Pal/Saved/SaveGames/0/029DD0464FC342C5962BC2B994E5BD23"
SIM = "C:/palworldserver/palworld-bridge/sim"
PID = "FA4200F8-0000-0000-0000-000000000000"


def make_feudo(name):
    wd = f"{SIM}/{name}"
    if os.path.exists(wd):
        shutil.rmtree(wd)
    (Path(wd) / "Players").mkdir(parents=True)
    shutil.copy2(f"{REAL}/Level.sav", f"{wd}/Level.sav")
    for p in Path(f"{REAL}/Players").glob("*.sav"):
        shutil.copy2(p, f"{wd}/Players/{p.name}")
    return wd


def pool_count(wd):
    with contextlib.redirect_stdout(io.StringIO()):
        st = extract_player_state(wd, PID)
    return len(st["pals"]["party"]) + len(st["pals"]["palbox"])


print(">> montando feudos (cópias do mundo real)...")
feudo_A = make_feudo("feudo_A")
feudo_B = make_feudo("feudo_B")
if os.path.exists(f"{SIM}/central.db"):
    os.remove(f"{SIM}/central.db")
central = CentralAuthority(f"{SIM}/central.db")

print("\n=== 1) ONBOARDING ===")
central.register_server("feudo_A", "ClanRaiz", feudo_A)
central.register_server("feudo_B", "ClanMizu", feudo_B)
print("servidores no grid:", [s["server_id"] for s in central.servers()])

print("\n=== 2) SYNC AUTORITATIVO (POOT joga no feudo_A) ===")
r = central.sync_player("feudo_A", feudo_A, PID)
print("sync feudo_A:", r)
print("stats central:", central.db.stats())

print("\n=== 3) VIAGEM feudo_A -> feudo_B (handoff + injeção real) ===")
before_B = pool_count(feudo_B)
r = central.travel(PID, "feudo_A", "feudo_B", feudo_B)
after_B = pool_count(feudo_B)
print(f"travel: moveu {r['moved']} Pals | amostra {r.get('sample')}")
print(f"Pals no save do feudo_B: {before_B} -> {after_B}")
print("transfers logados:", central.db.stats()["transfers"])

print("\n=== 4) ANTI-CHEAT: feudo_A (não-confiável) tenta re-sincronizar ===")
print("(feudo_A ainda TEM os Pals no save local e tenta reinjetá-los na economia)")
r = central.sync_player("feudo_A", feudo_A, PID, strict=False)
print(f"Pals aceitos de novo: {r['pals']} | itens aceitos: {r['unique_items']}")
print(f"REJEIÇÕES do central: {len(r['rejections'])}")
for msg in r["rejections"][:3]:
    print("   [BLOQUEADO]", msg)

print("\n=== 5) REGRA GLOBAL: reset de temporada (só o central pode) ===")
central.season_reset()
print("stats após reset:", central.db.stats())
