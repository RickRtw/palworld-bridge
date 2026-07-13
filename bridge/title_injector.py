"""Injeta o BUFF de um TÍTULO no personagem editando o save (M3 reliable path).

Títulos dão buff/debuff. A forma confiável (sem Lua ao vivo) e' ajustar os PONTOS
DE ATRIBUTO do personagem (GotStatusPointList) no Level.sav — coisa que o
injector ja' provou fazer losslessly.

REGRAS (iguais ao injector): servidor PARADO + backup antes de escrever.

Limite honesto: so' os atributos que existem como ponto de status do jogador
sao aplicaveis. Buffs como 'Defesa', 'Sorte', 'Dano a Bosses', 'Reducao de Dano'
NAO tem ponto de status -> ficam pra uma fase futura (logica dinamica/mods).
"""
from __future__ import annotations

from .savreader import load_gvas, write_gvas
from .saver import player_save_path, level_save_path
from .injector import backup_world

# rotulo da forja (PT) -> StatusName interno (japones) do save
STATUS_MAP = {
    "Ataque": "攻撃力",         # 攻撃力
    "Vida": "最大HP",               # 最大HP
    "Stamina": "最大SP",            # 最大SP
    "Peso": "所持重量",     # 所持重量
    "Captura de Pal": "捕獲率", # 捕獲率
    "Velocidade de Craft": "作業速度",  # 作業速度
    "Velocidade": "移動速度アップ",  # 移動速度アップ
}
# atributos sem ponto de status (nao aplicaveis por save) — reportados, nao aplicados
UNMAPPED = {"Defesa", "Sorte", "Dano a Bosses", "Reducao de Dano",
            "Cura Recebida", "Roubo de Vida", "XP"}


def _pct_to_points(pct: float) -> int:
    """Converte a % do buff em pontos de atributo. ~3% por ponto, sinal preservado."""
    pts = round(pct / 3.0)
    if pct != 0 and pts == 0:
        pts = 1 if pct > 0 else -1
    return int(pts)


def title_to_point_deltas(title: dict) -> tuple[dict, list]:
    """Do titulo (buffs/debuffs em %) -> {StatusName_jp: delta_pontos} + lista de ignorados."""
    deltas: dict[str, int] = {}
    ignored = []
    for stat, pct in {**title.get("buffs", {}), **{k: v for k, v in title.get("debuffs", {}).items()}}.items():
        jp = STATUS_MAP.get(stat)
        if not jp:
            ignored.append(stat)
            continue
        deltas[jp] = deltas.get(jp, 0) + _pct_to_points(pct)
    return deltas, ignored


TITLE_OPEN = " «"   # delimitadores do titulo no nome exibido
TITLE_CLOSE = "»"


def _base_nick(nick: str) -> str:
    """Remove um titulo previamente anexado ( 'POOT «Titulo»' -> 'POOT' )."""
    if TITLE_OPEN in nick and nick.rstrip().endswith(TITLE_CLOSE):
        return nick.split(TITLE_OPEN)[0].rstrip()
    return nick


def set_title_display(world_dir: str, player_id: str, title_name: str | None,
                      do_backup: bool = False) -> dict:
    """Mostra o titulo no personagem via NickName: 'POOT «Titulo»'.
    title_name=None remove o titulo do nome. Servidor PARADO. (Palworld nao tem
    campo de titulo editavel; o nome e' o caminho confiavel e visivel.)"""
    if do_backup:
        backup_world(world_dir, tag="title_display")
    gp = load_gvas(player_save_path(world_dir, player_id))
    instance_id = str(gp.properties["SaveData"]["value"]["IndividualId"]["value"]["InstanceId"]["value"])
    g = load_gvas(level_save_path(world_dir))
    sp = _find_player_sp(g, instance_id)
    if sp is None or "NickName" not in sp:
        raise ValueError("NickName do personagem nao encontrado")
    cur = sp["NickName"]["value"]
    base = _base_nick(cur)
    new = base if not title_name else f"{base}{TITLE_OPEN}{title_name}{TITLE_CLOSE}"
    sp["NickName"]["value"] = new
    write_gvas(g, level_save_path(world_dir))
    return {"before": cur, "after": new}


def _find_player_sp(level_gvas, instance_id: str):
    w = level_gvas.properties["worldSaveData"]["value"]
    for e in w["CharacterSaveParameterMap"]["value"]:
        if str(e["key"]["InstanceId"]["value"]) == instance_id:
            return e["value"]["RawData"]["value"]["object"]["SaveParameter"]["value"]
    return None


def _apply_deltas_to_list(status_list_values: list, deltas: dict) -> dict:
    """Aplica deltas na GotStatusPointList (cria entrada se faltar, clampa em 0).
    Retorna {StatusName: (antes, depois)} pro relatorio."""
    report = {}
    index = {it["StatusName"]["value"]: it for it in status_list_values}
    for jp, delta in deltas.items():
        entry = index.get(jp)
        if entry is None:
            # cria uma entrada nova nesse status
            entry = {
                "StatusName": {"id": None, "value": jp, "type": "NameProperty"},
                "StatusPoint": {"id": None, "value": 0, "type": "IntProperty"},
            }
            status_list_values.append(entry)
        before = entry["StatusPoint"]["value"]
        after = max(0, before + delta)   # clampa em 0 (nao vai negativo)
        entry["StatusPoint"]["value"] = after
        report[jp] = (before, after)
    return report


def apply_title(world_dir: str, player_id: str, title: dict, do_backup: bool = True,
                show_on_name: bool = False) -> dict:
    """Aplica o buff de um titulo ao personagem (edita Level.sav). Servidor PARADO.
    show_on_name (default OFF): anexa o titulo ao NickName ('POOT «Titulo»'). REJEITADO
    pelo usuario — o nome e' editavel pelo jogador, entao nao e' um titulo "de verdade".
    O prestigio do titulo fica no painel web do grid; o buff e' a manifestacao in-game.
    Display in-game travado = nameplate mod (futuro, ver memoria palworld-ue4ss-modding).
    Retorna relatorio {applied, ignored, display}."""
    deltas, ignored = title_to_point_deltas(title)
    if do_backup:
        backup_world(world_dir, tag="title")

    gp = load_gvas(player_save_path(world_dir, player_id))
    instance_id = str(gp.properties["SaveData"]["value"]["IndividualId"]["value"]["InstanceId"]["value"])

    g = load_gvas(level_save_path(world_dir))
    sp = _find_player_sp(g, instance_id)
    if sp is None:
        raise ValueError(f"personagem {instance_id} nao encontrado no Level.sav")

    status_list = sp["GotStatusPointList"]["value"]["values"]
    report = _apply_deltas_to_list(status_list, deltas)

    display = None
    if show_on_name and "NickName" in sp:
        base = _base_nick(sp["NickName"]["value"])
        tname = title.get("name")
        new = f"{base}{TITLE_OPEN}{tname}{TITLE_CLOSE}" if tname else base
        display = {"before": sp["NickName"]["value"], "after": new}
        sp["NickName"]["value"] = new

    write_gvas(g, level_save_path(world_dir))

    return {"title": title.get("name"), "applied": report, "ignored": ignored,
            "deltas": deltas, "display": display}
