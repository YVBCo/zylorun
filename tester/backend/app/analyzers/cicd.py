"""Analyzer 8: CI/CD and Deployment Analyzer.

Inspects GitHub Actions workflows (.github/workflows/*.yml), Dockerfiles, and deployment configs
(render.yaml, vercel.json, docker-compose.yml).
Detects insecure permissions, exposed secrets/tokens, unpinned actions, and missing build/test steps.
"""

from __future__ import annotations

import os
import re
from typing import Any, Dict, List, Optional, Set, Tuple

from app.analyzers.base import BaseAnalyzer
from app.analysis.indexer import build_repository_index

SECRET_PATTERNS = [
    (re.compile(r"""(?:api_key|token|password|secret|auth)[_-]?(?:key|token)?\s*[:=]\s*['"]([A-Za-z0-9_\-]{20,})['"]""", re.IGNORECASE), "Exposed hardcoded secret or token"),
    (re.compile(r"""ghp_[A-Za-z0-9_]{36}"""), "GitHub Personal Access Token"),
    (re.compile(r"""AKIA[0-9A-Z]{16}"""), "AWS Access Key ID"),
    (re.compile(r"""(?:sk_live_|pk_live_)[0-9a-zA-Z]{24,}"""), "Stripe API Key"),
]

INJECTION_PATTERNS = [
    re.compile(r"""\$\{\{\s*github\.event\.issue\.title\s*\}\}"""),
    re.compile(r"""\$\{\{\s*github\.event\.issue\.body\s*\}\}"""),
    re.compile(r"""\$\{\{\s*github\.event\.pull_request\.title\s*\}\}"""),
    re.compile(r"""\$\{\{\s*github\.event\.pull_request\.body\s*\}\}"""),
    re.compile(r"""\$\{\{\s*github\.event\.comment\.body\s*\}\}"""),
    re.compile(r"""\$\{\{\s*github\.head_ref\s*\}\}"""),
]

TEST_COMMAND_PATTERNS = [
    re.compile(r"""\b(?:pytest|npm\s+test|vitest|jest|yarn\s+test|pnpm\s+test|cargo\s+test|go\s+test|mvn\s+test|gradle\s+test)\b""", re.IGNORECASE),
]


class CicdDeploymentAnalyzer(BaseAnalyzer):
    name = "cicd_deployment"
    version = "1.0.0"
    description = "Inspects GitHub Actions, Dockerfiles, and deployment manifests for security, permission, and test gaps."

    def _run(self, repo_dir: str, commit_sha: str, index: Optional[Dict[str, Any]] = None, **kwargs) -> Dict[str, Any]:
        if not index:
            index = build_repository_index(repo_dir, commit_sha)

        findings: List[Dict[str, Any]] = []
        limitations: List[str] = []
        workflow_files: List[str] = []
        docker_files: List[str] = []
        deploy_configs: List[str] = []
        files_scanned = 0

        # Discover CI/CD & Deployment files
        for root, dirs, fnames in os.walk(repo_dir):
            dirs[:] = [d for d in dirs if d not in [".git", "node_modules", "venv", ".venv", "dist", "build", "__pycache__"]]
            for fn in fnames:
                full_p = os.path.join(root, fn)
                rel_p = os.path.relpath(full_p, repo_dir).replace("\\", "/")

                if ".github/workflows" in rel_p and fn.endswith((".yml", ".yaml")):
                    workflow_files.append(rel_p)
                elif fn == "Dockerfile" or fn.endswith(".dockerfile") or fn.startswith("Dockerfile."):
                    docker_files.append(rel_p)
                elif fn in ["render.yaml", "vercel.json", "netlify.toml", "docker-compose.yml", "docker-compose.yaml", "Procfile"]:
                    deploy_configs.append(rel_p)

        files_scanned = len(workflow_files) + len(docker_files) + len(deploy_configs)

        # 1. Analyze GitHub Actions Workflows
        has_any_test_step = False
        for wf_rel in workflow_files:
            wf_findings, has_tests = self._analyze_workflow(os.path.join(repo_dir, wf_rel), wf_rel)
            findings.extend(wf_findings)
            if has_tests:
                has_any_test_step = True

        # Check if automated test step is completely missing across all CI workflows
        if workflow_files and not has_any_test_step:
            findings.append({
                "rule_id": "CICD-NO-TEST-STEP",
                "category": "CI/CD",
                "severity": "Medium",
                "confidence": "High",
                "classification": "Definite pipeline verification gap",
                "file_path": workflow_files[0],
                "line_number": 1,
                "title": "Missing Automated Test Step in CI Workflows",
                "description": "None of the GitHub Actions workflows execute automated unit or integration tests (pytest, npm test, vitest, etc.).",
                "evidence": f"Scanned {len(workflow_files)} workflow files; no test runners detected.",
                "remediation": "Add an automated test verification step (`pytest` or `npm test`) to your pull request workflow.",
            })
        elif not workflow_files:
            findings.append({
                "rule_id": "CICD-NO-WORKFLOWS",
                "category": "CI/CD",
                "severity": "Low",
                "confidence": "High",
                "classification": "Repository hygiene finding",
                "file_path": ".github/workflows",
                "line_number": None,
                "title": "No CI/CD Workflows Detected",
                "description": "No GitHub Actions workflows were found under `.github/workflows/`.",
                "evidence": "Directory `.github/workflows/` is missing or contains no YAML workflows.",
                "remediation": "Set up a GitHub Actions workflow to run linting, tests, and security scanning on pull requests.",
            })

        # 2. Analyze Dockerfiles
        for df_rel in docker_files:
            df_findings = self._analyze_dockerfile(os.path.join(repo_dir, df_rel), df_rel)
            findings.extend(df_findings)

        # 3. Analyze Deployment Configs (render.yaml, vercel.json)
        for cfg_rel in deploy_configs:
            cfg_findings = self._analyze_deployment_config(os.path.join(repo_dir, cfg_rel), cfg_rel)
            findings.extend(cfg_findings)

        if not workflow_files and not docker_files and not deploy_configs:
            limitations.append("No CI/CD workflows, Dockerfiles, or platform deployment manifests found in repository.")

        summary = (
            f"Analyzed {len(workflow_files)} CI workflow(s), {len(docker_files)} Dockerfile(s), "
            f"and {len(deploy_configs)} deployment manifest(s). Discovered {len(findings)} security or reliability finding(s)."
        )

        details = {
            "workflows_count": len(workflow_files),
            "workflows": workflow_files,
            "dockerfiles_count": len(docker_files),
            "dockerfiles": docker_files,
            "deployment_configs_count": len(deploy_configs),
            "deployment_configs": deploy_configs,
            "has_automated_tests_in_ci": has_any_test_step,
            "findings_count": len(findings),
        }

        return {
            "status": "COMPLETED",
            "coverage_status": "FULL" if files_scanned > 0 else "PARTIAL",
            "files_analyzed": files_scanned,
            "summary": summary,
            "findings_count": len(findings),
            "findings": findings,
            "details": details,
            "limitations": limitations,
        }

    def _analyze_workflow(self, full_path: str, rel_path: str) -> Tuple[List[Dict[str, Any]], bool]:
        """Inspects a GitHub Actions workflow file for permissions, secrets, unpinned actions, and test steps."""
        findings: List[Dict[str, Any]] = []
        has_tests = False

        try:
            with open(full_path, "r", encoding="utf-8", errors="ignore") as f:
                lines = f.readlines()
        except Exception:
            return findings, False

        content = "".join(lines)
        has_permissions_block = "permissions:" in content
        is_pr_or_push = any(trig in content for trig in ["pull_request", "push", "pull_request_target"])

        # Check explicit permissions block
        if not has_permissions_block and is_pr_or_push:
            findings.append({
                "rule_id": "CICD-MISSING-PERMISSIONS",
                "category": "CI/CD",
                "severity": "Medium",
                "confidence": "High",
                "classification": "Definite security posture defect",
                "file_path": rel_path,
                "line_number": 1,
                "title": "Missing Explicit Workflow Permissions Block",
                "description": "Workflow does not specify top-level `permissions:`. The default GITHUB_TOKEN may inherit broad write permissions.",
                "evidence": "No top-level 'permissions:' declared in workflow.",
                "remediation": "Add `permissions: contents: read` at top level to enforce least-privilege token access.",
            })

        # Check write-all permissions
        if re.search(r"""permissions:\s*write-all\b""", content, re.IGNORECASE):
            findings.append({
                "rule_id": "CICD-OVERLY-PERMISSIVE-TOKEN",
                "category": "CI/CD",
                "severity": "High",
                "confidence": "High",
                "classification": "Definite security vulnerability",
                "file_path": rel_path,
                "line_number": 1,
                "title": "Overly Permissive Workflow Token: `write-all`",
                "description": "Workflow grants `write-all` permissions to GITHUB_TOKEN, creating lateral privilege escalation risk.",
                "evidence": "permissions: write-all",
                "remediation": "Restrict token permissions to only explicitly needed scopes (e.g. contents: read, pull-requests: write).",
            })

        # Line-by-line checks
        uses_re = re.compile(r"""^\s*-\s*uses:\s*([^@\s]+)@([^\s#]+)""")
        run_re = re.compile(r"""^\s*run:\s*(.*)$""")

        in_run_block = False

        for idx, line in enumerate(lines, start=1):
            # Check unpinned actions
            uses_match = uses_re.search(line)
            if uses_match:
                action_name = uses_match.group(1)
                action_ref = uses_match.group(2)
                # If ref is not a 40-character hex commit SHA
                if not re.match(r"^[0-9a-f]{40}$", action_ref):
                    findings.append({
                        "rule_id": "CICD-UNPINNED-ACTION",
                        "category": "CI/CD",
                        "severity": "Low",
                        "confidence": "High",
                        "classification": "Definite supply chain hardening finding",
                        "file_path": rel_path,
                        "line_number": idx,
                        "title": f"Unpinned GitHub Action: `{action_name}@{action_ref}`",
                        "description": (
                            f"Action `{action_name}` is referenced by mutable tag/branch `{action_ref}` rather than an immutable commit SHA. "
                            f"If the upstream tag is moved or compromised, malicious code could execute in CI."
                        ),
                        "evidence": line.strip(),
                        "remediation": f"Pin the action to an immutable 40-character commit SHA (e.g. `{action_name}@<full-sha> # {action_ref}`).",
                    })

            # Check hardcoded secrets
            for pat, secret_type in SECRET_PATTERNS:
                if pat.search(line) and not any(safe_token in line for safe_token in ["${{ secrets.", "${{ env.", "example", "dummy"]):
                    findings.append({
                        "rule_id": "CICD-EXPOSED-SECRET",
                        "category": "CI/CD",
                        "severity": "Critical",
                        "confidence": "High",
                        "classification": "Definite credential exposure defect",
                        "file_path": rel_path,
                        "line_number": idx,
                        "title": f"Exposed Secret in CI Workflow ({secret_type})",
                        "description": f"Workflow contains potential hardcoded credentials matching `{secret_type}`.",
                        "evidence": line.strip()[:60] + "...",
                        "remediation": "Store secret in GitHub Actions Repository Secrets and inject via `${{ secrets.MY_SECRET }}`.",
                    })

            # Check script injection vulnerabilities in run blocks
            if "run:" in line or in_run_block:
                for inj_pat in INJECTION_PATTERNS:
                    if inj_pat.search(line):
                        findings.append({
                            "rule_id": "CICD-EXPRESSION-INJECTION",
                            "category": "CI/CD",
                            "severity": "High",
                            "confidence": "High",
                            "classification": "Definite code injection vulnerability",
                            "file_path": rel_path,
                            "line_number": idx,
                            "title": "Untrusted Context Expression Injection in `run` Step",
                            "description": "Untrusted user-controlled input (e.g. PR title or body) is directly interpolated inside a bash script execution step.",
                            "evidence": line.strip(),
                            "remediation": "Store the expression in an intermediate environment variable (e.g. `env: TITLE: ${{ github.event... }}`) and reference `$TITLE` in the script.",
                        })

            # Check test execution commands
            for test_pat in TEST_COMMAND_PATTERNS:
                if test_pat.search(line):
                    has_tests = True

        return findings, has_tests

    def _analyze_dockerfile(self, full_path: str, rel_path: str) -> List[Dict[str, Any]]:
        """Inspects Dockerfile for root user execution, unpinned base images, and healthchecks."""
        findings: List[Dict[str, Any]] = []
        try:
            with open(full_path, "r", encoding="utf-8", errors="ignore") as f:
                lines = f.readlines()
        except Exception:
            return findings

        has_user_instruction = False
        has_healthcheck = False

        from_re = re.compile(r"""^FROM\s+([^\s:]+)(?::([^\s]+))?""", re.IGNORECASE)

        for idx, line in enumerate(lines, start=1):
            line_str = line.strip()
            if line_str.startswith("#"):
                continue

            # Check FROM base image
            from_match = from_re.match(line_str)
            if from_match:
                img_name = from_match.group(1)
                img_tag = from_match.group(2)
                if not img_tag or img_tag.lower() == "latest":
                    findings.append({
                        "rule_id": "DOCKER-UNPINNED-IMAGE",
                        "category": "CI/CD",
                        "severity": "Low",
                        "confidence": "High",
                        "classification": "Definite container hygiene finding",
                        "file_path": rel_path,
                        "line_number": idx,
                        "title": f"Unpinned Docker Base Image: `{line_str}`",
                        "description": f"Base image `{img_name}` uses `:latest` or no tag, causing non-deterministic image builds.",
                        "evidence": line_str,
                        "remediation": "Pin base image to specific semantic version tag (e.g. `python:3.11-slim`).",
                    })

            # Check USER instruction
            if line_str.upper().startswith("USER "):
                has_user_instruction = True

            # Check HEALTHCHECK instruction
            if line_str.upper().startswith("HEALTHCHECK "):
                has_healthcheck = True

            # Check hardcoded secret in ENV or ARG
            if line_str.upper().startswith(("ENV ", "ARG ")):
                for pat, secret_type in SECRET_PATTERNS:
                    if pat.search(line_str):
                        findings.append({
                            "rule_id": "DOCKER-EXPOSED-SECRET",
                            "category": "CI/CD",
                            "severity": "Critical",
                            "confidence": "High",
                            "classification": "Definite container credential exposure",
                            "file_path": rel_path,
                            "line_number": idx,
                            "title": f"Exposed Secret in Dockerfile `{line_str.split()[0]}` Instruction",
                            "description": "Dockerfile bakes sensitive credentials into intermediate container image layers.",
                            "evidence": line_str[:60] + "...",
                            "remediation": "Do not commit secrets in Dockerfiles. Use Docker BuildKit secrets (`--mount=type=secret`) or runtime env vars.",
                        })

        if not has_user_instruction:
            findings.append({
                "rule_id": "DOCKER-ROOT-USER",
                "category": "CI/CD",
                "severity": "Medium",
                "confidence": "High",
                "classification": "Definite container security hardening finding",
                "file_path": rel_path,
                "line_number": 1,
                "title": "Container Runs as Root (Missing `USER` Instruction)",
                "description": "Dockerfile lacks a non-root `USER` instruction. Running processes as root increases container breakout impact.",
                "evidence": "No USER instruction found in Dockerfile.",
                "remediation": "Create and switch to a dedicated non-root user (e.g. `RUN useradd -u 8888 appuser && USER appuser`).",
            })

        if not has_healthcheck:
            findings.append({
                "rule_id": "DOCKER-MISSING-HEALTHCHECK",
                "category": "CI/CD",
                "severity": "Low",
                "confidence": "High",
                "classification": "Definite reliability finding",
                "file_path": rel_path,
                "line_number": 1,
                "title": "Missing Container `HEALTHCHECK` Instruction",
                "description": "Dockerfile has no HEALTHCHECK instruction, preventing orchestrators (Kubernetes, Docker Swarm) from detecting deadlocks.",
                "evidence": "No HEALTHCHECK instruction declared in Dockerfile.",
                "remediation": "Add `HEALTHCHECK --interval=30s --timeout=3s CMD curl -f http://localhost:8000/health || exit 1`.",
            })

        return findings

    def _analyze_deployment_config(self, full_path: str, rel_path: str) -> List[Dict[str, Any]]:
        """Inspects render.yaml, vercel.json, and docker-compose configs."""
        findings: List[Dict[str, Any]] = []
        try:
            with open(full_path, "r", encoding="utf-8", errors="ignore") as f:
                lines = f.readlines()
        except Exception:
            return findings

        for idx, line in enumerate(lines, start=1):
            line_str = line.strip()
            # Hardcoded secrets
            for pat, secret_type in SECRET_PATTERNS:
                if pat.search(line_str) and not any(s in line_str for s in ["sync: false", "generateValue: true", "${", "dummy"]):
                    findings.append({
                        "rule_id": "DEPLOY-EXPOSED-SECRET",
                        "category": "CI/CD",
                        "severity": "High",
                        "confidence": "High",
                        "classification": "Definite deployment credential exposure",
                        "file_path": rel_path,
                        "line_number": idx,
                        "title": f"Exposed Secret in Deployment Manifest ({secret_type})",
                        "description": f"Deployment config `{rel_path}` contains plain-text credentials.",
                        "evidence": line_str[:60] + "...",
                        "remediation": "Reference environment variables dynamically through platform secrets manager.",
                    })

        return findings
