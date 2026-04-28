[English](README.md) | **Italiano**

# Workspace TUI

Interfaccia terminale per Gmail, Google Chat, Google Calendar, Google Drive e Jira.

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![CI](https://github.com/AndreaBonn/my-workplace-tui/actions/workflows/ci.yml/badge.svg)](https://github.com/AndreaBonn/my-workplace-tui/actions/workflows/ci.yml)

Workspace TUI è un'applicazione terminale controllata da tastiera che offre accesso unificato ai servizi Google Workspace e Jira senza uscire dal terminale. Sostituisce le schede del browser con un'interfaccia a tab per le operazioni quotidiane su email, chat, calendario, file e issue tracking.

## Funzionalità

- Gmail: lettura inbox, anteprima messaggi, composizione email
- Google Chat: navigazione spazi e messaggi
- Google Calendar: visualizzazione eventi, creazione nuovi eventi
- Google Drive: navigazione file, download, distinzione condivisioni interne/esterne
- Jira: lista/creazione/dettaglio issue, log lavoro, filtri JQL salvati (F1-F9)
- Polling in background con notifiche desktop OS (Linux)
- Cache locale delle risposte API via diskcache
- Cambio tab con tasti numerici (1-5), scorciatoie tastiera ovunque

## Installazione

Requisiti: Python 3.11+, terminale con almeno 120x30 caratteri e supporto 256 colori. Linux (testato su Ubuntu 22.04+).

```bash
git clone https://github.com/AndreaBonn/my-workplace-tui.git
cd my-workplace-tui
./install.sh
```

Lo script di installazione:
1. Verifica Python 3.11+
2. Installa [uv](https://docs.astral.sh/uv/) se non presente (prompt interattivo)
3. Installa le dipendenze con `uv sync`
4. Crea `.env` da `.env.example`
5. Crea il launcher `workspace-tui` in `~/.local/bin/`

## Utilizzo

```bash
workspace-tui
```

Oppure dalla directory del progetto:

```bash
uv run python -m workspace_tui
```

### Setup Google Cloud (una tantum)

1. Vai su [Google Cloud Console](https://console.cloud.google.com)
2. Crea un progetto e abilita le API: Gmail, Google Chat, Google Calendar, Google Drive
3. Crea credenziali OAuth2 (tipo Applicazione desktop)
4. Scarica il file JSON e salvalo come `credentials/client_secret.json`
5. Al primo avvio il browser si apre per l'autorizzazione OAuth2 — il token viene salvato automaticamente

### Setup Jira (opzionale)

1. Genera un API token su [impostazioni account Atlassian](https://id.atlassian.com/manage-profile/security/api-tokens)
2. Compila le variabili Jira nel `.env` (vedi Configurazione sotto)

Se Jira non è configurato, la tab Jira viene disabilitata. Le altre tab funzionano normalmente.

### Scorciatoie tastiera

| Tasto | Azione |
|-------|--------|
| 1-5 | Cambia tab (Gmail, Chat, Calendar, Drive, Jira) |
| r | Ricarica tab corrente |
| ? | Aiuto |
| q | Esci |

## Configurazione

Tutte le impostazioni sono nel file `.env` (creato da `.env.example` durante l'installazione). Variabili principali:

| Variabile | Descrizione | Default |
|-----------|-------------|---------|
| `GOOGLE_CLIENT_SECRET_PATH` | Path al client secret OAuth2 | `credentials/client_secret.json` |
| `GMAIL_POLL_INTERVAL` | Intervallo polling Gmail (secondi) | `60` |
| `CHAT_POLL_INTERVAL` | Intervallo polling Chat (secondi) | `30` |
| `CALENDAR_POLL_INTERVAL` | Intervallo polling Calendar (secondi) | `300` |
| `NOTIFICATIONS_ENABLED` | Notifiche desktop on/off | `true` |
| `CACHE_ENABLED` | Cache locale on/off | `true` |
| `CACHE_TTL` | TTL cache (secondi) | `300` |
| `JIRA_USERNAME` | Email Atlassian | — |
| `JIRA_API_TOKEN` | API token Jira | — |
| `JIRA_BASE_URL` | URL istanza Jira (HTTPS obbligatorio) | — |
| `JIRA_DEFAULT_PROJECT` | Chiave progetto di default | — |
| `DRIVE_DOWNLOAD_DIR` | Directory download per file Drive | `~/Scaricati` |
| `WORKSPACE_DOMAIN` | Dominio Google Workspace (per filtro condivisioni) | — |

Vedi `.env.example` per la lista completa, inclusi i filtri JQL salvati.

## Test

```bash
uv run pytest --cov --cov-report=term-missing
```

Controllo lint e formato:

```bash
uv run ruff check src/ tests/
uv run ruff format --check src/ tests/
```

## Contribuire

I contributi sono benvenuti. Apri una issue per discutere le modifiche proposte prima di inviare una pull request. Rispetta lo stile di codice esistente (gestito da ruff) e assicurati che i test passino con la soglia di coverage (85%).

## Sicurezza

Per segnalare vulnerabilità, vedi [SECURITY.it.md](SECURITY.it.md).

## Licenza

Rilasciato sotto licenza MIT — vedi [LICENSE](LICENSE).

## Autore

Andrea Bonacci — [@AndreaBonn](https://github.com/AndreaBonn)

---

Se questo progetto ti è utile, una stella su GitHub è gradita.
