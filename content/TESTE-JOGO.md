# Teste do mod no jogo (Microsoft Store / Xbox — Singleplayer)

Objetivo: provar, em etapas seguras, que dá pra rodar nossos mods. Nada aqui toca
no servidor dos seus amigos.

> Microsoft Store = versão "WinGDK" (mesma coisa que Xbox/Gamepass pro modding).
> O jogo fica numa pasta protegida (`WindowsApps`) — por isso o instalador
> automático abaixo é o caminho mais fácil.

---

## Etapa 0 — Instalar o UE4SS (a parte mais chata; fazemos 1x)

A versão Microsoft Store é protegida, então o mais fácil é o **instalador
automático** da comunidade (detecta a instalação e coloca o UE4SS no lugar certo):

1. Baixe o **UE4SS-PalSchema Standalone Installer** (GitHub: GungnirIncarnate/
   UE4SS-PalSchema-Standalone-Installer → Releases → o `.exe` mais recente).
2. Rode como **Administrador** (precisa de permissão pra escrever no WindowsApps).
3. Ele detecta o Palworld da Microsoft Store e instala **UE4SS + PalSchema** de uma vez.
   - Se NÃO detectar: aponte manualmente pra pasta
     `...\Pal\Binaries\WinGDK\` (dentro do app: Xbox app → Palworld → Manage →
     Files → Browse).

> Se o instalador automático falhar, me avise que passo o método 100% manual
> (mover `ue4ss` + `dwmapi.dll` pra `WinGDK`). É mais trabalhoso mas funciona.

---

## Etapa 1 — Provar que o UE4SS carrega (TESTE ZERO)

1. Abra o Palworld.
2. Deve surgir uma **janela de console preta do UE4SS** junto com o jogo.
   - Apareceu o console? ✅ UE4SS funciona. Siga.
   - Não apareceu? ❌ a instalação não pegou — me avise o que aconteceu.

---

## Etapa 2 — Provar que o UE4SS roda O NOSSO Lua

1. Copie a pasta **`GridHelloTest`** (está em `content/ue4ss_mod/`) para dentro de:
   `...\Pal\Binaries\WinGDK\ue4ss\Mods\`
2. Abra o `...\ue4ss\Mods\mods.txt` e adicione a linha:
   `GridHelloTest : 1`
3. Abra o jogo e entre num mundo qualquer (singleplayer, mapa aleatório serve).
4. Olhe o console do UE4SS. Deve aparecer:
   ```
   [GridHelloTest] Palworld Grid — Lua CARREGOU com sucesso!
   ```
5. Aperte **F9** no jogo → deve imprimir `F9 pressionado — hook de teclado OK!`

**Me mande o que apareceu no console** (print ou texto). A partir daqui eu sei
exatamente o que a sua versão do UE4SS expõe e ajusto o mod do boss com código
real (não mais placeholders).

---

## Depois (quando a Etapa 2 passar)

- **Boss único** via Lua (`GridBossSpawner`) — spawn sob tecla/comando.
- **Itens / equip / títulos / mapa** via **PalSchema** (JSON) — nossos geradores
  já produzem o formato; eu converto pro schema do PalSchema.

## Importante (singleplayer vs servidor)
No singleplayer você é o "servidor", então dá pra validar spawn e stats. A
validação final server-side fica pra um 2º servidor de teste (sem afetar o atual).
