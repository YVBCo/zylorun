# Project Audit: Project A (SecRunner) & Project B (Software Risk Passport)

## Executive Summary

This document presents a comprehensive, ground-truth code audit of two distinct security and developer platforms:
- **Project A (`software-testing-main` / SecRunner):** A specialized command execution, live host security scanning, network benchmarking, and manual log/ZIP vulnerability triage application.
- **Project B (`tester` / GitFlow - Software Risk Passport):** A GitHub repository intelligence, automated commit auditing, software risk scoring, pull-request security gate, and multi-analyzer platform.

Both projects utilize **FastAPI** backends and **React** frontends. However, they diverge in maturity, schema design, state management, security boundaries, and analyzer workflows. The goal is a production-grade merge using **Project B** as the architectural core while cleanly integrating the operational scanner, manual analyzer, URL performance testing, and target management features from **Project A**.

---

## 1. Project A: SecRunner (`software-testing-main`)

### 1.1 Directory Structure & Source Inventory
```text
software-testing-main/
├── backend/
│   ├── app/
│   │   ├── api/          # auth.py, commands.py, reports.py, runs.py, targets.py, users.py
│   │   ├── core/         # config.py, security.py (JWT & bcrypt)
│   │   ├── db/           # database.py (SQLite SessionLocal)
│   │   ├── models/       # models.py (RoleEnum, User, Target, CommandConfig, RunHistory)
│   │   ├── schemas/      # schemas.py (Pydantic user & token schemas)
│   │   ├── services/     # runner.py (subprocess/asyncio), analyzer.py (regex rules)
│   │   └── main.py       # FastAPI entry point, APScheduler background job
│   ├── tests/            # test_analyzer.py, test_api.py, test_runner.py
│   ├── requirements.txt  # FastAPI, APScheduler, websockets, bcrypt, etc.
│   ├── seed_db.py        # Seed script for default commands/targets
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── App.jsx            # Main dashboard, sidebar navigation, terminal runner
│   │   ├── CommandPrompt.jsx  # Pre-configured security testing commands catalog
│   │   ├── CommandRun.jsx     # Network latency, ping, TLS handshake & speed tests
│   │   ├── ManualAnalysis.jsx # High-speed client ZIP unpacking & log analyzer
│   │   ├── Login.jsx          # Login view
│   │   ├── Settings.jsx       # Target & command CRUD UI
│   │   └── index.css          # Tailwind custom theme (cyberpunk/neon dark)
│   ├── package.json           # React 18, Vite 5, Tailwind 3, Framer Motion, fflate, jsPDF
│   └── Dockerfile
└── e2e/                       # Playwright test specs
```

### 1.2 Architecture & Data Flow
- **Frontend-to-Backend:** React frontend communicates over HTTP (JSON REST) and WebSockets (`/runs/ws/{command_id}/{target_id}`). Hardcoded production Render URLs (`https://software-testing-teq9.onrender.com`) are present in several frontend components instead of dynamic environment variables.
- **Authentication:** OAuth2 password flow with JWT bearer tokens. Roles (`Admin`, `Analyst`, `Viewer`) exist in the database model, but RBAC enforcement is minimal across several routes.
- **Execution Subsystem:** `CommandRunner` executes system binaries (`subprocess.Popen`) based on `CommandConfig.executable` and an `allowed_args` JSON list. Process stdout is streamed line-by-line via WebSockets and regex patterns (`OutputAnalyzer`) classify findings into severity ranks (`Info`, `Low`, `Medium`, `Warning`, `High`, `Critical`).
- **Manual Analysis & ZIP Extraction:** `ManualAnalysis.jsx` uses `fflate` in the browser to safely decompress uploaded ZIP archives while excluding `node_modules/`, `.git/`, and binary file types, sending extracted text to `/runs/analyze-manual`.
- **Database:** SQLite (`secrunner.db` or `test.db`) with raw `Base.metadata.create_all(bind=engine)`. No migration engine (Alembic) is configured.
- **Background Jobs:** Uses `apscheduler.schedulers.background.BackgroundScheduler` running a 60-minute simulated nightly scan with simulated email alerts.

### 1.3 Strengths & Reusable Capabilities
1. **Interactive Command Runner:** Allows controlled, observable execution of CLI security tools (e.g. Nmap, ping, curl, linters).
2. **WebSocket Terminal Output:** Real-time line-by-line streaming of scanner stdout directly to an interactive terminal UI.
3. **Safe In-Browser ZIP Unpacking:** Client-side decompression of repository/code archives with path filtering and size throttling (500KB limit).
4. **Target Management:** Host and IP inventory tracking for remote audits.
5. **URL Performance Audit:** Fast latency, TTFB, and response grading (`/runs/url-speed-test`).

### 1.4 Deficiencies & Security Risks
- **Hardcoded URLs:** Multiple components (`App.jsx`, `CommandRun.jsx`, `ManualAnalysis.jsx`, `Settings.jsx`) directly call Render backend endpoints.
- **Command Injection Risk:** `subprocess.Popen` takes arguments and targets; while `allowed_args` checks exist, target hostname validation must be strictly sanitized against flag injection and shell expansions.
- **Lack of Database Migrations:** Uses raw `create_all`, hindering production schema evolution.
- **Missing Error Handling & Missing Dependencies:** In testing, `apscheduler` was missing from clean environments, breaking imports.

---

## 2. Project B: Software Risk Passport (`tester`)

### 2.1 Directory Structure & Source Inventory
```text
tester/
├── backend/
│   ├── app/
│   │   ├── ai/            # provider.py (Gemini/OpenAI abstraction), service.py
│   │   ├── analysis/      # impact.py, indexer.py, pr_gate.py
│   │   ├── analyzers/     # 12 modular AST & regex analyzers (API, DB, CI/CD, Docs, DNA, etc.)
│   │   ├── api/routes/    # admin.py, auth.py, notifications.py, project_hub.py, repositories.py, webhooks.py
│   │   ├── auth/          # security.py (token encryption, bcrypt, JWT)
│   │   ├── database/      # models.py (16 SQLAlchemy models), session.py
│   │   ├── events/        # bus.py (in-memory async pub/sub event bus)
│   │   ├── scanners/      # universal.py, sast.py, secrets.py, dependencies.py, licenses.py, quality.py
│   │   ├── scoring/       # engine.py (traceable risk scoring algorithm)
│   │   ├── services/      # pdf_report.py, failure_intel.py, fix_agent.py, cross_repo.py, cloud_preview.py
│   │   ├── utils/         # github.py, github_publisher.py
│   │   ├── workers/       # cron_trigger.py, pr_gate_job.py, scan_job.py
│   │   ├── config.py      # Pydantic BaseSettings with .env support
│   │   └── main.py        # FastAPI app with Alembic auto-upgrade on startup
│   ├── alembic/           # 11 versioned database migration scripts
│   ├── tests/             # 24 unit & integration test suites
│   └── requirements.txt   # SQLAlchemy 2.0, Alembic, ReportLab, PyGithub, FastAPI, etc.
└── frontend/
    ├── src/
    │   ├── components/    # Layout.tsx, ScanningHUD.tsx, FeatureExplainerModal.tsx
    │   ├── context/       # ThemeContext.tsx (Light/Dark mode)
    │   ├── pages/         # Dashboard.tsx, Landing.tsx, Login.tsx, Register.tsx,
    │   │                  # Onboarding.tsx, RiskPassport.tsx, CommitAudit.tsx, ProjectHub.tsx
    │   ├── config.ts      # Axios client with bearer token interceptor and API baseURL
    │   ├── App.tsx        # React Router 7 route definitions & AppErrorBoundary
    │   └── main.tsx
    ├── package.json       # React 19, TypeScript 6, Vite 8, Radix UI, Tailwind 3
    └── tsconfig.json
```

### 2.2 Architecture & Data Flow
- **Architecture Core:** Multi-layer clean architecture. Routers delegate to specialized services, workers, and scanner engines.
- **Frontend:** Strict TypeScript, React 19, Radix UI primitives, Tailwind CSS with full light/dark theme toggle, unified Axios interceptor.
- **Database & Migrations:** 16 relational models with explicit foreign keys, indexes, cascades, and 11 versioned Alembic migrations. Supports both PostgreSQL and SQLite.
- **Security Scanners & Analyzers:**
  - `UniversalScanner`: Multi-engine orchestrator detecting secrets, dependencies (via OSV database), licenses, and SAST vulnerabilities.
  - `Registry`: Decoupled analyzer plugin system (`accessibility`, `api_contract`, `cicd`, `database`, `dna`, `docs`, `impact`, `quality`, `security`, `test_intel`).
- **Scoring Engine:** Traceable 0-100 risk score derived from severity weights, finding confidence, and commit history delta.
- **PR Security Gate:** Evaluates incoming PR diffs against configurable blocking policies (Critical, High, Medium, Incomplete).
- **Report Generation:** Native high-fidelity PDF reports generated via `reportlab`.

### 2.3 Strengths
- Enterprise-grade software risk model and repository intelligence.
- Robust test suite with 24 dedicated test files covering AST parsing, database isolation, scanner precision, and API routes.
- Full Alembic migration history.
- Clean separation of concerns with strong typing throughout.

---

## 3. Comparison Matrix Summary

| Architectural Dimension | Project A (SecRunner) | Project B (Risk Passport) | Unified Application Target |
|---|---|---|---|
| **Frontend Framework** | React 18 (JSX), Vite 5 | React 19 (TypeScript), Vite 8 | React 19 + TypeScript + Vite |
| **UI Design System** | Custom Neon Dark theme | Modern Enterprise Dark/Light (Radix + Tailwind) | Enterprise Dark/Light with unified tokens |
| **Backend Framework** | FastAPI 0.109 | FastAPI 0.141 | FastAPI 0.141 (Canonical) |
| **Database ORM** | SQLAlchemy 2.0 (Raw `create_all`) | SQLAlchemy 2.0 + Alembic (11 migrations) | SQLAlchemy + Alembic (Canonical) |
| **Command Scanning** | CLI subprocess runner with WebSocket streaming | Static & AST-based code scanners | Hybrid: Static AST Scanners + Interactive Live Command Runner |
| **Repository Intelligence** | None (Single host/IP targets) | Full GitHub integration, commit history, diffs | Comprehensive GitHub + Target Host/IP support |
| **Manual Analysis** | Fast browser ZIP extraction + regex triage | File-level AST analyzer registry | Dual: Repo indexing + Direct ZIP/Log triage |
| **Reports** | Client-side jsPDF + CSV export | Server-side ReportLab PDF generator | Server ReportLab PDF + Client instant export |
| **AI Integration** | Direct Google Gemini REST call in runs.py | Abstracted `AIProvider` (Gemini & OpenAI fallback) | Centralized backend `AIProviderService` |

---

## 4. Key Risks & Action Items for Consolidation

1. **Database Unification:** Import Project A models (`Target`, `CommandConfig`, `RunHistory`) into Project B's canonical `models.py` and create an Alembic migration (`add_security_command_runner_tables`).
2. **API Unification:** Merge `commands.py`, `targets.py`, and `runs.py` into Project B's API router structure (`app/api/routes/`).
3. **Safe Subprocess Execution:** Sanitize target hosts and command arguments using strict regex validators before invoking system processes; prevent shell injection.
4. **Frontend Integration:** Convert Project A's JSX pages (`ManualAnalysis`, `CommandRun`, `CommandPrompt`, `Settings`) into strictly typed TypeScript (`.tsx`) components, integrating them into Project B's `Layout` navigation.
5. **Configuration Cleanup:** Remove hardcoded URLs and ensure all API requests use the centralized `apiClient` with bearer token authentication.
