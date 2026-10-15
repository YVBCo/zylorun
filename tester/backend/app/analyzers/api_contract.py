"""Analyzer 6: API and Contract Analyzer.

Discovers backend FastAPI, Flask, and Express route definitions, parses request/response contracts,
detects breaking API revisions, identifies frontend-to-backend consumer mismatches,
and clearly distinguishes between verified and heuristic contract findings.
"""

import ast
import hashlib
import os
import re
from typing import Any, Dict, List, Optional, Set, Tuple

from app.analyzers.base import BaseAnalyzer
from app.analysis.indexer import build_repository_index


class ApiContractAnalyzer(BaseAnalyzer):
    name = "api_contract"
    version = "1.0.0"
    description = "Discovers API routes, parameters, breaking changes, and frontend-backend contract mismatches."

    def _run(self, repo_dir: str, commit_sha: str, index: Optional[Dict[str, Any]] = None, **kwargs) -> Dict[str, Any]:
        if not index:
            index = build_repository_index(repo_dir, commit_sha)

        routes: List[Dict[str, Any]] = []
        frontend_calls: List[Dict[str, Any]] = []
        breaking_changes: List[Dict[str, Any]] = []
        findings: List[Dict[str, Any]] = []
        limitations: List[str] = []

        files_scanned = 0

        # 1. Parse Backend Routes (FastAPI, Flask, Express)
        for root, dirs, fnames in os.walk(repo_dir):
            dirs[:] = [d for d in dirs if d not in [".git", "node_modules", "venv", ".venv", "dist", "build", "__pycache__", ".pytest_cache"]]
            for fn in fnames:
                full_p = os.path.join(root, fn)
                rel_p = os.path.relpath(full_p, repo_dir).replace("\\", "/")

                if fn.endswith(".py"):
                    files_scanned += 1
                    routes.extend(self._parse_python_routes(full_p, rel_p))
                elif fn.endswith((".ts", ".tsx", ".js", ".jsx")):
                    files_scanned += 1
                    # Can contain Express backend routes or frontend API client calls
                    routes.extend(self._parse_express_routes(full_p, rel_p))
                    frontend_calls.extend(self._parse_frontend_calls(full_p, rel_p))
                elif fn.endswith((".vue", ".svelte", ".html")):
                    files_scanned += 1
                    frontend_calls.extend(self._parse_frontend_calls(full_p, rel_p))

        # 2. Check for Breaking Changes between revisions (if git/diff available)
        breaking_changes = self._detect_breaking_changes(repo_dir, commit_sha, routes)
        for bc in breaking_changes:
            findings.append({
                "rule_id": bc.get("rule_id", "API-BREAKING-CHANGE"),
                "category": "API Contract",
                "severity": bc.get("severity", "High"),
                "confidence": "High",
                "classification": "Verified breaking API change",
                "file_path": bc.get("file", ""),
                "line_number": bc.get("line"),
                "title": bc.get("title", "Breaking API Change Detected"),
                "description": bc.get("description", ""),
                "evidence": bc.get("evidence", ""),
                "remediation": bc.get("remediation", "Ensure backward compatibility or version the endpoint."),
            })

        # 3. Detect Frontend-to-Backend Mismatches
        mismatches = self._detect_consumer_mismatches(routes, frontend_calls)
        for mm in mismatches:
            is_heuristic = mm.get("is_heuristic", False)
            classification = (
                "Heuristic contract mismatch requiring manual verification"
                if is_heuristic
                else "Verified consumer contract mismatch"
            )
            confidence = "Medium" if is_heuristic else "High"
            severity = "Medium" if is_heuristic else "High"

            findings.append({
                "rule_id": mm.get("rule_id", "API-CONSUMER-MISMATCH"),
                "category": "API Contract",
                "severity": severity,
                "confidence": confidence,
                "classification": classification,
                "file_path": mm.get("file", ""),
                "line_number": mm.get("line"),
                "title": mm.get("title", "API Contract Mismatch"),
                "description": mm.get("description", ""),
                "evidence": mm.get("evidence", ""),
                "remediation": mm.get("remediation", "Verify endpoint path, HTTP method, and required parameters match backend contract."),
            })

        # Limitations
        if not routes:
            limitations.append("No backend API route definitions discovered in Python or Express files.")
        if not frontend_calls:
            limitations.append("No frontend API consumers discovered in client templates or source scripts.")

        verified_findings = [f for f in findings if f["confidence"] == "High"]
        heuristic_findings = [f for f in findings if f["confidence"] != "High"]

        summary = (
            f"Discovered {len(routes)} backend route definition(s) and {len(frontend_calls)} frontend API call(s). "
            f"Identified {len(breaking_changes)} potential breaking change(s) and {len(mismatches)} consumer mismatch(es) "
            f"({len(verified_findings)} verified, {len(heuristic_findings)} heuristic)."
        )

        details = {
            "routes_count": len(routes),
            "routes": routes[:50],
            "frontend_calls_count": len(frontend_calls),
            "frontend_calls": frontend_calls[:50],
            "breaking_changes_count": len(breaking_changes),
            "breaking_changes": breaking_changes,
            "consumer_mismatches_count": len(mismatches),
            "consumer_mismatches": mismatches,
            "verified_count": len(verified_findings),
            "heuristic_count": len(heuristic_findings),
        }

        return {
            "status": "COMPLETED",
            "coverage_status": "FULL" if routes or frontend_calls else "PARTIAL",
            "files_analyzed": files_scanned,
            "summary": summary,
            "findings_count": len(findings),
            "findings": findings,
            "details": details,
            "limitations": limitations,
        }

    def _parse_python_routes(self, file_path: str, rel_path: str) -> List[Dict[str, Any]]:
        """Parses FastAPI and Flask routes using AST analysis with regex fallback."""
        routes: List[Dict[str, Any]] = []
        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
        except Exception:
            return routes

        # Try AST parsing
        try:
            tree = ast.parse(content, filename=file_path)
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    for decorator in node.decorator_list:
                        route_info = self._extract_route_from_decorator(decorator, node, rel_path)
                        if route_info:
                            routes.append(route_info)
            if routes:
                return routes
        except Exception:
            pass

        # Regex fallback for FastAPI / Flask
        route_regex = re.compile(
            r"""@(?:router|app|bp|api)\.(get|post|put|delete|patch|options|route|api_route)\s*\(\s*["']([^"']+)["'](?:\s*,\s*methods=\[([^\]]+)\])?""",
            re.IGNORECASE,
        )
        for idx, line in enumerate(content.splitlines(), start=1):
            m = route_regex.search(line)
            if m:
                action = m.group(1).upper()
                path = m.group(2)
                methods_raw = m.group(3)
                if action == "ROUTE" and methods_raw:
                    methods = [x.strip().strip("'\"").upper() for x in methods_raw.split(",")]
                elif action in ["ROUTE", "API_ROUTE"]:
                    methods = ["GET"]
                else:
                    methods = [action]

                # Extract path params like {id}
                path_params = re.findall(r"\{([a-zA-Z0-9_]+)\}", path)
                for meth in methods:
                    routes.append({
                        "framework": "FastAPI/Flask",
                        "method": meth,
                        "path": path,
                        "file": rel_path,
                        "line": idx,
                        "parameters": [{"name": p, "type": "str", "required": True, "location": "path"} for p in path_params],
                        "response_model": None,
                        "deprecated": False,
                    })

        return routes

    def _extract_route_from_decorator(
        self, decorator: ast.AST, func_node: Any, rel_path: str
    ) -> Optional[Dict[str, Any]]:
        """Extracts route details from AST decorator node."""
        if not isinstance(decorator, ast.Call):
            return None

        func = decorator.func
        attr_name = ""
        obj_name = ""

        if isinstance(func, ast.Attribute):
            attr_name = func.attr
            if isinstance(func.value, ast.Name):
                obj_name = func.value.id
        else:
            return None

        # Check if router or app decorator
        valid_objs = {"app", "router", "bp", "api", "api_router", "blueprint"}
        if obj_name.lower() not in valid_objs and not any(v in obj_name.lower() for v in ["router", "api"]):
            return None

        http_methods = {"get", "post", "put", "delete", "patch", "options", "head", "route", "api_route"}
        if attr_name.lower() not in http_methods:
            return None

        path = ""
        methods = [attr_name.upper()]
        response_model = None
        deprecated = False

        if decorator.args and isinstance(decorator.args[0], ast.Constant) and isinstance(decorator.args[0].value, str):
            path = decorator.args[0].value

        for kw in decorator.keywords:
            if kw.arg == "methods" and isinstance(kw.value, (ast.List, ast.Tuple)):
                methods = [
                    elt.value.upper() for elt in kw.value.elts if isinstance(elt, ast.Constant) and isinstance(elt.value, str)
                ]
            elif kw.arg == "path" and isinstance(kw.value, ast.Constant) and isinstance(kw.value.value, str):
                path = kw.value.value
            elif kw.arg == "response_model":
                if isinstance(kw.value, ast.Name):
                    response_model = kw.value.id
                elif isinstance(kw.value, ast.Attribute):
                    response_model = kw.value.attr
            elif kw.arg == "deprecated" and isinstance(kw.value, ast.Constant):
                deprecated = bool(kw.value.value)

        if not path:
            return None

        # Inspect parameters in function definition
        params: List[Dict[str, Any]] = []
        path_param_names = set(re.findall(r"\{([a-zA-Z0-9_]+)\}", path))

        for arg in func_node.args.args:
            arg_name = arg.arg
            if arg_name in ["self", "cls", "request", "db", "session", "current_user"]:
                continue
            is_path = arg_name in path_param_names
            arg_type = "Any"
            if arg.annotation:
                arg_type = ast.unparse(arg.annotation) if hasattr(ast, "unparse") else "Any"

            params.append({
                "name": arg_name,
                "type": arg_type,
                "required": is_path,
                "location": "path" if is_path else "query_or_body",
            })

        for m in methods:
            return {
                "framework": "FastAPI/Flask",
                "method": m,
                "path": path,
                "file": rel_path,
                "line": getattr(func_node, "lineno", 1),
                "parameters": params,
                "response_model": response_model,
                "deprecated": deprecated,
            }

        return None

    def _parse_express_routes(self, file_path: str, rel_path: str) -> List[Dict[str, Any]]:
        """Extracts Express routes from JS/TS source files."""
        routes: List[Dict[str, Any]] = []
        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
        except Exception:
            return routes

        # Regex for router.get('/path', ...) or app.post('/path', ...)
        express_regex = re.compile(
            r"""(?:router|app)\.(get|post|put|delete|patch|options)\s*\(\s*["']([^"']+)["']""",
            re.IGNORECASE,
        )

        for idx, line in enumerate(content.splitlines(), start=1):
            for match in express_regex.finditer(line):
                method = match.group(1).upper()
                path = match.group(2)
                # Convert express :param to {param}
                params = [
                    {"name": p, "type": "string", "required": True, "location": "path"}
                    for p in re.findall(r":([a-zA-Z0-9_]+)", path)
                ]
                routes.append({
                    "framework": "Express",
                    "method": method,
                    "path": path,
                    "file": rel_path,
                    "line": idx,
                    "parameters": params,
                    "response_model": None,
                    "deprecated": False,
                })

        return routes

    def _parse_frontend_calls(self, file_path: str, rel_path: str) -> List[Dict[str, Any]]:
        """Discovers frontend API invocations from fetch, axios, and API client wrappers."""
        calls: List[Dict[str, Any]] = []
        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                lines = f.readlines()
        except Exception:
            return calls

        # Patterns for fetch and axios
        # axios.get('/api/users')
        axios_method_re = re.compile(
            r"""(?:axios|apiClient|api|http|client)\.(get|post|put|delete|patch)\s*\(\s*(?:`([^`]+)`|["']([^"']+)["'])""",
            re.IGNORECASE,
        )
        # fetch('/api/users', { method: 'POST' })
        fetch_re = re.compile(
            r"""fetch\s*\(\s*(?:`([^`]+)`|["']([^"']+)["'])""",
            re.IGNORECASE,
        )
        fetch_method_re = re.compile(r"""method:\s*["'](GET|POST|PUT|DELETE|PATCH)["']""", re.IGNORECASE)

        for idx, line in enumerate(lines, start=1):
            # Check axios style
            for match in axios_method_re.finditer(line):
                method = match.group(1).upper()
                template_path = match.group(2)
                literal_path = match.group(3)
                raw_path = template_path if template_path is not None else literal_path
                is_heuristic = template_path is not None and ("${" in template_path or "+" in line)

                if raw_path and (raw_path.startswith("/") or "/api" in raw_path or "http" in raw_path):
                    calls.append({
                        "method": method,
                        "raw_path": raw_path,
                        "normalized_path": self._normalize_endpoint_path(raw_path),
                        "file": rel_path,
                        "line": idx,
                        "is_heuristic": is_heuristic,
                    })

            # Check fetch style
            for match in fetch_re.finditer(line):
                template_path = match.group(1)
                literal_path = match.group(2)
                raw_path = template_path if template_path is not None else literal_path
                is_heuristic = template_path is not None and ("${" in template_path or "+" in line)

                # Look forward up to 3 lines for explicit method: 'POST'
                window = "".join(lines[idx - 1 : min(len(lines), idx + 3)])
                meth_match = fetch_method_re.search(window)
                method = meth_match.group(1).upper() if meth_match else "GET"

                if raw_path and (raw_path.startswith("/") or "/api" in raw_path or "http" in raw_path):
                    calls.append({
                        "method": method,
                        "raw_path": raw_path,
                        "normalized_path": self._normalize_endpoint_path(raw_path),
                        "file": rel_path,
                        "line": idx,
                        "is_heuristic": is_heuristic,
                    })

        return calls

    def _normalize_endpoint_path(self, path: str) -> str:
        """Normalizes API path by stripping host, query strings, and parameterizing template literals."""
        p = path.strip()
        # Remove origin if full url
        p = re.sub(r"^https?://[^/]+", "", p)
        # Strip query parameters
        p = p.split("?")[0]
        # Replace template interpolation ${...} with {param}
        p = re.sub(r"\$\{[^}]+\}", "{param}", p)
        # Replace express :param with {param}
        p = re.sub(r":([a-zA-Z0-9_]+)", "{param}", p)
        # Strip trailing slash if not root
        if len(p) > 1 and p.endswith("/"):
            p = p[:-1]
        return p

    def _paths_match(self, route_path: str, client_path: str) -> bool:
        """Determines if a backend route path matches a client requested path."""
        norm_r = self._normalize_endpoint_path(route_path)
        norm_c = self._normalize_endpoint_path(client_path)

        if norm_r == norm_c:
            return True

        # Check with or without /api prefix
        if norm_c.startswith("/api") and norm_r == norm_c[4:]:
            return True
        if norm_r.startswith("/api") and norm_c == norm_r[4:]:
            return True

        # Check token segment matching (e.g. /users/{user_id} vs /users/{param})
        r_tokens = [t for t in norm_r.split("/") if t]
        c_tokens = [t for t in norm_c.split("/") if t]

        if r_tokens and r_tokens[0] == "api" and (not c_tokens or c_tokens[0] != "api"):
            r_tokens = r_tokens[1:]
        elif c_tokens and c_tokens[0] == "api" and (not r_tokens or r_tokens[0] != "api"):
            c_tokens = c_tokens[1:]

        if len(r_tokens) != len(c_tokens):
            return False

        for rt, ct in zip(r_tokens, c_tokens):
            if rt.startswith("{") or ct.startswith("{"):
                continue
            if rt != ct:
                return False

        return True

    def _detect_breaking_changes(
        self, repo_dir: str, commit_sha: str, current_routes: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Identifies breaking API modifications from git diff or route deprecations."""
        breaking: List[Dict[str, Any]] = []

        # Check for deprecated routes flagged without alternative
        for route in current_routes:
            if route.get("deprecated"):
                breaking.append({
                    "rule_id": "API-DEPRECATED-ENDPOINT",
                    "severity": "Low",
                    "title": f"Deprecated API Endpoint: {route['method']} {route['path']}",
                    "description": f"Endpoint `{route['method']} {route['path']}` is marked as deprecated in {route['file']}:{route['line']}.",
                    "evidence": f"Route definition in {route['file']}:{route['line']}",
                    "file": route["file"],
                    "line": route["line"],
                    "remediation": "Provide migration documentation or API versioning before removing this endpoint.",
                })

        # Inspect git diff if available
        try:
            from app.analysis.impact import analyze_commit_changes
            changed_files = analyze_commit_changes(repo_dir, commit_sha)
            # Check for deleted route definitions in diff
            deleted_route_re = re.compile(r"""^-\s*@(?:router|app)\.(get|post|put|delete|patch)\s*\(\s*["']([^"']+)["']""", re.IGNORECASE)
            for change in changed_files:
                diff_text = change.get("patch", "") or ""
                for line in diff_text.splitlines():
                    match = deleted_route_re.search(line)
                    if match:
                        method = match.group(1).upper()
                        path = match.group(2)
                        breaking.append({
                            "rule_id": "API-BREAKING-ENDPOINT-REMOVAL",
                            "severity": "Critical",
                            "title": f"Breaking Change: Removed Route {method} {path}",
                            "description": f"Endpoint `{method} {path}` was deleted in revision {commit_sha[:8]} without backwards-compatible alias.",
                            "evidence": line.strip(),
                            "file": change["file"],
                            "line": None,
                            "remediation": "Maintain deprecated route redirect or issue API version increment.",
                        })
        except Exception:
            pass

        return breaking

    def _detect_consumer_mismatches(
        self, routes: List[Dict[str, Any]], frontend_calls: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Cross-references frontend API client requests against known backend endpoints."""
        mismatches: List[Dict[str, Any]] = []
        if not routes or not frontend_calls:
            return mismatches

        for call in frontend_calls:
            call_path = call["normalized_path"]
            call_method = call["method"]

            # Filter out external URLs (e.g. https://api.github.com)
            if call["raw_path"].startswith("http://") or call["raw_path"].startswith("https://"):
                if not any(local_host in call["raw_path"] for local_host in ["localhost", "127.0.0.1"]):
                    continue

            # Look for matching route
            matched_routes = [r for r in routes if self._paths_match(r["path"], call_path)]

            if not matched_routes:
                # Missing endpoint mismatch
                mismatches.append({
                    "rule_id": "API-MISSING-ENDPOINT",
                    "file": call["file"],
                    "line": call["line"],
                    "is_heuristic": call["is_heuristic"],
                    "title": f"Unmatched API Endpoint Call: {call_method} `{call['raw_path']}`",
                    "description": (
                        f"Frontend invokes `{call_method} {call['raw_path']}`, but no corresponding "
                        f"backend route path was discovered."
                    ),
                    "evidence": f"Call to '{call['raw_path']}' in {call['file']}:{call['line']}",
                    "remediation": f"Ensure backend route for `{call_path}` exists or adjust frontend endpoint URL.",
                })
            else:
                # Path matched, check method
                method_match = any(r["method"] == call_method for r in matched_routes)
                if not method_match:
                    allowed = ", ".join(sorted({r["method"] for r in matched_routes}))
                    mismatches.append({
                        "rule_id": "API-METHOD-MISMATCH",
                        "file": call["file"],
                        "line": call["line"],
                        "is_heuristic": call["is_heuristic"],
                        "title": f"HTTP Method Mismatch on `{call['raw_path']}`",
                        "description": (
                            f"Frontend invokes `{call_method} {call['raw_path']}`, but backend only accepts "
                            f"[{allowed}] on this route."
                        ),
                        "evidence": f"Backend supports [{allowed}]; frontend attempted {call_method}",
                        "remediation": f"Update frontend call in {call['file']} to use one of the supported methods: [{allowed}].",
                    })

        return mismatches
