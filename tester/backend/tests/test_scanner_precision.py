import os
import shutil
import tempfile
import unittest
from app.scanners.models import FindingItem
from app.scanners.secrets import (
    run_secret_scan,
    is_sample_or_placeholder_credential,
    redact_secret,
)
from app.scanners.sast import run_sast_scan, get_python_string_literal_lines
from app.scanners.dependencies import extract_npm_packages
from app.scanners.licenses import run_license_scan
from app.scoring.engine import calculate_risk_score
from app.scanners.universal import generate_fingerprint


class ScannerPrecisionTests(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_sample_credential_detection(self):
        """Verifies that sample/placeholder credentials are distinguished from live secrets."""
        # Non-functional documentation sample
        self.assertTrue(is_sample_or_placeholder_credential("AKIAIOSFODNN7EXAMPLE"))
        self.assertTrue(is_sample_or_placeholder_credential("your-super-secret-key-12345"))
        self.assertTrue(is_sample_or_placeholder_credential("replace_with_jwt_secret_key"))
        self.assertTrue(is_sample_or_placeholder_credential("super-secret-production-token"))
        self.assertTrue(is_sample_or_placeholder_credential("${DATABASE_PASSWORD}"))

        # Synthetic live secret
        self.assertFalse(is_sample_or_placeholder_credential("ghp_" + "1234567890abcdefghijklmnopqrstuvwx"))
        self.assertFalse(is_sample_or_placeholder_credential("AKIA" + "1234567890ABCDEF"))

    def test_secret_scanner_real_vs_sample_classification(self):
        """Verifies that sample secrets are classified as test fixtures while real secrets are confirmed exposures."""
        # Create file with sample credential
        sample_file = os.path.join(self.test_dir, "sample.py")
        with open(sample_file, "w") as f:
            f.write('aws_key = "AKIAIOSFODNN7EXAMPLE"\n')

        findings, _ = run_secret_scan(self.test_dir, generate_fingerprint)
        self.assertEqual(len(findings), 1)
        self.assertEqual(
            findings[0].classification,
            "Intentional test fixture or demonstration example"
        )
        self.assertEqual(findings[0].confidence, "Low")
        # Ensure secret is redacted
        self.assertNotIn("FODNN7EXAMPLE", findings[0].code_snippet)
        self.assertIn("AKIA", findings[0].code_snippet)

        # Create file with real-looking token
        real_file = os.path.join(self.test_dir, "real_secret.py")
        live_key = "sk_live_" + "51A2B3C4D5E6F7G8H9I0J1K2"
        with open(real_file, "w") as f:
            f.write(f'stripe_key = "{live_key}"\n')

        findings, _ = run_secret_scan(self.test_dir, generate_fingerprint)
        real_findings = [f for f in findings if f.file_path == "real_secret.py"]
        self.assertEqual(len(real_findings), 1)
        self.assertEqual(
            real_findings[0].classification,
            "Confirmed vulnerability or exposure"
        )
        self.assertEqual(real_findings[0].confidence, "High")
        self.assertNotIn("51A2B3C4D5E6F7G8H9I0J1K2", real_findings[0].code_snippet)

    def test_generic_secret_regex_avoids_code_and_yaml_false_positives(self):
        """Verifies that YAML keys and Python assignments do not trigger generic secret alerts."""
        yaml_file = os.path.join(self.test_dir, "render.yaml")
        with open(yaml_file, "w") as f:
            f.write(
                "services:\n"
                "  - type: web\n"
                "    envVars:\n"
                "      - key: GITHUB_WEBHOOK_SECRET\n"
                "        sync: false\n"
                "      - key: GITHUB_TOKEN_ENCRYPTION_KEY\n"
                "        sync: false\n"
            )

        py_file = os.path.join(self.test_dir, "auth_helper.py")
        with open(py_file, "w") as f:
            f.write('access_token = create_access_token(data={"sub": str(user.id)})\n')

        findings, _ = run_secret_scan(self.test_dir, generate_fingerprint)
        self.assertEqual(len(findings), 0, f"Unexpected false positives: {[f.message for f in findings]}")

    def test_sast_ast_distinguishes_string_literals_in_test_files(self):
        """Verifies that test code string fixtures are classified as test fixtures while runtime code is confirmed."""
        test_dir_sub = os.path.join(self.test_dir, "tests")
        os.makedirs(test_dir_sub)

        # Mock test file with string literal containing SQL injection sample
        test_file = os.path.join(test_dir_sub, "test_sample.py")
        with open(test_file, "w") as f:
            f.write(
                'def test_sql():\n'
                '    fixture_code = """cursor.execute("SELECT * FROM users WHERE id = " + user_input)"""\n'
            )

        # Runtime file with actual vulnerable execution
        app_file = os.path.join(self.test_dir, "app_vuln.py")
        with open(app_file, "w") as f:
            f.write(
                'def run_query(user_input):\n'
                '    cursor.execute("SELECT * FROM users WHERE id = " + user_input)\n'
            )

        findings, _ = run_sast_scan(self.test_dir, generate_fingerprint)
        test_findings = [f for f in findings if f.file_path.startswith("tests")]
        app_findings = [f for f in findings if f.file_path == "app_vuln.py"]

        self.assertGreaterEqual(len(test_findings), 1)
        self.assertEqual(
            test_findings[0].classification,
            "Intentional test fixture or demonstration example"
        )
        self.assertEqual(test_findings[0].confidence, "Low")

        self.assertGreaterEqual(len(app_findings), 1)
        self.assertEqual(
            app_findings[0].classification,
            "Confirmed vulnerability or exposure"
        )

    def test_npm_scoped_package_parsing(self):
        """Verifies that npm package-lock parser preserves @scope in package names."""
        lock_file = os.path.join(self.test_dir, "package-lock.json")
        with open(lock_file, "w") as f:
            f.write(
                '{\n'
                '  "name": "tester",\n'
                '  "version": "1.0.0",\n'
                '  "lockfileVersion": 3,\n'
                '  "packages": {\n'
                '    "": { "name": "tester", "version": "1.0.0" },\n'
                '    "node_modules/@jridgewell/gen-mapping": {\n'
                '      "version": "0.3.13"\n'
                '    },\n'
                '    "node_modules/lodash": {\n'
                '      "version": "4.17.21"\n'
                '    }\n'
                '  }\n'
                '}\n'
            )

        packages = extract_npm_packages(lock_file)
        pkg_dict = {p["name"]: p["version"] for p in packages}
        self.assertIn("@jridgewell/gen-mapping", pkg_dict)
        self.assertNotIn("gen-mapping", pkg_dict)
        self.assertEqual(pkg_dict["@jridgewell/gen-mapping"], "0.3.13")
        self.assertIn("lodash", pkg_dict)

    def test_scoring_engine_zero_deduction_for_test_fixtures(self):
        """Verifies that test fixtures result in 0 score deduction while confirmed findings deduct points."""
        fixture_finding = {
            "category": "Secret",
            "severity": "Critical",
            "message": "AWS Key sample in test_file.py",
            "classification": "Intentional test fixture or demonstration example",
            "fingerprint": "fp_fixture_01"
        }

        real_finding = {
            "category": "Secret",
            "severity": "Critical",
            "message": "Real secret exposed in prod.py",
            "classification": "Confirmed vulnerability or exposure",
            "fingerprint": "fp_real_01"
        }

        # Scan with only test fixture: score should remain 100
        details_fixture = calculate_risk_score([fixture_finding], "COMPLETED")
        self.assertEqual(details_fixture["final_score"], 100)
        self.assertEqual(len(details_fixture["deductions"]), 1)
        self.assertEqual(details_fixture["deductions"][0]["points"], 0)
        self.assertIn("Intentional test fixture", details_fixture["deductions"][0]["reason"])

        # Scan with real confirmed finding: score should deduct points
        details_real = calculate_risk_score([real_finding], "COMPLETED")
        self.assertLess(details_real["final_score"], 100)
        self.assertLess(details_real["deductions"][0]["points"], 0)

    def test_license_compliance_resolution(self):
        """Verifies that repository with standard MIT LICENSE produces zero missing license findings."""
        license_file = os.path.join(self.test_dir, "LICENSE")
        with open(license_file, "w") as f:
            f.write(
                "MIT License\n\n"
                "Copyright (c) 2026 Test\n\n"
                "Permission is hereby granted, free of charge...\n"
            )

        findings, coverage = run_license_scan(self.test_dir, generate_fingerprint)
        self.assertEqual(len(findings), 0)
        self.assertEqual(coverage.status, "COMPLETED")


if __name__ == "__main__":
    unittest.main()
