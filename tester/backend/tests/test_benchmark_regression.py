import os
import shutil
import tempfile
import unittest
from app.benchmark.fixtures import BENCHMARK_FIXTURES
from app.benchmark.evaluator import BenchmarkEvaluator
from app.benchmark.corpus import build_controlled_multicommit_repository
from app.scanners.universal import UniversalScanner, generate_fingerprint
from app.scoring.engine import calculate_risk_score


class BenchmarkRegressionTests(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp(prefix="gitflow_bench_test_")

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_benchmark_full_accuracy_and_zero_false_rates(self):
        """Validates that all ground-truth fixtures pass with 0 false positives and 0 false negatives."""
        evaluator = BenchmarkEvaluator()
        report = evaluator.evaluate_all()
        summary = report["summary"]

        self.assertEqual(summary["false_positives"], 0, f"False positives detected: {report['fixture_results']}")
        self.assertEqual(summary["false_negatives"], 0, f"False negatives detected: {report['fixture_results']}")
        self.assertEqual(summary["precision"], 1.0)
        self.assertEqual(summary["recall"], 1.0)
        self.assertTrue(summary["line_shift_stability_verified"])

        # Check unsupported language reporting
        self.assertGreaterEqual(len(report["unsupported_languages"]), 4)
        self.assertGreaterEqual(len(report["unsupported_vulnerability_classes"]), 4)

    def test_controlled_multicommit_lineage(self):
        """Verifies A -> B -> C -> D controlled multi-commit repository lifecycle.
        A: Clean baseline
        B: Introduce SQL injection (NEW)
        C: Remediate SQL injection (RESOLVED)
        D: Unrelated modification (stays RESOLVED)
        """
        shas = build_controlled_multicommit_repository(self.test_dir)
        self.assertEqual(len(shas), 4)

        # Scan A: Baseline clean
        # Checkout commit A
        import subprocess
        subprocess.run(["git", "checkout", shas[0]], cwd=self.test_dir, check=True, capture_output=True)
        scanner_a = UniversalScanner(self.test_dir)
        findings_a = scanner_a.scan()
        self.assertEqual(len(findings_a), 0, "Commit A should have 0 findings")

        # Scan B: Introduce SQL injection
        subprocess.run(["git", "checkout", shas[1]], cwd=self.test_dir, check=True, capture_output=True)
        scanner_b = UniversalScanner(self.test_dir)
        findings_b = scanner_b.scan()
        self.assertEqual(len(findings_b), 1, "Commit B should detect the introduced SQL injection")
        self.assertEqual(findings_b[0]["rule_id"], "SEC-SQLI-001")
        self.assertEqual(findings_b[0]["classification"], "Confirmed vulnerability or exposure")
        fp_b = findings_b[0]["fingerprint"]

        # Scan C: Remediate SQL injection
        subprocess.run(["git", "checkout", shas[2]], cwd=self.test_dir, check=True, capture_output=True)
        scanner_c = UniversalScanner(self.test_dir)
        findings_c = scanner_c.scan()
        self.assertEqual(len(findings_c), 0, "Commit C should have 0 findings")

        # Verify resolution comparison: fp_b in B is not in C
        current_fps = {f["fingerprint"] for f in findings_c}
        self.assertNotIn(fp_b, current_fps, "Remediated issue should no longer be present in C")

        # Scan D: Harmless modification
        subprocess.run(["git", "checkout", shas[3]], cwd=self.test_dir, check=True, capture_output=True)
        scanner_d = UniversalScanner(self.test_dir)
        findings_d = scanner_d.scan()
        self.assertEqual(len(findings_d), 0, "Commit D should have 0 findings")

    def test_test_fixture_classification_vs_runtime_code(self):
        """Verifies that vulnerable code inside test string literals yields 0 score deduction
        while executable runtime code deducts score."""
        fixture_finding = {
            "category": "Vulnerability",
            "severity": "High",
            "message": "Potential SQL Injection in test_mock.py",
            "classification": "Intentional test fixture or demonstration example",
            "fingerprint": "fp_fixture"
        }
        res_fixture = calculate_risk_score([fixture_finding], "COMPLETED")
        self.assertEqual(res_fixture["final_score"], 100)
        self.assertEqual(res_fixture["deductions"][0]["points"], 0)

        runtime_finding = {
            "category": "Vulnerability",
            "severity": "High",
            "message": "Potential SQL Injection in app/db.py",
            "classification": "Confirmed vulnerability or exposure",
            "fingerprint": "fp_runtime"
        }
        res_runtime = calculate_risk_score([runtime_finding], "COMPLETED")
        self.assertLess(res_runtime["final_score"], 100)
        self.assertLess(res_runtime["deductions"][0]["points"], 0)


if __name__ == "__main__":
    unittest.main()
