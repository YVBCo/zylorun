import asyncio
from sqlalchemy import select
from datetime import datetime
from app.database.session import AsyncSessionLocal
from app.database.models import Commit

async def main():
    async with AsyncSessionLocal() as db:
        commits = (await db.execute(select(Commit))).scalars().all()
        for c in commits:
            if not c.committed_at:
                c.committed_at = datetime.utcnow()
        await db.commit()
        print("Updated all missing commit timestamps")

if __name__ == "__main__":
    asyncio.run(main())
