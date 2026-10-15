"""Benchmark Corpus Builder.
Constructs disposable local Git repositories with isolated fixtures and controlled commit histories.
"""
import os
import subprocess
from typing import List, Optional
from app.benchmark.fixtures import BENCHMARK_FIXTURES, BenchmarkFixture


def run_cmd(args: List[str], cwd: str) -> subprocess.CompletedProcess:
    return subprocess.run(args, cwd=cwd, capture_output=True, text=True, check=True)


def build_benchmark_repository(target_dir: str, fixtures: Optional[List[BenchmarkFixture]] = None) -> str:
    """Builds a complete benchmark repository on disk from fixture definitions."""
    os.makedirs(target_dir, exist_ok=True)
    fixture_list = fixtures or BENCHMARK_FIXTURES

    # Initialize git repo
    run_cmd(["git", "init"], cwd=target_dir)
    run_cmd(["git", "config", "user.email", "benchmark@gitflow.test"], cwd=target_dir)
    run_cmd(["git", "config", "user.name", "GitFlow Benchmark Bot"], cwd=target_dir)

    for fix in fixture_list:
        full_path = os.path.join(target_dir, fix.file_path)
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        with open(full_path, "w", encoding="utf-8") as f:
            f.write(fix.content)

    run_cmd(["git", "add", "-A"], cwd=target_dir)
    run_cmd(["git", "commit", "-m", "chore: initialize benchmark corpus"], cwd=target_dir)
    return target_dir


def build_controlled_multicommit_repository(target_dir: str) -> List[str]:
    """Creates a controlled 4-commit sequence for lineage and gate testing:
    A: Baseline clean repository
    B: Introduce vulnerability (SQL Injection)
    C: Resolve vulnerability (remediated to parameterized query)
    D: Harmless unrelated modification (documentation)
    Returns list of commit SHAs: [sha_a, sha_b, sha_c, sha_d]
    """
    os.makedirs(target_dir, exist_ok=True)
    run_cmd(["git", "init"], cwd=target_dir)
    run_cmd(["git", "config", "user.email", "benchmark@gitflow.test"], cwd=target_dir)
    run_cmd(["git", "config", "user.name", "GitFlow Benchmark Bot"], cwd=target_dir)

    # Commit A: Clean baseline
    with open(os.path.join(target_dir, "LICENSE"), "w", encoding="utf-8") as f_lic:
        f_lic.write("MIT License\n\nCopyright (c) 2026 Test Benchmark\n")

    app_file = os.path.join(target_dir, "app", "service.py")
    os.makedirs(os.path.dirname(app_file), exist_ok=True)
    with open(app_file, "w", encoding="utf-8") as f:
        f.write(
            "def get_user(cursor, user_id):\n"
            "    cursor.execute('SELECT * FROM users WHERE id = %s', (user_id,))\n"
            "    return cursor.fetchall()\n"
        )
    run_cmd(["git", "add", "-A"], cwd=target_dir)
    run_cmd(["git", "commit", "-m", "feat: baseline clean application"], cwd=target_dir)
    sha_a = run_cmd(["git", "rev-parse", "HEAD"], cwd=target_dir).stdout.strip()

    # Commit B: Introduce SQL injection
    with open(app_file, "w", encoding="utf-8") as f:
        f.write(
            "def get_user(cursor, user_id):\n"
            "    cursor.execute('SELECT * FROM users WHERE id = ' + user_id)\n"
            "    return cursor.fetchall()\n"
        )
    run_cmd(["git", "add", "-A"], cwd=target_dir)
    run_cmd(["git", "commit", "-m", "fix: introduce dynamic string query"], cwd=target_dir)
    sha_b = run_cmd(["git", "rev-parse", "HEAD"], cwd=target_dir).stdout.strip()

    # Commit C: Remediate the SQL injection
    with open(app_file, "w", encoding="utf-8") as f:
        f.write(
            "def get_user(cursor, user_id):\n"
            "    cursor.execute('SELECT * FROM users WHERE id = %s', (user_id,))\n"
            "    return cursor.fetchall()\n"
        )
    run_cmd(["git", "add", "-A"], cwd=target_dir)
    run_cmd(["git", "commit", "-m", "fix: remediate sql injection using parameter binding"], cwd=target_dir)
    sha_c = run_cmd(["git", "rev-parse", "HEAD"], cwd=target_dir).stdout.strip()

    # Commit D: Harmless documentation update
    readme_file = os.path.join(target_dir, "README.md")
    with open(readme_file, "w", encoding="utf-8") as f:
        f.write("# Controlled Benchmark Repository\nDocumentation update only.\n")
    run_cmd(["git", "add", "-A"], cwd=target_dir)
    run_cmd(["git", "commit", "-m", "docs: update readme"], cwd=target_dir)
    sha_d = run_cmd(["git", "rev-parse", "HEAD"], cwd=target_dir).stdout.strip()

    return [sha_a, sha_b, sha_c, sha_d]
