import os
import re
import json
import time
import subprocess
import urllib.request
import urllib.error
from typing import List, Tuple, Dict, Any
from app.scanners.models import FindingItem, ToolCoverage, is_test_or_benchmark_path

def extract_python_packages(file_path: str) -> List[Dict[str, str]]:
    packages = []
    try:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                line = line.strip().split("#")[0].strip()
                if not line or line.startswith("-"):
                    continue
                # Match pinned versions like package==1.2.3
                m = re.match(r"^([a-zA-Z0-9_\-\.]+)\s*==\s*([a-zA-Z0-9_\-\.]+)", line)
                if m:
                    packages.append({"name": m.group(1), "version": m.group(2), "ecosystem": "PyPI"})
    except Exception:
        pass
    return packages

def extract_npm_packages(file_path: str) -> List[Dict[str, str]]:
    packages = []
    try:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            data = json.load(f)
            # Check package-lock.json v2/v3 packages
            if "packages" in data and isinstance(data["packages"], dict):
                for pkg_path, pkg_info in data["packages"].items():
                    name = pkg_info.get("name")
                    if not name:
                        clean_pkg = pkg_path.replace("\\", "/")
                        if "node_modules/" in clean_pkg:
                            clean_pkg = clean_pkg.split("node_modules/")[-1]
                        name = clean_pkg
                    version = pkg_info.get("version")
                    if name and version and not any(p["name"] == name and p["version"] == version for p in packages):
                        packages.append({"name": name, "version": version, "ecosystem": "npm"})
            # Check dependencies in package.json or package-lock v1
            deps = data.get("dependencies", {})
            if isinstance(deps, dict):
                for name, ver_val in deps.items():
                    if isinstance(ver_val, str):
                        clean_ver = re.sub(r"^[\^~>=<]", "", ver_val)
                        packages.append({"name": name, "version": clean_ver, "ecosystem": "npm"})
                    elif isinstance(ver_val, dict) and "version" in ver_val:
                        packages.append({"name": name, "version": ver_val["version"], "ecosystem": "npm"})
    except Exception:
        pass
    return packages

def query_osv_batch(queries: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    if not queries:
        return []
    url = "https://api.osv.dev/v1/querybatch"
    payload = json.dumps({"queries": queries[:100]}).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=payload,
        headers={"Content-Type": "application/json", "User-Agent": "GitFlow-Scanner/1.0"}
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return data.get("results", [])
    except Exception:
        return []

def run_dependency_scan(repo_path: str, fingerprint_generator) -> Tuple[List[FindingItem], ToolCoverage]:
    start_time = time.time()
    findings: List[FindingItem] = []
    manifests_found = 0
    tool_name = "OSV Dependency Vulnerability Scanner"

    # 1. Try native osv-scanner CLI first if installed
    osv_cli_available = False
    try:
        check = subprocess.run(["osv-scanner", "--version"], capture_output=True, text=True, timeout=5)
        if check.returncode == 0:
            osv_cli_available = True
            tool_name = f"OSV-Scanner {check.stdout.strip()}"
    except Exception:
        osv_cli_available = False

    if osv_cli_available:
        try:
            res = subprocess.run(
                ["osv-scanner", "-r", "--json", repo_path],
                capture_output=True,
                text=True,
                timeout=60
            )
            # osv-scanner exits with code 1 or 2 when vulnerabilities are found; parse stdout!
            if res.stdout:
                data = json.loads(res.stdout)
                results = data.get("results", [])
                for item in results:
                    source_path = item.get("source", {}).get("path", "")
                    rel_source = os.path.relpath(source_path, repo_path).replace("\\", "/") if source_path else "Manifest"
                    manifests_found += 1
                    for pkg in item.get("packages", []):
                        pkg_info = pkg.get("package", {})
                        pkg_name = pkg_info.get("name", "Unknown")
                        pkg_version = pkg_info.get("version", "")
                        for vuln in pkg.get("vulnerabilities", []):
                            vuln_id = vuln.get("id", "VULN-UNKNOWN")
                            summary = vuln.get("summary") or f"Vulnerability {vuln_id} in {pkg_name}"
                            fixed = "latest safe version"
                            for affected in vuln.get("affected", []):
                                for r in affected.get("ranges", []):
                                    for event in r.get("events", []):
                                        if "fixed" in event:
                                            fixed = event["fixed"]
                                            break

                            fp = fingerprint_generator(
                                "Dependency", rel_source, "Manifest",
                                vuln_id, f"{pkg_name}@{pkg_version}"
                            )
                            is_fixture_manifest = is_test_or_benchmark_path(rel_source)
                            classification = (
                                "Intentional test fixture or demonstration example"
                                if is_fixture_manifest
                                else "Confirmed vulnerability or exposure"
                            )
                            title = f"Vulnerable Dependency: {pkg_name} ({vuln_id})"
                            if is_fixture_manifest:
                                title += " (Sample / Test Fixture)"

                            findings.append(FindingItem(
                                fingerprint=fp,
                                rule_id=f"DEP-{vuln_id}",
                                title=title,
                                category="Dependency",
                                severity="High",
                                confidence="High",
                                file_path=rel_source,
                                line_number=None,
                                message=f"Package `{pkg_name}` (installed: `{pkg_version}`) is affected by {vuln_id}: {summary}",
                                code_snippet=f"{pkg_name}=={pkg_version}",
                                evidence=f"Advisory {vuln_id} reports vulnerabilities in version {pkg_version}.",
                                impact="Known security advisories in dependencies can be exploited to compromise the application.",
                                remediation=f"Upgrade `{pkg_name}` to version `{fixed}` or newer.",
                                references=[f"https://osv.dev/vulnerability/{vuln_id}"],
                                classification=classification
                            ))
                coverage = ToolCoverage(
                    tool_name=tool_name,
                    category="dependencies",
                    status="COMPLETED",
                    duration_seconds=time.time() - start_time,
                    files_scanned=manifests_found,
                    findings_count=len(findings)
                )
                return findings, coverage
        except Exception:
            pass

    # 2. Authoritative OSV API Fallback
    packages_to_query: List[Tuple[Dict[str, str], str]] = []
    manifest_files: List[str] = []

    for root, dirs, files in os.walk(repo_path):
        dirs[:] = [d for d in dirs if d not in {".git", "node_modules", "venv", ".venv", "dist", "build"}]
        for f in files:
            full_path = os.path.join(root, f)
            rel_path = os.path.relpath(full_path, repo_path).replace("\\", "/")
            if f in {"requirements.txt", "Pipfile.lock"}:
                manifest_files.append(rel_path)
                pkgs = extract_python_packages(full_path)
                for p in pkgs:
                    packages_to_query.append((p, rel_path))
            elif f in {"package.json", "package-lock.json"}:
                manifest_files.append(rel_path)
                pkgs = extract_npm_packages(full_path)
                for p in pkgs:
                    packages_to_query.append((p, rel_path))

    manifests_found = len(manifest_files)

    if not packages_to_query:
        # No dependency manifests present in the repository
        coverage = ToolCoverage(
            tool_name="OSV API Scanner",
            category="dependencies",
            status="COMPLETED",
            duration_seconds=time.time() - start_time,
            files_scanned=manifests_found,
            findings_count=0
        )
        return findings, coverage

    # Batch query OSV
    osv_queries = [
        {"package": {"name": p["name"], "ecosystem": p["ecosystem"]}, "version": p["version"]}
        for p, _ in packages_to_query
    ]

    api_results = query_osv_batch(osv_queries)

    if not api_results and packages_to_query:
        # Network unavailable or OSV offline
        coverage = ToolCoverage(
            tool_name="OSV API Scanner",
            category="dependencies",
            status="PARTIAL",
            duration_seconds=time.time() - start_time,
            files_scanned=manifests_found,
            findings_count=0,
            error_message="OSV vulnerability service was unavailable; manifests detected but advisory queries could not complete."
        )
        return findings, coverage

    for idx, res in enumerate(api_results):
        vulns = res.get("vulns", [])
        if not vulns:
            continue
        pkg_data, manifest_rel = packages_to_query[idx]
        pkg_name = pkg_data["name"]
        pkg_ver = pkg_data["version"]

        for vuln in vulns:
            vuln_id = vuln.get("id", "VULN-UNKNOWN")
            summary = vuln.get("summary") or f"Vulnerability in {pkg_name}"
            fixed_version = "latest patch"
            for aff in vuln.get("affected", []):
                for r in aff.get("ranges", []):
                    for event in r.get("events", []):
                        if "fixed" in event:
                            fixed_version = event["fixed"]
                            break

            fp = fingerprint_generator(
                "Dependency", manifest_rel, "Manifest",
                vuln_id, f"{pkg_name}@{pkg_ver}"
            )

            is_fixture_manifest = is_test_or_benchmark_path(manifest_rel)
            classification = (
                "Intentional test fixture or demonstration example"
                if is_fixture_manifest
                else "Confirmed vulnerability or exposure"
            )
            title = f"Vulnerable Dependency: {pkg_name} ({vuln_id})"
            if is_fixture_manifest:
                title += " (Sample / Test Fixture)"

            if not any(fi.fingerprint == fp for fi in findings):
                findings.append(FindingItem(
                    fingerprint=fp,
                    rule_id=f"DEP-{vuln_id}",
                    title=title,
                    category="Dependency",
                    severity="High",
                    confidence="High",
                    file_path=manifest_rel,
                    line_number=None,
                    message=f"Package `{pkg_name}` (version `{pkg_ver}`) is affected by {vuln_id}: {summary}",
                    code_snippet=f"{pkg_name}=={pkg_ver}",
                    evidence=f"Authoritative OSV advisory {vuln_id} flags version {pkg_ver}.",
                    impact="Security vulnerability in third-party dependency may compromise application integrity or availability.",
                    remediation=f"Upgrade `{pkg_name}` to version `{fixed_version}` or higher.",
                    references=[f"https://osv.dev/vulnerability/{vuln_id}"],
                    classification=classification
                ))

    coverage = ToolCoverage(
        tool_name="OSV API Scanner",
        category="dependencies",
        status="COMPLETED",
        duration_seconds=time.time() - start_time,
        files_scanned=manifests_found,
        findings_count=len(findings)
    )
    return findings, coverage
