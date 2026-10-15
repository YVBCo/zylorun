# Unified Application Merge Plan

## Overview & Execution Strategy

We are using **Project B (`tester`)** as the primary codebase foundation, into which we will cleanly merge the unique capabilities from **Project A (`software-testing-main`)**. The resulting unified application will be housed directly in `tester/` (or structured as the unified project root) with clean separation of frontend, backend, database models, and documentation.

---

## 1. Stage-by-Stage Implementation Steps

### Stage 1: Database Model Consolidation & Alembic Migration
1. **Extend `tester/backend/app/database/models.py`**:
   - Add `RoleEnum` with values: `ADMIN`, `ANALYST`, `VIEWER`.
   - Add `role` column to `User` (default: `ANALYST`).
   - Add `Target` model (`id`, `user_id`, `name`, `host`, `description`, `created_at`).
   - Add `CommandConfig` model (`id`, `name`, `executable`, `allowed_args`, `timeout_seconds`, `regex_rules`).
   - Add `RunHistory` model (`id`, `command_id`, `target_id`, `user_id`, `status`, `start_time`, `end_time`, `raw_output`, `findings`).
2. **Generate and apply Alembic migration**:
   - Create migration script `add_command_runner_and_targets_tables.py` in `tester/backend/alembic/versions/`.
   - Verify upgrade and downgrade against test database.

### Stage 2: Backend API & Service Integration
1. **Port Services**:
   - Create `tester/backend/app/services/runner.py`: Enhanced `CommandRunner` with safe argument validation, RFC-compliant host validation, and WebSocket stdout streaming.
   - Create `tester/backend/app/services/analyzer.py`: Regex-based `OutputAnalyzer` for live command output analysis.
2. **Port API Endpoints**:
   - Create `tester/backend/app/api/routes/commands.py` (`GET /commands`, `POST /commands`, `DELETE /commands/{id}`).
   - Create `tester/backend/app/api/routes/targets.py` (`GET /targets`, `POST /targets`, `DELETE /targets/{id}`).
   - Create `tester/backend/app/api/routes/runs.py` (`POST /runs/analyze-manual`, `POST /runs/generate-fix`, `POST /runs/url-speed-test`, `GET /runs`, `WebSocket /runs/ws/{command_id}/{target_id}`).
   - Create `tester/backend/app/api/routes/reports.py` (JSON and CSV report exports).
3. **Register Routers in `main.py`**:
   - Mount `/commands`, `/targets`, `/runs`, and `/reports` routers in `tester/backend/app/main.py`.
   - Update CORS configuration to support dynamic origins.

### Stage 3: Frontend TypeScript & UI Integration
1. **Create Unified TypeScript Pages in `tester/frontend/src/pages/`**:
   - `LiveRunner.tsx`: Interactive command execution HUD, target selector, status badges, real-time terminal window with WebSocket streaming, and scan elapsed timer.
   - `LogAnalyzer.tsx`: Safe in-browser ZIP and raw log vulnerability triage, findings filtering by severity, AI fix generator, and instant PDF/CSV exports.
   - `EdgeDiagnostics.tsx`: Live URL speed testing, TTFB measurement, response latency analysis, and HTTP header inspection.
   - `TargetManagement.tsx`: Target host and approved command configuration UI.
2. **Update Navigation & Theme in `tester/frontend/src/components/Layout.tsx`**:
   - Add navigation items for:
     - **Live Terminal** (`/scanner`)
     - **Log & ZIP Analyzer** (`/analyzer`)
     - **Edge Diagnostics** (`/diagnostics`)
     - **Target Settings** (`/settings/targets`)
   - Ensure seamless responsiveness and dark/light mode consistency across all new screens.
3. **Update Routes in `tester/frontend/src/App.tsx`**:
   - Map all newly integrated paths within `Layout`.

### Stage 4: Test Suite Integration & Verification
1. **Port Tests**:
   - Add `test_command_runner.py`, `test_targets_api.py`, and `test_analyzer.py` to `tester/backend/tests/`.
2. **Execute Full Test Suite**:
   - Run all pytest test suites to ensure 0 regressions.
3. **Frontend Verification**:
   - Run `npm run build` and `oxlint` to guarantee clean TypeScript compilation and production asset bundling.

---

## 2. Rollback & Data Preservation Plan
- All original files in `software-testing-main/` and `tester/` are preserved intact.
- Alembic migrations provide an explicit `downgrade()` function to cleanly reverse database schema changes if ever needed.
