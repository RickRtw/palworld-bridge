"""Cliente HTTP do bridge (feudo) -> API Central.

Roda na máquina de cada clã. Fala com a Autoridade Central por HTTP usando o
API_TOKEN. Substitui o `central.py` in-process (que era só pra simulação local).
"""
from __future__ import annotations

import requests


class CentralClient:
    def __init__(self, base_url: str, token: str, timeout: float = 15.0):
        self.base = base_url.rstrip("/")
        self.h = {"Authorization": f"Bearer {token}"}
        self.timeout = timeout

    def _post(self, path, json):
        r = requests.post(f"{self.base}{path}", headers=self.h, json=json, timeout=self.timeout)
        r.raise_for_status()
        return r.json()

    def _get(self, path):
        r = requests.get(f"{self.base}{path}", headers=self.h, timeout=self.timeout)
        r.raise_for_status()
        return r.json()

    def health(self) -> bool:
        return requests.get(f"{self.base}/health", timeout=self.timeout).json().get("ok", False)

    def register_server(self, server_id, owner, endpoint=None):
        return self._post("/v1/servers/register",
                          {"server_id": server_id, "owner": owner, "endpoint": endpoint})

    def sync(self, payload: dict):
        return self._post("/v1/sync", payload)

    def travel(self, player_uid, from_server, to_server):
        return self._post("/v1/travel",
                          {"player_uid": player_uid, "from_server": from_server, "to_server": to_server})

    def travel_confirm(self, to_server, injected: list[dict]):
        return self._post("/v1/travel/confirm", {"to_server": to_server, "injected": injected})

    def get_player(self, player_uid):
        return self._get(f"/v1/players/{player_uid}")

    # ---- títulos ----
    def grant_title(self, player_uid, title, server_id):
        return self._post("/v1/titles/grant",
                          {"player_uid": player_uid, "server_id": server_id, "title": title})

    def pending_titles(self, player_uid):
        return self._get(f"/v1/titles/{player_uid}/pending")

    def title_applied(self, title_id):
        return self._post(f"/v1/titles/{title_id}/applied", {})

    def player_titles(self, player_uid):
        return self._get(f"/v1/titles/{player_uid}")

    def servers(self):
        return self._get("/v1/servers")

    def stats(self):
        return self._get("/v1/stats")
