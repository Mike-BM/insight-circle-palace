import asyncio
import os
import sys

# Add project root
sys.path.insert(0, "C:/Users/brian/.gemini/antigravity/scratch/insight-circle-palace")
os.chdir("C:/Users/brian/.gemini/antigravity/scratch/insight-circle-palace")

import httpx
from main import app

async def run_tests():
    print("========================================")
    print("   ADMIN PORTAL ACCESS & HEALTH TEST   ")
    print("========================================")

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Test Admin Portal Redirects
        r = await client.get("/admin_portal", follow_redirects=False)
        print(f"1. GET /admin_portal         : HTTP {r.status_code} -> Location: {r.headers.get('location')}")
        assert r.status_code in [302, 307]
        assert r.headers.get("location") == "/admin/dashboard"

        r = await client.get("/admin", follow_redirects=False)
        print(f"2. GET /admin                : HTTP {r.status_code} -> Location: {r.headers.get('location')}")
        assert r.status_code in [302, 307]
        assert r.headers.get("location") == "/admin/dashboard"

        # 2. Test Admin Dashboard Page Serving
        r = await client.get("/admin/dashboard")
        print(f"3. GET /admin/dashboard      : HTTP {r.status_code} (Length: {len(r.text)})")
        assert r.status_code == 200
        assert '<script src="/admin_app/js/admin.js"></script>' in r.text
        print("   - Verified dashboard.html contains absolute /admin_app/js/admin.js script tag")

        # 3. Test Admin Login Page Serving
        r = await client.get("/admin/login")
        print(f"4. GET /admin/login          : HTTP {r.status_code} (Length: {len(r.text)})")
        assert r.status_code == 200
        assert "Admin Login" in r.text

        # 4. Test Static Admin JS Serving
        r1 = await client.get("/admin_app/js/admin.js")
        print(f"5. GET /admin_app/js/admin.js: HTTP {r1.status_code} (Length: {len(r1.text)})")
        assert r1.status_code == 200
        assert "allUsers" in r1.text

        r2 = await client.get("/admin/js/admin.js")
        print(f"6. GET /admin/js/admin.js    : HTTP {r2.status_code} (Length: {len(r2.text)})")
        assert r2.status_code == 200
        assert "allUsers" in r2.text

        # 5. Test Admin Login for brianmuema928@gmail.com
        login_res = await client.post("/auth/login", json={
            "email": "brianmuema928@gmail.com",
            "password": "Admin123!"
        })
        print(f"7. POST /auth/login (brian)  : HTTP {login_res.status_code}")
        assert login_res.status_code == 200, f"Login failed: {login_res.text}"
        user_data = login_res.json()["user"]
        print(f"   - Logged in as: {user_data['full_name']} ({user_data['email']}), Role: {user_data['role']}")
        assert user_data["role"] == "super_admin"

        # 6. Test Auth Check (/auth/me) with Cookie
        me_res = await client.get("/auth/me")
        print(f"8. GET /auth/me              : HTTP {me_res.status_code}")
        assert me_res.status_code == 200
        assert me_res.json()["email"] == "brianmuema928@gmail.com"

        # 7. Test Admin API Access (/admin/users)
        users_res = await client.get("/admin/users")
        print(f"9. GET /admin/users          : HTTP {users_res.status_code} (Found {len(users_res.json())} users)")
        assert users_res.status_code == 200
        assert len(users_res.json()) > 0

        # 8. Test Admin Dashboard Stats
        stats_res = await client.get("/admin/dashboard/stats")
        print(f"10. GET /admin/dashboard/stats: HTTP {stats_res.status_code}")
        assert stats_res.status_code == 200

        # 9. Test Analytics Admin Stats
        analytics_res = await client.get("/analytics/admin/stats")
        print(f"11. GET /analytics/admin/stats: HTTP {analytics_res.status_code}")
        assert analytics_res.status_code == 200

    # 10. Test Login for second admin rayazenlyx@gmail.com in fresh client
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client2:
        login2_res = await client2.post("/auth/login", json={
            "email": "rayazenlyx@gmail.com",
            "password": "Admin123!"
        })
        print(f"12. POST /auth/login (raya)  : HTTP {login2_res.status_code}")
        assert login2_res.status_code == 200, f"Login 2 failed: {login2_res.text}"
        user2_data = login2_res.json()["user"]
        print(f"   - Logged in as: {user2_data['full_name']} ({user2_data['email']}), Role: {user2_data['role']}")
        assert user2_data["role"] == "super_admin"

    print("\n========================================")
    print("   ALL 12 TESTS PASSED SUCCESSFULLY!    ")
    print("========================================")

def test_admin_portal_access():
    asyncio.run(run_tests())

if __name__ == "__main__":
    asyncio.run(run_tests())
