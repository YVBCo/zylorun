"""Shared Repository Indexer for GitFlow Project Hub.

Provides deterministic, revision-aware static indexing of a repository:
- Files, extensions, and language distribution
- Frameworks and build systems
- Application entry points
- API routes (FastAPI, Flask, Express)
- Database models and Alembic migrations
- Test suites and test-to-source mappings
- CI/CD workflows and deployment manifests
- Third-party packages and dependencies
"""

import json
import os
import re
from typing import Any, Dict, List, Optional, Set

LANGUAGE_EXTENSIONS = {
    ".py": "Python",
    ".ts": "TypeScript",
    ".tsx": "TypeScript (React)",
    ".js": "JavaScript",
    ".jsx": "JavaScript (React)",
    ".json": "JSON",
    ".html": "HTML",
    ".css": "CSS",
    ".scss": "SCSS",
    ".sql": "SQL",
    ".sh": "Shell",
    ".bash": "Shell",
    ".md": "Markdown",
    ".yml": "YAML",
    ".yaml": "YAML",
    ".go": "Go",
    ".rs": "Rust",
    ".java": "Java",
    ".c": "C",
    ".cpp": "C++",
    ".rb": "Ruby",
    ".php": "PHP",
}

IGNORED_DIRS = {
    ".git",
    ".venv",
    "venv",
    "env",
    "node_modules",
    "dist",
    "build",
    "out",
    ".next",
    ".turbo",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    "coverage",
    ".idea",
    ".vscode",
}


def build_repository_index(repo_dir: str, commit_sha: str) -> Dict[str, Any]:
    """Generates a comprehensive deterministic repository index from repo_dir."""
    files: List[str] = []
    language_counts: Dict[str, int] = {}
    file_count = 0

    # 1. Walk directory and catalog files
    for root, dirs, filenames in os.walk(repo_dir):
        # Prune ignored directories in-place
        dirs[:] = [d for d in dirs if d not in IGNORED_DIRS and not d.startswith(".")]

        rel_dir = os.path.relpath(root, repo_dir).replace("\\", "/")
        for filename in filenames:
            file_count += 1
            rel_path = f"{rel_dir}/{filename}" if rel_dir != "." else filename
            files.append(rel_path)

            _, ext = os.path.splitext(filename.lower())
            if filename.lower() == "dockerfile":
                lang = "Docker"
            else:
                lang = LANGUAGE_EXTENSIONS.get(ext, "Other")
            language_counts[lang] = language_counts.get(lang, 0) + 1

    # Format language distribution percentages
    languages_breakdown: Dict[str, Any] = {}
    if file_count > 0:
        for lang, count in sorted(language_counts.items(), key=lambda x: x[1], reverse=True):
            languages_breakdown[lang] = {
                "count": count,
                "percentage": round((count / file_count) * 100, 1),
            }

    # 2. Framework & technology detection
    frameworks: List[str] = []
    dependencies_list: List[Dict[str, str]] = []

    # Check package.json
    pkg_json_path = os.path.join(repo_dir, "package.json")
    if not os.path.exists(pkg_json_path):
        # Also check frontend/package.json
        pkg_json_path = os.path.join(repo_dir, "frontend", "package.json")

    if os.path.exists(pkg_json_path):
        try:
            with open(pkg_json_path, "r", encoding="utf-8", errors="ignore") as f:
                pkg_data = json.load(f)
                deps = {**pkg_data.get("dependencies", {}), **pkg_data.get("devDependencies", {})}
                for name, ver in deps.items():
                    dependencies_list.append({"name": name, "version": ver, "ecosystem": "npm"})
                    n_lower = name.lower()
                    if "react" in n_lower and "React" not in frameworks:
                        frameworks.append("React")
                    if "vite" in n_lower and "Vite" not in frameworks:
                        frameworks.append("Vite")
                    if "tailwind" in n_lower and "TailwindCSS" not in frameworks:
                        frameworks.append("TailwindCSS")
                    if "express" in n_lower and "Express" not in frameworks:
                        frameworks.append("Express")
                    if "next" in n_lower and "Next.js" not in frameworks:
                        frameworks.append("Next.js")
                    if "lucide" in n_lower and "Lucide Icons" not in frameworks:
                        frameworks.append("Lucide Icons")
                    if "axios" in n_lower and "Axios" not in frameworks:
                        frameworks.append("Axios")
        except Exception:
            pass

    # Check Python requirements / pyproject.toml
    req_files = ["requirements.txt", "backend/requirements.txt", "pyproject.toml"]
    for req_rel in req_files:
        req_path = os.path.join(repo_dir, req_rel)
        if os.path.exists(req_path):
            content = ""
            for enc in ["utf-8", "utf-16", "utf-16-le", "latin-1"]:
                try:
                    with open(req_path, "r", encoding=enc) as f:
                        content = f.read()
                    if content and "\x00" not in content:
                        break
                except Exception:
                    continue
            if content:
                for line in content.splitlines():
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue
                    match = re.match(r"^([a-zA-Z0-9_\-]+)(?:==|>=|<=|~=)?(.*)$", line)
                    if match:
                        pkg_name = match.group(1).lower()
                        pkg_ver = match.group(2) or "latest"
                        dependencies_list.append({"name": pkg_name, "version": pkg_ver, "ecosystem": "pypi"})
                        if "fastapi" in pkg_name and "FastAPI" not in frameworks:
                            frameworks.append("FastAPI")
                        if "sqlalchemy" in pkg_name and "SQLAlchemy" not in frameworks:
                            frameworks.append("SQLAlchemy")
                        if "alembic" in pkg_name and "Alembic" not in frameworks:
                            frameworks.append("Alembic")
                        if "pytest" in pkg_name and "pytest" not in frameworks:
                            frameworks.append("pytest")
                        if "pydantic" in pkg_name and "Pydantic" not in frameworks:
                            frameworks.append("Pydantic")
                        if "uvicorn" in pkg_name and "Uvicorn" not in frameworks:
                            frameworks.append("Uvicorn")
                        if "asyncpg" in pkg_name and "PostgreSQL (asyncpg)" not in frameworks:
                            frameworks.append("PostgreSQL (asyncpg)")

    # 3. Entry points
    potential_entry_points = [
        "backend/app/main.py",
        "app/main.py",
        "main.py",
        "server.py",
        "app.py",
        "frontend/src/main.tsx",
        "frontend/src/App.tsx",
        "src/main.tsx",
        "src/index.tsx",
        "src/index.js",
        "index.html",
        "frontend/index.html",
    ]
    entry_points = [ep for ep in potential_entry_points if ep in files or ep.replace("/", "\\") in files]

    # 4. API Routes discovery
    api_routes: List[Dict[str, str]] = []
    py_files = [f for f in files if f.endswith(".py")]
    route_regex = re.compile(r"""@(?:router|app)\.(get|post|put|delete|patch|options)\s*\(\s*["']([^"']+)["']""", re.IGNORECASE)

    for py_f in py_files:
        full_p = os.path.join(repo_dir, py_f)
        try:
            with open(full_p, "r", encoding="utf-8", errors="ignore") as f:
                for line_idx, line in enumerate(f, start=1):
                    match = route_regex.search(line)
                    if match:
                        method = match.group(1).upper()
                        path = match.group(2)
                        api_routes.append({
                            "method": method,
                            "path": path,
                            "file": py_f,
                            "line": line_idx,
                        })
        except Exception:
            pass

    # 5. Database models and Alembic migrations
    database_models: List[Dict[str, Any]] = []
    model_regex = re.compile(r"""class\s+([A-Za-z0-9_]+)\s*\(\s*(?:Base|models\.Model|db\.Model)""")
    table_regex = re.compile(r"""__tablename__\s*=\s*["']([^"']+)["']""")

    for py_f in py_files:
        full_p = os.path.join(repo_dir, py_f)
        try:
            with open(full_p, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
                matches = model_regex.finditer(content)
                for m in matches:
                    class_name = m.group(1)
                    # Extract table name if present in vicinity
                    sub_content = content[m.start():m.start() + 400]
                    tbl_match = table_regex.search(sub_content)
                    table_name = tbl_match.group(1) if tbl_match else None
                    database_models.append({
                        "name": class_name,
                        "table_name": table_name,
                        "file": py_f,
                    })
        except Exception:
            pass

    # Alembic migrations count and list
    migration_files = [f for f in files if "alembic/versions" in f and f.endswith(".py")]

    # 6. Test files discovery
    test_files = [
        f for f in files
        if (
            f.startswith("tests/")
            or "tests/" in f
            or f.startswith("backend/tests/")
            or os.path.basename(f).startswith("test_")
            or f.endswith(".test.ts")
            or f.endswith(".test.tsx")
            or f.endswith(".spec.ts")
            or f.endswith(".spec.tsx")
        )
    ]

    # 7. CI/CD & Deployment manifests
    ci_cd_files = [
        f for f in files
        if (
            f.startswith(".github/workflows/")
            or f in ["Dockerfile", "docker-compose.yml", "render.yaml", "vercel.json", "netlify.toml", "Procfile"]
            or f.endswith("/Dockerfile")
        )
    ]

    # 8. High-level module mapping
    module_map: Dict[str, List[str]] = {}
    for f_path in files:
        parts = f_path.split("/")
        top_module = parts[0] if len(parts) > 1 else "root"
        if top_module not in module_map:
            module_map[top_module] = []
        if len(module_map[top_module]) < 20:
            module_map[top_module].append(f_path)

    return {
        "commit_sha": commit_sha,
        "file_count": file_count,
        "languages": languages_breakdown,
        "frameworks": frameworks,
        "entry_points": entry_points,
        "module_map": module_map,
        "api_routes": api_routes,
        "database_models": database_models,
        "migrations_count": len(migration_files),
        "test_files": test_files,
        "dependencies": dependencies_list,
        "ci_cd_files": ci_cd_files,
    }
