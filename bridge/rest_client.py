"""Cliente da REST API oficial do Palworld Dedicated Server.

A REST API NAO expoe inventario/Pals/atributos completos. Serve como
'orquestrador de eventos': saber quem esta online, forcar Save, kickar, etc.
Os dados completos vem dos arquivos .sav (proximo milestone).

Docs dos endpoints: /v1/api/info, /v1/api/players, /v1/api/save
Auth: HTTP Basic, user 'admin', senha = AdminPassword do PalWorldSettings.ini
"""
from __future__ import annotations

import requests


class RestClient:
    def __init__(self, base_url: str, username: str, password: str, timeout: float = 8.0):
        self.base_url = base_url.rstrip("/")
        self.auth = (username, password)
        self.timeout = timeout

    def _get(self, path: str) -> dict:
        r = requests.get(f"{self.base_url}{path}", auth=self.auth, timeout=self.timeout)
        r.raise_for_status()
        return r.json()

    def _post(self, path: str, json: dict | None = None) -> dict:
        r = requests.post(f"{self.base_url}{path}", auth=self.auth, json=json, timeout=self.timeout)
        r.raise_for_status()
        # /save costuma responder texto simples; toleramos body vazio
        try:
            return r.json()
        except ValueError:
            return {"raw": r.text}

    def info(self) -> dict:
        """Metadados do servidor (versao, nome). Bom pra healthcheck."""
        return self._get("/v1/api/info")

    def players(self) -> list[dict]:
        """Lista de players online.

        Campos tipicos: name, accountName, playerId, userId, ip, ping,
        location_x, location_y, level. NAO inclui inventario nem Pals.
        """
        data = self._get("/v1/api/players")
        return data.get("players", [])

    def save(self) -> dict:
        """Forca flush do estado do mundo pro disco (.sav)."""
        return self._post("/v1/api/save")
