# Forja de Conteúdo — geradores únicos

Cunha conteúdo único **sem modelagem 3D**: varia o que o jogo já tem (IDs reais do
Palworld) por parâmetros — stats, raridade, nome, classe, afixos. Cada peça ganha
um ID único rastreável que entra na economia anti-duplicação.

## Tipos (todos gerados e testados)

| Tipo | Gera | Arquivo |
|---|---|---|
| `boss` | boss único (Pal-base + escala/stats/drops/nome) | `boss_generator.py` |
| `item` | itens únicos (consumível/material/relíquia) | `item_generator.py` |
| `equipment` | armas/armaduras/acessórios com afixos | `equipment_generator.py` |
| `pal` | Pal único (variante + classe única) | `pal_generator.py` |
| `class` | classe/arquétipo único (título + viés de stats) | `pal_generator.py` |
| `title` | títulos com buffs/debuffs (comum→único + maldição), obtenção e requisitos | `title_generator.py` |
| `map` | config de mapa por feudo (fatia limitada: spawns/recursos/Pals/dificuldade) | `map_generator.py` |

Base compartilhada (raridade, nomes, IDs): `common.py`.

### Títulos (buffs/debuffs)
Raridades: comum, raro, épico, lendário, único, **maldição**. Buffs escalam com a
raridade (+2% comum → +16% único). Maldições dão um buff pequeno mas debuff pesado
(risco/recompensa). Cada título tem `acquisition_method` (matar boss, guerra de
clãs, PvP, explorar, sobreviver...) e `requirements` (condições de conquista).

### Mapas por feudo
Cada feudo é uma **fatia limitada** do mapa: região/bioma, teto de nível local,
Pals capturáveis e recursos restritos, **0 bosses/dungeons locais**. Reforça a
regra: o feudo trava o progresso → obriga a ir ao Central. Emite `server_opts`
(subset de PalWorldSettings) + `limits` (regras do mod).

## A Forja (`forge.py`) — ponto único, ligável

```bash
python -m content.forge --list            # catálogo + o que está ligado
python -m content.forge boss --tier 5     # cunha 1 boss tier 5
python -m content.forge equipment -n 3    # cunha 3 equipamentos
python -m content.forge --disable pal     # desliga um tipo
python -m content.forge --enable pal      # religa
```

Ligar/desligar cada tipo é só uma flag em `content_flags.json` — feito pra ser
"ativado facilmente depois". A cunhagem de um tipo desligado é bloqueada.

## Economia (cunhar → rastrear)

`forge.mint_and_register(kind, central_client, owner_uid, server_id, ...)` cunha e
JÁ registra na Central (só o que é raridade `raro`+ entra no ledger global).
Testado ao vivo: boss + 2 equipamentos → `legendary_items` subiu pra 3.

## Boss no jogo (o único ponto que precisa de ajuste na máquina)

## O que está PRONTO e validado (lado servidor/Python)

- `boss_generator.py` — gera a definição do boss (JSON) + a def em Lua.
  - `python boss_generator.py --tier 4` → boss aleatório de tier 4
  - `python boss_generator.py --tier 5 --seed 7 --lua boss_def.lua` → também emite Lua
  - tiers 1..5 escalam nível, vida, dano, tamanho e recompensa
  - cada boss "cunha" 1 item lendário com `unique_id` (entra na economia anti-dupe)

Isso roda e foi testado. A geração é 100% funcional.

## O que precisa ser AJUSTADO NO JOGO (lado mod, não dá pra validar sem o jogo)

- `ue4ss_mod/GridBossSpawner/` — mod UE4SS (Lua) que faz o boss APARECER.
  - A **estrutura** está pronta; as chamadas exatas de API do Palworld/UE4SS
    (spawn, aplicar escala/stats) mudam entre versões e estão marcadas no
    `main.lua` como `[AJUSTAR NO JOGO]`.
  - Isso só dá pra terminar com o **jogo aberto + log do UE4SS aberto**, testando
    ao vivo. É trabalho de máquina, não de código offline.

## Como fica o fluxo completo (quando o mod estiver ajustado)

1. Central roda `boss_generator.py` e cunha o boss (registra o ID na economia).
2. A def do boss vai pro feudo (arquivo Lua).
3. UE4SS instalado no servidor do feudo carrega o `GridBossSpawner`.
4. Admin dá `/spawnboss` (ou evento) → o boss único aparece e é lutável.
5. Ao morrer, dropa o item lendário com ID único → economia rastreia.

## Instalar o UE4SS no servidor (pré-requisito do mod)

1. Baixe o UE4SS (experimental, compatível com Palworld 1.0).
2. Extraia em `Pal/Binaries/Win64/` (cria `ue4ss/`).
3. Copie `GridBossSpawner/` para `Pal/Binaries/Win64/ue4ss/Mods/`.
4. Garanta que o mod está listado/ativo (arquivo `enabled.txt` presente).
5. `bAllowClientMod=True` no servidor (o do POOT já está).

> O instalador do feudo (`setup_feudo.bat`) pode, no futuro, baixar o UE4SS e
> instalar o mod automaticamente — hoje isso é manual até o mod estar validado.
