-- GridHelloTest — mod minimo pra PROVAR que o UE4SS carrega nosso Lua.
-- Nao spawna nada, nao mexe em nada. So escreve no console do UE4SS.
-- Se voce ver estas linhas no console do UE4SS = o pipeline de mod funciona.

print("========================================")
print("[GridHelloTest] Palworld Grid — Lua CARREGOU com sucesso!")
print("[GridHelloTest] Se voce esta lendo isto, o UE4SS roda nossos mods.")
print("========================================")

-- Tecla de teste: aperte F9 dentro do jogo -> deve imprimir no console.
local ok = pcall(function()
    RegisterKeyBind(Key.F9, function()
        print("[GridHelloTest] F9 pressionado — hook de teclado OK!")
    end)
end)

if ok then
    print("[GridHelloTest] hotkey F9 registrada (aperte F9 no jogo pra testar).")
else
    print("[GridHelloTest] aviso: RegisterKeyBind indisponivel nesta versao (nao critico).")
end
