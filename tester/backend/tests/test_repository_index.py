"""Tests for Phase 1: Shared Repository Indexer and Event Bus."""

import os
import tempfile
import pytest
from app.analysis.indexer import build_repository_index
from app.events.bus import emit_event, subscribe, get_recent_events, clear_repository_events


def test_build_repository_index_detects_structure():
    with tempfile.TemporaryDirectory() as tmp_dir:
        # Create minimal python app
        os.makedirs(os.path.join(tmp_dir, "backend", "app"), exist_ok=True)
        with open(os.path.join(tmp_dir, "backend", "app", "main.py"), "w", encoding="utf-8") as f:
            f.write("""
from fastapi import FastAPI, APIRouter

app = FastAPI()
router = APIRouter()

@router.get("/users")
def get_users():
    return []

@app.post("/login")
def login():
    return {}
""")

        # Create requirements.txt
        with open(os.path.join(tmp_dir, "requirements.txt"), "w", encoding="utf-8") as f:
            f.write("fastapi==0.100.0\nsqlalchemy>=2.0.0\npytest\n")

        # Create frontend mock
        os.makedirs(os.path.join(tmp_dir, "frontend", "src"), exist_ok=True)
        with open(os.path.join(tmp_dir, "frontend", "src", "App.tsx"), "w", encoding="utf-8") as f:
            f.write("export default function App() { return <div>App</div>; }")

        with open(os.path.join(tmp_dir, "frontend", "package.json"), "w", encoding="utf-8") as f:
            f.write('{"dependencies": {"react": "^18.0.0", "vite": "^4.0.0"}}')

        # Create test file
        with open(os.path.join(tmp_dir, "backend", "test_app.py"), "w", encoding="utf-8") as f:
            f.write("def test_dummy(): assert True")

        # Run indexer
        index = build_repository_index(tmp_dir, "dummy_sha")

        assert index["file_count"] >= 5
        assert "FastAPI" in index["frameworks"]
        assert "React" in index["frameworks"]
        assert "Vite" in index["frameworks"]
        assert any(ep in index["entry_points"] for ep in ["backend/app/main.py", "frontend/src/App.tsx"])
        assert len(index["api_routes"]) == 2
        routes_paths = [r["path"] for r in index["api_routes"]]
        assert "/users" in routes_paths
        assert "/login" in routes_paths
        assert len(index["test_files"]) >= 1
        assert "Python" in index["languages"]
        assert "TypeScript (React)" in index["languages"]


def test_event_bus_lifecycle():
    repo_id = 9999
    clear_repository_events(repo_id)

    received_events = []

    def handler(ev):
        received_events.append(ev)

    subscribe("commit_indexed", handler)

    ev = emit_event("commit_indexed", repo_id, {"commit_sha": "abc1234", "files": 10})
    assert ev["event_type"] == "commit_indexed"
    assert ev["repository_id"] == repo_id
    assert ev["payload"]["commit_sha"] == "abc1234"

    # Verify handler caught it
    assert len(received_events) >= 1
    assert received_events[-1]["id"] == ev["id"]

    # Verify Watchtower retrieval
    history = get_recent_events(repo_id)
    assert len(history) >= 1
    assert history[0]["event_type"] == "commit_indexed"

    # Verify cleanup on repository deletion
    clear_repository_events(repo_id)
    assert len(get_recent_events(repo_id)) == 0
