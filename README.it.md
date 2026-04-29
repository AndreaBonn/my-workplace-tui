[English](README.md) | **Italiano**

# Workspace TUI

Interfaccia terminale per Gmail, Google Chat, Google Calendar, Google Drive e Jira.

<div align="center">

[![CI](https://github.com/AndreaBonn/my-workplace-tui/actions/workflows/ci.yml/badge.svg)](https://github.com/AndreaBonn/my-workplace-tui/actions/workflows/ci.yml)
[![Tests](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/AndreaBonn/my-workplace-tui/main/badges/test-badge.json)](https://github.com/AndreaBonn/my-workplace-tui/actions/workflows/ci.yml)
[![Coverage](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/AndreaBonn/my-workplace-tui/main/badges/coverage-badge.json)](https://github.com/AndreaBonn/my-workplace-tui/actions/workflows/ci.yml)
[![Ruff](https://img.shields.io/badge/linter-ruff-261230.svg)](https://docs.astral.sh/ruff/)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Security](https://img.shields.io/badge/security-policy-green.svg)](SECURITY.md)

</div>

Workspace TUI porta Google Workspace e Jira in un'unica interfaccia a tab nel terminale. Al posto di una dozzina di schede nel browser, hai email, chat, calendario, file, issue tracking, ricerca cross-servizio e una dashboard riassuntiva, tutto da tastiera.

## Funzionalità

**Gmail** — Leggi, componi, rispondi, inoltra, aggiungi/rimuovi stella, archivia, elimina. Visualizzazione thread, download allegati, apertura nel browser. Navigazione cartelle.

**Google Chat** — Navigazione spazi e messaggi diretti. Invio messaggi. Se l'API Chat non è abilitata dall'admin Workspace, la tab mostra un avviso invece di bloccarsi.

**Google Calendar** — Visualizzazione eventi dei prossimi 30 giorni. Creazione eventi con partecipanti. Rilevamento meeting con link a videochiamate.

**Google Drive** — Navigazione e ricerca file. Download e upload. Filtro per tipo file. Distinzione condivisioni interne/esterne in base al dominio Workspace.

**Jira** — Lista, creazione e dettaglio issue. Log lavoro, transizioni di stato, commenti. Tracking epic tramite campo parent. Filtri JQL salvati su F1-F9. Supporto multi-account per lavorare su più istanze Jira contemporaneamente.

**Ricerca globale** — Interroga Gmail, Jira, Drive e Chat in parallelo da un'unica barra di ricerca.

**Dashboard** — Mostra email non lette, prossimi meeting, task recenti e distribuzione stati. Quando Jira non è configurato, le sezioni Jira vengono nascoste.

**Polling in background** — Controlli periodici per nuove email, eventi calendario, messaggi chat e aggiornamenti Jira. State-diffing per evitare notifiche duplicate al riavvio. Notifiche desktop OS su Linux (via plyer).

**Cache locale** — Le risposte API vengono salvate localmente via diskcache con TTL configurabile per servizio, così la navigazione ripetuta non chiama l'API ogni volta.

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
4. Crea la directory `credentials/`
5. Crea `.env` da `.env.example`
6. Crea il launcher `workspace-tui` in `~/.local/bin/`

Se `~/.local/bin` non è nel PATH, aggiungi questa riga al tuo `.bashrc` o `.zshrc`:

```bash
export PATH="${HOME}/.local/bin:${PATH}"
```

## Utilizzo

```bash
workspace-tui
```

Oppure dalla directory del progetto:

```bash
uv run python -m workspace_tui
```

## Setup

### Google Cloud (una tantum)

1. Vai su [Google Cloud Console](https://console.cloud.google.com)
2. Crea un progetto (o selezionane uno esistente)
3. Abilita queste API: **Gmail**, **Google Chat**, **Google Calendar**, **Google Drive**
4. Vai su **Credenziali** > **Crea credenziali** > **ID client OAuth**
5. Seleziona **Applicazione desktop** come tipo di applicazione
6. Scarica il file JSON e salvalo come `credentials/client_secret.json`
7. Al primo avvio, il browser si apre per l'autorizzazione OAuth2. Il token viene salvato automaticamente in `credentials/token.json`

Gli scope OAuth2 includono accesso in scrittura (es. `gmail.modify`, `calendar`, `drive`) perché l'app può inviare email, creare eventi e caricare file. Vedi [ASSUMPTIONS.md](ASSUMPTIONS.md) per la motivazione.

### Jira (opzionale)

1. Genera un API token nelle [impostazioni account Atlassian](https://id.atlassian.com/manage-profile/security/api-tokens)
2. Imposta `JIRA_USERNAME`, `JIRA_API_TOKEN` e `JIRA_BASE_URL` nel `.env`

Se Jira non è configurato, la tab Jira mostra un placeholder e la dashboard nasconde le sezioni Jira. Le altre tab funzionano normalmente.

#### Jira multi-account

Per collegare più istanze Jira, usa `JIRA_ACCOUNTS` al posto di `JIRA_BASE_URL`:

```env
JIRA_USERNAME=tua.email@azienda.com
JIRA_API_TOKEN=il-tuo-api-token

JIRA_ACCOUNTS=acme,widgets

JIRA_ACME_BASE_URL=https://acme.atlassian.net
JIRA_ACME_DEFAULT_PROJECT=PROJ

JIRA_WIDGETS_BASE_URL=https://widgets.atlassian.net
JIRA_WIDGETS_DEFAULT_PROJECT=WDG
```

I nomi degli account sono arbitrari. Per ogni nome, l'app legge `JIRA_{NOME}_BASE_URL` e `JIRA_{NOME}_DEFAULT_PROJECT` (nome in maiuscolo). Le query di ricerca vengono inviate a tutti gli account in parallelo.

## Configurazione

Tutte le impostazioni sono nel file `.env` (creato da `.env.example` durante l'installazione). Modificalo con qualsiasi editor di testo.

### Guida al .env

```env
# -- Google OAuth2 ────────────────────────────────────────────
# Path al file client_secret.json scaricato da Google Cloud Console.
GOOGLE_CLIENT_SECRET_PATH=credentials/client_secret.json

# Se usi più account Google nel browser, imposta l'email con cui
# vuoi che si aprano i link Google (Gmail, Calendar). Lascia vuoto
# per usare l'account predefinito del browser.
GOOGLE_ACCOUNT_EMAIL=

# -- Gmail ────────────────────────────────────────────────────
# Ogni quanti secondi controllare nuove email (minimo 10).
GMAIL_POLL_INTERVAL=60

# -- Google Chat ──────────────────────────────────────────────
CHAT_POLL_INTERVAL=30

# -- Google Calendar ──────────────────────────────────────────
CALENDAR_POLL_INTERVAL=300

# -- Google Drive ─────────────────────────────────────────────
# Il dominio della tua organizzazione Google Workspace (es. "azienda.com").
# Serve per distinguere le condivisioni interne da quelle esterne.
# Lascia vuoto per saltare questa distinzione.
WORKSPACE_DOMAIN=

# Dove salvare i file scaricati.
DRIVE_DOWNLOAD_DIR=~/Scaricati

# -- Notifiche ────────────────────────────────────────────────
# Notifiche desktop per nuove email, eventi e aggiornamenti Jira.
# Richiede un notification daemon su Linux (es. dunst, mako).
NOTIFICATIONS_ENABLED=true

# -- Cache ────────────────────────────────────────────────────
# Cache locale per le risposte API. Velocizza la navigazione e riduce
# le chiamate alle API.
CACHE_ENABLED=true
CACHE_TTL=300

# -- Jira (opzionale) ────────────────────────────────────────
# La tua email dell'account Atlassian.
JIRA_USERNAME=

# API token generato dalle impostazioni account Atlassian.
JIRA_API_TOKEN=

# Modalità singolo account: imposta direttamente l'URL dell'istanza.
JIRA_BASE_URL=
JIRA_DEFAULT_PROJECT=

# Modalità multi-account: nomi separati da virgola. Vedi README per dettagli.
# JIRA_ACCOUNTS=acme,widgets
# JIRA_ACME_BASE_URL=https://acme.atlassian.net
# JIRA_ACME_DEFAULT_PROJECT=PROJ

# Ogni quanti secondi controllare aggiornamenti Jira (minimo 10).
JIRA_POLL_INTERVAL=120

# Imposta a true solo per istanze Jira locali di sviluppo senza HTTPS.
JIRA_ALLOW_HTTP=false

# -- Filtri JQL Salvati ──────────────────────────────────────
# Filtri ad accesso rapido associati a F1-F9 nella tab Jira.
# Esempio: JIRA_SAVED_JQL_1=assignee = currentUser() AND status = "In Progress"
JIRA_SAVED_JQL_1=
JIRA_SAVED_JQL_2=
JIRA_SAVED_JQL_3=
JIRA_SAVED_JQL_4=
JIRA_SAVED_JQL_5=
JIRA_SAVED_JQL_6=
JIRA_SAVED_JQL_7=
JIRA_SAVED_JQL_8=
JIRA_SAVED_JQL_9=
```

### Riferimento configurazione

| Variabile | Descrizione | Default |
|-----------|-------------|---------|
| `GOOGLE_CLIENT_SECRET_PATH` | Path al client secret OAuth2 JSON | `credentials/client_secret.json` |
| `GOOGLE_ACCOUNT_EMAIL` | Forza i link Google ad aprirsi con questo account | — |
| `GMAIL_POLL_INTERVAL` | Intervallo polling Gmail in secondi | `60` |
| `CHAT_POLL_INTERVAL` | Intervallo polling Chat in secondi | `30` |
| `CALENDAR_POLL_INTERVAL` | Intervallo polling Calendar in secondi | `300` |
| `WORKSPACE_DOMAIN` | Dominio Google Workspace per filtro condivisioni | — |
| `DRIVE_DOWNLOAD_DIR` | Directory download per file Drive | `~/Scaricati` |
| `NOTIFICATIONS_ENABLED` | Notifiche desktop on/off | `true` |
| `CACHE_ENABLED` | Cache locale risposte on/off | `true` |
| `CACHE_TTL` | TTL cache in secondi | `300` |
| `JIRA_USERNAME` | Email Atlassian | — |
| `JIRA_API_TOKEN` | API token Jira | — |
| `JIRA_BASE_URL` | URL istanza Jira (singolo account) | — |
| `JIRA_DEFAULT_PROJECT` | Chiave progetto default (singolo account) | — |
| `JIRA_ACCOUNTS` | Nomi account separati da virgola (multi-account) | — |
| `JIRA_POLL_INTERVAL` | Intervallo polling Jira in secondi | `120` |
| `JIRA_ALLOW_HTTP` | Permetti connessioni Jira non-HTTPS | `false` |
| `JIRA_SAVED_JQL_1` .. `_9` | Filtri JQL salvati per F1-F9 | — |

Tutti gli intervalli di polling hanno un minimo di 10 secondi. Valori inferiori vengono portati automaticamente a 10.

## Scorciatoie tastiera

### Globali

| Tasto | Azione |
|-------|--------|
| `1`-`7` | Cambia tab (Gmail, Chat, Calendar, Drive, Jira, Search, Dashboard) |
| `Tab` / `Shift+Tab` | Naviga tra i pannelli |
| `r` | Ricarica tab corrente (svuota cache) |
| `?` | Aiuto |
| `q` | Esci |

### Gmail

| Tasto | Azione |
|-------|--------|
| `c` | Nuova email |
| `r` | Rispondi |
| `R` | Rispondi a tutti |
| `f` | Inoltra |
| `d` | Sposta nel cestino |
| `e` | Archivia |
| `m` | Segna come letto/non letto |
| `s` | Aggiungi/rimuovi stella |
| `/` | Cerca nella inbox |
| `a` | Scarica allegato |
| `t` | Visualizza thread |
| `o` | Apri nel browser |
| `g` | Apri Gmail web |

### Jira

| Tasto | Azione |
|-------|--------|
| `c` | Crea issue |
| `t` | Transizione stato |
| `w` | Log lavoro |
| `C` | Aggiungi commento |
| `o` | Apri nel browser |
| `/` | Ricerca JQL |
| `F1`-`F9` | Filtri JQL salvati |

### Calendar

| Tasto | Azione |
|-------|--------|
| `c` | Crea evento |
| `/` | Cerca |
| `o` | Apri nel browser |

### Drive

| Tasto | Azione |
|-------|--------|
| `/` | Cerca file |
| `d` | Scarica file |
| `n` | Nuova cartella |
| `u` | Carica file |
| `o` | Apri nel browser |

### Chat

| Tasto | Azione |
|-------|--------|
| `c` | Scrivi messaggio |
| `/` | Cerca |

## Architettura

```
WorkspaceTUI (Textual App)
+-- Tabs (livello UI)
|   +-- Gmail, Chat, Calendar, Drive, Jira, Search, Dashboard
|   +-- Widget (lista email, dettaglio issue, modale composizione, ...)
+-- Services (logica di business)
|   +-- Gmail, Chat, Calendar, Drive, Jira, Search, Dashboard
|   +-- BaseService (retry con backoff esponenziale, categorizzazione errori)
+-- Auth
|   +-- Google OAuth2 (Desktop flow, auto-refresh token)
|   +-- Jira Basic Auth (API token, sessioni per-account)
+-- Cache (diskcache, TTL per servizio)
+-- Notifiche (plyer, notifiche desktop a livello OS)
+-- Polling (PollManager, state-diffing, first-poll-silent)
+-- Config (pydantic-settings, .env)
```

I servizi non importano mai componenti UI. Le tab ricevono i servizi tramite il modello di composizione di Textual.

## Test

```bash
uv run pytest --cov --cov-report=term-missing
```

Controllo lint e formato:

```bash
uv run ruff check src/ tests/
uv run ruff format --check src/ tests/
```

La soglia di copertura è impostata all'85% in `pyproject.toml`. La suite di test usa risposte API mockate e gira senza accesso alla rete.

## Contribuire

I contributi sono benvenuti. Apri una issue per discutere le modifiche proposte prima di inviare una pull request. Rispetta lo stile di codice esistente (gestito da ruff) e assicurati che i test passino con la soglia di copertura.

## Sicurezza

Per segnalare vulnerabilità, vedi [SECURITY.it.md](SECURITY.it.md).

## Licenza

Rilasciato sotto licenza MIT — vedi [LICENSE](LICENSE).

## Autore

Andrea Bonacci — [@AndreaBonn](https://github.com/AndreaBonn)

---

Se questo progetto ti è utile, una stella su GitHub è gradita.
