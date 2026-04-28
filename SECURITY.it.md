[English](SECURITY.md) | **Italiano**

# Policy di Sicurezza

## Versioni supportate

| Versione | Supportata |
|----------|------------|
| 0.1.x    | Sì         |

## Segnalare una vulnerabilità

Usa [GitHub Security Advisories](https://github.com/AndreaBonn/my-workplace-tui/security/advisories/new) per segnalare vulnerabilità in modo privato.

Non aprire issue pubbliche per vulnerabilità di sicurezza.

### Cosa includere

- Descrizione della vulnerabilità
- Passi per riprodurla
- Versione/i affette
- Valutazione dell'impatto (cosa potrebbe ottenere un attaccante)

### Tempi di risposta

- Conferma ricezione: entro 72 ore
- Fix per vulnerabilità critiche: obiettivo 30 giorni dalla segnalazione
- Disclosure pubblica: coordinata dopo il rilascio del fix

## Misure di sicurezza implementate

Le seguenti misure sono state verificate nel codice sorgente:

- **Permessi file token OAuth2**: i token sono salvati con permessi `0600`, leggibili solo dal proprietario del file (`auth/oauth.py:95`)
- **HTTPS obbligatorio per Jira**: le connessioni a Jira rifiutano URL non-HTTPS per default; il testo in chiaro è consentito solo con opt-in esplicito via `JIRA_ALLOW_HTTP=true` (`auth/jira_auth.py:46-55`)
- **Nessun secret hardcoded**: tutte le credenziali sono caricate da `.env` tramite pydantic-settings (`config/settings.py`); `.env` e `credentials/` sono esclusi dal version control (`.gitignore`)
- **Validazione input**: intervalli di polling e path dei file sono validati all'avvio tramite field validator Pydantic (`config/settings.py:80-97`)
- **Lockfile dipendenze**: `uv.lock` fissa le versioni di tutte le dipendenze transitive

## Buone pratiche per gli utenti

- Conserva `credentials/client_secret.json` e `.env` fuori dal version control. Il `.gitignore` li esclude già, ma verifica se usi un setup personalizzato.
- La cache locale (`~/.local/share/workspace-tui/cache/`) contiene dati API non cifrati (snippet email, eventi calendario, riassunti issue Jira). Proteggila con permessi filesystem appropriati.
- Gli scope OAuth2 includono accesso in scrittura (`gmail.modify`, `calendar`, `drive`). Consulta `auth/oauth.py:10-16` per la lista completa.
- Ruota periodicamente i token API Jira tramite [impostazioni account Atlassian](https://id.atlassian.com/manage-profile/security/api-tokens).

## Fuori ambito

I seguenti casi non sono considerati vulnerabilità per questo progetto:

- Attacchi che richiedono accesso fisico alla macchina
- Ingegneria sociale
- Self-XSS o attacchi che richiedono all'utente di eseguire comandi arbitrari sul proprio terminale
- Vulnerabilità in dipendenze di terze parti già divulgate pubblicamente (segnalare a monte)
- Problemi che richiedono un account Google o Atlassian compromesso

## Ringraziamenti

Nessuna vulnerabilità di sicurezza è stata segnalata finora.

---

[Torna al README](README.it.md)
