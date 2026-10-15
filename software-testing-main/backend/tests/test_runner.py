import pytest
import json
from fastapi.testclient import TestClient
from fastapi.websockets import WebSocket
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.main import app
from app.db.database import get_db, Base
from app.models.models import CommandConfig, Target
import sys

SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base.metadata.create_all(bind=engine)

def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)

@pytest.fixture(autouse=True)
def run_around_tests():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    
    db = TestingSessionLocal()
    db.add(Target(name="Localhost", host="127.0.0.1", description="Test"))
    
    db.add(CommandConfig(
        name="MockNmap",
        executable=sys.executable, 
        allowed_args=json.dumps(["-c", "print('hello from mock'); import time; time.sleep(0.1); print('done')"]),
        timeout_seconds=5,
        regex_rules="{}"
    ))
    db.commit()
    db.close()
    
    yield

def test_websocket_runner():
    with client.websocket_connect("/runs/ws/1/1") as websocket:
        websocket.send_text(json.dumps({"args": ["-c", "print('hello from mock'); import time; time.sleep(0.1); print('done')"]}))
        
        data1 = websocket.receive_json()
        assert data1.get("stream") == "stdout"
        assert "hello from mock" in data1["data"]
        
        data2 = websocket.receive_json()
        assert data2["stream"] == "stdout"
        assert "done" in data2["data"]
        
        data3 = websocket.receive_json()
        assert data3["status"] == "Completed"
        assert data3["exit_code"] == 0
