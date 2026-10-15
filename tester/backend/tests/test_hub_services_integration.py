"""Integration tests for Project Hub routes and Verified Automation Services."""

import pytest
from httpx import ASGITransport, AsyncClient
from app.main import app
from app.services.failure_intel import failure_intel_service
from app.services.cloud_preview import cloud_preview_service
from app.services.fix_agent import fix_agent
from app.services.cross_repo import cross_repo_service
from app.ai.service import ai_service


async def request(method, path, **kwargs):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        return await client.request(method, path, **kwargs)


@pytest.mark.asyncio
async def test_failure_intel_service_direct():
    log = """
    Step 4/5 : RUN pytest tests/
    ---> Running in abcdef123456
    FAILED tests/test_security.py::test_jwt - AssertionError: expected valid
    The command '/bin/sh -c pytest tests/' returned a non-zero code: 1
    """
    res = failure_intel_service.analyze_build_or_ci_failure(log)
    assert res["status"] == "ANALYZED"
    assert len(res["failed_steps"]) > 0
    assert len(res["ranked_root_causes"]) > 0


@pytest.mark.asyncio
async def test_cloud_preview_service_direct():
    contract = cloud_preview_service.create_isolated_preview_contract(
        repo_id=99,
        repo_name="preview-test",
        commit_sha="HEAD",
        user_id=1,
    )
    assert contract["status"] == "READY"
    assert contract["contract"]["max_cpu_cores"] == 1
    assert contract["contract"]["max_runtime_seconds"] == 30
    cleaned = cloud_preview_service.cleanup_preview(contract["preview_id"])
    assert cleaned is True


@pytest.mark.asyncio
async def test_hub_auth_protection_on_services():
    # Calling hub endpoints without auth returns 401
    res1 = await request("POST", "/repositories/1/hub/cloud-preview")
    assert res1.status_code == 401

    res2 = await request("GET", "/repositories/1/hub/cross-repo")
    assert res2.status_code == 401

    res3 = await request("POST", "/repositories/1/hub/failure-intelligence", json={"failure_log": "error"})
    assert res3.status_code == 401

    res4 = await request("POST", "/repositories/1/hub/findings/1/fix")
    assert res4.status_code == 401
