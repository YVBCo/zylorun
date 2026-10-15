import asyncio
import httpx
import json

BASE_URL = "https://gitflow-c2li.onrender.com"

async def main():
    async with httpx.AsyncClient(timeout=30) as client:
        res = await client.post(f"{BASE_URL}/auth/login", data={"username": "testuser_5887@example.com", "password": "password123"})
        token = res.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        
        res = await client.get(f"{BASE_URL}/repositories/6/scans/47", headers=headers)
        print("Status code:", res.status_code)
        print(json.dumps(res.json(), indent=2))
        
if __name__ == "__main__":
    asyncio.run(main())
