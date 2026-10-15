import pytest
import json
from unittest.mock import MagicMock
from app.api.routes.repositories import is_fixture_finding

def test_is_fixture_finding_helper():
    class MockFinding:
        def __init__(self, file_path, description=""):
            self.file_path = file_path
            self.description = description

    # Benchmark engine file path
    f1 = MockFinding("backend/app/benchmarks/benchmark_engine.py", "Test pattern")
    assert is_fixture_finding(f1) is True

    # Test fixtures file path
    f2 = MockFinding("backend/tests/fixtures/synthetic_secrets.py", "Test secret")
    assert is_fixture_finding(f2) is True

    # Real application code with real vulnerability
    f3 = MockFinding("backend/app/api/routes/users.py", "Unsanitized user input in query")
    assert is_fixture_finding(f3) is False

    # Real application file but marked as intentional fixture in metadata
    f4 = MockFinding("backend/app/config.py", json.dumps({"classification": "Intentional test fixture or demonstration example"}))
    assert is_fixture_finding(f4) is True

    # Test fixture with is_test_fixture boolean in json
    f5 = MockFinding("sample.py", json.dumps({"is_test_fixture": True}))
    assert is_fixture_finding(f5) is True
