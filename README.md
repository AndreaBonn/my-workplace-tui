# Workspace TUI

Applicazione TUI per gestire Gmail, Google Chat, Google Calendar, Google Drive e Jira da terminale. Alternativa leggera al browser per le operazioni quotidiane su account Google Workspace.

Requisiti: Python 3.11+, Ubuntu 22.04+, terminale 120x40 minimo con supporto 256 colori.

## Installazione

```bash
git clone <repo-url>
cd myWorkTUI
./install.sh
```

Lo script:
- Verifica Python 3.11+
- Installa uv (se non presente)
- Installa le dipendenze
- Crea `.env` da `.env.example`
- Crea il comando `workspace-tui` in `/usr/local/bin/`

## Setup Google Cloud (una tantum)

1. Vai su [Google Cloud Console](https://console.cloud.google.com)
2. Crea un nuovo progetto
3. Abilita le API: Gmail, Google Chat, Google Calendar, Google Drive
4. Vai su "Credenziali" → "Crea credenziali" → "ID client OAuth" → tipo "Applicazione desktop"
5. Scarica il JSON e salvalo come `credentials/client_secret.json`
6. Al primo avvio, il browser si apre per autorizzare l'accesso — il token viene salvato automaticamente

## Setup Jira (opzionale)

1. Vai su [Gestione API Token Atlassian](https://id.atlassian.com/manage-profile/security/api-tokens)
2. Crea un nuovo API Token
3. Modifica `.env` con i tuoi dati Jira:
   ```
   JIRA_USERNAME=tua-email@azienda.com
   JIRA_API_TOKEN=il-token-generato
   JIRA_BASE_URL=https://tuaazienda.atlassian.net
   JIRA_DEFAULT_PROJECT=PROJ
   ```

Se le variabili Jira non sono configurate, la tab Jira viene disabilitata. Le altre tab funzionano normalmente.

## Avvio

```bash
workspace-tui
```

Oppure dalla directory del progetto:

```bash
uv run python -m workspace_tui
```

## Navigazione

| Tasto | Azione |
|---|---|
| `1`-`5` | Cambia tab (Gmail, Chat, Calendar, Drive, Jira) |
| `Tab` / `Shift+Tab` | Pannello successivo / precedente |
| `r` | Ricarica dati tab corrente |
| `q` | Esci |
| `?` | Mostra help |

Ogni tab ha shortcut specifici documentati nell'help contestuale.

## Configurazione

Tutte le variabili sono in `.env` — vedi `.env.example` per la lista completa con descrizioni.

## Test

```bash
uv run pytest
uv run pytest --cov --cov-report=term-missing
```

## Lint

```bash
uv run ruff check src/ tests/
uv run ruff format --check src/ tests/
```

## Struttura progetto

```
src/workspace_tui/
├── app.py              # App Textual principale
├── config/settings.py  # Configurazione pydantic-settings
├── auth/               # OAuth2 Google + Basic Auth Jira
├── services/           # Wrapper API (Gmail, Chat, Calendar, Drive, Jira)
├── ui/tabs/            # Tab per ogni servizio
├── ui/widgets/         # Widget riutilizzabili
├── cache/              # Cache locale (diskcache)
├── notifications/      # Notifiche desktop Ubuntu
└── utils/              # Utilità (HTML→testo, date)
```

## Limitazioni note

- Google Chat API richiede abilitazione da parte dell'admin Workspace — se non disponibile, la tab mostra un messaggio esplicativo
- Google Docs/Sheets/Slides: solo visualizzazione e download, non editing
- Le notifiche desktop richiedono un display manager attivo (non funzionano in sessione SSH pura)
