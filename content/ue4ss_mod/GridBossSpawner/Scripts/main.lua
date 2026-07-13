-- GridBossSpawner — FASE 5: spawn via CONSOLE COMMAND (contexto correto).
-- Chamar a UFunction crua crasha (ponteiro nulo). ConsoleCommand roteia o cheat
-- pelo caminho oficial do jogo, com o contexto montado. Muito mais seguro.
-- F5 = spawna BlueDragon nv5 (CONTROLE seguro). F6 = boss. F4 = contar.

local boss = require("boss_def")
local function log(m) print("[GridBoss] " .. tostring(m)) end
local BOSS_KEY = (boss.base_pal:gsub("^BOSS_", ""))
log("carregado. boss key=" .. BOSS_KEY)

local function count_pals(tag)
    local ok, arr = pcall(function() return FindAllOf("PalCharacter") end)
    local n = (ok and arr) and #arr or 0
    log(tag .. ": pals = " .. n); return n
end

local function run_cmd(cmd, tag)
    log("====== CMD " .. tag .. ": '" .. cmd .. "' ======")
    local ctrl = FindFirstOf("PalPlayerController")
    if not ctrl or not ctrl:IsValid() then log("sem controller"); return end
    count_pals("ANTES")
    local scheduled = pcall(function()
        ExecuteInGameThread(function()
            local ok, err = pcall(function() ctrl:ConsoleCommand(cmd, true) end)
            if not ok then
                -- alguns builds usam 1 argumento so
                ok, err = pcall(function() ctrl:ConsoleCommand(cmd) end)
            end
            log(ok and "ConsoleCommand executado" or ("ERRO: " .. tostring(err)))
        end)
    end)
    if not scheduled then log("ExecuteInGameThread indisponivel") end
    pcall(function()
        ExecuteWithDelay(3000, function()
            count_pals("DEPOIS")
            log("== se DEPOIS > ANTES, SPAWNOU! ==")
        end)
    end)
end

pcall(function()
    RegisterKeyBind(Key.F5, function() run_cmd("SpawnMonster BlueDragon 5", "CONTROLE") end)
    RegisterKeyBind(Key.F6, function() run_cmd("SpawnMonster " .. BOSS_KEY .. " " .. boss.level, "BOSS") end)
    RegisterKeyBind(Key.F4, function() count_pals("MANUAL") end)
    log("hotkeys: F5=BlueDragon nv5 (seguro), F6=boss, F4=contar.")
end)
