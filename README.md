# Palworld Bridge

Bridge "espião/ponte" que roda ao lado do Palworld Dedicated Server.
Sincroniza o estado dos players (inventário, Pals, atributos) com a
**Autoridade Central** do grid federado de Palworld.

## 🚀 Instalação num feudo (1 clique)

Baixe e rode o **`setup_feudo.bat`** — ele instala tudo, detecta seu mundo,
liga a REST/RCON, pergunta o nome do feudo/senha/token e registra na Central.
Passo a passo: **[FEUDO_SETUP.md](FEUDO_SETUP.md)**.

> Só precisa de **Python 3.10+** instalado (o resto o .bat resolve).
> A comunicação é **outbound** (feudo → VPS pública): funciona atrás de NAT
> residencial / Radmin VPN sem abrir porta.

## Arquitetura (M1)

```
REST API :8212  --(quem está online)-->  Watcher  --logout-->  força /save
                                            |                       |
                                            |            aguarda .sav mudar no disco
                                            v                       v
                                          Sink  <----  payload JSON (metadados + caminho do save)
```

> A REST API **não** expõe inventário/Pals/atributos — só metadados.
> O parse completo do `.sav` (inventário + Pals + stats) é feito no **Milestone 2**
> (ver `bridge/savreader.py` + `bridge/extractor.py`).

## ⚠️ Formato de save do Palworld 1.0 (`PlM`/Oodle)

O Palworld 1.0 mudou **duas** coisas no `.sav`:
1. **Compressão**: de zlib (`PlZ`) para **Oodle Kraken (`PlM`)**. Resolvido em
   `savreader.py` via lib open-source `ooz` (pacote PyPI `pyooz`), sem DLL proprietária.
2. **Layout interno** de vários structs (character, item, map_object). A lib oficial
   no PyPI (`palworld-save-tools` 0.24.0) **não acompanha** — por isso usamos o **fork
   1.0-ready `oMaN-Rod/palworld-save-tools`** (o mesmo do editor Palworld Save Pal).

## Instalação

```powershell
cd C:\palworldserver\palworld-bridge
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
# parser 1.0 (fork) — SEM deps pra nao compilar o pyooz do fork:
pip install --no-deps "git+https://github.com/oMaN-Rod/palworld-save-tools.git@main"
```

## Pré-requisitos no servidor

Editar `Pal/Saved/Config/WindowsServer/PalWorldSettings.ini`:

```
RESTAPIEnabled=True
RCONEnabled=True
```

Reiniciar o PalServer. A senha usada é a `AdminPassword` do mesmo arquivo.

## Uso

```powershell
python main.py --check   # testa conexão com a REST API
python main.py --once    # um único tick (login/logout uma vez)
python main.py           # roda o loop contínuo
```

Saídas ficam em `out/` no modo `file` (config `sink.mode`).

## Config (`config.json`)

- `rest_api` — url/usuário/senha da REST API do Palworld
- `save.world_dir` — pasta do mundo (já apontada pro seu World ID)
- `save.wait_after_save_secs` — quanto esperar o `.sav` mudar após `/save`
- `poll.interval_secs` — intervalo de polling
- `sink.mode` — `"file"` (mock local) ou `"http"` (sua API cloud)

## Estado dos milestones

- **M1 — Bridge poller**: ✅ detecta login/logout via REST API, força `/save`,
  localiza o `.sav` e empurra pro sink.
- **M2 — Parser/extrator**: ✅ `savreader.py` (descompressão `PlM`/`PlZ`) +
  `extractor.py` extraem inventário, Pals (party+Palbox) e atributos de
  `Level.sav` + `Players/<UID>.sav`. Itens trazem `dynamic_id`
  (`created_world_id` + `local_id_in_created_world`) — base do anti-duplicação.
- **M3 — Injeção inversa**: ✅ `injector.py` reescreve `.sav` (server parado +
  backup automático). Como o `ooz` prebuilt só descomprime, **escrevemos em PlZ
  (zlib)** — validado ao vivo: o servidor 1.0 carrega PlZ e re-salva em PlM sem
  perda de dados. Patches escalares (tech points, level/exp) prontos.
- **M3b — Transferência de Pal cross-server (remap de UUID)**: ✅ `inject_pal()`
  insere um Pal com InstanceId novo atualizando as 4 referências
  (CharacterSaveParameterMap, OwnerPlayerUId+SlotId, slot do container Palbox,
  handle da guilda). **Validado ao vivo**: clone injetado sobreviveu ao re-save do
  servidor (Palbox 106→107, dono correto, resto intacto). É o núcleo da viagem
  entre feudos: Pal vem do DB e é reinjetado sem colisão/duplicação.
- **M4 — DB global + anti-duplicação**: ✅ `globaldb.py` (SQLite, portável p/
  Postgres). Serialização lossless de nós GVAS crus (Pal/item) via `orjson`
  (round-trip provado). Ledger de itens únicos por `dynamic_id` — 2 servidores
  reivindicando o mesmo `dynamic_id` = DUPLICAÇÃO bloqueada. Pals com **custódia**
  (`global_pal_id`): só ativos em 1 servidor; transferência = handoff. Ver
  `m4_demo.py`. Falta: escolher o DB cloud e criptografar os IDs no ledger.

## Módulos

- `bridge/rest_client.py` — REST API (eventos: online, save)
- `bridge/watcher.py` — loop de polling + detecção de logout
- `bridge/saver.py` — resolve `.sav` do player + força/aguarda save
- `bridge/savreader.py` — descompressão `PlM`(Oodle)/`PlZ`(zlib) + GVAS
- `bridge/extractor.py` — estado completo do player (itens/Pals/stats)
- `bridge/injector.py` — escrita/injeção de volta no `.sav` (server parado + backup)
- `bridge/globaldb.py` — DB global (SQLite): serialização, ledger de itens, custódia + instâncias de Pals
- `bridge/central.py` — Autoridade Central: registro de feudos, sync, viagem/handoff, reset
- `bridge/sink.py` — destino (arquivo local ou HTTP)
- `m4_demo.py` — demo de ingestão + anti-duplicação
- `sim_grid.py` — simulação do grid federado (2 feudos + central) numa máquina só

## Grid federado (modelo edge NÃO-confiável)

Servidores de clã rodam em máquinas não-controladas → **nada é real até o Central validar**.
O estado local é provisório; custódia e economia vivem no Central.

- **Onboarding**: `register_server` (registro de feudos com dono/endpoint).
- **Identidade global**: o Steam UID do player é o mesmo em todos os servers.
- **Viagem**: `travel()` aposenta as instâncias de Pal na origem, injeta no destino
  (InstanceId novo) e migra custódia de Pals + itens.
- **Anti-cheat**: uma instância de Pal que já viajou é marcada `retired`; se o feudo
  de origem tentar re-sincronizá-la (ainda está no save local dele) → `DupeError`.
- **Regra global**: `season_reset()` zera o progresso global (só o Central dispara).

Rodar a simulação: `python sim_grid.py` (copia o mundo real p/ 2 feudos, não toca no vivo).
- `explore_sav.py` — utilitário de exploração da árvore de um `.sav`
