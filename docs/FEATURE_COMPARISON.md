# Feature Comparison Inventory: Project A vs. Project B

## 1. Comprehensive Feature Comparison Table

| Capability | Project A (`software-testing-main`) | Project B (`tester`) | Decision | Technical Rationale |
|---|---|---|---|---|
| **User Authentication** | OAuth2 password flow with JWT; roles: Admin, Analyst, Viewer | OAuth2 password flow with JWT; active status; access token encryption | **Merge** | Keep Project B's encrypted token store and password hashing while adding Project A's RBAC role schema (`Admin`, `Analyst`, `Viewer`). |
| **Repository Integration** | None (Operates on arbitrary IP/Host targets) | Full GitHub integration, remote polling, branch/commit tracking | **Keep Project B** | Foundation for repo-level CI/CD and commit analysis. |
| **Target Management** | CRUD for Host/IP targets (`targets` table) | None (Only GitHub repositories) | **Keep & Integrate from A** | Expands platform capability from pure GitHub scanning to infrastructure and network endpoint security audits. |
| **Command-Line Scanning** | Subprocess execution with approved argument allowlists and WebSocket output streaming | None | **Keep & Integrate from A** | Provides interactive execution of approved security tools (nmap, ping, linters, curl). |
| **Code Scanners (SAST, Secrets, Deps, Licenses)** | Basic regex pattern matching on raw command output | Specialized multi-engine scanner (`UniversalScanner`, `sast.py`, `secrets.py`, OSV batch API) | **Keep Project B** | Project B's scanners provide high precision, line tracking, fingerprinting, and false-positive suppression. |
| **Modular AST Analyzers** | None | 12 AST analyzers (Accessibility, API Contracts, CI/CD, DB migrations, DNA, Docs, Impact, Quality, etc.) | **Keep Project B** | Deep code structure analysis with registry auto-resolution on change sets. |
| **Manual ZIP & Log Triage** | High-speed browser-side `fflate` ZIP unpacking and regex vulnerability triage | File upload placeholder in Project Hub | **Keep & Integrate from A** | Allows ad-hoc manual audits of zip archives without requiring full Git clone. |
| **URL & Network Performance** | Dedicated latency, TTFB, DNS lookup, and HTTP handshake diagnostic (`/runs/url-speed-test`) | None | **Keep & Integrate from A** | Extremely valuable for live site health audits and edge latency measurement. |
| **Risk Scoring Engine** | Simple pass/warning/fail based on max regex severity | Mathematical scoring engine factoring severity weights, delta shifts, and confidence | **Keep Project B** | Provides traceable, evidence-backed 0-100 risk scoring with historical trend tracking. |
| **Pull Request Security Gate** | None | Configurable gate policies (Critical/High/Medium block rules) with PR summary generation | **Keep Project B** | Enterprise-grade CI/CD automation feature. |
| **AI Fix & Assistant** | Direct REST calls to Google Gemini v1beta | Abstracted `AIProvider` supporting Gemini and OpenAI with graceful fallback | **Merge** | Centralize AI assistance in Project B's `AIProviderService`, supporting Project A's fix generation prompts. |
| **PDF & Report Export** | Client-side `jsPDF` table generation & CSV export | Server-side `ReportLab` canvas-decorated PDF reports | **Merge** | Keep server-side ReportLab PDF generation as canonical, while retaining instant client-side CSV/PDF exports for manual logs. |
| **Database & Migrations** | SQLite with raw `Base.metadata.create_all()` | SQLAlchemy 2.0 with PostgreSQL/SQLite support + 11 Alembic migrations | **Keep Project B** | Production-ready database schema evolution with versioned migration tracking. |
| **Frontend UI & Themes** | Cyberpunk/neon dark theme (JSX, React 18, Vite 5) | Modern enterprise UI with Light/Dark mode (TSX, React 19, Vite 8, Radix UI) | **Keep Project B** | Project B provides superior typography, accessibility, responsive navigation, and strict TypeScript types. |
| **Background Processing** | `APScheduler` background thread with simulated scan | Asyncio coroutine polling + background scan workers | **Keep Project B** | Native async background worker loops prevent GIL blocking and eliminate extra dependencies. |

---

## 2. Features Unique to Project A
1. **Interactive Command Runner:** Live terminal HUD with WebSocket stdout/stderr streaming.
2. **Host / Target Inventory:** Dedicated management of hostnames, IP addresses, and scan scopes.
3. **URL Latency & Speed Diagnostic:** Multi-metric web audit measuring TTFB, total response time, redirects, and HTTP status codes.
4. **Client-Side Safe ZIP Decompression:** In-browser decompression and text extraction using `fflate` with strict path exclusions.
5. **Pre-configured Security Command Catalog:** Preset commands for SCA, secrets, dangerous functions, SQL injection hotspots, and TLS audits.

## 3. Features Unique to Project B
1. **GitHub Repository Lifecycle:** Automated polling, commit tracking, branch detection, and webhook integration.
2. **Universal Code Scanners:** AST-driven SAST, secret detection with entropy and placeholder filtering, OSV batch dependency vulnerability queries, and license classification.
3. **Multi-Analyzer Registry:** Extensible analyzer registry covering API contracts, database migrations, CI/CD workflows, documentation onboarding, and code quality.
4. **Pull Request Security Gate:** Automated evaluation of PR diffs against organizational risk policies.
5. **Project Hub:** Persistent project memory (ADRs, conventions, notes), issue tracking linked to security findings, and release readiness scoring.
6. **ReportLab Enterprise PDF Generator:** Formal security audit PDF reports with executive summaries, findings breakdowns, and mitigation advice.

## 4. Conflict Analysis & Resolution

### 4.1 Frontend Routing & Layout Conflicts
- **Conflict:** Project A uses `/run`, `/analyze`, `/command-run`, `/command-prompt`, and `/manage-commands` inside its own sidebar layout. Project B uses `/dashboard`, `/hub`, `/onboarding`, `/passport`, and `/repositories/.../audit` in its `Layout.tsx`.
- **Resolution:** Integrate Project A's features into Project B's navigation under clear, cohesive module names:
  - **Live Scanner & Terminal:** `/scanner` (integrates Project A's live command runner and target execution).
  - **Ad-hoc Log & ZIP Analyzer:** `/analyzer` (integrates Project A's manual triage and fast ZIP scanner).
  - **Network & URL Diagnostics:** `/diagnostics` (integrates Project A's URL speed and network latency audits).
  - **Security Targets:** Integrated into Project Settings / Target Management.

### 4.2 Database Model Conflicts
- **Conflict:** Both projects declare a `User` model with slight column name differences (`password_hash` vs `hashed_password`).
- **Resolution:** Maintain Project B's canonical `users` table (`hashed_password`, `email`, `is_active`, `github_access_token`) and add a `role` column (`ADMIN`, `ANALYST`, `VIEWER`). Port `targets`, `command_configs`, and `run_history` as new tables referencing the canonical `User.id`.

### 4.3 API Path Clashes
- **Conflict:** Project A uses `/auth` and `/reports` while Project B uses `/auth` and `/repositories/{id}/reports`.
- **Resolution:** Mount Project A's command and target endpoints under `/commands`, `/targets`, and `/runs`, preserving all functionality without colliding with repository routes.

### 4.4 Unsafe Command Execution Redesign
- **Risk in Project A:** Arbitrary arguments passed to `subprocess.Popen` could enable shell escape or argument injection.
- **Remediation in Unified Architecture:** All commands are restricted to an allowlist of pre-registered executables (`ping`, `curl`, `nmap`, `eslint`, `bandit`). Target hosts are validated against a strict hostname/IPv4/IPv6 regex. Shell execution (`shell=True`) is strictly prohibited.
