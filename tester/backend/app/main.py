from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from app.database.session import engine, Base
from app.api.routes import (
    auth,
    repositories,
    webhooks,
    notifications,
    admin,
    project_hub,
    targets,
    commands,
    runs,
    reports,
    system_tests
)
# import models to ensure they are registered with Base metadata
from app.database import models

import asyncio
import logging

logger = logging.getLogger(__name__)

def run_migrations():
    from alembic.config import Config
    from alembic import command
    # Assuming the working directory is backend
    import os
    alembic_ini_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "alembic.ini")
    alembic_cfg = Config(alembic_ini_path)
    # Set the script location manually just in case
    alembic_cfg.set_main_option("script_location", os.path.join(os.path.dirname(os.path.dirname(__file__)), "alembic"))
    command.upgrade(alembic_cfg, "head")

async def background_repo_poller():
    """Continuously polls active repositories for new commits in the background.
    Runs periodically every 60 seconds with lock protection and error isolation.
    """
    import os
    if os.environ.get("PYTEST_CURRENT_TEST") or os.environ.get("TESTING"):
        return

    await asyncio.sleep(15)  # Grace period after boot
    while True:
        try:
            from app.api.routes.admin import execute_polling_cycle
            await execute_polling_cycle()
        except asyncio.CancelledError:
            break
        except Exception as exc:
            logger.warning("Background repository polling cycle encountered error: %s", exc)
        try:
            await asyncio.sleep(60)
        except asyncio.CancelledError:
            break


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        try:
            await asyncio.to_thread(run_migrations)
            logger.info("Successfully ran database migrations.")
        except Exception as mig_err:
            logger.warning("Database migrations skipped or encountered note: %s. Ensuring schema via Base.metadata...", mig_err)
            try:
                from app.database.session import sync_engine, Base
                await asyncio.to_thread(Base.metadata.create_all, bind=sync_engine)
                logger.info("Successfully verified database schema via metadata fallback.")
            except Exception as meta_err:
                logger.warning("Metadata verification notice: %s", meta_err)

        try:
            from app.database.session import SessionLocal
            from app.database.models import CommandConfig
            import json
            def _seed():
                db = SessionLocal()
                try:
                    if db.query(CommandConfig).count() == 0:
                        defaults = [
                            CommandConfig(
                                name="Ping Latency Diagnostic",
                                executable="ping",
                                allowed_args=json.dumps(["-c", "4", "-n", "4"]),
                                timeout_seconds=30,
                                regex_rules=json.dumps({
                                    "rules": [
                                        {"pattern": r"100% packet loss|Destination host unreachable", "severity": "Critical", "message": "Host is completely unreachable."},
                                        {"pattern": r"Request timed out", "severity": "Warning", "message": "Packet loss detected."}
                                    ]
                                })
                            ),
                            CommandConfig(
                                name="HTTPS TLS Header Audit",
                                executable="curl",
                                allowed_args=json.dumps(["-I", "-s", "--max-time", "15"]),
                                timeout_seconds=30,
                                regex_rules=json.dumps({
                                    "rules": [
                                        {"pattern": r"HTTP/(?:1\.1|2|3)\s+(?:4\d\d|5\d\d)", "severity": "Warning", "message": "Non-200 HTTP response status returned by target."},
                                        {"pattern": r"Strict-Transport-Security", "severity": "Info", "message": "HSTS security header detected."}
                                    ]
                                })
                            ),
                            CommandConfig(
                                name="Nmap Security Port Scan",
                                executable="nmap",
                                allowed_args=json.dumps(["-F", "-sT", "--top-ports", "20"]),
                                timeout_seconds=120,
                                regex_rules=json.dumps({
                                    "rules": [
                                        {"pattern": r"22/open", "severity": "Warning", "message": "SSH port 22 is publicly exposed."},
                                        {"pattern": r"23/open|21/open", "severity": "Critical", "message": "Insecure legacy protocol (Telnet/FTP) detected."}
                                    ]
                                })
                            )
                        ]
                        for c in defaults:
                            db.add(c)
                        db.commit()
                except Exception as exc:
                    logger.warning("Could not seed default command configs: %s", exc)
                finally:
                    db.close()
            await asyncio.to_thread(_seed)
        except Exception as exc:
            logger.warning("Default command seeding encountered exception: %s", exc)

        poller_task = asyncio.create_task(background_repo_poller())
        yield
        poller_task.cancel()
        try:
            await poller_task
        except (asyncio.CancelledError, Exception):
            pass
    finally:
        await engine.dispose()


app = FastAPI(title="Software Risk Passport", lifespan=lifespan)

from app.config import settings

cors_origins = [
    "https://zylorun-five.vercel.app",
    "https://zylorun.vercel.app",
    "https://vovalyx.in",
    "https://www.vovalyx.in",
    "http://localhost:5173",
    "http://localhost:3000",
    "http://localhost:8000",
    "http://127.0.0.1:5173",
    "http://127.0.0.1:3000",
]

if settings.FRONTEND_URL and settings.FRONTEND_URL != "*":
    for origin in settings.FRONTEND_URL.split(","):
        origin = origin.strip()
        if origin and origin not in cors_origins:
            cors_origins.append(origin)

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_origin_regex=r"^https://.*\.vercel\.app$|^https://.*\.onrender\.com$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

app.include_router(auth.router)
app.include_router(repositories.router)
app.include_router(project_hub.router)
app.include_router(webhooks.router)
app.include_router(notifications.router)
app.include_router(admin.router)
app.include_router(targets.router)
app.include_router(commands.router)
app.include_router(runs.router)
app.include_router(reports.router)
app.include_router(system_tests.router)

@app.get("/api/v1/health")
@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "Unified Security Platform", "version": "2.0.0"}

@app.get("/")
async def root():
    return {"message": "Welcome to Software Risk Passport API"}
