-- GridBossSpawner — mod UE4SS que spawna o BOSS UNICO gerado.
--
-- IMPORTANTE (honestidade): a ESTRUTURA e o fluxo abaixo estao prontos, mas as
-- chamadas exatas de API do jogo (spawn, set de stats/escala) MUDAM entre versoes
-- do Palworld e do UE4SS. Os pontos marcados [AJUSTAR NO JOGO] precisam ser
-- confirmados/ajustados com o jogo aberto e o log do UE4SS aberto. Isso NAO da
-- pra validar sem o jogo rodando.
--
-- Comando in-game (chat de admin): /spawnboss

local boss = require("boss_def")   -- def gerada por boss_generator.py

local function log(msg)
    print("[GridBossSpawner] " .. tostring(msg))
end

log("carregado. boss alvo: " .. boss.name .. " (" .. boss.base_pal .. ") lvl " .. boss.level)

-- Spawna o boss perto de uma localizacao (x,y,z).
local function spawn_boss(x, y, z)
    log(("spawnando %s em (%d, %d, %d)"):format(boss.name, x, y, z))

    -- [AJUSTAR NO JOGO] obter o mundo/PlayerController e chamar o spawner do Pal.
    -- Ex. de padrao usado pelos mods de "custom pal spawner": localizar a funcao
    -- de spawn do PalGameManager / PalCharacterSpawnParameter e passar:
    --   CharacterID = boss.base_pal, Level = boss.level, Rank = 4 (boss)
    -- Apos spawnar, aplicar:
    --   escala do ator     -> boss.scale
    --   HP/ATK multiplier   -> boss.hp_multiplier / boss.attack_multiplier
    --   moveset             -> boss.moves
    --   passivas            -> boss.passives
    --   drops               -> boss.drops
    -- Essas setas dependem das classes expostas pelo UE4SS na sua versao.

    log("stub de spawn executado (ver marcacoes [AJUSTAR NO JOGO]).")
end

-- Registra o comando de chat /spawnboss (admin).
-- [AJUSTAR NO JOGO] o hook de chat depende do mod-base (ex: Paled / Server-Essentials).
RegisterConsoleCommandHandler and RegisterConsoleCommandHandler("spawnboss", function()
    spawn_boss(0, 0, 0)
    return true
end)

-- Hotkey de teste (opcional): F8 spawna o boss na origem.
RegisterKeyBind and RegisterKeyBind(Key.F8, function()
    spawn_boss(0, 0, 0)
end)
