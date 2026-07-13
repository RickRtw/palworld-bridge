"""CLI do feudo — facilita o teste com a API Central.

Uso (token via env CENTRAL_API_TOKEN):
  python feudo_cli.py stats
  python feudo_cli.py register
  python feudo_cli.py sync   <player_id>
  python feudo_cli.py travel <player_id> <from_server> <to_server>
  python feudo_cli.py player <player_id>
"""
import json, os, sys
from pathlib import Path

from bridge.central_client import CentralClient
from bridge.feudo import sync_to_central, travel_in

CFG = json.loads(Path(__file__).with_name("config.json").read_text(encoding="utf-8"))
CEN = CFG["central"]
WD = CFG["save"]["world_dir"]

token = os.environ.get(CEN.get("token_env", "CENTRAL_API_TOKEN"))
if not token:
    tok_file = Path(__file__).with_name(".token")
    if tok_file.exists():
        token = tok_file.read_text(encoding="utf-8").strip()
if not token:
    sys.exit(f"Defina o token: set {CEN.get('token_env','CENTRAL_API_TOKEN')}=<API_TOKEN>  (ou crie o arquivo .token)")

c = CentralClient(CEN["base_url"], token)
cmd = sys.argv[1] if len(sys.argv) > 1 else "stats"

if cmd == "stats":
    print("health:", c.health())
    print("stats :", c.stats())
    print("feudos:", c.servers())
elif cmd == "register":
    print(c.register_server(CEN["server_id"], CEN["owner"], CEN.get("base_url")))
elif cmd == "sync":
    r = sync_to_central(c, WD, sys.argv[2], CEN["server_id"])
    print(f"sync -> Pals:{r['accepted_pals']} itens:{r['accepted_items']} rejeicoes:{len(r['rejections'])}")
    for m in r["rejections"][:5]:
        print("   [BLOQUEADO]", m[:100])
elif cmd == "travel":
    print(travel_in(c, WD, sys.argv[2], sys.argv[3], sys.argv[4]))
elif cmd == "player":
    print(json.dumps(c.get_player(sys.argv[2]), indent=2, ensure_ascii=False)[:800])
else:
    print(__doc__)
