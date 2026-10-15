import os
import shutil
import subprocess
import tempfile
import unittest

from app.analysis.impact import analyze_commit_changes, analyze_structural_changes, build_dependency_graph, analyze_impact
from app.scanners.models import FindingItem, ScanCoverage
from app.scanners.sast import run_sast_scan, SAST_RULES
from app.scanners.secrets import run_secret_scan, redact_secret
from app.scanners.dependencies import extract_python_packages, extract_npm_packages, run_dependency_scan
from app.scanners.universal import UniversalScanner, generate_fingerprint
from app.scoring.engine import calculate_risk_score
from app.workers.scan_job import calculate_score_delta


class CommitIntelligenceTests(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp(prefix="gitflow_test_")

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def _init_git_repo(self):
        subprocess.run(["git", "init"], cwd=self.test_dir, check=True, capture_output=True)
        subprocess.run(["git", "config", "user.name", "Test Runner"], cwd=self.test_dir, check=True)
        subprocess.run(["git", "config", "user.email", "runner@example.test"], cwd=self.test_dir, check=True)

    def test_impact_root_commit_and_renames(self):
        self._init_git_repo()
        file_a = os.path.join(self.test_dir, "initial.txt")
        with open(file_a, "w") as f:
            f.write("Line 1\nLine 2\n")

        subprocess.run(["git", "add", "initial.txt"], cwd=self.test_dir, check=True)
        subprocess.run(["git", "commit", "-m", "Root commit"], cwd=self.test_dir, check=True)
        root_sha = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=self.test_dir, text=True).strip()

        # 1. Root commit analysis
        root_changes = analyze_commit_changes(self.test_dir, root_sha)
        self.assertEqual(len(root_changes), 1)
        self.assertEqual(root_changes[0]["file"], "initial.txt")
        self.assertEqual(root_changes[0]["status"], "A")
        self.assertEqual(root_changes[0]["additions"], 2)
        self.assertEqual(root_changes[0]["deletions"], 0)

        # 2. Rename commit analysis
        subprocess.run(["git", "mv", "initial.txt", "renamed.txt"], cwd=self.test_dir, check=True)
        subprocess.run(["git", "commit", "-m", "Rename initial to renamed"], cwd=self.test_dir, check=True)
        rename_sha = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=self.test_dir, text=True).strip()

        rename_changes = analyze_commit_changes(self.test_dir, rename_sha)
        self.assertEqual(len(rename_changes), 1)
        self.assertTrue(rename_changes[0]["status"].startswith("R"))
        self.assertEqual(rename_changes[0]["file"], "renamed.txt")
        self.assertEqual(rename_changes[0]["old_path"], "initial.txt")

    def test_sast_scanner_rules(self):
        py_vuln_file = os.path.join(self.test_dir, "vuln_sample.py")
        with open(py_vuln_file, "w") as f:
            f.write(
                "import os\n"
                "import hashlib\n"
                "import pickle\n"
                "\n"
                "def bad_sql(user_input):\n"
                "    query = cursor.execute('SELECT * FROM users WHERE id = ' + user_input)\n"
                "    return query\n"
                "\n"
                "def bad_cmd(ip):\n"
                "    os.system('ping ' + ip)\n"
                "\n"
                "def weak_hash(data):\n"
                "    return hashlib.md5(data).hexdigest()\n"
                "\n"
                "def bad_pickle(blob):\n"
                "    return pickle.loads(blob)\n"
            )

        findings, coverage = run_sast_scan(self.test_dir, generate_fingerprint)

        self.assertGreaterEqual(len(findings), 3)
        rules_found = {f.rule_id for f in findings}
        self.assertIn("SEC-SQLI-001", rules_found)
        self.assertIn("SEC-CMDI-001", rules_found)
        self.assertIn("SEC-CRYP-001", rules_found)
        self.assertEqual(coverage.status, "COMPLETED")

    def test_secret_scanner_and_redaction(self):
        # Test redaction utility
        raw_key = "AKIAIOSFODNN7EXAMPLE"
        redacted = redact_secret(raw_key)
        self.assertNotIn("FODNN7", redacted)
        self.assertTrue(redacted.startswith("AKIA*"))

        # Test secret file detection
        secret_file = os.path.join(self.test_dir, "config_secrets.py")
        with open(secret_file, "w") as f:
            f.write('AWS_KEY = "AKIAIOSFODNN7EXAMPLE"\n')

        findings, coverage = run_secret_scan(self.test_dir, generate_fingerprint)
        self.assertGreaterEqual(len(findings), 1)
        self.assertEqual(findings[0].category, "Secret")
        self.assertEqual(findings[0].severity, "Critical")
        self.assertNotIn("AKIAIOSFODNN7EXAMPLE", findings[0].message)

    def test_dependency_scanner_manifest_parsing(self):
        req_file = os.path.join(self.test_dir, "requirements.txt")
        with open(req_file, "w") as f:
            f.write("requests==2.20.0\nflask==1.0.2\n")

        dep_items = extract_python_packages(req_file)
        self.assertEqual(len(dep_items), 2)
        pkg_names = {d["name"] for d in dep_items}
        self.assertIn("requests", pkg_names)
        self.assertIn("flask", pkg_names)

        package_json = os.path.join(self.test_dir, "package.json")
        with open(package_json, "w") as f:
            f.write('{"dependencies": {"lodash": "4.17.15", "express": "4.16.0"}}\n')

        node_items = extract_npm_packages(package_json)
        self.assertEqual(len(node_items), 2)
        node_names = {d["name"] for d in node_items}
        self.assertIn("lodash", node_names)
        self.assertIn("express", node_names)

    def test_defensible_scoring_engine(self):
        findings = [
            {"category": "Secret", "severity": "Critical", "fingerprint": "sec1", "message": "AWS Key leaked"},
            {"category": "Vulnerability", "severity": "High", "fingerprint": "vuln1", "message": "SQL Injection"},
            {"category": "DependencyScan", "severity": "Medium", "fingerprint": "dep1", "message": "Outdated lib"},
        ]

        result = calculate_risk_score(findings)
        self.assertLess(result["final_score"], 100)
        self.assertGreaterEqual(result["final_score"], 0)
        
        # Verify category scores separation
        cat_scores = result.get("category_scores", {})
        self.assertIn("secrets", cat_scores)
        self.assertIn("security", cat_scores)
        self.assertIn("dependencies", cat_scores)
        self.assertLess(cat_scores["secrets"], 100)
        self.assertLess(cat_scores["security"], 100)
        self.assertEqual(cat_scores["licenses"], 100)

        # Delta calculation
        delta = calculate_score_delta(85, 95)
        self.assertEqual(delta, -10)
        baseline_delta = calculate_score_delta(85, None)
        self.assertIsNone(baseline_delta)

    def test_universal_scanner_coverage_diagnostics(self):
        test_py = os.path.join(self.test_dir, "main.py")
        with open(test_py, "w") as f:
            f.write("print('clean hello world')\n")

        universal = UniversalScanner(self.test_dir)
        findings = universal.scan()
        coverage = universal.get_coverage()

        self.assertIn("overall_status", coverage)
        self.assertIn("tools", coverage)
        self.assertIn("sast", coverage["tools"])
        self.assertIn("secrets", coverage["tools"])
        self.assertIn("dependencies", coverage["tools"])
        self.assertGreaterEqual(coverage["files_examined"], 1)


if __name__ == "__main__":
    unittest.main()
