# Gerador de Conteúdo — Bosses únicos

Cunha bosses únicos **sem modelagem 3D**: varia parâmetros de Pals que já existem
no jogo (espécie-base, escala, stats, moveset, passivas, drops, nome) e dá a cada
boss um ID único rastreável.

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
