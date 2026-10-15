import os
import sys
import json
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

sys.path.append(os.path.abspath(r"c:\Users\DELL\OneDrive\Desktop\testing\sec-runner\backend"))
from app.models.models import Target, CommandConfig, Base

engine = create_engine("sqlite:///c:/Users/DELL/OneDrive/Desktop/testing/sec-runner/backend/secrunner.db")
Base.metadata.create_all(bind=engine)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

db = SessionLocal()

t = db.query(Target).filter_by(id=1).first()
if not t:
    t = Target(id=1, name="Localhost", host="127.0.0.1", description="Test")
    db.add(t)

c = db.query(CommandConfig).filter_by(id=1).first()
if not c:
    c = CommandConfig(
        id=1,
        name="MockNmap",
        executable=sys.executable,
        allowed_args=json.dumps(["-u", "-c", "print('hello from mock'); import time; time.sleep(0.5); print('done')"]),
        timeout_seconds=5,
        regex_rules="{}"
    )
    db.add(c)
    
db.commit()
print("DB seeded")
