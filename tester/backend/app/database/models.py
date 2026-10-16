import enum
from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, DateTime, UniqueConstraint, Text
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from app.database.session import Base

class RoleEnum(str, enum.Enum):
    ADMIN = "Admin"
    ANALYST = "Analyst"
    VIEWER = "Viewer"

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    github_access_token = Column(String, nullable=True)
    role = Column(String, default=RoleEnum.ANALYST.value, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None), nullable=True)
    last_login_at = Column(DateTime, nullable=True)

    repositories = relationship("Repository", back_populates="owner", cascade="all, delete-orphan")
    targets = relationship("Target", back_populates="user", cascade="all, delete-orphan")
    run_history = relationship("RunHistory", back_populates="user", cascade="all, delete-orphan")

class Repository(Base):
    __tablename__ = "repositories"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True, nullable=False)
    url = Column(String, nullable=False)
    owner_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    provider = Column(String, default="github")
    github_owner = Column(String, nullable=True)
    default_branch = Column(String, nullable=True)
    is_public = Column(Boolean, default=True)
    github_created_at = Column(DateTime(timezone=True), nullable=True)
    github_updated_at = Column(DateTime(timezone=True), nullable=True)
    monitoring_status = Column(String, default="NOT_CONFIGURED")
    last_polled_at = Column(DateTime(timezone=True), nullable=True)
    last_successful_poll_at = Column(DateTime(timezone=True), nullable=True)
    last_processed_sha = Column(String, nullable=True)
    last_seen_sha = Column(String, nullable=True)
    last_poll_error = Column(String, nullable=True)
    last_etag = Column(String, nullable=True)

    # Pull Request Security Gate Policy (Opt-in)
    pr_gate_enabled = Column(Boolean, default=False, nullable=False)
    pr_gate_block_critical = Column(Boolean, default=True, nullable=False)
    pr_gate_block_high = Column(Boolean, default=True, nullable=False)
    pr_gate_block_medium = Column(Boolean, default=False, nullable=False)
    pr_gate_block_incomplete = Column(Boolean, default=True, nullable=False)
    ai_enabled = Column(Boolean, default=True, nullable=False)

    owner = relationship("User", back_populates="repositories")
    commits = relationship("Commit", back_populates="repository", cascade="all, delete-orphan")
    pr_checks = relationship("PullRequestCheck", back_populates="repository", cascade="all, delete-orphan")
    notifications = relationship("Notification", back_populates="repository", cascade="all, delete-orphan")
    webhook_deliveries = relationship("WebhookDelivery", back_populates="repository", cascade="all, delete-orphan")
    indexes = relationship("RepositoryIndex", back_populates="repository", cascade="all, delete-orphan")
    analyzer_runs = relationship("AnalyzerRun", back_populates="repository", cascade="all, delete-orphan")
    project_memories = relationship("ProjectMemory", back_populates="repository", cascade="all, delete-orphan")
    issues = relationship("RepositoryIssue", back_populates="repository", cascade="all, delete-orphan")
    releases = relationship("ReleaseRecord", back_populates="repository", cascade="all, delete-orphan")
    downstream_dependencies = relationship("CrossRepoDependency", foreign_keys="[CrossRepoDependency.upstream_repo_id]", back_populates="upstream_repo", cascade="all, delete-orphan")
    upstream_dependencies = relationship("CrossRepoDependency", foreign_keys="[CrossRepoDependency.downstream_repo_id]", back_populates="downstream_repo", cascade="all, delete-orphan")

class Commit(Base):
    __tablename__ = "commits"
    __table_args__ = (UniqueConstraint('repository_id', 'hash', name='uq_commit_repo_hash'),)

    id = Column(Integer, primary_key=True, index=True)
    hash = Column(String, index=True, nullable=False)
    message = Column(String)
    author_name = Column(String)
    author_email = Column(String)
    committed_at = Column(DateTime)
    parent_shas = Column(String)
    repository_id = Column(Integer, ForeignKey("repositories.id", ondelete="CASCADE"), nullable=False)

    repository = relationship("Repository", back_populates="commits")
    scans = relationship("Scan", back_populates="commit", cascade="all, delete-orphan")

class Scan(Base):
    __tablename__ = "scans"

    id = Column(Integer, primary_key=True, index=True)
    commit_id = Column(Integer, ForeignKey("commits.id", ondelete="CASCADE"), nullable=False, unique=True)
    status = Column(String, default="QUEUED", nullable=False)
    # Existing naive DB columns store UTC values; preserve that schema while avoiding deprecated utcnow().
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None))
    completed_at = Column(DateTime, nullable=True)

    commit = relationship("Commit", back_populates="scans")
    error_message = Column(String, nullable=True)
    findings = relationship("Finding", back_populates="scan", cascade="all, delete-orphan")
    risk_score = relationship("RiskScore", back_populates="scan", uselist=False, cascade="all, delete-orphan")
    commit_analysis = relationship("CommitAnalysis", back_populates="scan", uselist=False, cascade="all, delete-orphan")

class Finding(Base):
    __tablename__ = "findings"

    id = Column(Integer, primary_key=True, index=True)
    scan_id = Column(Integer, ForeignKey("scans.id", ondelete="CASCADE"), nullable=False)
    fingerprint = Column(String, index=True, nullable=False)
    status = Column(String, default="NEW") # NEW, UNCHANGED, RESOLVED
    type = Column(String)  # secret, dependency, license, large_file
    description = Column(Text)
    file_path = Column(String)
    line_number = Column(Integer, nullable=True)
    severity = Column(String, default="Medium")

    scan = relationship("Scan", back_populates="findings")

class RiskScore(Base):
    __tablename__ = "risk_scores"

    id = Column(Integer, primary_key=True, index=True)
    scan_id = Column(Integer, ForeignKey("scans.id", ondelete="CASCADE"), unique=True, nullable=False)
    score = Column(Integer, default=100)
    score_delta = Column(Integer, nullable=True)
    details = Column(Text)

    scan = relationship("Scan", back_populates="risk_score")

class WebhookDelivery(Base):
    __tablename__ = 'webhook_deliveries'

    id = Column(Integer, primary_key=True, index=True)
    repository_id = Column(Integer, ForeignKey('repositories.id', ondelete='CASCADE'), nullable=False)
    event_type = Column(String, nullable=False)
    delivery_id = Column(String, index=True)
    status = Column(String, nullable=False)
    payload_sha = Column(String)
    error_message = Column(Text)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None))

    repository = relationship('Repository', back_populates='webhook_deliveries')

  

class CommitAnalysis(Base):
    __tablename__ = 'commit_analyses'

    id = Column(Integer, primary_key=True, index=True)
    scan_id = Column(Integer, ForeignKey('scans.id', ondelete='CASCADE'), unique=True, nullable=False)
    changed_files = Column(Text)
    structural_changes = Column(Text)
    dependency_graph = Column(Text)
    impact_analysis = Column(Text)
    actions_detected = Column(Text)

    scan = relationship('Scan', back_populates='commit_analysis')

class Notification(Base):
    __tablename__ = 'notifications'

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    repository_id = Column(Integer, ForeignKey('repositories.id', ondelete='CASCADE'), nullable=False)
    scan_id = Column(Integer, ForeignKey('scans.id', ondelete='CASCADE'), nullable=True)
    type = Column(String, nullable=False)
    title = Column(String, nullable=False)
    message = Column(Text, nullable=False)
    is_read = Column(Boolean, default=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None))

    user = relationship('User')
    repository = relationship('Repository', back_populates='notifications')
    scan = relationship('Scan')

class PullRequestCheck(Base):
    __tablename__ = 'pull_request_checks'

    id = Column(Integer, primary_key=True, index=True)
    repository_id = Column(Integer, ForeignKey('repositories.id', ondelete='CASCADE'), nullable=False, index=True)
    pr_number = Column(Integer, nullable=True)
    base_sha = Column(String, nullable=True)
    head_sha = Column(String, nullable=False, index=True)
    status = Column(String, default="QUEUED", nullable=False)
    conclusion = Column(String, nullable=True)
    policy_decision = Column(String, nullable=True)
    coverage_status = Column(String, nullable=True)
    newly_introduced_count = Column(Integer, default=0, nullable=False)
    resolved_count = Column(Integer, default=0, nullable=False)
    summary_markdown = Column(Text, nullable=True)
    github_check_run_id = Column(String, nullable=True)
    details_url = Column(String, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None))
    completed_at = Column(DateTime, nullable=True)

    repository = relationship('Repository', back_populates='pr_checks')


class RepositoryIndex(Base):
    __tablename__ = "repository_indexes"

    id = Column(Integer, primary_key=True, index=True)
    repository_id = Column(Integer, ForeignKey("repositories.id", ondelete="CASCADE"), nullable=False, index=True)
    commit_sha = Column(String, index=True, nullable=False)
    file_count = Column(Integer, default=0)
    languages_json = Column(Text, default="{}")
    frameworks_json = Column(Text, default="[]")
    entry_points_json = Column(Text, default="[]")
    module_map_json = Column(Text, default="{}")
    routes_json = Column(Text, default="[]")
    models_json = Column(Text, default="[]")
    tests_json = Column(Text, default="[]")
    dependencies_json = Column(Text, default="[]")
    ci_cd_json = Column(Text, default="[]")
    indexed_at = Column(DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None))

    repository = relationship("Repository", back_populates="indexes")


class AnalyzerRun(Base):
    __tablename__ = "analyzer_runs"

    id = Column(Integer, primary_key=True, index=True)
    repository_id = Column(Integer, ForeignKey("repositories.id", ondelete="CASCADE"), nullable=False, index=True)
    commit_sha = Column(String, index=True, nullable=False)
    analyzer_name = Column(String, nullable=False, index=True)
    analyzer_version = Column(String, default="1.0.0")
    status = Column(String, default="QUEUED", nullable=False)  # QUEUED, RUNNING, COMPLETED, FAILED, SKIPPED
    coverage_status = Column(String, default="FULL")  # FULL, PARTIAL, UNSUPPORTED
    files_analyzed = Column(Integer, default=0)
    duration_seconds = Column(Integer, default=0)
    summary_text = Column(Text, nullable=True)
    findings_count = Column(Integer, default=0)
    details_json = Column(Text, default="{}")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None))
    completed_at = Column(DateTime, nullable=True)

    repository = relationship("Repository", back_populates="analyzer_runs")


class ProjectMemory(Base):
    __tablename__ = "project_memories"

    id = Column(Integer, primary_key=True, index=True)
    repository_id = Column(Integer, ForeignKey("repositories.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    category = Column(String, default="NOTE")  # ADR, CONVENTION, LIMITATION, PROCEDURE, INCIDENT, NOTE
    title = Column(String, nullable=False)
    content = Column(Text, nullable=False)
    tags = Column(String, nullable=True)
    reference_commit_sha = Column(String, nullable=True)
    reference_file = Column(String, nullable=True)
    is_approved = Column(Boolean, default=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None))

    repository = relationship("Repository", back_populates="project_memories")
    user = relationship("User")


class RepositoryIssue(Base):
    __tablename__ = "repository_issues"

    id = Column(Integer, primary_key=True, index=True)
    repository_id = Column(Integer, ForeignKey("repositories.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    finding_id = Column(Integer, ForeignKey("findings.id", ondelete="SET NULL"), nullable=True)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=False)
    severity = Column(String, default="Medium")
    status = Column(String, default="OPEN")  # OPEN, IN_PROGRESS, RESOLVED, CLOSED
    github_issue_number = Column(Integer, nullable=True)
    github_issue_url = Column(String, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None))

    repository = relationship("Repository", back_populates="issues")
    user = relationship("User")
    finding = relationship("Finding")


class ReleaseRecord(Base):
    __tablename__ = "release_records"

    id = Column(Integer, primary_key=True, index=True)
    repository_id = Column(Integer, ForeignKey("repositories.id", ondelete="CASCADE"), nullable=False, index=True)
    version_tag = Column(String, nullable=False)
    target_commit_sha = Column(String, nullable=False)
    status = Column(String, default="DRAFT")  # DRAFT, READY, RELEASED
    readiness_score = Column(Integer, default=100)
    release_notes = Column(Text, nullable=True)
    checklist_json = Column(Text, default="{}")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None))

    repository = relationship("Repository", back_populates="releases")


class CrossRepoDependency(Base):
    __tablename__ = "cross_repo_dependencies"

    id = Column(Integer, primary_key=True, index=True)
    upstream_repo_id = Column(Integer, ForeignKey("repositories.id", ondelete="CASCADE"), nullable=False, index=True)
    downstream_repo_id = Column(Integer, ForeignKey("repositories.id", ondelete="CASCADE"), nullable=False, index=True)
    dependency_type = Column(String, default="PACKAGE")  # PACKAGE, API, SCHEMA, SUBMODULE
    details_json = Column(Text, default="{}")
    discovered_at = Column(DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None))

    upstream_repo = relationship("Repository", foreign_keys=[upstream_repo_id], back_populates="downstream_dependencies")
    downstream_repo = relationship("Repository", foreign_keys=[downstream_repo_id], back_populates="upstream_dependencies")


class Target(Base):
    __tablename__ = "targets"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String, nullable=False, index=True)
    host = Column(String, nullable=False)
    description = Column(String, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None))

    user = relationship("User", back_populates="targets")
    runs = relationship("RunHistory", back_populates="target", cascade="all, delete-orphan")


class CommandConfig(Base):
    __tablename__ = "command_configs"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False, index=True)
    executable = Column(String, nullable=False)
    allowed_args = Column(Text, nullable=False, default="[]")  # JSON list
    timeout_seconds = Column(Integer, default=60, nullable=False)
    regex_rules = Column(Text, nullable=False, default="{}")  # JSON rules
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None))

    runs = relationship("RunHistory", back_populates="command", cascade="all, delete-orphan")


class RunHistory(Base):
    __tablename__ = "run_history"

    id = Column(Integer, primary_key=True, index=True)
    command_id = Column(Integer, ForeignKey("command_configs.id", ondelete="CASCADE"), nullable=False, index=True)
    target_id = Column(Integer, ForeignKey("targets.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    status = Column(String, default="Pending", nullable=False)  # Pending, Running, Done, Pass, Fail, Warning, Error, Timeout
    start_time = Column(DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None))
    end_time = Column(DateTime, nullable=True)
    raw_output = Column(Text, nullable=True)
    findings = Column(Text, nullable=True)  # JSON

    command = relationship("CommandConfig", back_populates="runs")
    target = relationship("Target", back_populates="runs")
    user = relationship("User", back_populates="run_history")


class VisitorLog(Base):
    __tablename__ = "visitor_logs"

    id = Column(Integer, primary_key=True, index=True)
    visitor_id = Column(String, index=True, nullable=True)
    ip_address = Column(String, nullable=True)
    user_agent = Column(String, nullable=True)
    path = Column(String, nullable=False, default="/")
    referrer = Column(String, nullable=True)
    username = Column(String, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None), index=True)


class SystemErrorLog(Base):
    __tablename__ = "system_error_logs"

    id = Column(Integer, primary_key=True, index=True)
    error_type = Column(String, nullable=False)  # "FRONTEND_EXCEPTION", "API_ERROR", "DATABASE_ERROR", "NETWORK_ERROR"
    severity = Column(String, default="ERROR")    # "CRITICAL", "ERROR", "WARNING"
    message = Column(Text, nullable=False)
    stack_trace = Column(Text, nullable=True)
    path = Column(String, nullable=True)
    method = Column(String, nullable=True)
    status_code = Column(Integer, nullable=True)
    username = Column(String, nullable=True)
    resolved = Column(Boolean, default=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None), index=True)

