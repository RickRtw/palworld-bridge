"""Entrypoint do bridge. Uso:

    python main.py                 # usa config.json ao lado
    python main.py --once          # roda um unico tick (teste rapido)
    python main.py --check         # so testa conexao com a REST API
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from bridge.watcher import Watcher

HERE = Path(__file__).parent


def load_config(path: str) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default=str(HERE / "config.json"))
    ap.add_argument("--once", action="store_true", help="roda um unico tick e sai")
    ap.add_argument("--check", action="store_true", help="testa a REST API e sai")
    args = ap.parse_args()

    cfg = load_config(args.config)
    w = Watcher(cfg)

    if args.check:
        print(w.rest.info())
        print("players online:", w.rest.players())
        return 0
    if args.once:
        w.tick()
        return 0

    w.run()
    return 0


if __name__ == "__main__":
    sys.exit(main())
