from fastapi import FastAPI
from app.api import auth, users, runs, commands, targets, reports
from app.db.database import engine, Base
import sys
import asyncio
from dotenv import load_dotenv

load_dotenv()

if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

Base.metadata.create_all(bind=engine)

from fastapi.middleware.cors import CORSMiddleware
from apscheduler.schedulers.background import BackgroundScheduler
from app.db.database import SessionLocal
import datetime

def send_alert_email(failed_targets: list):
    # Simulated Email Sending (Could use smtplib here)
    print("\n" + "="*50)
    print("📧 [EMAIL ALERT SYSTEM]")
    print(f"TO: security-team@company.com")
    print(f"SUBJECT: 🚨 CRITICAL: Nightly Security Scan Failed!")
    print("\nThe automated security scan has detected vulnerabilities on the following targets:")
    for t in failed_targets:
        print(f"  - {t}")
    print("\nPlease log into the SecRunner Dashboard to view the full PDF reports.")
    print("="*50 + "\n")

def automated_scan_job():
    print(f"[{datetime.datetime.now()}] Running automated nightly security scan on all targets...")
    # In a full app, this would iterate over the targets table and call CommandRunner.
    # For demonstration, we simulate a scan that fails and triggers an email alert.
    simulated_failed_targets = ["Prod DB (192.168.1.5)", "Staging Web (10.0.0.12)"]
    send_alert_email(simulated_failed_targets)

scheduler = BackgroundScheduler()

app = FastAPI(title="Security Command Runner & Analyzer API")

@app.on_event("startup")
def startup_tasks():
    # Start the scheduler
    scheduler.add_job(automated_scan_job, 'interval', minutes=60)
    scheduler.start()
    print("Automated Scan Scheduler Started")
    
    # Bootstrap default Admin User if database is empty
    db = SessionLocal()
    try:
        from app.models.models import User
        from app.core.security import get_password_hash
        admin = db.query(User).filter(User.username == "admin").first()
        if not admin:
            print("Bootstrapping default admin user...")
            new_admin = User(
                username="admin",
                password_hash=get_password_hash("secret"),
                role="admin"
            )
            db.add(new_admin)
            db.commit()
    except Exception as e:
        print(f"Failed to bootstrap admin: {e}")
    finally:
        db.close()

@app.on_event("shutdown")
def stop_scheduler():
    scheduler.shutdown()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, tags=["auth"])
app.include_router(users.router)
app.include_router(runs.router)
app.include_router(commands.router)
app.include_router(targets.router)
app.include_router(reports.router)

@app.get("/")
def read_root():
    return {"message": "Welcome to SecRunner API"}
