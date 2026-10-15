"""Analyzer 10: Documentation and Onboarding Analyzer.

Inspects README.md, setup guides, and documentation files.
Checks for broken relative markdown links, references to nonexistent files,
and undocumented environment variables accessed in the codebase.
Generates comprehensive repository onboarding guide data.
"""

import os
import re
from typing import Any, Dict, List, Optional, Set, Tuple

from app.analyzers.base import BaseAnalyzer
from app.analysis.indexer import build_repository_index

SYSTEM_ENV_VARS = {
    "PATH", "PYTHONPATH", "NODE_ENV", "PORT", "HOST", "HOME", "USER",
    "PWD", "SHELL", "TERM", "CI", "DEBUG", "LANG", "LC_ALL", "TZ"
}


class DocsOnboardingAnalyzer(BaseAnalyzer):
    name = "docs_onboarding"
    version = "1.0.0"
    description = "Inspects repository documentation, broken relative links, undocumented env vars, and onboarding guides."

    def _run(self, repo_dir: str, commit_sha: str, index: Optional[Dict[str, Any]] = None, **kwargs) -> Dict[str, Any]:
        if not index:
            index = build_repository_index(repo_dir, commit_sha)

        doc_files: List[str] = []
        findings: List[Dict[str, Any]] = []
        limitations: List[str] = []

        all_repo_files: Set[str] = set()

        # 1. Walk repo to catalog files and find doc files
        for root, dirs, fnames in os.walk(repo_dir):
            dirs[:] = [d for d in dirs if d not in [".git", "node_modules", "venv", ".venv", "dist", "build", "__pycache__", ".pytest_cache"]]
            for fn in fnames:
                full_p = os.path.join(root, fn)
                rel_p = os.path.relpath(full_p, repo_dir).replace("\\", "/")
                all_repo_files.add(rel_p)

                if fn.lower().startswith("readme") or fn.endswith((".md", ".rst")) or "docs/" in rel_p.lower():
                    doc_files.append(rel_p)

        # 2. Extract environment variables referenced across codebase
        code_env_vars = self._extract_code_env_vars(repo_dir)

        # 3. Read documentation files and .env.example files to discover documented env vars
        documented_env_vars, doc_contents = self._extract_documented_env_vars(repo_dir, doc_files)

        # 4. Check for Broken Relative Links and References to Nonexistent Files in docs
        broken_links, missing_files = self._check_doc_links_and_files(repo_dir, doc_files, all_repo_files)
        findings.extend(broken_links)
        findings.extend(missing_files)

        # 5. Check for Undocumented Environment Variables
        undocumented_vars = []
        for var_name, usages in code_env_vars.items():
            if var_name not in documented_env_vars and var_name not in SYSTEM_ENV_VARS:
                undocumented_vars.append({"name": var_name, "usages": usages})
                first_usage = usages[0] if usages else {"file": "codebase", "line": 1}
                findings.append({
                    "rule_id": "DOCS-UNDOCUMENTED-ENV-VAR",
                    "category": "Documentation",
                    "severity": "Medium",
                    "confidence": "High",
                    "classification": "Definite onboarding defect",
                    "file_path": first_usage["file"],
                    "line_number": first_usage["line"],
                    "title": f"Undocumented Environment Variable: `{var_name}`",
                    "description": (
                        f"Environment variable `{var_name}` is accessed in {len(usages)} location(s) "
                        f"(e.g. `{first_usage['file']}:{first_usage['line']}`), but is not documented in README or .env.example."
                    ),
                    "evidence": f"os.getenv('{var_name}') / process.env.{var_name}",
                    "remediation": f"Add `{var_name}` with a description and default value to `.env.example` and `README.md`.",
                })

        # Check if README.md exists
        has_readme = any(os.path.basename(f).lower() == "readme.md" for f in doc_files)
        if not has_readme:
            findings.append({
                "rule_id": "DOCS-MISSING-README",
                "category": "Documentation",
                "severity": "High",
                "confidence": "High",
                "classification": "Definite documentation defect",
                "file_path": "README.md",
                "line_number": 1,
                "title": "Missing Repository README.md",
                "description": "Repository root does not contain a README.md file to guide new developers.",
                "evidence": "No README.md discovered in root directory.",
                "remediation": "Create a README.md documenting project purpose, prerequisites, setup instructions, and architecture.",
            })

        # Calculate documentation health score (0 - 100)
        has_env_example = any("env.example" in f.lower() or "env.sample" in f.lower() for f in all_repo_files)
        health_score = 100
        if not has_readme:
            health_score -= 35
        if not has_env_example and code_env_vars:
            health_score -= 20
        health_score -= min(30, len(broken_links) * 10)
        health_score -= min(25, len(undocumented_vars) * 5)
        health_score -= min(15, len(missing_files) * 5)
        health_score = max(0, min(100, health_score))

        # Synthesize repository onboarding guide
        onboarding_guide = self._synthesize_onboarding_guide(index, code_env_vars, has_env_example, all_repo_files)

        if not doc_files:
            limitations.append("No Markdown or reStructuredText documentation files found in repository.")

        summary = (
            f"Analyzed {len(doc_files)} documentation file(s) and {len(code_env_vars)} code environment variable(s). "
            f"Found {len(broken_links)} broken relative link(s), {len(missing_files)} nonexistent file reference(s), "
            f"and {len(undocumented_vars)} undocumented env var(s) (Doc Health Score: {health_score}/100)."
        )

        details = {
            "documentation_files_count": len(doc_files),
            "documentation_files": doc_files[:20],
            "documentation_health_score": health_score,
            "code_environment_variables": {k: len(v) for k, v in code_env_vars.items()},
            "documented_environment_variables": sorted(list(documented_env_vars)),
            "undocumented_environment_variables": [u["name"] for u in undocumented_vars],
            "broken_links_count": len(broken_links),
            "missing_file_references_count": len(missing_files),
            "onboarding_guide": onboarding_guide,
        }

        return {
            "status": "COMPLETED",
            "coverage_status": "FULL" if doc_files else "PARTIAL",
            "files_analyzed": len(doc_files),
            "summary": summary,
            "findings_count": len(findings),
            "findings": findings,
            "details": details,
            "limitations": limitations,
        }

    def _extract_code_env_vars(self, repo_dir: str) -> Dict[str, List[Dict[str, Any]]]:
        """Scans Python, JS, and TS files for environment variable accesses."""
        env_vars: Dict[str, List[Dict[str, Any]]] = {}

        patterns = [
            # Python os.getenv("VAR") or os.environ.get("VAR") or os.environ["VAR"]
            re.compile(r"""(?:os\.)?(?:getenv|environ(?:\.get)?)\s*[\(\[]\s*['"]([A-Z0-9_]{3,})['"]"""),
            # JS/TS process.env.VAR or process.env['VAR']
            re.compile(r"""process\.env(?:\.([A-Z0-9_]{3,})|\[['"]([A-Z0-9_]{3,})['"]\])"""),
            # Vite / Next import.meta.env.VITE_VAR
            re.compile(r"""import\.meta\.env\.([A-Z0-9_]{3,})"""),
        ]

        for root, dirs, fnames in os.walk(repo_dir):
            dirs[:] = [d for d in dirs if d not in [".git", "node_modules", "venv", ".venv", "dist", "build", "__pycache__"]]
            for fn in fnames:
                if not fn.endswith((".py", ".ts", ".tsx", ".js", ".jsx")):
                    continue
                full_p = os.path.join(root, fn)
                rel_p = os.path.relpath(full_p, repo_dir).replace("\\", "/")

                try:
                    with open(full_p, "r", encoding="utf-8", errors="ignore") as f:
                        for idx, line in enumerate(f, start=1):
                            for pat in patterns:
                                for match in pat.finditer(line):
                                    var_name = match.group(1) or (match.group(2) if match.lastindex >= 2 else None)
                                    if var_name:
                                        if var_name not in env_vars:
                                            env_vars[var_name] = []
                                        env_vars[var_name].append({"file": rel_p, "line": idx})
                except Exception:
                    pass

        return env_vars

    def _extract_documented_env_vars(
        self, repo_dir: str, doc_files: List[str]
    ) -> Tuple[Set[str], Dict[str, str]]:
        """Collects env vars mentioned in docs and .env* files."""
        documented: Set[str] = set()
        doc_contents: Dict[str, str] = {}

        # 1. Check doc files
        env_mention_re = re.compile(r"""\b([A-Z][A-Z0-9_]{2,})\b""")
        for df in doc_files:
            full_p = os.path.join(repo_dir, df)
            try:
                with open(full_p, "r", encoding="utf-8", errors="ignore") as f:
                    txt = f.read()
                    doc_contents[df] = txt
                    for match in env_mention_re.finditer(txt):
                        documented.add(match.group(1))
            except Exception:
                pass

        # 2. Check .env.example, .env.sample, .env.template, etc.
        env_files = [".env.example", ".env.sample", ".env.template", "backend/.env.example", "frontend/.env.example"]
        env_line_re = re.compile(r"""^\s*([A-Za-z0-9_]+)\s*=""", re.MULTILINE)

        for ef in env_files:
            full_p = os.path.join(repo_dir, ef)
            if os.path.exists(full_p):
                try:
                    with open(full_p, "r", encoding="utf-8", errors="ignore") as f:
                        txt = f.read()
                        for match in env_line_re.finditer(txt):
                            documented.add(match.group(1))
                except Exception:
                    pass

        return documented, doc_contents

    def _check_doc_links_and_files(
        self, repo_dir: str, doc_files: List[str], all_repo_files: Set[str]
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """Checks relative links and file references in documentation files."""
        broken_links: List[Dict[str, Any]] = []
        missing_files: List[Dict[str, Any]] = []

        link_re = re.compile(r"""\[([^\]]+)\]\(([^)]+)\)""")
        file_ref_re = re.compile(r"""`([a-zA-Z0-9_\-\./]+\.[a-zA-Z0-9_\-]+)`""")

        # Ignore non-file extensions
        code_symbol_exts = {".get", ".post", ".put", ".delete", ".run", ".length", ".map", ".filter", ".then", ".catch"}

        for df in doc_files:
            full_p = os.path.join(repo_dir, df)
            try:
                with open(full_p, "r", encoding="utf-8", errors="ignore") as f:
                    lines = f.readlines()
            except Exception:
                continue

            doc_dir = os.path.dirname(df)

            for idx, line in enumerate(lines, start=1):
                # 1. Relative markdown links
                for match in link_re.finditer(line):
                    link_text = match.group(1)
                    target = match.group(2).strip()

                    # Ignore external URLs, anchors, mailto
                    if target.startswith(("http://", "https://", "mailto:", "#", "tel:")):
                        continue

                    # Strip anchor from relative link (e.g. ./docs/setup.md#prerequisites)
                    target_file = target.split("#")[0]
                    if not target_file:
                        continue

                    # Resolve target path relative to doc directory
                    resolved_rel = os.path.normpath(os.path.join(doc_dir, target_file)).replace("\\", "/")
                    target_full = os.path.join(repo_dir, resolved_rel)

                    if not os.path.exists(target_full) and resolved_rel not in all_repo_files:
                        broken_links.append({
                            "rule_id": "DOCS-BROKEN-RELATIVE-LINK",
                            "category": "Documentation",
                            "severity": "Medium",
                            "confidence": "High",
                            "classification": "Definite broken documentation link",
                            "file_path": df,
                            "line_number": idx,
                            "title": f"Broken Relative Link in `{df}`: `{target}`",
                            "description": f"Markdown link `[{link_text}]({target})` points to non-existent path `{resolved_rel}`.",
                            "evidence": line.strip()[:80],
                            "remediation": f"Update the link in `{df}` to a valid repository file path or remove it.",
                        })

                # 2. Backtick file references
                for match in file_ref_re.finditer(line):
                    ref = match.group(1).strip()
                    _, ext = os.path.splitext(ref)

                    if ext.lower() in code_symbol_exts or "/" not in ref and "." not in ref:
                        continue

                    # Check if looks like a setup reference (e.g. .env.example, docker-compose.yml)
                    if ref in [".env.example", ".env", "docker-compose.yml", "Dockerfile", "render.yaml", "requirements.txt", "package.json"]:
                        # Check if file exists anywhere in repo or with relative prefix
                        found = any(f.endswith(ref) or f == ref for f in all_repo_files)
                        if not found and ref not in [".env"]:  # .env is expected to be gitignored
                            missing_files.append({
                                "rule_id": "DOCS-MISSING-REFERENCED-FILE",
                                "category": "Documentation",
                                "severity": "Medium",
                                "confidence": "High",
                                "classification": "Definite missing onboarding resource",
                                "file_path": df,
                                "line_number": idx,
                                "title": f"Referenced Configuration File Missing: `{ref}`",
                                "description": f"Documentation references configuration file `{ref}`, but it does not exist in the repository.",
                                "evidence": f"Mentioned in `{df}:{idx}`",
                                "remediation": f"Provide `{ref}` template in the repository or update documentation.",
                            })

        return broken_links, missing_files

    def _synthesize_onboarding_guide(
        self,
        index: Dict[str, Any],
        code_env_vars: Dict[str, List[Dict[str, Any]]],
        has_env_example: bool,
        all_files: Set[str],
    ) -> Dict[str, Any]:
        """Synthesizes structured onboarding guide from repository index and detected stack."""
        frameworks = index.get("frameworks", [])
        languages = index.get("languages", {})

        prerequisites = ["Git"]
        if "Python" in languages:
            prerequisites.append("Python 3.10+")
        if any("TypeScript" in l or "JavaScript" in l for l in languages):
            prerequisites.append("Node.js 18+ & npm/pnpm")
        if "Docker" in languages or any("Dockerfile" in f for f in all_files):
            prerequisites.append("Docker & Docker Compose")

        install_steps = []
        dev_commands = []
        test_commands = []

        if "Python" in languages:
            install_steps.append("python -m venv venv && source venv/bin/activate (or .\\venv\\Scripts\\Activate.ps1)")
            install_steps.append("pip install -r backend/requirements.txt (or requirements.txt)")
            dev_commands.append("uvicorn app.main:app --reload --port 8000")
            test_commands.append("pytest backend/tests")

        if any("TypeScript" in l or "JavaScript" in l for l in languages):
            install_steps.append("npm install (or cd frontend && npm install)")
            dev_commands.append("npm run dev")
            test_commands.append("npm test")

        config_steps = []
        if has_env_example:
            config_steps.append("cp .env.example .env (and configure required environment variables)")
        elif code_env_vars:
            config_steps.append("Create `.env` file containing required environment variables")

        return {
            "title": "Automated Developer Onboarding Guide",
            "prerequisites": prerequisites,
            "installation_steps": install_steps,
            "configuration_steps": config_steps,
            "development_commands": dev_commands,
            "testing_commands": test_commands,
            "required_env_vars_count": len(code_env_vars),
        }
