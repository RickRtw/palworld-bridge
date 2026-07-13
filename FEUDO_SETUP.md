# Setup de um Feudo (máquina de clã) — 1 clique

Guia pra plugar uma NOVA máquina no grid. A API Central já está no ar.

## Pré-requisitos

**Nenhum além de uma máquina Windows com internet.** O `.bat` instala tudo —
incluindo o Python e o próprio Servidor Dedicado de Palworld (via SteamCMD).

> Reserve espaço em disco (o servidor baixa vários GB) e uma boa conexão.

## Passo a passo (tudo automático)

1. **Baixe o instalador** (1 arquivo):
   https://raw.githubusercontent.com/RickRtw/palworld-bridge/main/setup_feudo.bat
   (abra o link, `Ctrl+S`, salve como `setup_feudo.bat` numa pasta qualquer)

2. **Dê 2 cliques** no `setup_feudo.bat`. Ele vai, em ordem:
   - instalar **Python 3.12** e **Git** se faltarem
   - baixar o bridge do GitHub e instalar as dependências
   - **perguntar os dados**: pasta de instalação, nome do servidor, senha de
     admin, senha de entrada, porta, máx. de players, ID do feudo, clã e token
   - baixar e instalar o **Palworld Dedicated Server** (SteamCMD) — vários GB
   - escrever o `PalWorldSettings.ini` (com REST/RCON ligados)
   - **subir o servidor** e esperar o mundo ser criado
   - escrever a config do bridge e **registrar o feudo na Central**

3. Pronto — servidor no ar e no grid. Nada manual.

## O token

Peça o **token da API** ao admin (POOT). Ele está no arquivo
`palworld-bridge\.central_secrets` na máquina do POOT (linha `API_TOKEN=...`).
O `.bat` guarda o token localmente — não precisa digitar de novo.

## Usar depois do setup

Abra a pasta do bridge e ative o ambiente:
```powershell
.\.venv\Scripts\Activate.ps1
python feudo_cli.py stats                 # status do grid
python feudo_cli.py sync <PLAYER_UID>     # envia o estado de um player
python feudo_cli.py player <PLAYER_UID>   # lê o estado autoritativo
```
O `<PLAYER_UID>` é o nome do arquivo em `Players\` (sem o `.sav`).

## Rede (Radmin / NAT residencial) — não é problema

O bridge só faz conexões **de saída** pra VPS pública da Central. Isso funciona
atrás de qualquer NAT residencial ou Radmin VPN, **sem abrir porta**. O Radmin
continua sendo usado só pro tráfego do jogo (jogadores → servidor Palworld),
como já era. As duas coisas são independentes.

## O que validar no teste

1. **Onboarding**: a 2ª máquina aparece em `feudo_cli.py stats`.
2. **Sync**: `sync <uid>` envia Pals+itens; os números sobem no `stats`.
3. **Anti-dupe**: sincronizar o MESMO player de 2 feudos diferentes → o 2º é
   bloqueado ("já ativo em outro servidor").
4. **Viagem**: `travel <player> <origem> <destino>` move os Pals entre feudos.

## Reset de temporada (só o admin/POOT)

```powershell
curl -X POST -H "Authorization: Bearer <ADMIN_TOKEN>" `
  http://d11k35y3n9lwh44dsticgbgu.178.18.251.2.sslip.io/v1/admin/season-reset
```
