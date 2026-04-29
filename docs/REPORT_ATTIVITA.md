# Report Attività — Workspace TUI

Data creazione: 2026-04-29

---

## 2026-04-29 | Sessione #1 [UI]

### Richiesta

Dashboard UI polish: layout senza Jira troppo vuoto, 70% spazio inutilizzato.

### Azioni Eseguite

1. Aggiunto metodo `_render_no_jira` in `dashboard_tab.py` che collassa il layout quando Jira non è disponibile
2. Nascosti pannelli vuoti (time-tracking, weekly-chart, tasks) impostandoli a stringa vuota
3. Quick Stats mostrate con hint di configurazione Jira (variabili `.env`)
4. Rimossi guard ridondanti `if not metrics.jira_available` dai metodi render individuali (ora gestiti a monte)
5. Messaggio "Jira non configurato" eliminato dalla duplicazione — mostrato una sola volta

### File Modificati

| File | Tipo | Descrizione |
|------|------|-------------|
| `src/workspace_tui/ui/tabs/dashboard_tab.py` | Modifica | Layout collassato per caso no-Jira, hint configurazione |

### Note per il Cliente

Quando Jira non è configurato, la dashboard ora mostra solo le informazioni disponibili (email, meeting) in modo compatto, con istruzioni chiare su come attivare il time tracking. Niente più spazio bianco inutilizzato.

### Riepilogo

Complessità: Bassa | Stato: Completato
