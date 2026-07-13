"""Destino dos dados do player (o 'DB global').

Por enquanto suporta dois modos, escolhidos no config:
  - "file": grava um JSON local em out/ (MVP, sem infra)
  - "http": faz POST pra sua API cloud quando voce decidir o stack

A troca de mock -> cloud e so mudar sink.mode no config.json.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import requests


class Sink:
    def __init__(self, cfg: dict):
        self.mode = cfg.get("mode", "file")
        self.file_dir = Path(cfg.get("file_dir", "./out"))
        self.http_url = cfg.get("http_url", "")
        if self.mode == "file":
            self.file_dir.mkdir(parents=True, exist_ok=True)

    def push_player(self, payload: dict) -> None:
        payload = {**payload, "synced_at": datetime.now(timezone.utc).isoformat()}
        if self.mode == "http":
            r = requests.post(self.http_url, json=payload, timeout=10)
            r.raise_for_status()
            print(f"[sink] POST {self.http_url} -> {r.status_code}")
        else:
            uid = payload.get("player_id", "unknown")
            ts = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
            out = self.file_dir / f"{uid}_{ts}.json"
            out.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
            print(f"[sink] gravado {out}")
