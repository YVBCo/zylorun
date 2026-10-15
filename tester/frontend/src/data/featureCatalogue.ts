/**
 * Comprehensive Feature Description Catalogue for GitFlow Project Hub.
 * Centralized, verifiable explanations for all 9 tabs, 10 analyzers, and key controls.
 */

export interface TabExplanation {
  id: string;
  title: string;
  summary: string;
  purpose: string;
  whyUseIt: string;
  inputsUsed: string[];
  outputsProvided: string[];
  howToInterpret: string;
  actionsAvailable: string[];
  verificationType: 'Deterministic' | 'Heuristic' | 'Hybrid' | 'External API';
  limitations: string[];
}

export interface AnalyzerExplanation {
  id: string;
  name: string;
  title: string;
  purpose: string;
  problemsDetected: string[];
  whenItRuns: string;
  evidenceProduced: string;
  supportedFiles: string[];
  toolsExecuted: string[];
  requiresAi: boolean;
  whatItCannotVerify: string;
}

export interface ControlExplanation {
  id: string;
  title: string;
  shortHelp: string;
  details: string;
  interpretation: string;
}

export const TABS_EXPLANATIONS: Record<string, TabExplanation> = {
  overview: {
    id: 'overview',
    title: 'Overview & Repository DNA',
    summary: 'High-level architectural health, runtime frameworks, languages, and structural inventory.',
    purpose: 'Provides an instant, shared architectural understanding of the connected repository.',
    whyUseIt: 'Quickly evaluate code health, understand the underlying tech stack, and identify architectural patterns without manually reading through folders.',
    inputsUsed: ['Root manifests (package.json, pyproject.toml, go.mod, Cargo.toml)', 'Directory tree and file extensions', 'Git commit history and author metadata'],
    outputsProvided: ['Health Score (0-100)', 'Detected frameworks and runtimes', 'Language distribution breakdown', 'Routes, models, and test file counts'],
    howToInterpret: 'Scores above 85 indicate a healthy codebase. Low scores highlight unmanaged dependencies, missing tests, or high finding density.',
    actionsAvailable: ['Switch active repository', 'Navigate to individual analyzer drilldowns', 'Trigger fresh repository scan'],
    verificationType: 'Deterministic',
    limitations: ['Dynamic dependencies injected at runtime or non-standard manifest paths may require explicit configuration.'],
  },
  analyzers: {
    id: 'analyzers',
    title: 'Analyzer Suite (10 Continuous Analyzers)',
    summary: 'Suite of 10 specialized static and contract analyzers running incrementally across changes.',
    purpose: 'Continuously assess code quality, security exposures, API contracts, migrations, and accessibility.',
    whyUseIt: 'Catch regressions, broken contracts, insecure permissions, and database hazards before pull request merge.',
    inputsUsed: ['Git working tree', 'Commit diffs', 'Abstract Syntax Trees (AST)', 'Framework route decorators', 'SQL/Alembic migration scripts'],
    outputsProvided: ['Normalized analyzer status (COMPLETED, PARTIAL, FAILED)', 'Execution durations and files analyzed', 'Classified findings with line numbers and evidence'],
    howToInterpret: 'VERIFIED badges indicate exact AST/regex proof. HEURISTIC badges denote pattern-matched suggestions requiring developer review.',
    actionsAvailable: ['Run All 10 Analyzers', 'Run individual analyzers', 'Inspect finding evidence and remediation'],
    verificationType: 'Deterministic',
    limitations: ['Analyzers perform static analysis only; dynamic runtime exploits (DAST) are outside static scope.'],
  },
  timemachine: {
    id: 'timemachine',
    title: 'Time Machine & Change Impact',
    summary: 'Commit revision timeline, risk delta progression, and dependency blast radius calculation.',
    purpose: 'Trace how code edits alter repository risk and identify all downstream files impacted by changes.',
    whyUseIt: 'Understand whether a specific commit introduced or resolved vulnerabilities, and see which components might break.',
    inputsUsed: ['Git commit graph', 'git diff and numstat', 'Internal import dependency graphs (Python, TS, JS)'],
    outputsProvided: ['Directly changed files count', 'Shared dependencies count', 'Potentially affected downstream files', 'Delta score trajectory'],
    howToInterpret: 'High blast radius on core auth or database models warrants extra testing, even for small line changes.',
    actionsAvailable: ['Browse historical commit snapshots', 'Inspect unified diffs', 'Open Commit Audit for any commit'],
    verificationType: 'Deterministic',
    limitations: ['Dynamic reflection or string-interpolated imports cannot be traced through static dependency graphs.'],
  },
  watchtower: {
    id: 'watchtower',
    title: 'Watchtower Live Activity Stream',
    summary: 'Real-time repository event stream capturing scans, findings, releases, and memory entries.',
    purpose: 'Deliver situational awareness of all background automated operations and developer actions.',
    whyUseIt: 'Monitor ongoing scans, verify webhook triggers, and audit when release candidates or issues were created.',
    inputsUsed: ['In-memory shared event bus', 'GitHub webhook delivery logs', 'Background scanner triggers'],
    outputsProvided: ['Real-time event feed polling every 10s', 'Event type pills', 'Structured JSON payloads and timestamps'],
    howToInterpret: 'Events appear chronologically. Scan failures or high-severity finding alerts appear in red/amber.',
    actionsAvailable: ['Auto-refresh feed', 'Filter events by type', 'Copy event payload'],
    verificationType: 'Deterministic',
    limitations: ['Event history in memory retains the last 100 events per repository to prevent unbounded memory growth.'],
  },
  issues: {
    id: 'issues',
    title: 'Issues & Ownership',
    summary: 'Action item tracking linked directly to scanner findings and author contribution bus factors.',
    purpose: 'Bridge findings into actionable engineering tasks and evaluate repository knowledge concentration.',
    whyUseIt: 'Ensure critical security findings are tracked to resolution and identify single points of failure in codebase ownership.',
    inputsUsed: ['Scanner findings database', 'Git commit author history', 'Repository issue tracking table'],
    outputsProvided: ['Open/In-Progress/Resolved task list', 'Author commit distribution', 'Bus factor metrics'],
    howToInterpret: 'A single author with >80% commits indicates low bus factor. High open issues indicate accumulated technical debt.',
    actionsAvailable: ['Create new issue task', 'Convert finding to issue', 'Update status to RESOLVED'],
    verificationType: 'Deterministic',
    limitations: ['Commit author matching is based on Git author name and email, which may vary across developer machines.'],
  },
  memory: {
    id: 'memory',
    title: 'Project Memory (Living Knowledge Base)',
    summary: 'Persistent engineering knowledge: Architecture Decisions (ADR), runbooks, hazards, and setup notes.',
    purpose: 'Preserve institutional knowledge and critical context across sessions so developers never lose tribal knowledge.',
    whyUseIt: 'Document why certain architectural choices were made, outline migration procedures, and flag dangerous areas.',
    inputsUsed: ['Developer-authored memory records', 'Searchable categorization tags', 'Indexed repository context'],
    outputsProvided: ['Searchable memory cards', 'Categorized tabs (DECISION, RUNBOOK, HAZARD, ONBOARDING)', 'Tag-filtered views'],
    howToInterpret: 'HAZARD notes warn about non-obvious traps. DECISION records serve as immutable Architecture Decision Records.',
    actionsAvailable: ['Record new memory note', 'Delete outdated memory', 'Filter by category and tags'],
    verificationType: 'Deterministic',
    limitations: ['Memories are maintained by team members and should be kept up to date when architecture changes.'],
  },
  releases: {
    id: 'releases',
    title: 'Release Readiness & Checklist',
    summary: 'Automated release candidate gate evaluating security scores, critical issues, and migrations.',
    purpose: 'Determine whether a commit is safe for production deployment with an automated verification checklist.',
    whyUseIt: 'Eliminate manual release guesswork and prevent deploying code with unverified migrations or critical CVEs.',
    inputsUsed: ['Latest scan security score', 'Critical finding count', 'Database migration status', 'CI/CD workflow outcomes'],
    outputsProvided: ['Readiness score (0-100%)', 'Release status (READY vs DRAFT)', 'Automated readiness checklist', 'Audit history'],
    howToInterpret: 'Readiness >= 70% with zero critical vulnerabilities earns the READY certification.',
    actionsAvailable: ['Prepare new release candidate with version tag', 'Generate changelog notes', 'Review historical releases'],
    verificationType: 'Deterministic',
    limitations: ['Checklist evaluates static criteria; smoke tests in staging environments should still be executed.'],
  },
  aiexpert: {
    id: 'aiexpert',
    title: 'AI Expert & Self-Validating Fix Agent',
    summary: 'Natural-language codebase Q&A, feature completeness checker, and automated syntax-verified fix patches.',
    purpose: 'Provide contextual assistance and automated remediation while maintaining strict security and privacy.',
    whyUseIt: 'Ask questions about complex logic, verify whether acceptance criteria are implemented, and preview candidate fix patches.',
    inputsUsed: ['Indexed routes, models, and test fixtures', 'Stored project memories', 'Secret-redacted prompts', 'Selected finding context'],
    outputsProvided: ['Contextual answers (clearly labeled AI vs Deterministic)', 'Feature completeness evidence mapping', 'Unified diff candidate patches with syntax checks'],
    howToInterpret: 'Check the badge: "AI-generated" means a live model responded; "Deterministic fallback" means local codebase indexing generated the answer.',
    actionsAvailable: ['Ask repository question', 'Check feature completeness against spec', 'Generate candidate patch for a finding', 'Test AI connection'],
    verificationType: 'Hybrid',
    limitations: ['Candidate patches require explicit user authorization before application. Remote GitHub repos are never mutated.'],
  },
  radar: {
    id: 'radar',
    title: 'Cross-Repository Change Radar',
    summary: 'Dependency and contract topology across multiple repositories connected to GitFlow.',
    purpose: 'Detect cross-service breaking changes, shared library version drifts, and downstream impacts.',
    whyUseIt: 'In multi-repo architectures, understand how an API change in one service affects consuming frontend or microservice repos.',
    inputsUsed: ['CrossRepoDependency database table', 'Connected repositories package manifests', 'Discovered API routes and consumers'],
    outputsProvided: ['Upstream dependencies count', 'Downstream consumers list', 'Shared package version divergence alerts'],
    howToInterpret: 'High downstream count indicates a foundational service where breaking API changes have wide blast radius.',
    actionsAvailable: ['Inspect cross-repo links', 'Detect version drifts', 'Refresh dependency links'],
    verificationType: 'Deterministic',
    limitations: ['Only repositories connected to GitFlow by the user are visible in the cross-repo radar.'],
  },
};

export const ANALYZERS_EXPLANATIONS: Record<string, AnalyzerExplanation> = {
  repository_dna: {
    id: 'repository_dna',
    name: 'repository_dna',
    title: 'Repository DNA Analyzer',
    purpose: 'Extracts core runtime architecture, primary programming languages, and dependency topology.',
    problemsDetected: ['Unrecognized project structure', 'Outdated language runtimes', 'Missing package manifests'],
    whenItRuns: 'Initial onboarding and on every repository scan or manual suite execution.',
    evidenceProduced: 'Manifest parsing results, directory tree language statistics, architecture classification.',
    supportedFiles: ['package.json', 'requirements.txt', 'pyproject.toml', 'Cargo.toml', 'go.mod', 'pom.xml'],
    toolsExecuted: ['Custom manifest parsers', 'Language classifier'],
    requiresAi: false,
    whatItCannotVerify: 'Dynamic dependency injection loaded at runtime without manifest entries.',
  },
  security_and_secrets: {
    id: 'security_and_secrets',
    name: 'security_and_secrets',
    title: 'Security & Secrets Analyzer',
    purpose: 'Scans for hard-coded credentials, cryptographic tokens, vulnerable dependencies, and SAST injection hazards.',
    problemsDetected: ['API keys and private keys in code', 'High-severity CVE dependencies', 'SQL injection and command injection patterns'],
    whenItRuns: 'Continuous commit scans, pull request gates, and on-demand suite runs.',
    evidenceProduced: 'Line-precise code excerpts with SHA-256 fingerprinting and secret masking.',
    supportedFiles: ['All text and source code files, package manifests, .env files'],
    toolsExecuted: ['UniversalScanner', 'Regex secret detector', 'OSV CVE database matcher', 'AST taint heuristics'],
    requiresAi: false,
    whatItCannotVerify: 'Encrypted or compiled binary files, runtime-generated tokens.',
  },
  change_impact: {
    id: 'change_impact',
    name: 'change_impact',
    title: 'Change Impact & Blast Radius Analyzer',
    purpose: 'Computes the blast radius of Git commit diffs against the internal codebase dependency graph.',
    problemsDetected: ['Edits to core shared modules impacting multiple consumers', 'Unreviewed security-sensitive changes'],
    whenItRuns: 'On every analyzed commit with parent comparison.',
    evidenceProduced: 'Categorized file lists (Directly Changed, Shared Dependency, Potentially Affected).',
    supportedFiles: ['.py', '.js', '.ts', '.tsx', '.jsx'],
    toolsExecuted: ['Git diff parser', 'Regex import scanner', 'Reverse dependency graph builder'],
    requiresAi: false,
    whatItCannotVerify: 'Dynamic module imports via string variables (e.g., importlib.import_module(var)).',
  },
  test_intelligence: {
    id: 'test_intelligence',
    name: 'test_intelligence',
    title: 'Test Intelligence Analyzer',
    purpose: 'Discovers automated test suites, checks test coverage topology, and flags untested source modules.',
    problemsDetected: ['Source files lacking corresponding test files', 'Missing test runners', 'Empty test directories'],
    whenItRuns: 'Repository indexing and analyzer suite runs.',
    evidenceProduced: 'Test framework detection, test file inventories, missing test ratios.',
    supportedFiles: ['test_*.py', '*_test.py', '*.test.ts', '*.spec.ts', '*.test.js'],
    toolsExecuted: ['Test runner manifest detector', 'Naming convention matcher'],
    requiresAi: false,
    whatItCannotVerify: 'Actual line-by-line runtime execution code coverage percentage (requires executing test runner with coverage tools).',
  },
  code_quality: {
    id: 'code_quality',
    name: 'code_quality',
    title: 'Code Quality & Technical Debt Analyzer',
    purpose: 'Evaluates structural maintainability, cyclomatic complexity, oversized functions, and dead code.',
    problemsDetected: ['Functions > 50 lines', 'Files > 500 lines', 'Excessive TODO/FIXME comments', 'Commented-out code blocks'],
    whenItRuns: 'Commit audits and suite runs.',
    evidenceProduced: 'Function line count measurements, complexity estimates, debt comment tallies.',
    supportedFiles: ['.py', '.js', '.ts', '.tsx', '.java', '.go'],
    toolsExecuted: ['AST function parser', 'Comment density scanner'],
    requiresAi: false,
    whatItCannotVerify: 'Subjective architectural aesthetics or business logic correctness.',
  },
  api_contract: {
    id: 'api_contract',
    name: 'api_contract',
    title: 'API & Contract Analyzer',
    purpose: 'Discovers backend route trees (FastAPI, Flask, Express) and compares them against frontend API client calls.',
    problemsDetected: ['Client calls to nonexistent backend endpoints', 'HTTP method mismatches (e.g. GET vs POST)', 'Deleted endpoints causing frontend breakages'],
    whenItRuns: 'Commit scans and analyzer suite runs.',
    evidenceProduced: 'Backend route list, frontend fetch/axios client call list, mismatch classification (Verified vs Heuristic).',
    supportedFiles: ['.py', '.ts', '.tsx', '.js', '.jsx'],
    toolsExecuted: ['FastAPI/Flask decorator parser', 'Axios/fetch call extractor', 'Route contract diff engine'],
    requiresAi: false,
    whatItCannotVerify: 'Endpoints dynamically constructed via complex string concatenation or third-party SDK proxies.',
  },
  database_migration: {
    id: 'database_migration',
    name: 'database_migration',
    title: 'Database & Migration Analyzer',
    purpose: 'Inspects ORM models and migration scripts to catch risky schema changes before production rollout.',
    problemsDetected: ['Dropped table columns without deprecation', 'NOT NULL columns added without default values', 'Unindexed foreign keys', 'Dangerous cascade deletes'],
    whenItRuns: 'Scans modifying models or migrations.',
    evidenceProduced: 'Schema hazard flags, Alembic revision history checks, expand-contract migration guidance.',
    supportedFiles: ['SQLAlchemy model files', 'alembic/versions/*.py', '*.sql'],
    toolsExecuted: ['SQLAlchemy AST parser', 'Alembic revision graph reader'],
    requiresAi: false,
    whatItCannotVerify: 'Live production database data distribution or query plan performance.',
  },
  cicd_deployment: {
    id: 'cicd_deployment',
    name: 'cicd_deployment',
    title: 'CI/CD & Deployment Analyzer',
    purpose: 'Inspects GitHub Actions workflows, Dockerfiles, and deployment configs for security and permission hazards.',
    problemsDetected: ['Unpinned third-party actions (@master)', 'Excessive write-all permissions', 'Untrusted context script injection', 'Docker containers running as root'],
    whenItRuns: 'Scans modifying .github/workflows or Dockerfile.',
    evidenceProduced: 'Workflow YAML AST checks, permission level audits, Dockerfile directive inspection.',
    supportedFiles: ['.github/workflows/*.yml', 'Dockerfile', 'render.yaml', 'vercel.json'],
    toolsExecuted: ['YAML workflow parser', 'Dockerfile directive auditor'],
    requiresAi: false,
    whatItCannotVerify: 'Secrets configured in GitHub repository settings UI (cannot see secret values outside repository).',
  },
  ui_accessibility: {
    id: 'ui_accessibility',
    name: 'ui_accessibility',
    title: 'UI/UX & Accessibility Analyzer',
    purpose: 'Static analysis of frontend templates against WCAG 2.1 AA accessibility standards.',
    problemsDetected: ['Images missing alt text', 'Icon buttons missing aria-label', 'Form inputs missing accessible labels', 'Non-semantic clickable divs without keyboard handlers'],
    whenItRuns: 'Frontend template audits and suite runs.',
    evidenceProduced: 'HTML/JSX tag parse trees, line-precise accessibility violations, accessibility score (0-100).',
    supportedFiles: ['.tsx', '.jsx', '.html', '.vue', '.svelte'],
    toolsExecuted: ['JSX tag tokenizer with nested brace parser', 'WCAG AA rule validator'],
    requiresAi: false,
    whatItCannotVerify: 'Color contrast ratios relying on complex computed CSS stylesheets or dynamic theme variables.',
  },
  docs_onboarding: {
    id: 'docs_onboarding',
    name: 'docs_onboarding',
    title: 'Documentation & Onboarding Analyzer',
    purpose: 'Audits README files, setup documentation, and environment variable references to ensure smooth onboarding.',
    problemsDetected: ['Broken relative markdown links', 'References to deleted files', 'Undocumented environment variables read in code'],
    whenItRuns: 'Commit scans and documentation audits.',
    evidenceProduced: 'Broken link list, undocumented environment variable list, auto-generated onboarding guide.',
    supportedFiles: ['README.md', 'docs/**/*.md', '.env.example', 'All source code files'],
    toolsExecuted: ['Markdown link validator', 'Codebase env variable extractor'],
    requiresAi: false,
    whatItCannotVerify: 'External HTTP web URLs (to prevent external network dependencies during offline scans).',
  },
};

export const CONTROLS_EXPLANATIONS: Record<string, ControlExplanation> = {
  risk_score: {
    id: 'risk_score',
    title: 'Security Risk Score',
    shortHelp: '0–100 score quantifying overall repository security health.',
    details: 'Calculated using deterministic deductions: Critical (-25 pts), High (-15 pts), Medium (-8 pts), Low (-3 pts). Clamped between 0 and 100.',
    interpretation: 'Scores >= 85 are Healthy. Scores 70–84 indicate moderate risk. Scores < 70 indicate active vulnerabilities requiring remediation.',
  },
  score_delta: {
    id: 'score_delta',
    title: 'Score Delta',
    shortHelp: 'Point change compared to previous completed commit scan.',
    details: 'Positive numbers indicate risk reduction (e.g. +10 means vulnerabilities were resolved). Negative numbers indicate new issues were introduced.',
    interpretation: 'A green +delta shows security progress; a red -delta alerts the team to regressions.',
  },
  finding_classification: {
    id: 'finding_classification',
    title: 'Finding Classification',
    shortHelp: 'Distinction between confirmed vulnerabilities, test fixtures, and heuristics.',
    details: 'Every finding is classified as Confirmed Vulnerability, Heuristic Verification, or Intentional Test Fixture. Test fixtures do not penalize scores.',
    interpretation: 'Ensures zero false alarms on mock credentials or test assertions while keeping an audit trail.',
  },
  scanner_coverage: {
    id: 'scanner_coverage',
    title: 'Scanner Coverage Status',
    shortHelp: 'COMPLETED vs PARTIAL vs FAILED coverage disclosure.',
    details: 'COMPLETED indicates all registered tools ran successfully. PARTIAL indicates certain file types lacked tools or timed out. FAILED indicates fatal scanner error.',
    interpretation: 'PARTIAL coverage generates a provisional score to prevent false confidence when tools cannot complete.',
  },
  blast_radius: {
    id: 'blast_radius',
    title: 'Change Blast Radius',
    shortHelp: 'Downstream impact severity of modified files.',
    details: 'Assesses whether modified files are isolated, shared across components, or core to auth/database architectures.',
    interpretation: 'HIGH blast radius requires comprehensive integration and regression testing before merge.',
  },
  watchtower_stream: {
    id: 'watchtower_stream',
    title: 'Watchtower Live Feed',
    shortHelp: 'Real-time repository activity and scan execution log.',
    details: 'Thread-safe in-memory event stream capturing scan progress, finding alerts, and release events polled automatically every 10 seconds.',
    interpretation: 'Provides instantaneous team awareness without needing page reloads.',
  },
  ai_execution_mode: {
    id: 'ai_execution_mode',
    title: 'AI Execution Mode',
    shortHelp: 'Honest label: AI-Generated vs Deterministic Fallback vs Mock Mode.',
    details: 'Indicates the exact intelligence mechanism: real cloud provider (OpenAI, Anthropic, Gemini), deterministic codebase indexing, or cached response.',
    interpretation: 'Guarantees transparent provenance: you always know whether an external model or local deterministic rules generated the output.',
  },
  fix_agent_validation: {
    id: 'fix_agent_validation',
    title: 'Fix Agent Validation Status',
    shortHelp: 'VALIDATED vs UNVALIDATED candidate patch check.',
    details: 'The Self-Validating Fix Agent parses candidate patches through Python AST and JSON parsers to ensure no syntax errors are introduced.',
    interpretation: 'VALIDATED patches are syntactically safe to apply; user authorization is strictly required prior to any mutation.',
  },
  pdf_export: {
    id: 'pdf_export',
    title: 'Server-Side PDF Export',
    shortHelp: 'Standalone professional PDF audit report generated by ReportLab.',
    details: 'Generates clean A4 paginated document with NumberedCanvas ("Page X of Y"), white background, secret redaction, and executive summary.',
    interpretation: 'Suitable for executive compliance, security audits, and client reporting without capturing browser UI chrome.',
  },
  safe_delete: {
    id: 'safe_delete',
    title: 'Safe Delete Repository',
    shortHelp: 'Removes repository from GitFlow without affecting GitHub.',
    details: 'Transactionally cascade-deletes all GitFlow database records (scans, findings, memories, issues, releases). Does NOT call GitHub deletion API.',
    interpretation: 'Completely removes tracked telemetry from GitFlow while leaving the actual remote GitHub repository 100% intact.',
  },
};
