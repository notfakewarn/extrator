# WhatsApp Web Contact Extractor + Lead Viewer

Aplicação Python modular para extrair contatos de grupos do WhatsApp Web com tolerância a falhas, retry com exponential backoff, checkpointing e persistência incremental.

## Compliance

- Não implementa scraping adicional de grupos além do que já existe no sistema.
- A interface de leads apenas visualiza/exporta dados já coletados em `data/`.
- Use somente dados com consentimento dos titulares.

## Como ver a "preview" da automação Selenium

Como essa aplicação usa Selenium no WhatsApp Web, a preview é **abrir o navegador automatizado** e ver o robô atuando em tempo real.

### 1) Instalar dependências

```bash
python -m venv .venv
# Linux/macOS
source .venv/bin/activate
# Windows (PowerShell)
# .venv\Scripts\Activate.ps1

pip install -r requirements.txt
```

### 2) Criar `.env`

Crie um arquivo `.env` na raiz do projeto:

```env
WA_TARGET_GROUP=Nome exato do grupo
WA_HEADLESS=false
WA_RETRY_ATTEMPTS=5
WA_TIMEOUT_LONG=60
```

> Para preview visual, mantenha `WA_HEADLESS=false`.

### 3) Rodar extração

```bash
python main.py
```

### O que você verá na preview
- Chrome abre em `https://web.whatsapp.com/`.
- Se for primeiro acesso no perfil, você verá QR Code para autenticar.
- Após login, o script busca o grupo definido em `WA_TARGET_GROUP`.
- Ele abre o painel de participantes e faz a rolagem até não encontrar novos itens.

## Nova interface web de leads

A interface web permite visualizar, filtrar e exportar leads já existentes.

### Subir API + frontend (FastAPI)

```bash
uvicorn api:app --reload --host 0.0.0.0 --port 8000
```

Abra no navegador:

- Painel web: `http://localhost:8000/`
- API de leads: `http://localhost:8000/leads`
- Export CSV: `http://localhost:8000/export`

## Endpoints

### `GET /leads`
Retorna lista de leads no formato:

- `nome`
- `telefone`
- `origem`
- `data`
- `status`
- `tag`

Filtros suportados por query string:

- `origem`
- `start_date` (ISO)
- `end_date` (ISO)
- `status`
- `tag`
- `limit`

### `GET /export`
Exporta CSV com os mesmos filtros de `GET /leads`.

## UX da página

- Dropdown de origem (WhatsApp/site/campanha).
- Filtro por data.
- Botão **Buscar**.
- Tabela com leads.
- Botão **Exportar CSV**.
- Atualização automática a cada 10 segundos (tempo real por polling).

## Fonte de dados

A API lê dados de `data/contacts.csv` e mapeia para modelo de leads.

- `name` -> `nome`
- `phone` -> `telefone`
- `source_group` -> `origem`
- `extracted_at` -> `data`
- `status` e `tag` usam defaults quando ausentes.

## Onde conferir saída da extração

- Logs detalhados: `logs/extractor.log`
- CSV incremental: `data/contacts.csv`
- JSONL incremental: `data/contacts.jsonl`
- JSON consolidado final: `data/contacts.json`
- Checkpoint de retomada: `data/checkpoint.json`

## Preview em modo servidor/headless

Se estiver em servidor sem interface gráfica:

```env
WA_HEADLESS=true
```

Nesse caso não há janela de preview visual; acompanhe pelo log (`logs/extractor.log`) e pelos arquivos em `data/`.

## Troubleshooting rápido

- **Não abriu grupo**: valide o nome exato em `WA_TARGET_GROUP`.
- **QR aparece sempre**: não apague `.chrome_profile/` (perfil persistente).
- **Sem contatos**: confira se o grupo tem participantes visíveis para sua conta.
- **WhatsApp mudou UI**: ajuste seletores em `config.py`.
