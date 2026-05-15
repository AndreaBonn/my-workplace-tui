# Architecture

Technical diagrams for Workspace TUI internals. For a high-level overview, see the main [README](../README.md#architecture).

## System Overview

```mermaid
%%{init: {'theme': 'default'}}%%
graph LR
    classDef core fill:#2563eb,stroke:#1d4ed8,color:#fff
    classDef data fill:#d97706,stroke:#b45309,color:#fff
    classDef ext fill:#6b7280,stroke:#4b5563,color:#fff
    classDef engine fill:#059669,stroke:#047857,color:#fff

    user(["User Terminal"]):::ext

    subgraph app["WorkspaceTUI"]
        ui["UI Tabs"]:::core
        svc["Services"]:::core
        base["BaseService"]:::core
        poll["PollManager"]:::engine
        cache["Cache"]:::data
        auth["Auth"]:::engine
        config["Config"]:::data
    end

    subgraph apis["External APIs"]
        google["Google APIs"]:::ext
        jira_api["Jira REST API"]:::ext
    end

    user --> ui
    ui --> svc
    svc --> base
    base --> cache
    base --> apis
    auth --> google
    auth --> jira_api
    poll --> svc
    poll -->|"notify"| user
    config --> auth
    config --> svc
```

**Layers:** Tabs (UI) -> Services (business logic) -> BaseService (retry/cache/error) -> External APIs.

Services never import UI. Tabs receive services via `set_service()`. Config flows inward through pydantic-settings.

## Service Initialization

On `on_mount`, the app spawns a worker thread that authenticates with Google (and optionally Jira), creates service instances, and wires them into tabs via `call_from_thread`. Search and Dashboard services are wired progressively as backends come online.

```mermaid
sequenceDiagram
    participant App as WorkspaceTUI
    participant Worker as Worker Thread
    participant OAuth as OAuth2
    participant Google as Google APIs
    participant Jira as Jira Auth
    participant UI as UI Tabs
    participant Poll as PollManager

    App->>Worker: on_mount spawn
    Worker->>OAuth: load_or_create_credentials
    alt token.json valid
        OAuth-->>Worker: Credentials
    else token expired
        OAuth->>OAuth: refresh
        OAuth-->>Worker: Credentials
    else no token
        OAuth->>Google: run_local_server
        Google-->>OAuth: Authorization code
        OAuth-->>Worker: Credentials
    end

    Worker->>Worker: Create Google services
    Worker->>App: call_from_thread wire Google
    App->>UI: set_service per tab

    alt Jira configured
        Worker->>Jira: create_session per account
        Jira-->>Worker: Sessions
        Worker->>Worker: Create JiraMultiService
        Worker->>App: call_from_thread wire Jira
        App->>UI: set_service jira_tab
    end

    Worker->>App: wire SearchService
    Worker->>App: wire DashboardService
    Worker->>Poll: start
    Poll->>Poll: Timer chains per service
```

Key details:
- OAuth2 token is saved with `chmod 0o600` and auto-refreshed on expiry
- Jira is optional: if not configured, Jira tab shows a placeholder, dashboard adapts
- `_start_polling()` runs last, regardless of individual service failures

## Polling and State-Diffing

`PollManager` runs independent timer chains per service. Each poll fetches fresh data (bypassing cache), diffs against stored state using set difference on IDs, and notifies only on genuinely new items. The first poll after startup populates the baseline silently.

```mermaid
sequenceDiagram
    participant Timer as Timer Thread
    participant Poll as PollManager
    participant Svc as Service
    participant State as PollState
    participant Notifier as Notifier
    participant UI as StatusBar

    loop Every N seconds per service
        Timer->>Poll: _poll_service
        Poll->>Svc: fetch skip_cache=True
        Svc-->>Poll: Current items

        Poll->>State: Compare IDs
        State-->>Poll: New items via set difference

        alt First poll - not initialized
            Poll->>State: Populate baseline
            Note over Poll: Silent, no notification
        else Subsequent poll + new items
            Poll->>Notifier: send title, message
            Notifier-->>Poll: OS notification
        end

        Poll->>State: Update stored IDs
        Poll->>UI: _emit_update PollResult
        Poll->>Timer: Reschedule timer
    end
```

Default intervals: Gmail 60s, Chat 30s, Calendar 300s, Jira 120s (all configurable, minimum 10s).

State-diffing per service:
- **Gmail**: `current_ids - stored_unread_ids` = new unread messages
- **Chat**: last message name per space, compared against stored value
- **Calendar**: 15-minute lookahead window, notified IDs tracked in a pruned set
- **Jira**: `current_keys - stored_known_keys` = newly assigned issues

## BaseService Retry

Every API call goes through `_retry()`, which acquires a per-service lock, classifies errors, and applies exponential backoff for retryable failures.

```mermaid
stateDiagram-v2
    [*] --> api_call : Execute operation

    api_call --> acquire_lock : _api_lock
    acquire_lock --> attempt : attempt = 0

    attempt --> success : Operation OK
    success --> [*] : Return result

    attempt --> classify : Exception raised
    classify --> auth_error : AuthenticationError
    classify --> permission : PermissionDeniedError
    classify --> retryable : RateLimit / Connection / ServerError
    classify --> fatal : Other errors

    auth_error --> refresh : Has callback + attempt 0
    refresh --> attempt : Retry immediately

    auth_error --> raise_err : No callback or already refreshed
    permission --> raise_err : Raise immediately
    fatal --> raise_err : Raise immediately

    retryable --> check_attempts : attempts < max_retries
    check_attempts --> backoff : Yes
    backoff --> attempt : sleep min 2^attempt 30s
    check_attempts --> raise_err : Max retries exceeded

    raise_err --> [*] : Raise exception
```

Error classification (`_categorize_error`):
- Google `HttpError` with `.resp["status"]` -> status-based mapping
- `requests.HTTPError` with `.response.status_code` -> status-based mapping
- String heuristics ("connection", "timeout") -> `ConnectionFailedError`
- Fallback -> generic `ServiceError`

Backoff schedule: 1s, 2s, 4s (capped at 30s), max 3 attempts.

## Jira Multi-Account Routing

`JiraMultiService` wraps N `JiraService` instances. Methods that aggregate data fan out to all accounts in parallel via `ThreadPoolExecutor`. Methods that target a specific issue route to the correct account by extracting the project key and looking it up in a lazily-populated cache.

```mermaid
%%{init: {'theme': 'default'}}%%
graph TD
    classDef core fill:#2563eb,stroke:#1d4ed8,color:#fff
    classDef data fill:#d97706,stroke:#b45309,color:#fff
    classDef ext fill:#6b7280,stroke:#4b5563,color:#fff
    classDef engine fill:#059669,stroke:#047857,color:#fff

    caller["JiraMultiService"]:::core

    caller --> fan_out{"Fan-out method?"}
    fan_out -->|"Yes: search, list_projects"| parallel["ThreadPoolExecutor"]:::engine
    parallel --> svc_a["JiraService A"]:::data
    parallel --> svc_b["JiraService B"]:::data
    parallel --> svc_n["JiraService N"]:::data
    svc_a --> merge["Merge + sort by updated"]:::engine
    svc_b --> merge
    svc_n --> merge

    fan_out -->|"No: get_issue, transition"| resolve["_resolve_service"]:::core
    resolve --> extract_proj["Extract project from key"]:::data
    extract_proj --> cache_lookup{"Project in cache?"}
    cache_lookup -->|"Yes"| route["Route to account"]:::engine
    cache_lookup -->|"No"| populate["_populate_project_map"]:::engine
    populate --> cache_lookup
    route --> target["Target JiraService"]:::data
```

Fan-out methods: `search_issues`, `list_projects`, `get_worklogs_since`, `search_users`.

Delegating methods: `get_issue`, `transition_issue`, `add_worklog`, `add_comment`, `create_issue`, `update_issue`.

Config: `JIRA_ACCOUNTS=acme,widgets` + `JIRA_{NAME}_BASE_URL` + `JIRA_{NAME}_DEFAULT_PROJECT` per account (name uppercased).
