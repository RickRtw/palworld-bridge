"""Loop principal: detecta login/logout por diffing da lista de players online.

Quando um player some da lista -> evento de logout -> forca Save,
resolve o .sav dele e empurra pro sink. O parse real do .sav
(inventario + Pals + stats) entra no proximo milestone; por ora
enviamos os metadados da REST + o caminho do save capturado.
"""
from __future__ import annotations

import time
import traceback

from .rest_client import RestClient
from .saver import force_save_and_wait, player_save_path
from .sink import Sink
from .extractor import extract_player_state


class Watcher:
    def __init__(self, config: dict):
        self.cfg = config
        rc = config["rest_api"]
        self.rest = RestClient(rc["base_url"], rc["username"], rc["password"])
        self.sink = Sink(config["sink"])
        self.world_dir = config["save"]["world_dir"]
        self.wait_secs = config["save"].get("wait_after_save_secs", 20)
        self.interval = config["poll"].get("interval_secs", 5)
        # userId -> objeto player (ultimo estado conhecido online)
        self.online: dict[str, dict] = {}

    def _key(self, p: dict) -> str:
        return p.get("userId") or p.get("playerId") or p.get("name", "?")

    def handle_logout(self, player: dict) -> None:
        pid = player.get("playerId", "")
        name = player.get("name", "?")
        print(f"[event] LOGOUT {name} (playerId={pid})")
        save_path = None
        try:
            save_path = force_save_and_wait(self.rest, self.world_dir, pid, self.wait_secs)
        except Exception:
            print("[warn] falha ao forcar/aguardar save:")
            traceback.print_exc()
            save_path = player_save_path(self.world_dir, pid)

        payload = {
            "event": "logout",
            "player_id": pid,
            "user_id": player.get("userId"),
            "name": name,
            "account_name": player.get("accountName"),
            "last_location": {"x": player.get("location_x"), "y": player.get("location_y")},
            "save_file": str(save_path) if save_path else None,
        }

        # M2: extrai o estado completo do .sav (inventario + Pals + stats)
        try:
            state = extract_player_state(self.world_dir, pid)
            payload["attributes"] = state["attributes"]
            payload["technology"] = state["technology"]
            payload["inventory"] = state["inventory"]
            payload["pals"] = state["pals"]
            party = len(state["pals"]["party"])
            box = len(state["pals"]["palbox"])
            print(f"[extract] {state['attributes']['nickname']} nv{state['attributes']['level']} "
                  f"| {party} party + {box} palbox | inv ok")
        except Exception:
            print("[warn] falha ao extrair estado do .sav (persistindo so metadados):")
            traceback.print_exc()
            payload["attributes"] = {"level": player.get("level")}
            payload["inventory"] = None
            payload["pals"] = None

        self.sink.push_player(payload)

    def tick(self) -> None:
        players = self.rest.players()
        current = {self._key(p): p for p in players}

        for key, p in current.items():
            if key not in self.online:
                print(f"[event] LOGIN  {p.get('name','?')} (playerId={p.get('playerId')})")

        for key, p in list(self.online.items()):
            if key not in current:
                self.handle_logout(p)

        self.online = current

    def run(self) -> None:
        print(f"[bridge] iniciando. polling a cada {self.interval}s")
        try:
            print(f"[bridge] server: {self.rest.info()}")
        except Exception:
            print("[warn] nao consegui falar com a REST API. RESTAPIEnabled=True e server no ar?")
        while True:
            try:
                self.tick()
            except Exception:
                print("[warn] erro no tick:")
                traceback.print_exc()
            time.sleep(self.interval)
