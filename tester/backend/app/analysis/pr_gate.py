"""Pull Request Security Gate Engine.

Implements base-vs-head diff analysis, changed line attribution,
baseline comparison, configurable opt-in policy evaluation,
and readable GitHub PR summary generation.
"""

import json
import logging
import os
import re
import subprocess
from typing import Any, Dict, List, Optional, Set, Tuple

from app.scanners.universal import UniversalScanner, generate_fingerprint
from app.scoring.engine import calculate_risk_score

logger = logging.getLogger(__name__)


def parse_diff_changed_lines(diff_text: str) -> Tuple[Dict[str, Set[int]], Dict[str, str], Dict[str, str]]:
    """Parses `git diff -U0` unified diff output.

    Returns:
        changed_lines_by_file: Mapping of normalized file path -> set of 1-indexed changed line numbers in HEAD.
        file_statuses: Mapping of file path -> status ('ADDED', 'MODIFIED', 'DELETED', 'RENAMED').
        renames: Mapping of old_path -> new_path.
    """
    changed_lines: Dict[str, Set[int]] = {}
    file_statuses: Dict[str, str] = {}
    renames: Dict[str, str] = {}

    current_old_file: Optional[str] = None
    current_new_file: Optional[str] = None
    is_deleted = False
    is_new = False
    rename_from: Optional[str] = None
    rename_to: Optional[str] = None

    hunk_pattern = re.compile(r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@")

    for line in diff_text.splitlines():
        if line.startswith("diff --git "):
            # Reset per-file state
            parts = line.split(" ")
            if len(parts) >= 4:
                old_p = parts[2].removeprefix("a/").strip()
                new_p = parts[3].removeprefix("b/").strip()
                current_old_file = old_p
                current_new_file = new_p
            is_deleted = False
            is_new = False
            rename_from = None
            rename_to = None
            continue

        if line.startswith("deleted file mode"):
            is_deleted = True
            continue
        if line.startswith("new file mode"):
            is_new = True
            continue
        if line.startswith("rename from "):
            rename_from = line.removeprefix("rename from ").strip()
            continue
        if line.startswith("rename to "):
            rename_to = line.removeprefix("rename to ").strip()
            if rename_from:
                renames[rename_from] = rename_to
                file_statuses[rename_to] = "RENAMED"
                current_new_file = rename_to
            continue

        if line.startswith("--- "):
            if "/dev/null" in line:
                is_new = True
            continue

        if line.startswith("+++ "):
            if "/dev/null" in line:
                is_deleted = True
                if current_old_file:
                    file_statuses[current_old_file] = "DELETED"
            else:
                target = line.removeprefix("+++ b/").strip()
                current_new_file = target
                if rename_from and rename_to:
                    renames[rename_from] = rename_to
                    file_statuses[rename_to] = "RENAMED"
                elif is_new:
                    file_statuses[target] = "ADDED"
                elif not is_deleted:
                    file_statuses[target] = "MODIFIED"

                if target not in changed_lines:
                    changed_lines[target] = set()
            continue

        if line.startswith("@@ "):
            m = hunk_pattern.match(line)
            if m and current_new_file and not is_deleted:
                new_start = int(m.group(3))
                new_count = int(m.group(4)) if m.group(4) is not None else 1
                if new_count > 0:
                    if current_new_file not in changed_lines:
                        changed_lines[current_new_file] = set()
                    for line_num in range(new_start, new_start + new_count):
                        changed_lines[current_new_file].add(line_num)

    # Normalize file paths to forward slashes
    norm_changed_lines = {os.path.normpath(k).replace("\\", "/"): v for k, v in changed_lines.items()}
    norm_file_statuses = {os.path.normpath(k).replace("\\", "/"): v for k, v in file_statuses.items()}
    norm_renames = {
        os.path.normpath(k).replace("\\", "/"): os.path.normpath(v).replace("\\", "/")
        for k, v in renames.items()
    }

    return norm_changed_lines, norm_file_statuses, norm_renames


def get_git_diff_output(repo_dir: str, base_sha: str, head_sha: str) -> str:
    """Executes `git diff -U0` between base_sha and head_sha."""
    try:
        res = subprocess.run(
            ["git", "diff", "-U0", "-M", base_sha, head_sha],
            cwd=repo_dir,
            capture_output=True,
            text=True,
            check=True,
            timeout=30,
        )
        return res.stdout
    except subprocess.CalledProcessError as e:
        logger.warning(f"git diff failed between {base_sha} and {head_sha}: {e.stderr}")
        return ""
    except Exception as e:
        logger.error(f"Unexpected error running git diff: {e}")
        return ""


def categorize_finding_for_pr(
    finding: Dict[str, Any],
    changed_lines_by_file: Dict[str, Set[int]],
    file_statuses: Dict[str, str],
    base_fingerprints: Set[str],
    has_valid_baseline: bool,
) -> str:
    """Categorizes a head finding relative to the PR diff and base findings.

    Returns one of:
        - 'PR_INTRODUCED_ACTIONABLE': Confirmed or verified finding on changed lines of the PR.
        - 'PR_INTRODUCED_HEURISTIC': Unverified/heuristic finding on changed lines.
        - 'INFORMATIONAL_FIXTURE': Intentional test fixture or demonstration code.
        - 'EXISTING': Pre-existing codebase finding outside changed lines or present in base.
    """
    fingerprint = finding.get("fingerprint") or generate_fingerprint(finding)
    classification = finding.get("classification", "")

    # 1. Informational Test Fixture match
    if classification == "Intentional test fixture or demonstration example":
        return "INFORMATIONAL_FIXTURE"

    # 2. Check if present in base commit
    if has_valid_baseline and fingerprint in base_fingerprints:
        return "EXISTING"

    # 3. Path and line check
    raw_path = finding.get("file_path") or finding.get("file") or ""
    norm_path = os.path.normpath(raw_path).replace("\\", "/")

    line_number = finding.get("line_number")
    if line_number is None and str(finding.get("location", "")).startswith("Line "):
        try:
            line_number = int(str(finding["location"]).split(" ")[1])
        except (ValueError, IndexError):
            line_number = None

    # If the file is not part of the PR changes at all:
    if norm_path not in changed_lines_by_file and norm_path not in file_statuses:
        return "EXISTING"

    file_status = file_statuses.get(norm_path, "")

    # If file was newly added, all lines are PR-introduced
    if file_status == "ADDED":
        is_on_changed_line = True
    elif line_number is not None:
        is_on_changed_line = line_number in changed_lines_by_file.get(norm_path, set())
    else:
        # Dependency / license manifests without line numbers (e.g. requirements.txt)
        # Treated as on changed lines if the manifest file itself was modified/added in PR
        is_on_changed_line = norm_path in changed_lines_by_file or norm_path in file_statuses

    if not is_on_changed_line:
        return "EXISTING"

    # Heuristic vs Confirmed Actionable
    if classification == "Confirmed vulnerability or exposure" or finding.get("severity") in ("Critical", "High"):
        return "PR_INTRODUCED_ACTIONABLE"
    elif "heuristic" in classification.lower() or finding.get("confidence") == "Low":
        return "PR_INTRODUCED_HEURISTIC"
    else:
        return "PR_INTRODUCED_ACTIONABLE"


def evaluate_pr_gate_policy(
    newly_introduced_actionable: List[Dict[str, Any]],
    coverage_status: str,
    policy: Dict[str, Any],
) -> Tuple[str, str]:
    """Evaluates the PR gate status against owner-configured policy.

    Returns:
        status: 'PASSED', 'FAILED', or 'NEUTRAL'
        reason: Clear human-readable explanation
    """
    enabled = policy.get("enabled", False)
    if not enabled:
        return "NEUTRAL", "PR Gate enforcement is disabled (monitoring mode)."

    block_incomplete = policy.get("block_incomplete", True)
    if block_incomplete and coverage_status != "COMPLETED":
        return (
            "FAILED",
            f"Security scan coverage was incomplete (status: {coverage_status}). "
            "Gate policy requires complete scanner execution before approval.",
        )

    block_critical = policy.get("block_critical", True)
    block_high = policy.get("block_high", True)
    block_medium = policy.get("block_medium", False)

    critical_findings = [f for f in newly_introduced_actionable if f.get("severity", "").title() == "Critical"]
    high_findings = [f for f in newly_introduced_actionable if f.get("severity", "").title() == "High"]
    medium_findings = [f for f in newly_introduced_actionable if f.get("severity", "").title() == "Medium"]

    blocking_reasons = []
    if block_critical and critical_findings:
        blocking_reasons.append(f"{len(critical_findings)} Critical severity finding(s)")
    if block_high and high_findings:
        blocking_reasons.append(f"{len(high_findings)} High severity finding(s)")
    if block_medium and medium_findings:
        blocking_reasons.append(f"{len(medium_findings)} Medium severity finding(s)")

    if blocking_reasons:
        return "FAILED", f"Blocked by security policy: introduced {', '.join(blocking_reasons)} on changed lines."

    return "PASSED", "All pull request checks passed. No blocking security findings introduced."


def generate_pr_summary_markdown(
    base_sha: str,
    head_sha: str,
    gate_status: str,
    gate_reason: str,
    policy: Dict[str, Any],
    coverage_data: Dict[str, Any],
    newly_introduced_actionable: List[Dict[str, Any]],
    newly_introduced_heuristic: List[Dict[str, Any]],
    resolved_findings: List[Dict[str, Any]],
    existing_findings: List[Dict[str, Any]],
    fixture_matches: List[Dict[str, Any]],
    head_score: int,
    base_score: Optional[int],
) -> str:
    """Generates a structured, readable Markdown summary for GitHub PR comment or check run."""
    status_emoji = {
        "PASSED": "✅ **PASSED**",
        "FAILED": "❌ **FAILED**",
        "NEUTRAL": "⚪ **MONITORING ONLY (NOT ENFORCED)**",
    }.get(gate_status, gate_status)

    score_diff_str = ""
    if base_score is not None:
        delta = head_score - base_score
        delta_str = f"+{delta}" if delta > 0 else str(delta)
        score_diff_str = f"(Delta: {delta_str} from base {base_score}/100)"

    lines = [
        "## 🛡️ GitFlow Pull Request Security Gate",
        "",
        f"**Status**: {status_emoji}",
        f"**Reason**: {gate_reason}",
        f"**Target Commit Range**: `{base_sha[:8]}`...`{head_sha[:8]}`",
        f"**Head Risk Score**: **{head_score}/100** {score_diff_str}".strip(),
        "",
    ]

    # Coverage Warning / Limitations
    overall_cov = coverage_data.get("overall_status", "COMPLETED")
    if overall_cov != "COMPLETED":
        lines.extend([
            "> [!WARNING]",
            f"> **Partial Scanner Coverage ({overall_cov})**",
            "> One or more security checks did not complete. Unchecked security classes are not guaranteed clean.",
            "",
        ])

    # Defensive copy for clean scores
    if head_score == 100:
        lines.extend([
            "> [!NOTE]",
            "> *No confirmed issues were detected on changed lines by the checks that completed.*",
            "",
        ])

    # Policy details
    lines.extend([
        "<details>",
        "<summary>⚙️ Gate Policy Settings</summary>",
        "",
        f"- **Enforcement Active**: `{'Yes' if policy.get('enabled') else 'No (Monitoring)'}`",
        f"- **Block on Critical**: `{'Yes' if policy.get('block_critical', True) else 'No'}`",
        f"- **Block on High**: `{'Yes' if policy.get('block_high', True) else 'No'}`",
        f"- **Block on Medium**: `{'Yes' if policy.get('block_medium', False) else 'No'}`",
        f"- **Block on Incomplete Scan**: `{'Yes' if policy.get('block_incomplete', True) else 'No'}`",
        "",
        "</details>",
        "",
    ])

    # 1. Newly Introduced Actionable Findings
    if newly_introduced_actionable:
        lines.extend([
            "### 🚨 Newly Introduced Actionable Findings",
            "The following security issues were introduced on lines modified in this pull request:",
            "",
            "| Severity | Rule ID | File & Line | Message | Remediation |",
            "| :--- | :--- | :--- | :--- | :--- |",
        ])
        for f in newly_introduced_actionable:
            loc = f.get("location") or f"Line {f.get('line_number', 'N/A')}"
            file_loc = f"`{f.get('file_path') or f.get('file')}`:{loc}"
            rule = f.get("rule_id") or f.get("rule") or "SEC-VULN"
            sev = f.get("severity", "Medium")
            msg = f.get("message") or f.get("title") or ""
            rem = f.get("remediation") or "Review and sanitize input."
            lines.append(f"| **{sev}** | `{rule}` | {file_loc} | {msg} | {rem} |")
        lines.append("")
    else:
        lines.extend([
            "### 🚨 Newly Introduced Actionable Findings",
            "✅ *No new actionable vulnerabilities introduced on changed lines.*",
            "",
        ])

    # 2. Resolved Findings
    if resolved_findings:
        lines.extend([
            "### ✨ Resolved Findings",
            "The following security issues were resolved or removed in this pull request:",
            "",
            "| Severity | Rule ID | File | Message |",
            "| :--- | :--- | :--- | :--- |",
        ])
        for f in resolved_findings:
            f_path = f.get("file_path") or f.get("file") or ""
            rule = f.get("rule_id") or f.get("rule") or ""
            sev = f.get("severity", "Info")
            msg = f.get("message") or f.get("title") or "Resolved"
            lines.append(f"| {sev} | `{rule}` | `{f_path}` | {msg} |")
        lines.append("")

    # 3. Informational & Pre-existing Findings summary
    lines.extend([
        "### 📊 Finding Lineage & Inventory",
        f"- **Newly Introduced Actionable**: {len(newly_introduced_actionable)}",
        f"- **Newly Introduced Heuristic**: {len(newly_introduced_heuristic)}",
        f"- **Resolved in this PR**: {len(resolved_findings)}",
        f"- **Pre-existing Codebase Findings**: {len(existing_findings)} *(not blocking this PR)*",
        f"- **Test Fixture Matches**: {len(fixture_matches)} *(demonstration examples, not production risks)*",
        "",
        "---",
        "*Automated assessment generated by [GitFlow Security Engine](https://gitflow-rose-eight.vercel.app/).*",
    ])

    return "\n".join(lines)


def run_pr_security_check(
    repo_dir: str,
    base_sha: str,
    head_sha: str,
    policy: Optional[Dict[str, Any]] = None,
    precomputed_head_findings: Optional[List[Dict[str, Any]]] = None,
    precomputed_base_findings: Optional[List[Dict[str, Any]]] = None,
    precomputed_coverage: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Runs a complete PR security evaluation comparing base_sha and head_sha.

    Attributes findings to changed lines, computes finding lineage,
    evaluates policy, and produces markdown summary report.
    """
    if policy is None:
        policy = {
            "enabled": False,
            "block_critical": True,
            "block_high": True,
            "block_medium": False,
            "block_incomplete": True,
        }

    base_sha = str(getattr(base_sha, "stdout", base_sha)).strip()
    head_sha = str(getattr(head_sha, "stdout", head_sha)).strip()

    # 1. Parse diff
    diff_text = get_git_diff_output(repo_dir, base_sha, head_sha)
    changed_lines, file_statuses, renames = parse_diff_changed_lines(diff_text)

    # 2. Get HEAD findings
    if precomputed_head_findings is not None:
        head_findings = precomputed_head_findings
        coverage_data = precomputed_coverage or {"overall_status": "COMPLETED"}
    else:
        # Scan head
        scanner = UniversalScanner(repo_dir)
        head_findings = scanner.scan()
        coverage_data = scanner.get_coverage()

    # 3. Get BASE findings
    has_valid_baseline = False
    base_findings: List[Dict[str, Any]] = []
    if precomputed_base_findings is not None:
        base_findings = precomputed_base_findings
        has_valid_baseline = True
    elif base_sha and base_sha != head_sha:
        # Check if base commit is accessible in git
        try:
            res = subprocess.run(["git", "cat-file", "-e", f"{base_sha}^{{commit}}"], cwd=repo_dir, capture_output=True)
            if res.returncode == 0:
                has_valid_baseline = True
                import tempfile
                import shutil
                base_temp = tempfile.mkdtemp(prefix="gitflow_base_scan_")
                try:
                    subprocess.run(["git", "worktree", "add", "--detach", base_temp, base_sha], cwd=repo_dir, capture_output=True, check=True)
                    base_scanner = UniversalScanner(base_temp)
                    base_findings = base_scanner.scan()
                    subprocess.run(["git", "worktree", "remove", "--force", base_temp], cwd=repo_dir, capture_output=True)
                except Exception:
                    curr_head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=repo_dir, capture_output=True, text=True).stdout.strip()
                    subprocess.run(["git", "checkout", "--detach", base_sha], cwd=repo_dir, capture_output=True)
                    base_scanner = UniversalScanner(repo_dir)
                    base_findings = base_scanner.scan()
                    subprocess.run(["git", "checkout", "--detach", curr_head], cwd=repo_dir, capture_output=True)
                finally:
                    shutil.rmtree(base_temp, ignore_errors=True)
        except Exception as e:
            logger.warning(f"Could not scan base commit {base_sha}: {e}")
            has_valid_baseline = False

    base_fingerprints = {
        (f.get("fingerprint") or generate_fingerprint(f)) for f in base_findings
    }
    head_fingerprints = {
        (f.get("fingerprint") or generate_fingerprint(f)) for f in head_findings
    }

    # 4. Categorize HEAD findings
    newly_actionable: List[Dict[str, Any]] = []
    newly_heuristic: List[Dict[str, Any]] = []
    existing: List[Dict[str, Any]] = []
    fixtures: List[Dict[str, Any]] = []

    for f in head_findings:
        cat = categorize_finding_for_pr(
            finding=f,
            changed_lines_by_file=changed_lines,
            file_statuses=file_statuses,
            base_fingerprints=base_fingerprints,
            has_valid_baseline=has_valid_baseline,
        )
        if cat == "PR_INTRODUCED_ACTIONABLE":
            newly_actionable.append(f)
        elif cat == "PR_INTRODUCED_HEURISTIC":
            newly_heuristic.append(f)
        elif cat == "INFORMATIONAL_FIXTURE":
            fixtures.append(f)
        else:
            existing.append(f)

    # 5. Categorize Resolved findings
    resolved: List[Dict[str, Any]] = []
    if has_valid_baseline:
        for f in base_findings:
            fp = f.get("fingerprint") or generate_fingerprint(f)
            if fp not in head_fingerprints:
                resolved.append(f)

    # 6. Scores
    head_score_dict = calculate_risk_score(head_findings, coverage_status=coverage_data.get("overall_status", "COMPLETED"))
    head_score = head_score_dict["final_score"]

    base_score = None
    if has_valid_baseline and base_findings is not None:
        base_score_dict = calculate_risk_score(base_findings, coverage_status="COMPLETED")
        base_score = base_score_dict["final_score"]

    # 7. Evaluate Policy
    gate_status, gate_reason = evaluate_pr_gate_policy(
        newly_introduced_actionable=newly_actionable,
        coverage_status=coverage_data.get("overall_status", "COMPLETED"),
        policy=policy,
    )

    # 8. Markdown Summary
    summary_md = generate_pr_summary_markdown(
        base_sha=base_sha,
        head_sha=head_sha,
        gate_status=gate_status,
        gate_reason=gate_reason,
        policy=policy,
        coverage_data=coverage_data,
        newly_introduced_actionable=newly_actionable,
        newly_introduced_heuristic=newly_heuristic,
        resolved_findings=resolved,
        existing_findings=existing,
        fixture_matches=fixtures,
        head_score=head_score,
        base_score=base_score,
    )

    return {
        "status": gate_status,
        "reason": gate_reason,
        "base_sha": base_sha,
        "head_sha": head_sha,
        "policy": policy,
        "head_risk_score": head_score,
        "base_risk_score": base_score,
        "coverage": coverage_data,
        "changed_files_count": len(file_statuses),
        "changed_files": file_statuses,
        "newly_introduced_actionable_count": len(newly_actionable),
        "newly_introduced_actionable": newly_actionable,
        "newly_introduced_heuristic_count": len(newly_heuristic),
        "newly_introduced_heuristic": newly_heuristic,
        "resolved_count": len(resolved),
        "resolved_findings": resolved,
        "existing_count": len(existing),
        "existing_findings": existing,
        "fixture_matches_count": len(fixtures),
        "fixture_matches": fixtures,
        "summary_markdown": summary_md,
    }
