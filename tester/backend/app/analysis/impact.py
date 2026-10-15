import subprocess
import re
import os
import json
from typing import Dict, List, Any

EMPTY_TREE_SHA = "4b825dc642cb6eb9a060e54bf8d69288fbee4904"

def run_git_command(repo_dir: str, command: List[str]) -> str:
    result = subprocess.run(command, cwd=repo_dir, capture_output=True, text=True)
    if result.returncode != 0:
        return ""
    return result.stdout

def get_commit_parent(repo_dir: str, current_sha: str) -> tuple[str, bool]:
    """Resolves first-parent for standard/merge commits, or flags root commit."""
    try:
        res = subprocess.run(
            ["git", "rev-parse", "--verify", f"{current_sha}^1"],
            cwd=repo_dir, capture_output=True, text=True
        )
        if res.returncode == 0 and res.stdout.strip():
            return res.stdout.strip(), False
    except Exception:
        pass
    return EMPTY_TREE_SHA, True

def analyze_commit_changes(repo_dir: str, current_sha: str) -> List[Dict[str, Any]]:
    """Analyzes exact file-level changes between commit and its parent."""
    parent_sha, is_root = get_commit_parent(repo_dir, current_sha)

    if is_root:
        status_out = run_git_command(repo_dir, ["git", "diff-tree", "--root", "--no-commit-id", "--name-status", "-M", "-r", current_sha])
    else:
        status_out = run_git_command(repo_dir, ["git", "diff-tree", "--no-commit-id", "--name-status", "-M", "-r", parent_sha, current_sha])

    numstat_out = run_git_command(repo_dir, ["git", "diff", "--numstat", "-M", parent_sha, current_sha])
    
    numstat: Dict[str, Dict[str, Any]] = {}
    for line in numstat_out.strip().split('\n'):
        if not line:
            continue
        parts = line.split('\t')
        if len(parts) == 3:
            add, sub, path = parts
            is_bin = (add == '-' and sub == '-')
            numstat[path] = {
                'add': 0 if is_bin else int(add) if add.isdigit() else 0,
                'sub': 0 if is_bin else int(sub) if sub.isdigit() else 0,
                'is_binary': is_bin
            }

    # Extract unified diff per file
    full_diff_out = run_git_command(repo_dir, ["git", "diff", "-U3", "-M", parent_sha, current_sha])
    diffs_by_file: Dict[str, Dict[str, Any]] = {}

    if full_diff_out:
        chunks = full_diff_out.split('\ndiff --git ')
        for i, chunk in enumerate(chunks):
            if i == 0 and not chunk.startswith('diff --git '):
                continue
            chunk_content = ('diff --git ' + chunk) if i > 0 else chunk
            lines = chunk_content.split('\n')
            if lines:
                m = re.match(r'^diff --git a/(.*?) b/(.*)$', lines[0])
                if m:
                    target_file = m.group(2)
                    is_bin = any("Binary files" in l for l in lines[:5])
                    is_trunc = False
                    if len(lines) > 1000:
                        chunk_content = '\n'.join(lines[:1000]) + '\n... [Diff truncated due to size limit]'
                        is_trunc = True
                    diffs_by_file[target_file] = {
                        "patch": chunk_content,
                        "is_binary": is_bin,
                        "is_truncated": is_trunc
                    }

    results = []
    for line in status_out.strip().split('\n'):
        if not line:
            continue
        parts = line.split('\t')
        raw_status = parts[0]
        path = parts[1]
        old_path = None
        if len(parts) >= 3 and raw_status.startswith('R'):
            old_path = parts[1]
            path = parts[2]

        stat_info = numstat.get(path, {})
        diff_info = diffs_by_file.get(path, {})

        is_binary = stat_info.get('is_binary', False) or diff_info.get('is_binary', False)
        adds = stat_info.get('add', 0)
        subs = stat_info.get('sub', 0)
        patch = diff_info.get('patch', "")
        is_truncated = diff_info.get('is_truncated', False)

        # Detect canonical status string
        if raw_status.startswith('A'):
            status = 'A'
        elif raw_status.startswith('M'):
            status = 'M'
        elif raw_status.startswith('D'):
            status = 'D'
        elif raw_status.startswith('R'):
            status = raw_status  # preserves R100
        else:
            status = raw_status

        lang = os.path.splitext(path)[1].lower()

        results.append({
            "file": path,
            "old_path": old_path,
            "status": status,
            "language": lang,
            "additions": adds,
            "deletions": subs,
            "is_binary": is_binary,
            "is_truncated": is_truncated,
            "patch": patch
        })

    return results

def analyze_structural_changes(repo_dir: str, current_sha: str) -> Dict[str, Any]:
    parent_sha, _ = get_commit_parent(repo_dir, current_sha)
    diff_out = run_git_command(repo_dir, ["git", "diff", parent_sha, current_sha])

    added = []
    removed = []
    pattern = re.compile(r'^([+-])\s*(?:class|def|function|async\s+function|const|let|var)\s+([a-zA-Z0-9_]+)')

    for line in diff_out.split('\n'):
        match = pattern.match(line)
        if match:
            sign = match.group(1)
            name = match.group(2)
            if sign == '+':
                added.append(name)
            else:
                removed.append(name)

    return {
        "added_structures": list(set(added))[:50],
        "removed_structures": list(set(removed))[:50]
    }

def build_dependency_graph(repo_dir: str) -> Dict[str, List[str]]:
    import_regex = re.compile(r'^\s*(?:import|from)\s+([a-zA-Z0-9_\.]+)|require\([\'"]([^\'"]+)[\'"]\)')
    graph = {}

    for root, _, files in os.walk(repo_dir):
        if any(d in root for d in ['.git', 'node_modules', 'venv', '.venv', 'dist', 'build']):
            continue

        for file in files:
            if not file.endswith(('.py', '.js', '.ts', '.tsx', '.jsx')):
                continue

            path = os.path.join(root, file)
            rel_path = os.path.relpath(path, repo_dir).replace('\\', '/')
            graph[rel_path] = []

            try:
                with open(path, 'r', encoding='utf-8', errors="ignore") as f:
                    for line in f:
                        match = import_regex.search(line)
                        if match:
                            mod = match.group(1) or match.group(2)
                            if mod and mod not in graph[rel_path]:
                                graph[rel_path].append(mod)
            except Exception:
                pass

    return graph

def analyze_impact(changed_files: List[str], dependency_graph: Dict[str, List[str]]) -> Dict[str, Any]:
    # Invert dependency graph
    imported_by: Dict[str, List[str]] = {}
    for source_file, imports in dependency_graph.items():
        for imp in imports:
            clean_imp = imp.replace('.', '/').split('/')[0]
            for candidate in dependency_graph.keys():
                if clean_imp and clean_imp in candidate:
                    imported_by.setdefault(candidate, []).append(source_file)

    impacted_files = set()
    reasons = {}

    for changed in changed_files:
        dependents = imported_by.get(changed, [])
        for dep in dependents:
            impacted_files.add(dep)
            reasons[dep] = f"Imports `{changed}` which was modified in this commit"

    return {
        "directly_changed_count": len(changed_files),
        "potentially_affected_files": [
            {"file": f, "reason": reasons.get(f, "Downstream dependency")}
            for f in sorted(list(impacted_files))[:25]
        ]
    }
