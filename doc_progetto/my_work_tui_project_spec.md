# Gmail Workspace TUI — Documento di Specifiche di Progetto

> **Versione:** 2.0  
> **Data:** Aprile 2026  
> **Destinatario:** Claude Code (implementazione autonoma)  
> **Lingua del codice:** Inglese (commenti, variabili, funzioni)  
> **Lingua UI:** Italiano (label, menu, messaggi di stato)

---

## 1. Panoramica del Progetto

### 1.1 Descrizione

Sviluppare un'applicazione TUI (Text User Interface) per Ubuntu che permetta la gestione completa dell'account Gmail di lavoro di un singolo utente. L'applicazione integra in un'unica interfaccia a tab i seguenti servizi Google:

- **Gmail** — lettura, scrittura, gestione email
- **Google Chat** — messaggi diretti e spazi di conversazione
- **Google Calendar** — visualizzazione e gestione eventi
- **Google Drive** — navigazione file e download/upload
- **Jira** — gestione issue, transizioni di stato, worklog ore, ricerca JQL

### 1.2 Obiettivi

- Sostituire l'uso del browser per le operazioni quotidiane sull'account Google di lavoro
- Permettere l'uso completo da tastiera senza mai toccare il mouse
- Funzionare su Ubuntu tramite terminale, incluso via SSH
- Essere veloce, leggero e stabile

### 1.3 Utente Target

Singolo utente tecnico su Ubuntu 22.04+, con un account Google Workspace (Gmail aziendale). Non è richiesto supporto multi-utente.

---

## 2. Stack Tecnologico

### 2.1 Linguaggio

**Python 3.11+**

### 2.2 Framework TUI

**[Textual](https://github.com/Textualize/textual)** (versione ≥ 0.55)

- Framework TUI moderno per Python
- Supporta layout reattivi, tab, widget personalizzati
- CSS-like styling integrato
- Gestione eventi asincrona nativa

### 2.3 Librerie Google

| Servizio | Libreria |
|---|---|
| Auth OAuth2 | `google-auth`, `google-auth-oauthlib`, `google-auth-httplib2` |
| Gmail | `google-api-python-client` (servizio: `gmail`, v1) |
| Google Chat | `google-api-python-client` (servizio: `chat`, v1) |
| Google Calendar | `google-api-python-client` (servizio: `calendar`, v3) |
| Google Drive | `google-api-python-client` (servizio: `drive`, v3) |
| Jira | `requests` (chiamate dirette alla Jira REST API v3) |

### 2.4 Librerie Ausiliarie

| Scopo | Libreria |
|---|---|
| Notifiche di sistema | `plyer` |
| Rendering HTML → testo | `html2text` |
| Formattazione date | `python-dateutil` |
| Configurazione | `pydantic-settings` + file `.env` |
| Logging | `loguru` |
| Cache locale | `diskcache` |
| Rendering Markdown nel TUI | `rich` (integrato con Textual) |

### 2.5 File `requirements.txt`

```
textual>=0.55.0
google-api-python-client>=2.100.0
google-auth>=2.22.0
google-auth-oauthlib>=1.1.0
google-auth-httplib2>=0.1.1
html2text>=2020.1.16
python-dateutil>=2.8.2
pydantic-settings>=2.0.0
plyer>=2.1.0
loguru>=0.7.0
diskcache>=5.6.0
rich>=13.0.0
requests>=2.31.0
```

---

## 3. Struttura del Progetto

```
gmail-tui/
├── main.py                    # Entry point
├── .env                       # Credenziali e configurazione (non committare)
├── .env.example               # Template delle variabili d'ambiente
├── requirements.txt
├── credentials/
│   ├── client_secret.json     # OAuth2 client secret scaricato da Google Cloud
│   └── token.json             # Token generato al primo login (auto-generato)
├── config/
│   └── settings.py            # Configurazione via pydantic-settings
├── auth/
│   ├── oauth.py               # Gestione OAuth2 Google, refresh token
│   └── jira_auth.py           # Autenticazione Jira via API Token (Basic Auth)
├── services/
│   ├── gmail_service.py       # Wrapper Gmail API
│   ├── chat_service.py        # Wrapper Google Chat API
│   ├── calendar_service.py    # Wrapper Google Calendar API
│   ├── drive_service.py       # Wrapper Google Drive API
│   └── jira_service.py        # Wrapper Jira REST API v3
├── ui/
│   ├── app.py                 # Classe principale Textual App
│   ├── tabs/
│   │   ├── gmail_tab.py       # Tab Gmail
│   │   ├── chat_tab.py        # Tab Google Chat
│   │   ├── calendar_tab.py    # Tab Google Calendar
│   │   ├── drive_tab.py       # Tab Google Drive
│   │   └── jira_tab.py        # Tab Jira
│   ├── widgets/
│   │   ├── email_list.py      # Lista email (widget riutilizzabile)
│   │   ├── email_preview.py   # Anteprima email
│   │   ├── compose_modal.py   # Modal per scrivere email
│   │   ├── event_card.py      # Card evento calendario
│   │   ├── file_browser.py    # Browser file Drive
│   │   ├── issue_list.py      # Lista issue Jira
│   │   ├── issue_detail.py    # Pannello dettaglio issue Jira
│   │   ├── worklog_modal.py   # Modal log ore Jira
│   │   ├── issue_create_modal.py  # Modal creazione issue Jira
│   │   └── status_bar.py      # Barra di stato globale
│   └── styles/
│       └── main.tcss          # CSS Textual globale
├── notifications/
│   └── notifier.py            # Notifiche di sistema Ubuntu
├── cache/
│   └── cache_manager.py       # Gestione cache locale
└── utils/
    ├── text_utils.py          # HTML→testo, formattazione
    └── date_utils.py          # Formattazione date/orari
```

---

## 4. Configurazione e Autenticazione

### 4.1 Google Cloud Setup (operazione manuale una-tantum)

L'utente deve eseguire i seguenti passi **prima** di avviare l'applicazione:

1. Creare un progetto su [Google Cloud Console](https://console.cloud.google.com)
2. Abilitare le seguenti API:
   - Gmail API
   - Google Chat API
   - Google Calendar API
   - Google Drive API
3. Creare credenziali OAuth 2.0 di tipo **"Desktop application"**
4. Scaricare il file `client_secret.json` e posizionarlo in `credentials/client_secret.json`

Il README deve documentare questi passaggi in dettaglio.

### 4.2 Flusso OAuth2

- Al primo avvio, se `credentials/token.json` non esiste, l'applicazione apre il browser per il login Google
- L'utente autorizza i permessi richiesti
- Il token viene salvato in `credentials/token.json`
- Agli avvii successivi, il token viene caricato e refreshato automaticamente se scaduto
- Il refresh è trasparente per l'utente

### 4.3 Scope OAuth2 Richiesti

```python
SCOPES = [
    "https://www.googleapis.com/auth/gmail.modify",
    "https://www.googleapis.com/auth/chat.messages",
    "https://www.googleapis.com/auth/chat.spaces.readonly",
    "https://www.googleapis.com/auth/calendar",
    "https://www.googleapis.com/auth/drive",
]
```

### 4.4 File `.env`

```env
# Percorso al client secret
GOOGLE_CLIENT_SECRET_PATH=credentials/client_secret.json

# Percorso al token salvato
GOOGLE_TOKEN_PATH=credentials/token.json

# Intervallo polling Gmail in secondi (default: 60)
GMAIL_POLL_INTERVAL=60

# Intervallo polling Chat in secondi (default: 30)
CHAT_POLL_INTERVAL=30

# Intervallo polling Calendar in secondi (default: 300)
CALENDAR_POLL_INTERVAL=300

# Numero massimo email da caricare per pagina
GMAIL_MAX_RESULTS=50

# Abilita notifiche di sistema (true/false)
NOTIFICATIONS_ENABLED=true

# Abilita cache locale (true/false)
CACHE_ENABLED=true

# TTL cache in secondi (default: 300)
CACHE_TTL=300

# ── Jira ──────────────────────────────────────────
# Username Jira (email dell'account Atlassian)
JIRA_USERNAME=mario@azienda.com

# API Token generato su id.atlassian.com
JIRA_API_TOKEN=il-tuo-token-atlassian

# URL base dell'istanza Jira
JIRA_BASE_URL=https://nomeazienda.atlassian.net

# Chiave progetto Jira di default (es. PROJ)
JIRA_DEFAULT_PROJECT=PROJ

# ID account Jira dell'utente (per pre-filtrare "assegnati a me")
JIRA_ACCOUNT_ID=

# Intervallo polling Jira in secondi (default: 120)
JIRA_POLL_INTERVAL=120

# Numero massimo issue da caricare per pagina
JIRA_MAX_RESULTS=50
```

---

## 5. Interfaccia Utente

### 5.1 Layout Generale

```
┌──────────────────────────────────────────────────────────────────────────┐
│  Workspace TUI  │  [1] Gmail  [2] Chat  [3] Calendar  [4] Drive [5] Jira │
├──────────────────────────────────────────────────────────────────────────┤
│                                                                           │
│                       [CONTENUTO TAB ATTIVA]                              │
│                                                                           │
├──────────────────────────────────────────────────────────────────────────┤
│ Stato: Connesso  │  mario@azienda.com  │  Ultime notifiche: ...           │
└──────────────────────────────────────────────────────────────────────────┘
```

### 5.2 Navigazione Globale tra Tab

| Tasto | Azione |
|---|---|
| `1` | Vai alla tab Gmail |
| `2` | Vai alla tab Chat |
| `3` | Vai alla tab Calendar |
| `4` | Vai alla tab Drive |
| `5` | Vai alla tab Jira |
| `Tab` | Passa al pannello successivo nella tab corrente |
| `Shift+Tab` | Passa al pannello precedente |
| `q` | Esci dall'applicazione (con conferma) |
| `?` | Mostra help globale |
| `r` | Ricarica i dati della tab corrente |

### 5.3 Status Bar (sempre visibile)

La barra di stato in basso mostra:
- Stato connessione (Connesso / Errore / Sincronizzando...)
- Account email attivo
- Numero email non lette (aggiornato in tempo reale)
- Numero issue Jira assegnate e in corso
- Ultimo aggiornamento
- Shortcut contestuali della vista corrente

---

## 6. Tab Gmail

### 6.1 Layout a Tre Pannelli

```
┌──────────────┬───────────────────────────┬─────────────────────┐
│  CARTELLE    │       LISTA EMAIL          │   ANTEPRIMA EMAIL   │
│              │                            │                     │
│ > In arrivo  │ ● Da: Mario Rossi          │ Da: mario@...       │
│   Inviati    │   Obj: Riunione domani     │ A: me@...           │
│   Bozze      │   Oggi 14:32              │ Data: ...           │
│   Spam       │                            │                     │
│   Cestino    │ ● Da: Anna Bianchi         │ [CORPO EMAIL]       │
│              │   Obj: Fattura Q1          │                     │
│ [LABEL]      │   Ieri                     │                     │
│ Lavoro       │                            │                     │
│ Personale    │   Da: Newsletter           │                     │
│              │   Obj: Aggiornamenti       │                     │
│              │   3 giorni fa              │                     │
└──────────────┴───────────────────────────┴─────────────────────┘
```

### 6.2 Funzionalità

#### Pannello Cartelle
- Lista di cartelle standard Gmail: In arrivo, Inviati, Bozze, Spam, Cestino
- Lista label personalizzate dell'utente
- Numero email non lette accanto a ogni cartella
- Navigazione con `j`/`k` o frecce
- `Invio` per selezionare la cartella

#### Pannello Lista Email
- Lista email della cartella selezionata
- Per ogni email: mittente, oggetto, data, indicatore di non letto (●)
- Paginazione: carica le prossime email con `PageDown`
- Ricerca inline con `/` (cerca per oggetto, mittente, corpo)
- Navigazione con `j`/`k`
- `Invio` per aprire l'anteprima nel pannello destro
- `o` per aprire l'email a tutto schermo

#### Pannello Anteprima
- Intestazioni: Da, A, CC, Data, Oggetto
- Corpo email renderizzato (HTML → testo con `html2text`)
- Scroll con `j`/`k` o frecce
- Allegati elencati in fondo con dimensione

### 6.3 Shortcut Gmail

| Tasto | Azione |
|---|---|
| `c` | Componi nuova email |
| `r` | Rispondi all'email selezionata |
| `R` | Rispondi a tutti |
| `f` | Inoltra |
| `d` | Sposta nel cestino |
| `e` | Archivia |
| `m` | Segna come letto/non letto |
| `s` | Segna/rimuovi stella |
| `l` | Applica label |
| `/` | Cerca email |
| `Esc` | Chiudi ricerca / torna al pannello precedente |
| `n` | Prossima email |
| `p` | Email precedente |
| `a` | Scarica allegato selezionato |

### 6.4 Modal di Composizione Email

Aperto con `c`, `r`, `R`, `f`. Campi:

```
┌─────────────────────────────────────────────────────┐
│  NUOVA EMAIL                                        │
│                                                     │
│  A:      [                                        ] │
│  CC:     [                                        ] │
│  Oggetto:[                                        ] │
│                                                     │
│  ┌─────────────────────────────────────────────┐   │
│  │                                             │   │
│  │   [corpo del messaggio]                     │   │
│  │                                             │   │
│  └─────────────────────────────────────────────┘   │
│                                                     │
│  [Ctrl+Invio] Invia   [Ctrl+S] Salva bozza         │
│  [Esc] Annulla                                      │
└─────────────────────────────────────────────────────┘
```

- Autocompletamento indirizzi dalla rubrica Gmail
- `Ctrl+Invio` per inviare
- `Ctrl+S` per salvare come bozza
- `Esc` per chiudere con conferma se ci sono modifiche

### 6.5 Funzionalità API Gmail Utilizzate

```python
# Endpoint principali da implementare
gmail.users().labels().list()           # Lista cartelle/label
gmail.users().messages().list()         # Lista email
gmail.users().messages().get()          # Dettaglio singola email
gmail.users().messages().send()         # Invia email
gmail.users().messages().modify()       # Archivia, segna letto, applica label
gmail.users().messages().trash()        # Sposta nel cestino
gmail.users().drafts().create()         # Crea bozza
gmail.users().drafts().send()           # Invia bozza
gmail.users().messages().attachments().get()  # Scarica allegato
```

---

## 7. Tab Google Chat

### 7.1 Layout

```
┌─────────────────────┬───────────────────────────────────────────┐
│   SPAZI / DM        │          CONVERSAZIONE                    │
│                     │                                           │
│ MESSAGGI DIRETTI    │  ┌───────────────────────────────────┐   │
│ > Mario Rossi    ●  │  │ Mario Rossi - 14:32               │   │
│   Anna Bianchi      │  │ Ciao, hai visto il documento?     │   │
│   Luca Verdi        │  └───────────────────────────────────┘   │
│                     │  ┌───────────────────────────────────┐   │
│ SPAZI               │  │ Tu - 14:35                        │   │
│ > Team Dev       ●  │  │ Sì, lo sto revisionando           │   │
│   Marketing         │  └───────────────────────────────────┘   │
│   Generale          │                                           │
│                     │  ┌─────────────────────────────────────┐ │
│                     │  │ [Scrivi un messaggio...]            │ │
│                     │  │                          [Invio]    │ │
│                     │  └─────────────────────────────────────┘ │
└─────────────────────┴───────────────────────────────────────────┘
```

### 7.2 Funzionalità

#### Pannello Spazi/DM
- Lista messaggi diretti con indicatore non letto (●)
- Lista spazi (spaces) di cui l'utente fa parte
- Navigazione con `j`/`k`
- `Invio` per aprire la conversazione

#### Pannello Conversazione
- Visualizzazione cronologica messaggi con nome mittente e timestamp
- Scroll con `j`/`k` o frecce
- Area di input testo in basso
- Invio messaggio con `Invio`
- Nuova riga con `Shift+Invio`

### 7.3 Shortcut Chat

| Tasto | Azione |
|---|---|
| `i` | Vai all'area di input (insert mode) |
| `Esc` | Torna alla navigazione messaggi |
| `Invio` (su lista) | Apri conversazione selezionata |
| `g` | Vai all'inizio della conversazione |
| `G` | Vai alla fine (messaggio più recente) |
| `n` | Prossima conversazione con non letti |

### 7.4 Funzionalità API Google Chat Utilizzate

```python
# Endpoint principali
chat.spaces().list()                          # Lista spazi
chat.spaces().messages().list()               # Lista messaggi in uno spazio
chat.spaces().messages().create()             # Invia messaggio
chat.spaces().members().list()                # Membri di uno spazio
```

**Nota:** Google Chat API non supporta notifiche push per client non-bot. Usare polling ogni `CHAT_POLL_INTERVAL` secondi per verificare nuovi messaggi.

---

## 8. Tab Google Calendar

### 8.1 Layout

```
┌─────────────────────────────────────────────────────────────────┐
│  [Settimana]  [Mese]  [Agenda]          < Aprile 2026 >        │
├─────────────────────────────────────────────────────────────────┤
│  Lun 27   Mar 28    Mer 29    Gio 30    Ven 1    Sab 2   Dom 3 │
├──────────┬──────────┬──────────┬──────────┬─────────┬──────────┤
│ 09:00    │          │          │          │         │          │
│          │ Riunione │          │          │         │          │
│          │ team     │          │          │         │          │
│ 10:00    │          │ Call     │          │         │          │
│          │          │ cliente  │          │         │          │
│ 11:00    │          │          │          │         │          │
│          │          │          │ Review   │         │          │
│ 12:00    │          │          │          │         │          │
└──────────┴──────────┴──────────┴──────────┴─────────┴──────────┘
```

### 8.2 Viste Disponibili

- **Agenda**: lista testuale degli eventi dei prossimi 30 giorni (vista default)
- **Settimana**: griglia settimanale con slot orari
- **Mese**: griglia mensile con eventi compatti

### 8.3 Funzionalità

- Navigazione tra periodi con `h`/`l` (precedente/successivo)
- Selezione giorno con `Invio` per vedere dettagli
- Creazione nuovo evento con `c`
- Modifica evento con `e`
- Eliminazione evento con `d` (con conferma)
- Calendari multipli mostrati con colori diversi (se il terminale supporta 256 colori)
- Vista dettaglio evento (modal): titolo, orario, luogo, descrizione, partecipanti, link Meet

### 8.4 Modal Creazione/Modifica Evento

```
┌───────────────────────────────────────────────────┐
│  NUOVO EVENTO                                     │
│                                                   │
│  Titolo:   [                                    ] │
│  Data:     [GG/MM/AAAA]                           │
│  Inizio:   [HH:MM]    Fine: [HH:MM]               │
│  Luogo:    [                                    ] │
│  Note:     [                                    ] │
│  Partec.:  [email, separati da virgola          ] │
│                                                   │
│  [Ctrl+Invio] Salva   [Esc] Annulla               │
└───────────────────────────────────────────────────┘
```

### 8.5 Shortcut Calendar

| Tasto | Azione |
|---|---|
| `h` | Periodo precedente |
| `l` | Periodo successivo |
| `t` | Vai a oggi |
| `c` | Crea nuovo evento |
| `e` | Modifica evento selezionato |
| `d` | Elimina evento selezionato |
| `v` | Cambia vista (Agenda → Settimana → Mese) |
| `Invio` | Dettaglio evento |

### 8.6 Funzionalità API Google Calendar Utilizzate

```python
calendar.calendarList().list()              # Lista calendari dell'utente
calendar.events().list()                    # Lista eventi
calendar.events().get()                     # Dettaglio singolo evento
calendar.events().insert()                  # Crea evento
calendar.events().update()                  # Modifica evento
calendar.events().delete()                  # Elimina evento
```

---

## 9. Tab Google Drive

### 9.1 Layout

```
┌───────────────────────┬─────────────────────────────────────────┐
│   BREADCRUMB          │  DETTAGLIO / ANTEPRIMA                  │
│   Il mio Drive > ... │                                         │
├───────────────────────┤  Nome:    Presentazione Q1.pptx         │
│ 📁 Documenti          │  Tipo:    PowerPoint                    │
│ 📁 Progetti           │  Dim.:    2.4 MB                        │
│ 📄 Report.docx        │  Modif.:  25/04/2026 10:32             │
│ 📄 Budget.xlsx        │  Prop.:   mario@azienda.com            │
│ 📄 Note.txt           │                                         │
│ 📁 Archivio           │  [Invio] Apri  [d] Download            │
│                       │  [i] Condividi info                    │
│                       │                                         │
└───────────────────────┴─────────────────────────────────────────┘
```

### 9.2 Funzionalità

#### Pannello Browser File
- Navigazione cartelle con struttura ad albero
- Icone per tipo file (📁 cartella, 📄 documento, 📊 foglio, ecc.)
- Nome file, data ultima modifica, dimensione
- Navigazione con `j`/`k`
- `Invio` per entrare in una cartella
- `Backspace` per tornare alla cartella superiore
- Ricerca file con `/`
- Vista "Recenti" accessibile con `R`
- Vista "Condivisi con me" accessibile con `S`

#### Pannello Dettaglio
- Metadati del file selezionato
- Download file con `d` (salva in `~/Downloads/`)
- Upload file con `u` (apre prompt per inserire percorso locale)
- Per Google Docs/Sheets/Slides: esporta in formato testuale/CSV per visualizzazione

### 9.3 Shortcut Drive

| Tasto | Azione |
|---|---|
| `Invio` | Entra nella cartella / dettaglio file |
| `Backspace` | Vai alla cartella superiore |
| `d` | Scarica file selezionato |
| `u` | Carica file (prompt percorso) |
| `R` | Vista Recenti |
| `S` | Vista Condivisi con me |
| `M` | Vista Il mio Drive (root) |
| `/` | Cerca in Drive |
| `i` | Mostra dettagli completi |

### 9.4 Funzionalità API Google Drive Utilizzate

```python
drive.files().list()        # Lista file e cartelle
drive.files().get()         # Metadati file
drive.files().export()      # Esporta Google Docs/Sheets in formato leggibile
drive.files().get_media()   # Download file binario
drive.files().create()      # Upload nuovo file
```

**Formati di export:**
- Google Docs → `text/plain`
- Google Sheets → `text/csv`
- Google Slides → `text/plain` (outline)

---

## 10. Tab Jira

### 10.1 Autenticazione Jira

Jira usa un sistema di autenticazione **separato e indipendente** da Google OAuth2. Non richiede browser né flussi OAuth — usa HTTP Basic Auth con API Token.

Il modulo `auth/jira_auth.py` deve:
- Leggere `JIRA_USERNAME` e `JIRA_API_TOKEN` dal file `.env`
- Costruire l'header `Authorization: Basic base64(username:token)` per ogni richiesta
- Esporre un client `requests.Session` preconfigurato con base URL e headers
- Non salvare mai il token in chiaro nei log

L'utente genera il token su `https://id.atlassian.com/manage-profile/security/api-tokens` (operazione manuale una-tantum, documentata nel README).

### 10.2 Layout

```
┌─────────────────────────┬──────────────────────────────────────────────┐
│   FILTRI / ISSUE LIST   │          DETTAGLIO ISSUE                     │
│                         │                                              │
│ [Progetto: PROJ     ▼]  │  PROJ-142 · Task · Priorità: Media          │
│ [Stato: In corso    ▼]  │  Integrare OAuth2 con Gmail API              │
│ [Assegnato: me      ▼]  │                                              │
│ [/ cerca o JQL]         │  Assegnato: mario@azienda.com                │
│                         │  Sprint: Sprint 14                           │
│ PROJ-142  In corso  ●   │  Stima: 3h  │  Logged: 2h 30m               │
│ Integrare OAuth2...     │                                              │
│                         │  ┌─ Descrizione ──────────────────────────┐ │
│ PROJ-138  Review        │  │ Implementare il flusso di              │ │
│ Fix: token refresh...   │  │ autenticazione OAuth2...               │ │
│                         │  └────────────────────────────────────────┘ │
│ PROJ-145  To Do         │                                              │
│ Crash su allegati...    │  [Tab] Commenti  [Tab] Worklogs  [Tab] Link  │
│                         │                                              │
│ PROJ-147  To Do         │  ── Worklogs ──────────────────────────────  │
│ Aggiungere tab Drive    │  1h 30m · mario · ieri 16:45               │
│                         │  Implementato flusso base...                │
│ PROJ-112  In corso  ●   │                                              │
│ Ricerca JQL avanzata    │  1h · mario · oggi 09:30                    │
│                         │  Aggiunto auto-refresh...                   │
└─────────────────────────┴──────────────────────────────────────────────┘
```

### 10.3 Pannello Sinistro — Issue List

**Filtri in cima al pannello:**
- Dropdown progetto (pre-seleziona `JIRA_DEFAULT_PROJECT`)
- Dropdown stato (To Do / In corso / In Review / Done / Tutti)
- Dropdown assegnato (Me / Tutti / utente specifico)
- Campo ricerca testo libero o JQL (attivato con `/`)

**Lista issue:**
- Per ogni issue: chiave (`PROJ-142`), summary, badge stato, indicatore non letta (●)
- Colori badge: To Do = grigio, In corso = blu, In Review = viola, Done = verde, Bug = rosso
- Ordinamento default: aggiornate di recente prima
- Navigazione con `j`/`k`
- `Invio` per aprire il dettaglio nel pannello destro

**Filtri JQL salvati:**
Definibili nel `.env` come lista, es:
```env
JIRA_SAVED_JQL_1=assignee = currentUser() AND status != Done
JIRA_SAVED_JQL_2=project = PROJ AND sprint in openSprints()
```
Accessibili con `F1`, `F2`, ecc. direttamente dalla tab.

### 10.4 Pannello Destro — Dettaglio Issue

**Header issue:**
- Chiave, tipo, priorità, summary
- Assegnato, reporter, sprint, data creazione, data aggiornamento

**Tab interne al pannello dettaglio** (navigabili con `Tab`):
- **Descrizione** — testo renderizzato (Jira usa Atlassian Document Format → convertire in testo leggibile)
- **Commenti** — lista commenti con autore, data, testo
- **Worklogs** — lista log ore con durata, autore, data, nota
- **Link** — issue collegate (blocca, è bloccata da, duplica, ecc.)
- **Subtask** — lista subtask con stato

### 10.5 Shortcut Tab Jira

| Tasto | Azione |
|---|---|
| `j` / `k` | Naviga issue nella lista |
| `Invio` | Apri dettaglio issue selezionata |
| `/` | Attiva campo ricerca / JQL |
| `Esc` | Chiudi ricerca, torna alla lista |
| `c` | Crea nuova issue (modal) |
| `t` | Transizione stato issue selezionata (modal con stati disponibili) |
| `w` | Log ore sull'issue selezionata (modal worklog) |
| `C` | Aggiungi commento all'issue selezionata |
| `e` | Modifica summary o priorità issue |
| `a` | Cambia assegnatario |
| `o` | Apri issue nel browser |
| `F1`–`F9` | Applica filtro JQL salvato corrispondente |
| `r` | Ricarica lista issue |
| `g` | Vai alla prima issue della lista |
| `G` | Vai all'ultima issue della lista |

### 10.6 Modal Log Ore (`w`)

```
┌───────────────────────────────────────┐
│  LOG ORE — PROJ-142                   │
│                                       │
│  Tempo:   [1h 30m                   ] │
│  Data:    [27/04/2026               ] │
│  Note:    [Implementato flusso...   ] │
│                                       │
│  [Ctrl+Invio] Salva   [Esc] Annulla   │
└───────────────────────────────────────┘
```

- Il campo Tempo accetta formato Jira standard: `1h 30m`, `2h`, `45m`, `1d`
- Data default: oggi
- La nota è opzionale

### 10.7 Modal Transizione Stato (`t`)

```
┌──────────────────────────────────┐
│  CAMBIA STATO — PROJ-142         │
│  Stato attuale: In corso         │
│                                  │
│  > In Review                     │
│    Done                          │
│    To Do                         │
│                                  │
│  [Invio] Conferma  [Esc] Annulla │
└──────────────────────────────────┘
```

Gli stati disponibili vengono recuperati dinamicamente dall'API Jira per quella specifica issue (ogni progetto può avere workflow diversi).

### 10.8 Modal Creazione Issue (`c`)

```
┌──────────────────────────────────────────┐
│  NUOVA ISSUE                             │
│                                          │
│  Progetto:  [PROJ                     ▼] │
│  Tipo:      [Task                     ▼] │
│  Summary:   [                          ] │
│  Priorità:  [Media                    ▼] │
│  Assegnato: [mario@azienda.com        ▼] │
│  Descrizione:                            │
│  ┌──────────────────────────────────┐   │
│  │                                  │   │
│  └──────────────────────────────────┘   │
│                                          │
│  [Ctrl+Invio] Crea   [Esc] Annulla       │
└──────────────────────────────────────────┘
```

### 10.9 Integrazione con Gmail — Deep Link

Quando l'utente visualizza un'email in Gmail che contiene nel testo una chiave Jira (pattern `[A-Z]+-\d+`, es. `PROJ-142`), la status bar mostra un suggerimento:

```
Trovato PROJ-142 nell'email · [5] Vai a Jira
```

Premendo `5` si apre la tab Jira direttamente sull'issue rilevata. Questo collegamento è unidirezionale e basato su pattern matching nel testo dell'email — non richiede API aggiuntive.

### 10.10 Funzionalità API Jira Utilizzate

```python
# Endpoint REST Jira Cloud v3 (base: JIRA_BASE_URL/rest/api/3/)

GET  /myself                                    # Info utente corrente (recupera account ID)
GET  /project                                   # Lista progetti
GET  /issue/{issueKey}                          # Dettaglio issue
GET  /issue/{issueKey}/transitions              # Stati disponibili per transizione
POST /issue/{issueKey}/transitions              # Esegui transizione di stato
GET  /issue/{issueKey}/worklog                  # Lista worklog
POST /issue/{issueKey}/worklog                  # Aggiungi worklog
POST /issue/{issueKey}/comment                  # Aggiungi commento
PUT  /issue/{issueKey}                          # Modifica issue (summary, priorità, assegnato)
POST /issue                                     # Crea nuova issue
GET  /search?jql=...&maxResults=...&startAt=... # Ricerca issue con JQL
GET  /priority                                  # Lista priorità disponibili
GET  /issuetype                                 # Lista tipi issue
GET  /user/search?query=...                     # Cerca utenti per assegnazione
```

**Autenticazione per ogni richiesta:**
```python
import requests
from base64 import b64encode

session = requests.Session()
token = b64encode(f"{JIRA_USERNAME}:{JIRA_API_TOKEN}".encode()).decode()
session.headers.update({
    "Authorization": f"Basic {token}",
    "Content-Type": "application/json",
    "Accept": "application/json",
})
```

### 10.11 Cache Jira

| Dato | TTL |
|---|---|
| Lista issue (per filtro JQL) | 2 minuti |
| Dettaglio singola issue | 1 minuto |
| Lista stati disponibili per issue | 10 minuti |
| Lista progetti | 30 minuti |
| Lista tipi issue e priorità | 30 minuti |
| Worklogs di una issue | 1 minuto |

### 10.12 Polling Jira

Il polling avviene ogni `JIRA_POLL_INTERVAL` secondi. Al polling:
1. Recupera le issue assegnate all'utente con stato != Done aggiornate dall'ultimo poll
2. Se ci sono nuove issue assegnate → notifica di sistema Ubuntu
3. Se ci sono issue con commenti nuovi → aggiorna indicatore (●) nella lista
4. Aggiorna il contatore nella status bar

---

## 11. Sistema di Notifiche

### 11.1 Comportamento

Le notifiche di sistema Ubuntu vengono mostrate tramite `plyer` nei seguenti casi:

| Evento | Condizione |
|---|---|
| Nuova email | Email non letta arrivata durante il polling Gmail |
| Nuovo messaggio Chat | Messaggio non letto in un DM o spazio |
| Evento imminente | 10 minuti prima dell'inizio di un evento Calendar |
| Nuova issue Jira assegnata | Issue assegnata all'utente rilevata dal polling |
| Commento su issue Jira | Nuovo commento su una issue assegnata all'utente |

### 11.2 Implementazione

```python
# notifier.py
from plyer import notification

def notify(title: str, message: str, timeout: int = 5):
    notification.notify(
        title=title,
        message=message,
        app_name="Workspace TUI",
        timeout=timeout
    )
```

Le notifiche sono disabilitabili via `NOTIFICATIONS_ENABLED=false` nel `.env`.

---

## 12. Cache Locale

### 12.1 Strategia

Usare `diskcache` per ridurre le chiamate API e migliorare la reattività:

| Dato | TTL |
|---|---|
| Lista email (per cartella) | 60 secondi |
| Corpo singola email | 10 minuti |
| Lista spazi/DM Chat | 5 minuti |
| Messaggi Chat | 30 secondi |
| Lista eventi Calendar | 5 minuti |
| Lista file Drive | 2 minuti |
| Metadati file Drive | 5 minuti |
| Lista issue Jira (per filtro) | 2 minuti |
| Dettaglio issue Jira | 1 minuto |
| Metadati Jira (progetti, tipi, priorità) | 30 minuti |

### 12.2 Invalidazione

La cache viene invalidata manualmente quando l'utente preme `r` (reload) nella tab corrente, o automaticamente quando l'utente compie un'azione di scrittura (invia email, crea evento, crea/aggiorna issue, ecc.).

---

## 13. Gestione Errori

### 13.1 Errori API Google

Tutti i servizi Google devono gestire:

- `HttpError 401` → token scaduto → refresh automatico → retry
- `HttpError 403` → permessi insufficienti → messaggio all'utente
- `HttpError 429` → rate limit → backoff esponenziale (1s, 2s, 4s, max 30s)
- `HttpError 5xx` → errore server → retry con backoff → messaggio se persiste
- `ConnectionError` → nessuna connessione → mostrare stato "Offline" nella status bar

### 13.2 Errori API Jira

- `HTTP 401` → token non valido o scaduto → messaggio guidato per rigenerare il token
- `HTTP 403` → permessi insufficienti sull'issue o progetto → messaggio all'utente
- `HTTP 404` → issue non trovata → messaggio all'utente
- `HTTP 429` → rate limit → backoff esponenziale (1s, 2s, 4s, max 30s)
- `HTTP 5xx` → errore Atlassian → retry con backoff → messaggio se persiste
- `ConnectionError` → mostrare stato "Jira: Offline" nella status bar

### 13.3 Visualizzazione Errori nel TUI

Gli errori non bloccano l'interfaccia. Vengono mostrati come:
- Banner rosso temporaneo (5 secondi) in cima all'area contenuto
- Messaggio nella status bar
- Log dettagliato in `~/.local/share/workspace-tui/logs/app.log`

---

## 14. Avvio e Installazione

### 14.1 Script di Installazione (`install.sh`)

Creare uno script shell che:
1. Controlla che Python 3.11+ sia installato
2. Crea un virtual environment in `.venv/`
3. Installa le dipendenze da `requirements.txt`
4. Crea la cartella `credentials/` se non esiste
5. Copia `.env.example` in `.env` se non esiste
6. Crea uno script `workspace-tui` in `/usr/local/bin/` per avviare l'app da qualsiasi directory

### 14.2 Avvio

```bash
workspace-tui
```

oppure direttamente:

```bash
cd gmail-tui && python main.py
```

### 14.3 Sequenza di Avvio

1. Carica configurazione da `.env`
2. Verifica esistenza `credentials/client_secret.json` → errore guidato se mancante
3. Verifica presenza di `JIRA_USERNAME`, `JIRA_API_TOKEN`, `JIRA_BASE_URL` → se mancanti la tab Jira viene disabilitata con messaggio esplicativo, le altre tab funzionano normalmente
4. Carica token OAuth2 Google o avvia flusso di login browser
5. Inizializza i client API Google e il client Jira (se configurato)
6. Avvia l'app Textual
7. Mostra la tab Gmail con i dati iniziali
8. Avvia i worker di polling in background (async) per tutti i servizi attivi

---

## 15. README

Il progetto deve includere un `README.md` completo con:

1. Screenshot/demo ASCII dell'interfaccia con tutte e 5 le tab
2. Prerequisiti (Python 3.11+, account Google Workspace, account Atlassian)
3. Istruzioni step-by-step per il setup di Google Cloud (abilitare API, creare credenziali OAuth2)
4. Istruzioni step-by-step per generare l'API Token Atlassian su `id.atlassian.com`
5. Istruzioni di installazione
6. Guida rapida ai shortcut per tutte le tab
7. Risoluzione problemi comuni
8. Limitazioni note

---

## 16. Vincoli e Note Implementative

- **Non usare `asyncio.run()` nel codice Textual**: Textual gestisce il proprio event loop. Usare `self.run_worker()` e `await` nei metodi dell'app.
- **Thread safety**: le chiamate API devono avvenire in worker thread separati, mai nel thread UI principale, per non bloccare il rendering.
- **Nessun dato sensibile nel codice**: token, client secret, API token Jira e indirizzi email non devono mai apparire in log o output visibile all'utente.
- **Google Docs/Sheets non sono editabili nel TUI**: l'applicazione supporta solo visualizzazione e download. Non tentare di implementare un editor per questi formati.
- **Google Chat API limitazioni**: l'API Chat è progettata per bot. Alcune funzionalità (es. reazioni ai messaggi, thread) possono avere limitazioni. Implementare solo: lettura messaggi, invio messaggio di testo, lista spazi.
- **Jira: Atlassian Document Format**: le descrizioni delle issue sono in formato ADF (JSON). Convertirle in testo leggibile estraendo i nodi di tipo `text` ricorsivamente. Non tentare un rendering completo.
- **Jira opzionale**: se le variabili Jira non sono configurate nel `.env`, la tab `[5] Jira` deve essere visibile ma disabilitata, con messaggio "Configura JIRA_USERNAME, JIRA_API_TOKEN e JIRA_BASE_URL nel file .env per abilitare questa tab."
- **Deep link Gmail → Jira**: il pattern matching per le chiavi Jira nell'anteprima email deve essere configurabile tramite `JIRA_DEFAULT_PROJECT` nel `.env` (es. se `JIRA_DEFAULT_PROJECT=PROJ`, cerca pattern `PROJ-\d+`).
- **Compatibilità terminale**: l'app deve funzionare su terminali con supporto a 256 colori. Testare su `gnome-terminal`, `xterm-256color`, e via SSH con `tmux`.
- **Dimensione minima terminale**: l'app richiede almeno 120 colonne × 40 righe. Mostrare un errore chiaro se il terminale è troppo piccolo.

---

*Fine del documento di specifiche — versione 2.0*
