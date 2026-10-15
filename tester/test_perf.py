import asyncio
import time
from sqlalchemy import select
from app.database.session import AsyncSessionLocal
from app.database.models import Scan, Repository
from app.workers.scan_job import run_scan

async def main():
    async with AsyncSessionLocal() as db:
        scan = (await db.execute(select(Scan).order_by(Scan.id.desc()).limit(1))).scalars().first()
        if not scan:
            print("No scans to test")
            return
        
        print(f"Profiling scan {scan.id} (Commit {scan.commit_id})")
        
        start = time.time()
        await run_scan(scan.id)
        end = time.time()
        
        print(f"Total scan time: {end - start:.2f}s")

if __name__ == "__main__":
    asyncio.run(main())
