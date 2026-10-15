import asyncio
import httpx

BASE_URL = "https://gitflow-c2li.onrender.com"

async def main():
    async with httpx.AsyncClient(timeout=30) as client:
        res = await client.post(f"{BASE_URL}/auth/login", data={
            "username": "testuser_5887@example.com",
            "password": "password123"
        })
        token = res.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        repo_id = 6
        
        res = await client.get(f"{BASE_URL}/repositories/", headers=headers)
        repos = res.json()
        for r in repos:
            if r["id"] == repo_id:
                print(f"- last_processed_sha: {r.get('last_processed_sha')}")
                print(f"- last_seen_sha: {r.get('last_seen_sha')}")
                print(f"- last_poll_error: {r.get('last_poll_error')}")
                
if __name__ == "__main__":
    asyncio.run(main())
