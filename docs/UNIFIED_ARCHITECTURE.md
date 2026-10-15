# Unified Application Architecture

## 1. Architectural Blueprint

The unified application integrates the repository intelligence, AST analyzers, and PR gate infrastructure of **Project B** with the live command-scanning engine, interactive terminal HUD, and network/log triage tools of **Project A**.

```mermaid
flowchart TD
    subgraph Client["Unified Frontend (React 19 + TypeScript + Vite)"]
        UI_Nav["Main Navigation (Layout.tsx)"]
        UI_Dash["Overview Dashboard"]
        UI_Hub["Project Hub & Memory"]
        UI_Passport["Security Passport & Scans"]
        UI_Terminal["Live Security Terminal & Runner"]
        UI_Analyzer["Ad-hoc ZIP & Log Analyzer"]
        UI_Diag["URL & Edge Diagnostics"]
        UI_Settings["Target & Scanner Settings"]
    end

    subgraph Gateway["FastAPI Canonical API Gateway"]
        Auth_MW["JWT Auth & RBAC Middleware"]
        CORS_MW["Strict CORS Middleware"]
        API_Repos["/repositories (Git Intelligence)"]
        API_Scans["/scans & /analyzers (Code AST)"]
        API_Runs["/runs (Live Subprocess & WS Streaming)"]
        API_Diag["/runs/url-speed-test (Diagnostics)"]
        API_Targets["/targets & /commands (Allowlists)"]
        API_Hub["/project-hub (Memory & Releases)"]
        API_Reports["/reports (PDF & CSV Export)"]
    end

    subgraph Services["Core Backend Services"]
        UnivScanner["Universal Scanner (SAST, Secrets, OSV Deps, Lic)"]
        AnalyzerReg["AST Analyzer Registry (12 Analyzers)"]
        CmdRunner["Sandboxed Command Runner (Allowlisted Execution)"]
        RiskEngine["Traceable Risk Scoring Engine"]
        PdfGen["ReportLab & Canvas PDF Generator"]
        AIService["AI Provider Service (Gemini / OpenAI Fallback)"]
        EventBus["In-Memory Event Bus & Notifications"]
    end

    subgraph Storage["Data Persistence"]
        DB[(PostgreSQL / SQLite via SQLAlchemy & Alembic)]
        FileCache[Temporary Isolated Scan Workspaces]
    end

    Client -->|REST & WebSockets| Gateway
    Gateway --> Auth_MW
    Auth_MW --> Services
    Services --> Storage
```

---

## 2. Request & Execution Flows

### 2.1 Repository Analysis & Commit Scanning Flow
1. **Trigger:** User registers a repository or background poller detects a new commit SHA on GitHub.
2. **Worker Execution:** `workers/scan_job.py` fetches commit tree into an isolated, safe temporary workspace.
3. **Multi-Engine Scan:**
   - `UniversalScanner` runs regex + AST scanners (detects hardcoded keys, high-entropy secrets, and SAST injection flaws).
   - `OSV API Batch Query` resolves dependencies declared in `package.json`, `requirements.txt`, etc., identifying known CVEs.
   - `Registry` executes active code analyzers (`ApiContractAnalyzer`, `DatabaseMigrationAnalyzer`, `CicdDeploymentAnalyzer`, etc.).
4. **Scoring & Normalization:** Findings are deduplicated using cryptographic fingerprints (`sha256(type + path + line)`), stored with foreign keys to the scan record, and `RiskScoreEngine` updates the repository risk posture.
5. **Notification:** Results are emitted via `EventBus` to notify connected clients.

### 2.2 Live Security Tool Execution Flow (WebSocket Streaming)
1. **Initiation:** Authenticated user selects a registered `Target` and approved `CommandConfig` in `/scanner`.
2. **Validation:** Backend verifies user permissions, validates target host against an RFC-compliant regex, and checks requested arguments against `CommandConfig.allowed_args`.
3. **Execution:** `CommandRunner` executes the executable without shell invocation (`shell=False`) under strict timeout limits.
4. **Streaming:** Process stdout/stderr chunks are forwarded in real time over WebSocket to the frontend terminal HUD.
5. **Pattern Analysis:** `OutputAnalyzer` matches regex rules on the fly, creating structured findings and writing the completed `RunHistory` to the database.

### 2.3 Ad-Hoc ZIP & Log Triage Flow
1. **Client Decompression:** The browser unzips the uploaded archive using `fflate` in chunks, ignoring binary assets, lockfiles, and `node_modules/`.
2. **Analysis Request:** Filtered text is sent to `/runs/analyze-manual`.
3. **Inspection:** Deterministic pattern recognition categorizes errors (e.g., prototype pollution, XSS, unhandled promises, leaked credentials).
4. **Remediation Advice:** Actionable guidance is generated locally; optional "Generate AI Fix" calls `AIProviderService` for detailed diff proposals.
5. **Export:** Reports can be exported to server-generated PDF or downloaded instantly as CSV/JSON.

---

## 3. Database Architecture & Relationships

```mermaid
erDiagram
    users ||--o{ repositories : owns
    users ||--o{ targets : manages
    users ||--o{ run_history : triggers
    users ||--o{ notifications : receives
    repositories ||--o{ commits : contains
    commits ||--o{ scans : triggers
    scans ||--o{ findings : produces
    scans ||--|| risk_scores : calculates
    scans ||--|| commit_analyses : details
    targets ||--o{ run_history : targets
    command_configs ||--o{ run_history : executes

    users {
        int id PK
        string username
        string email
        string hashed_password
        string role "ADMIN, ANALYST, VIEWER"
        boolean is_active
    }

    targets {
        int id PK
        int user_id FK
        string name
        string host
        string description
        datetime created_at
    }

    command_configs {
        int id PK
        string name
        string executable
        string allowed_args "JSON"
        int timeout_seconds
        string regex_rules "JSON"
    }

    run_history {
        int id PK
        int command_id FK
        int target_id FK
        int user_id FK
        string status
        datetime start_time
        datetime end_time
        text raw_output
        text findings "JSON"
    }
```

---

## 4. Key Security Controls

1. **Strict Subprocess Containment:**
   - No `shell=True`.
   - Arguments must be exact matches from `CommandConfig.allowed_args`.
   - Target hostnames must match `^[a-zA-Z0-9.-]+$` (or IPv4/IPv6).
   - Timeouts enforce termination of hanging or unresponsive processes.
2. **Safe Archive Processing:**
   - Maximum archive extraction limit (500,000 characters).
   - Explicit exclusion of directory traversals (`..`), symbolic links, binary executables, and dependencies.
3. **AI Safety & Data Privacy:**
   - Backend keys never leave the server.
   - Code excerpts are sanitized of secrets prior to external AI prompt assembly.
   - Graceful deterministic fallbacks ensure core operations never depend on external AI availability.
