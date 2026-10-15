import os
import pytest
from pathlib import Path

# Ensure testing environment and isolated SQLite DB for tests
test_db_path = Path(__file__).parent.parent / "test_suite.db"
os.environ["ENVIRONMENT"] = "testing"
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{test_db_path.as_posix()}"
os.environ["GITFLOW_CRON_SECRET"] = "test-secret"
os.environ["SECRET_KEY"] = "test-secret-key-for-unit-tests-only"
os.environ["GITHUB_WEBHOOK_SECRET"] = "test-webhook-secret"

@pytest.fixture(scope="session", autouse=True)
def setup_test_database():
    if test_db_path.exists():
        try:
            test_db_path.unlink()
        except OSError:
            pass
    yield
    if test_db_path.exists():
        try:
            test_db_path.unlink()
        except OSError:
            pass
