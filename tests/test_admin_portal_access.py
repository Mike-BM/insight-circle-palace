import asyncio
import os
import sys
import uuid

# Add project root
sys.path.insert(0, "C:/Users/brian/.gemini/antigravity/scratch/insight-circle-palace")
os.chdir("C:/Users/brian/.gemini/antigravity/scratch/insight-circle-palace")

import httpx
from main import app
from app.auth import get_password_hash
from app.database import AsyncSessionLocal
from app.models import User

async def setup_test_users():
    """Ensure test users exist in the database."""
    async with AsyncSessionLocal() as session:
        from sqlalchemy.future import select

        # 1. Normal member
        member = await session.scalar(select(User).where(User.email == "test_member@insightcircle.org"))
        if not member:
            member = User(
                id=str(uuid.uuid4()),
                email="test_member@insightcircle.org",
                full_name="Normal Member",
                password_hash=get_password_hash("Member123!"),
                role="member",
                status="active",
                email_verified=True,
            )
            session.add(member)
        else:
            member.role = "member"
            member.password_hash = get_password_hash("Member123!")

        # 2. Super admins
        admin_brian = await session.scalar(select(User).where(User.email == "brianmuema928@gmail.com"))
        if not admin_brian:
            admin_brian = User(
                id="b314c169-d766-47f3-ad1d-107383eef6b4",
                email="brianmuema928@gmail.com",
                full_name="Brian Muema",
                password_hash=get_password_hash("Admin123!"),
                role="super_admin",
                status="active",
                email_verified=True,
            )
            session.add(admin_brian)
        else:
            admin_brian.role = "super_admin"

        admin_raya = await session.scalar(select(User).where(User.email == "rayazenlyx@gmail.com"))
        if not admin_raya:
            admin_raya = User(
                id="e494cd3e-9973-4ccf-a024-f54e8f372045",
                email="rayazenlyx@gmail.com",
                full_name="Raya Zenlyx",
                password_hash=get_password_hash("Admin123!"),
                role="super_admin",
                status="active",
                email_verified=True,
            )
            session.add(admin_raya)
        else:
            admin_raya.role = "super_admin"

        await session.commit()

async def run_tests():
    print("==================================================================")
    print("   ADMIN PORTAL ACCESS CONTROL & SECURITY AUDIT TEST SUITE       ")
    print("==================================================================")

    await setup_test_users()

    transport = httpx.ASGITransport(app=app)

    # =========================================================================
    # PART A: LOGGED-OUT VISITOR (UNAUTHENTICATED)
    # =========================================================================
    print("\n--- PART A: Testing Logged-Out Visitor Access ---")
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as anon_client:
        # A1: Opening /admin directly by URL -> Redirect to /admin/login
        r = await anon_client.get("/admin", follow_redirects=False)
        print(f"A1. GET /admin (anon)                : HTTP {r.status_code} -> Location: {r.headers.get('location')}")
        assert r.status_code in [302, 307]
        assert r.headers.get("location") == "/admin/login"

        # A2: Opening /admin/ directly by URL -> Redirect to /admin/login
        r = await anon_client.get("/admin/", follow_redirects=False)
        print(f"A2. GET /admin/ (anon)               : HTTP {r.status_code} -> Location: {r.headers.get('location')}")
        assert r.status_code in [302, 307]
        assert r.headers.get("location") == "/admin/login"

        # A3: Opening /admin_portal directly by URL -> Redirect to /admin/login
        r = await anon_client.get("/admin_portal", follow_redirects=False)
        print(f"A3. GET /admin_portal (anon)         : HTTP {r.status_code} -> Location: {r.headers.get('location')}")
        assert r.status_code in [302, 307]
        assert r.headers.get("location") == "/admin/login"

        # A4: Opening /admin/dashboard directly by URL -> Redirect to /admin/login
        r = await anon_client.get("/admin/dashboard", follow_redirects=False)
        print(f"A4. GET /admin/dashboard (anon)      : HTTP {r.status_code} -> Location: {r.headers.get('location')}")
        assert r.status_code in [302, 307]
        assert r.headers.get("location") == "/admin/login"

        # A5: Opening /admin_app/dashboard.html directly -> Redirect to /admin/login
        r = await anon_client.get("/admin_app/dashboard.html", follow_redirects=False)
        print(f"A5. GET /admin_app/dashboard.html    : HTTP {r.status_code} -> Location: {r.headers.get('location')}")
        assert r.status_code in [302, 307]
        assert r.headers.get("location") == "/admin/login"

        # A6: Opening arbitrary nested /admin route -> Redirect to /admin/login
        r = await anon_client.get("/admin/nested/secret-view", follow_redirects=False)
        print(f"A6. GET /admin/nested/secret-view    : HTTP {r.status_code} -> Location: {r.headers.get('location')}")
        assert r.status_code in [302, 307]
        assert r.headers.get("location") == "/admin/login"

        # A7: Direct API calls by logged-out visitor must all return 401 Unauthorized
        endpoints_401 = [
            ("GET", "/admin/users"),
            ("GET", "/admin/dashboard/stats"),
            ("GET", "/analytics/admin/stats"),
            ("GET", "/api/admin/recordings"),
            ("GET", "/api/admin/merchandise/orders"),
            ("GET", "/api/admin/memberships/overview"),
            ("GET", "/admin/audit-logs"),
            ("GET", "/admin/enquiries"),
            ("GET", "/admin/payment-requests"),
            ("GET", "/admin/entitlements"),
            ("POST", "/api/admin/insighters_monday"),
            ("POST", "/api/admin/upload-image"),
        ]
        for method, ep in endpoints_401:
            if method == "GET":
                resp = await anon_client.get(ep)
            else:
                resp = await anon_client.post(ep)
            print(f"A7. {method} {ep:32} : HTTP {resp.status_code}")
            assert resp.status_code == 401, f"Expected 401 on {ep}, got {resp.status_code}"

        # A8: Public Admin Login page and static JS must be accessible
        login_page_res = await anon_client.get("/admin/login")
        print(f"A8. GET /admin/login                 : HTTP {login_page_res.status_code} (Admin Login form served)")
        assert login_page_res.status_code == 200
        assert "Admin Login" in login_page_res.text

        r_js1 = await anon_client.get("/admin_app/js/admin.js")
        assert r_js1.status_code == 200
        r_js2 = await anon_client.get("/admin/js/admin.js")
        assert r_js2.status_code == 200
        print("A9. Static admin JS files served cleanly with HTTP 200")

    # =========================================================================
    # PART B: NORMAL MEMBER (AUTHENTICATED NON-ADMIN)
    # =========================================================================
    print("\n--- PART B: Testing Normal Member Access ---")
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as member_client:
        # B1: Log in as normal member
        login_res = await member_client.post("/auth/login", json={
            "email": "test_member@insightcircle.org",
            "password": "Member123!"
        })
        print(f"B1. POST /auth/login (member)        : HTTP {login_res.status_code}")
        assert login_res.status_code == 200
        user_info = login_res.json()["user"]
        assert user_info["role"] == "member"
        print(f"   - Logged in as: {user_info['full_name']}, Role: {user_info['role']}")

        # B2: Verify member cannot escalate privileges by updating own profile row
        escalate_res = await member_client.put("/auth/me", json={"role": "super_admin"})
        print(f"B2. PUT /auth/me with role='super_admin' : HTTP {escalate_res.status_code}")
        assert escalate_res.status_code in [400, 200]
        # Check current role in DB/session
        me_check = await member_client.get("/auth/me")
        assert me_check.status_code == 200
        assert me_check.json()["role"] == "member", "Privilege escalation vulnerability: user changed their own role!"
        print("   - Verified user cannot update their own role via /auth/me")

        # B3: Member opens /admin directly by URL -> Redirect to /dashboard
        r = await member_client.get("/admin", follow_redirects=False)
        print(f"B3. GET /admin (member)              : HTTP {r.status_code} -> Location: {r.headers.get('location')}")
        assert r.status_code in [302, 307]
        assert r.headers.get("location") == "/dashboard"

        # B4: Member opens /admin/dashboard directly -> Redirect to /dashboard
        r = await member_client.get("/admin/dashboard", follow_redirects=False)
        print(f"B4. GET /admin/dashboard (member)    : HTTP {r.status_code} -> Location: {r.headers.get('location')}")
        assert r.status_code in [302, 307]
        assert r.headers.get("location") == "/dashboard"

        # B5: Member opens /admin_portal directly -> Redirect to /dashboard
        r = await member_client.get("/admin_portal", follow_redirects=False)
        print(f"B5. GET /admin_portal (member)       : HTTP {r.status_code} -> Location: {r.headers.get('location')}")
        assert r.status_code in [302, 307]
        assert r.headers.get("location") == "/dashboard"

        # B6: Member opens arbitrary nested /admin route -> Redirect to /dashboard
        r = await member_client.get("/admin/nested/private", follow_redirects=False)
        print(f"B6. GET /admin/nested/private        : HTTP {r.status_code} -> Location: {r.headers.get('location')}")
        assert r.status_code in [302, 307]
        assert r.headers.get("location") == "/dashboard"

        # B7: Direct API calls by normal member must all return 403 Forbidden
        endpoints_403 = [
            ("GET", "/admin/users"),
            ("GET", "/admin/dashboard/stats"),
            ("GET", "/analytics/admin/stats"),
            ("GET", "/api/admin/recordings"),
            ("GET", "/api/admin/merchandise/orders"),
            ("GET", "/api/admin/memberships/overview"),
            ("GET", "/admin/audit-logs"),
            ("GET", "/admin/enquiries"),
            ("GET", "/admin/payment-requests"),
            ("GET", "/admin/entitlements"),
            ("POST", "/api/admin/insighters_monday"),
            ("POST", "/api/admin/upload-image"),
        ]
        for method, ep in endpoints_403:
            if method == "GET":
                resp = await member_client.get(ep)
            else:
                resp = await member_client.post(ep)
            print(f"B7. {method} {ep:32} : HTTP {resp.status_code}")
            assert resp.status_code == 403, f"Expected 403 Forbidden on {ep}, got {resp.status_code}"

    # =========================================================================
    # PART C: VERIFIED ADMIN (SUPER_ADMIN)
    # =========================================================================
    print("\n--- PART C: Testing Verified Admin Access ---")
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as admin_client:
        # C1: Log in as super_admin
        login_res = await admin_client.post("/auth/login", json={
            "email": "brianmuema928@gmail.com",
            "password": "Admin123!"
        })
        print(f"C1. POST /auth/login (brian)         : HTTP {login_res.status_code}")
        assert login_res.status_code == 200
        admin_data = login_res.json()["user"]
        print(f"   - Logged in as: {admin_data['full_name']} ({admin_data['email']}), Role: {admin_data['role']}")
        assert admin_data["role"] == "super_admin"

        # C2: Admin opens /admin directly by URL -> Redirect to /admin/dashboard
        r = await admin_client.get("/admin", follow_redirects=False)
        print(f"C2. GET /admin (admin)               : HTTP {r.status_code} -> Location: {r.headers.get('location')}")
        assert r.status_code in [302, 307]
        assert r.headers.get("location") == "/admin/dashboard"

        # C3: Admin opens /admin/dashboard directly by URL -> 200 OK dashboard served
        dash_res = await admin_client.get("/admin/dashboard")
        print(f"C3. GET /admin/dashboard (admin)     : HTTP {dash_res.status_code} (Length: {len(dash_res.text)})")
        assert dash_res.status_code == 200
        assert '<script src="/admin_app/js/admin.js"></script>' in dash_res.text
        assert 'id="admin-portal-loader"' in dash_res.text
        print("   - Verified dashboard.html served with admin script tag and secure loader")

        # C4: Direct API calls by admin succeed with 200 OK
        users_res = await admin_client.get("/admin/users")
        print(f"C4. GET /admin/users                 : HTTP {users_res.status_code} (Found {len(users_res.json())} users)")
        assert users_res.status_code == 200

        dash_stats_res = await admin_client.get("/admin/dashboard/stats")
        print(f"C5. GET /admin/dashboard/stats       : HTTP {dash_stats_res.status_code}")
        assert dash_stats_res.status_code == 200

        analytics_res = await admin_client.get("/analytics/admin/stats")
        print(f"C6. GET /analytics/admin/stats       : HTTP {analytics_res.status_code}")
        assert analytics_res.status_code == 200

        payment_req_res = await admin_client.get("/admin/payment-requests")
        print(f"C7. GET /admin/payment-requests      : HTTP {payment_req_res.status_code}")
        assert payment_req_res.status_code == 200

        entitlements_res = await admin_client.get("/admin/entitlements")
        print(f"C8. GET /admin/entitlements          : HTTP {entitlements_res.status_code}")
        assert entitlements_res.status_code == 200

        merch_res = await admin_client.get("/api/admin/merchandise/orders")
        print(f"C9. GET /api/admin/merchandise/orders: HTTP {merch_res.status_code}")
        assert merch_res.status_code == 200

        # C10: Prevent admin from changing their own role
        self_role_res = await admin_client.put(f"/admin/users/{admin_data['id']}", json={"role": "member"})
        print(f"C10. PUT /admin/users/own_id (change role): HTTP {self_role_res.status_code}")
        assert self_role_res.status_code == 400
        assert "cannot update their own role" in self_role_res.text.lower()
        print("   - Verified admin is prevented from altering their own role")

    # =========================================================================
    # PART D: VERIFY SECOND ADMIN ACCOUNT
    # =========================================================================
    print("\n--- PART D: Testing Second Admin Account ---")
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as admin2_client:
        login2_res = await admin2_client.post("/auth/login", json={
            "email": "rayazenlyx@gmail.com",
            "password": "Admin123!"
        })
        print(f"D1. POST /auth/login (raya)          : HTTP {login2_res.status_code}")
        assert login2_res.status_code == 200
        user2_data = login2_res.json()["user"]
        print(f"   - Logged in as: {user2_data['full_name']} ({user2_data['email']}), Role: {user2_data['role']}")
        assert user2_data["role"] == "super_admin"

        r = await admin2_client.get("/admin/dashboard")
        assert r.status_code == 200
        print("D2. GET /admin/dashboard (raya)      : HTTP 200")

    print("\n==================================================================")
    print("   ALL SECURITY ACCESS CONTROL TESTS PASSED SUCCESSFULLY!       ")
    print("==================================================================")

def test_admin_portal_access():
    asyncio.run(run_tests())

if __name__ == "__main__":
    asyncio.run(run_tests())
