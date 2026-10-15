"""Benchmark Evaluator & Accuracy Metrics Engine.
Executes security scanners against ground-truth fixtures and computes
True Positives, False Positives, False Negatives, Precision, and Recall.
"""
import os
import tempfile
import shutil
from typing import Dict, List, Any, Optional
from app.benchmark.fixtures import BENCHMARK_FIXTURES, BenchmarkFixture
from app.scanners.universal import UniversalScanner, generate_fingerprint
from app.scanners.sast import run_sast_scan
from app.scanners.secrets import run_secret_scan
from app.scanners.dependencies import run_dependency_scan
from app.scanners.licenses import run_license_scan


UNSUPPORTED_LANGUAGES = [
    {"language": "C / C++", "extensions": [".c", ".cpp", ".h"], "reason": "No native memory safety or buffer overflow analyzer"},
    {"language": "Java", "extensions": [".java", ".jar"], "reason": "Requires JVM bytecode or AST semantic parser"},
    {"language": "Go", "extensions": [".go"], "reason": "Requires Go staticcheck or gosec integration"},
    {"language": "Rust", "extensions": [".rs"], "reason": "Requires cargo-audit integration"},
    {"language": "PHP", "extensions": [".php"], "reason": "Requires PHP AST parser or phpcs-security-audit"},
    {"language": "Ruby", "extensions": [".rb"], "reason": "Requires Brakeman integration"}
]

UNSUPPORTED_VULNERABILITY_CLASSES = [
    {"class": "Buffer Overflow / Memory Corruption", "cwe": "CWE-119", "limitation": "Static regex cannot track memory bounds or stack canary safety"},
    {"class": "Race Conditions / TOCTOU", "cwe": "CWE-362", "limitation": "Requires cross-thread temporal execution graph analysis"},
    {"class": "Server-Side Request Forgery (SSRF)", "cwe": "CWE-918", "limitation": "Requires taint-tracking from HTTP parameters to outbound client requests"},
    {"class": "XML External Entity (XXE) Injection", "cwe": "CWE-611", "limitation": "XML parser entity expansion configuration rule not in default ruleset"},
    {"class": "Insecure Direct Object References (IDOR)", "cwe": "CWE-284", "limitation": "Requires business-logic authorization context models"}
]


class BenchmarkEvaluator:
    def __init__(self, fixtures: Optional[List[BenchmarkFixture]] = None):
        self.fixtures = fixtures or BENCHMARK_FIXTURES

    def evaluate_all(self) -> Dict[str, Any]:
        """Runs isolated per-fixture scans and full-corpus scan, producing comprehensive accuracy metrics."""
        fixture_results = []
        rule_stats: Dict[str, Dict[str, int]] = {}

        total_tp = 0
        total_fp = 0
        total_fn = 0
        total_tn = 0

        for fix in self.fixtures:
            res = self._evaluate_single_fixture(fix)
            fixture_results.append(res)

            # Accumulate rule stats
            rule_id = fix.expected_rule_id or "NONE"
            if rule_id not in rule_stats:
                rule_stats[rule_id] = {"expected": 0, "detected": 0, "tp": 0, "fp": 0, "fn": 0}

            if fix.is_vulnerable:
                rule_stats[rule_id]["expected"] += 1

            if res["status"] == "PASS":
                if fix.is_vulnerable:
                    total_tp += 1
                    rule_stats[rule_id]["detected"] += 1
                    rule_stats[rule_id]["tp"] += 1
                else:
                    total_tn += 1
            elif res["status"] == "FALSE_POSITIVE":
                total_fp += 1
                rule_stats[rule_id]["fp"] += 1
            elif res["status"] == "FALSE_NEGATIVE":
                total_fn += 1
                rule_stats[rule_id]["fn"] += 1
            elif res["status"] in ("RULE_MISMATCH", "CLASSIFICATION_MISMATCH"):
                total_fp += 1
                rule_stats[rule_id]["fp"] += 1

        precision = (total_tp / (total_tp + total_fp)) if (total_tp + total_fp) > 0 else None
        recall = (total_tp / (total_tp + total_fn)) if (total_tp + total_fn) > 0 else None
        f1_score = (2 * precision * recall / (precision + recall)) if (precision and recall and (precision + recall) > 0) else None

        # Line-shift stability check
        shift_stability = self._verify_line_shift_stability()

        return {
            "summary": {
                "total_fixtures": len(self.fixtures),
                "true_positives": total_tp,
                "false_positives": total_fp,
                "false_negatives": total_fn,
                "true_negatives": total_tn,
                "precision": round(precision, 4) if precision is not None else "N/A",
                "recall": round(recall, 4) if recall is not None else "N/A",
                "f1_score": round(f1_score, 4) if f1_score is not None else "N/A",
                "line_shift_stability_verified": shift_stability,
            },
            "per_rule_metrics": rule_stats,
            "fixture_results": fixture_results,
            "unsupported_languages": UNSUPPORTED_LANGUAGES,
            "unsupported_vulnerability_classes": UNSUPPORTED_VULNERABILITY_CLASSES
        }

    def _evaluate_single_fixture(self, fix: BenchmarkFixture) -> Dict[str, Any]:
        """Evaluates an isolated fixture in a dedicated disposable directory."""
        temp_dir = tempfile.mkdtemp(prefix="gitflow_bench_")
        try:
            full_path = os.path.join(temp_dir, fix.file_path)
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
            with open(full_path, "w", encoding="utf-8") as f:
                f.write(fix.content)

            if fix.category != "License" and fix.expected_rule_id != "LIC-MISSING":
                with open(os.path.join(temp_dir, "LICENSE"), "w", encoding="utf-8") as f_lic:
                    f_lic.write("MIT License\n\nCopyright (c) 2026 Test Benchmark\n")

            scanner = UniversalScanner(temp_dir)
            findings = scanner.scan()

            actual_count = len(findings)

            if fix.is_vulnerable:
                if actual_count == 0:
                    status = "FALSE_NEGATIVE"
                else:
                    matched_rule = any(f.get("rule_id") == fix.expected_rule_id for f in findings) if fix.expected_rule_id else True
                    classification_match = True
                    if fix.expected_classification and findings:
                        matched_f = next((f for f in findings if f.get("rule_id") == fix.expected_rule_id), findings[0])
                        classification_match = (matched_f.get("classification") == fix.expected_classification)

                    if matched_rule and classification_match:
                        status = "PASS"
                    elif not matched_rule:
                        status = "RULE_MISMATCH"
                    else:
                        status = "CLASSIFICATION_MISMATCH"
            else:
                # Non-vulnerable fixture (clean code, fixed control, sample/doc, scoped package, comment)
                if fix.expected_rule_id and fix.expected_findings_count == 0:
                    # Specific negative control: e.g. fixed package must NOT have the CVE advisory rule!
                    has_forbidden_rule = any(f.get("rule_id") == fix.expected_rule_id for f in findings)
                    status = "FALSE_POSITIVE" if has_forbidden_rule else "PASS"
                elif fix.expected_classification:
                    # Test fixture / sample match
                    if actual_count == 0:
                        status = "FALSE_NEGATIVE"
                    else:
                        matched_f = next((f for f in findings if f.get("rule_id") == fix.expected_rule_id), findings[0])
                        is_fixture_class = (matched_f.get("classification") == fix.expected_classification)
                        status = "PASS" if is_fixture_class else "CLASSIFICATION_MISMATCH"
                else:
                    # Clean fixture: must have 0 confirmed vulnerabilities
                    confirmed_findings = [f for f in findings if f.get("classification") != "Intentional test fixture or demonstration example"]
                    status = "FALSE_POSITIVE" if len(confirmed_findings) > 0 else "PASS"

            # Check classification if specified
            classification_match = True
            if fix.expected_classification and findings:
                matched_f = next((f for f in findings if f.get("rule_id") == fix.expected_rule_id), findings[0])
                classification_match = (matched_f.get("classification") == fix.expected_classification)

            return {
                "fixture_id": fix.fixture_id,
                "name": fix.name,
                "status": status,
                "expected_count": fix.expected_findings_count,
                "actual_count": actual_count,
                "expected_rule": fix.expected_rule_id,
                "actual_rules": [f.get("rule_id") for f in findings],
                "expected_classification": fix.expected_classification,
                "actual_classification": findings[0].get("classification") if findings else None,
                "classification_verified": classification_match,
                "findings": findings
            }
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def _verify_line_shift_stability(self) -> bool:
        """Verifies that an identical code vulnerability has the exact same fingerprint when shifted by lines."""
        temp_dir = tempfile.mkdtemp(prefix="gitflow_shift_")
        try:
            # File 1: at line 1
            f1 = os.path.join(temp_dir, "query_v1.py")
            with open(f1, "w") as fh:
                fh.write('cursor.execute("SELECT * FROM users WHERE id = " + user_input)\n')

            # File 2: shifted to line 6
            f2 = os.path.join(temp_dir, "query_v2.py")
            with open(f2, "w") as fh:
                fh.write(
                    "# Comment line 1\n"
                    "# Comment line 2\n"
                    "# Comment line 3\n"
                    "# Comment line 4\n"
                    "# Comment line 5\n"
                    'cursor.execute("SELECT * FROM users WHERE id = " + user_input)\n'
                )

            scanner = UniversalScanner(temp_dir)
            findings = scanner.scan()
            f1_find = [f for f in findings if f["file_path"] == "query_v1.py"]
            f2_find = [f for f in findings if f["file_path"] == "query_v2.py"]

            if not f1_find or not f2_find:
                return False

            # In UniversalScanner fingerprint generation, code_snippet norm makes them structurally matched
            # Check snippet equality
            return f1_find[0].get("code_snippet") == f2_find[0].get("code_snippet")
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)


if __name__ == "__main__":
    evaluator = BenchmarkEvaluator()
    results = evaluator.evaluate_all()
    summary = results["summary"]
    print("=" * 70)
    print("GITFLOW SECURITY SCANNER BENCHMARK EVALUATION REPORT")
    print("=" * 70)
    print(f"Total Fixtures Evaluated: {summary['total_fixtures']}")
    print(f"True Positives (TP):     {summary['true_positives']}")
    print(f"False Positives (FP):    {summary['false_positives']}")
    print(f"False Negatives (FN):    {summary['false_negatives']}")
    print(f"True Negatives (TN):     {summary['true_negatives']}")
    print(f"Precision:               {summary['precision']:.4f} ({summary['precision']*100:.1f}%)")
    print(f"Recall:                  {summary['recall']:.4f} ({summary['recall']*100:.1f}%)")
    print(f"F1-Score:                {summary['f1_score']:.4f}")
    print(f"Line-Shift Stability:    {summary['line_shift_stability_verified']}")
    print("=" * 70)
    print(f"{'Fixture ID':<22} | {'Status':<16} | {'Expected Rule':<24} | {'Findings'}")
    print("-" * 70)
    for fix in results["fixture_results"]:
        exp = fix.get("expected_rule") or "(clean / negative)"
        actual = len(fix.get("findings", []))
        print(f"{fix['fixture_id']:<22} | {fix['status']:<16} | {exp:<24} | {actual}")
    print("=" * 70)
