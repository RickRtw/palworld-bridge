# Setup de um Feudo (máquina de clã) — teste com a API Central

Guia pra plugar uma NOVA máquina no grid. A API Central já está no ar:
`http://d11k35y3n9lwh44dsticgbgu.178.18.251.2.sslip.io`

## 1. Pré-requisitos na máquina do feudo

- **Servidor Dedicado de Palworld** rodando, com no `PalWorldSettings.ini`:
  ```
  RESTAPIEnabled=True
  RCONEnabled=True
  ```
- **Python 3.10+**

## 2. Copiar o bridge

Copie a pasta `palworld-bridge` inteira pra essa máquina (zip, pendrive, ou git).
> O bridge NÃO está num repositório ainda — hoje ele mora só na máquina do POOT.
> Pra facilitar, dá pra publicar num repo privado depois.

## 3. Instalar dependências

```powershell
cd palworld-bridge
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
# parser 1.0 (fork) — SEM deps pra nao compilar o pyooz do fork:
pip install --no-deps "git+https://github.com/oMaN-Rod/palworld-save-tools.git@main"
```

## 4. Configurar `config.json`

Edite o bloco `save` e `central`:
- `save.world_dir` → o World ID **desta** máquina (pasta em `Pal/Saved/SaveGames/0/<ID>`)
- `rest_api.password` → o `AdminPassword` **deste** servidor
- `central.server_id` → um id ÚNICO pro feudo (ex: `feudo_mizu`)
- `central.owner` → nome do clã
- `central.base_url` → já aponta pra API central (não mude)

## 5. Definir o token (segredo — não vai em arquivo compartilhado)

```powershell
$env:CENTRAL_API_TOKEN = "<API_TOKEN>"   # peça o valor ao POOT (está em .central_secrets)
```

## 6. Rodar o teste

```powershell
python feudo_cli.py stats                 # confirma conexão com a Central
python feudo_cli.py register              # registra este feudo no grid
python feudo_cli.py sync <PLAYER_UID>     # envia o estado do player pra Central
python feudo_cli.py player <PLAYER_UID>   # lê o estado autoritativo de volta
```

O `<PLAYER_UID>` é o nome do arquivo em `Players/` (ex: `AB12CD34-0000-0000-0000-000000000000`).

## O que validar no teste de amanhã

1. **Onboarding**: a 2ª máquina aparece em `feudo_cli.py stats` (lista de feudos).
2. **Sync**: `sync` envia Pals+itens do player da 2ª máquina; `stats` mostra os números subindo.
3. **Anti-dupe**: tente sincronizar o MESMO player de duas máquinas com o mesmo `server_id`
   diferente → a 2ª é bloqueada (Pals/itens "já ativos em outro servidor").
4. **Viagem** (avançado): `travel <player> <origem> <destino>` move os Pals de um feudo pro
   outro com remapeamento de UUID (exige o player existir nos dois mundos).

## Reset (só o admin/POOT)

```powershell
curl -X POST -H "Authorization: Bearer <ADMIN_TOKEN>" `
  http://d11k35y3n9lwh44dsticgbgu.178.18.251.2.sslip.io/v1/admin/season-reset
```
