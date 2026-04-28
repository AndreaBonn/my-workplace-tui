# Design Decisions e Assumptions

Decisioni prese dove le specifiche erano ambigue o incomplete.

## Google Chat — best-effort

Google Chat API è progettata per bot. L'accesso utente con OAuth2 Desktop funziona solo se l'admin Workspace ha abilitato l'API. Implementata la tab con gestione graceful: se l'API restituisce 403, la tab mostra un messaggio esplicativo senza impattare le altre.

## Ordine di priorità delle slice

Skeleton → Gmail → Jira → Calendar → Drive → Chat → Notifiche. Gmail è il servizio più usato, Jira il secondo per esplicita richiesta.

## Package layout

Usato `src/workspace_tui/` layout invece di flat layout. Permette installazione via pip, import puliti e separazione netta tra sorgente e test.

## uv invece di pip

Usato uv come package manager (con lockfile) invece di pip + requirements.txt. Lo script install.sh installa uv automaticamente se non presente.

## OAuth2 scopes — write access intenzionale

Gli scope OAuth2 richiedono permessi di scrittura (`gmail.modify`, `calendar`, `drive`) e non solo lettura. Motivazione: l'app non è un viewer passivo — consente invio email, creazione eventi, upload file su Drive, transizioni issue Jira. Scope read-only avrebbero richiesto un secondo flusso OAuth al primo tentativo di scrittura, peggiorando la UX. Trade-off accettato: superficie d'attacco più ampia in cambio di single-consent flow. Il token viene salvato con permessi `0600` e la directory credentials è in `.gitignore`.

## Test strategy

Unit test con mock delle API esterne per copertura totale. No test E2E del TUI (complessità sproporzionata per un tool personale). Test di integrazione opzionali con credenziali reali (skippati in CI).
