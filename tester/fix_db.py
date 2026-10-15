import asyncio
from sqlalchemy import select
from app.database.session import AsyncSessionLocal
from app.database.models import Commit, Scan

async def main():
    async with AsyncSessionLocal() as db:
        commit = (await db.execute(select(Commit).where(Commit.hash == "7e64470d9c14b940066ce74a599fcd51976ed0c1"))).scalars().first()
        if commit:
            scan = (await db.execute(select(Scan).where(Scan.commit_id == commit.id))).scalars().first()
            if scan:
                scan.status = "FAILED"
                await db.commit()
                print("Set scan to FAILED")
            else:
                print("Scan not found")
        else:
            print("Commit not found")

if __name__ == "__main__":
    asyncio.run(main())
