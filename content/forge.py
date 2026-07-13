"""Forja de Conteudo — ponto unico que liga TODOS os geradores.

"Facilmente ativada depois": cada tipo de conteudo e uma entrada no REGISTRY com
uma flag `enabled`. Ligar/desligar um tipo = mudar a flag (ou content_flags.json).
A Central chama forge.mint(tipo) pra cunhar e registrar na economia.

Tipos: boss, item, equipment, pal, class.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .boss_generator import generate_boss
from .item_generator import generate_item
from .equipment_generator import generate_equipment
from .pal_generator import generate_pal, generate_class

HERE = Path(__file__).parent
FLAGS_FILE = HERE / "content_flags.json"

# registro central: tipo -> (funcao geradora, habilitado por padrao)
REGISTRY = {
    "boss":      {"fn": generate_boss,      "enabled": True},
    "item":      {"fn": generate_item,      "enabled": True},
    "equipment": {"fn": generate_equipment, "enabled": True},
    "pal":       {"fn": generate_pal,       "enabled": True},
    "class":     {"fn": generate_class,     "enabled": True},
}


def _load_flags():
    """Sobrescreve os defaults com content_flags.json, se existir."""
    if FLAGS_FILE.exists():
        flags = json.loads(FLAGS_FILE.read_text(encoding="utf-8"))
        for k, on in flags.items():
            if k in REGISTRY:
                REGISTRY[k]["enabled"] = bool(on)


def is_enabled(kind: str) -> bool:
    _load_flags()
    return REGISTRY.get(kind, {}).get("enabled", False)


def set_enabled(kind: str, on: bool):
    _load_flags()
    flags = {k: REGISTRY[k]["enabled"] for k in REGISTRY}
    flags[kind] = on
    FLAGS_FILE.write_text(json.dumps(flags, indent=2, ensure_ascii=False), encoding="utf-8")


def mint(kind: str, **kwargs) -> dict:
    """Cunha 1 peca de conteudo do tipo pedido, se o tipo estiver habilitado."""
    if kind not in REGISTRY:
        raise ValueError(f"tipo desconhecido: {kind}. Validos: {list(REGISTRY)}")
    if not is_enabled(kind):
        raise RuntimeError(f"tipo '{kind}' esta DESABILITADO (content_flags.json)")
    return REGISTRY[kind]["fn"](**kwargs)


def mint_batch(kind: str, n: int, **kwargs) -> list[dict]:
    return [mint(kind, **kwargs) for _ in range(n)]


def mint_and_register(kind: str, central_client, owner_uid: str, server_id: str, **kwargs) -> dict:
    """Cunha e JA registra na economia da Central (via /v1/sync).

    Bosses registram o seu item lendario; itens/equip/pals registram a si mesmos
    com o unique_id. So o que e 'tradeable_globally' (raro+) entra no ledger.
    Retorna a peca cunhada.
    """
    piece = mint(kind, server_id=server_id, **kwargs)

    # extrai o unique_id que representa a peca na economia
    if kind == "boss":
        uid = piece["unique_item"]["unique_id"]
        static = piece["unique_item"]["static_id"]
        tradeable = True
    else:
        uid = piece.get("unique_id")
        static = piece.get("base_item") or piece.get("base_equip") or piece.get("base_pal") or kind
        tradeable = piece.get("tradeable_globally", False)

    if tradeable and central_client is not None:
        # usa o dynamic_id como (created_world_id=server, local_id=unique_id)
        central_client.sync({
            "server_id": server_id,
            "player_uid": owner_uid,
            "payload": {"minted": piece["name"]},
            "pals": [],
            "items": [{
                "created_world_id": server_id,
                "local_id_in_created_world": uid,
                "static_id": static,
            }],
            "strict": False,
        })
        piece["_registered"] = True
    return piece


def catalog() -> dict:
    """Retorna o estado atual dos tipos (pra UI/admin)."""
    _load_flags()
    return {k: {"enabled": v["enabled"]} for k, v in REGISTRY.items()}


def main() -> int:
    ap = argparse.ArgumentParser(description="Forja de conteudo do grid")
    ap.add_argument("kind", nargs="?", help="boss|item|equipment|pal|class")
    ap.add_argument("-n", type=int, default=1, help="quantidade")
    ap.add_argument("--tier", type=int, help="(boss) tier 1..5")
    ap.add_argument("--server", default="central")
    ap.add_argument("--enable", help="habilita um tipo e sai")
    ap.add_argument("--disable", help="desabilita um tipo e sai")
    ap.add_argument("--list", action="store_true", help="mostra o catalogo e sai")
    args = ap.parse_args()

    if args.enable:
        set_enabled(args.enable, True); print(f"'{args.enable}' habilitado."); return 0
    if args.disable:
        set_enabled(args.disable, False); print(f"'{args.disable}' desabilitado."); return 0
    if args.list or not args.kind:
        print(json.dumps(catalog(), indent=2, ensure_ascii=False)); return 0

    kwargs = {"server_id": args.server}
    if args.kind == "boss" and args.tier:
        kwargs["tier"] = args.tier
    out = mint_batch(args.kind, args.n, **kwargs)
    print(json.dumps(out if args.n > 1 else out[0], indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
