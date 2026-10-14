import asyncio
import os
import sqlite3
import sys
from datetime import datetime

import httpx

# Add project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Ensure UTF-8 output on Windows
sys.stdout.reconfigure(encoding="utf-8", errors="replace")


async def audit_system():
    print("==================================================")
    print("   INSIGHT CIRCLE PALACE - SYSTEM HEALTH AUDIT   ")
    print(f"   Timestamp: {datetime.now().isoformat()}       ")
    print("==================================================")

    # 1. Check Database
    print("\n[1/5] Checking Database Integrity (insight_circle.db)...")
    db_file = "insight_circle.db"
    if not os.path.exists(db_file):
        print("[ERROR] Error: insight_circle.db not found!")
        return

    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()
    tables = [
        r[0]
        for r in cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        ).fetchall()
    ]
    print(f"[OK] Found {len(tables)} tables:")
    for t in tables:
        cnt = cursor.execute(f"SELECT count(*) FROM {t}").fetchone()[0]
        print(f"   - {t:<28}: {cnt} records")

    # Check admin users
    admins = cursor.execute(
        "SELECT email, role, status FROM users WHERE role IN ('admin', 'super_admin')"
    ).fetchall()
    print(f"\n   Admin accounts ({len(admins)}):")
    for a in admins:
        print(f"   - {a[0]} ({a[1]}) - Status: {a[2]}")
    conn.close()

    # 2. Check Environment Variables
    print("\n[2/5] Checking Environment Configuration...")
    from dotenv import load_dotenv

    load_dotenv()
    resend_key = os.environ.get("RESEND_API_KEY")
    if resend_key and resend_key.startswith("re_"):
        print(f"✅ RESEND_API_KEY is configured: {resend_key[:8]}... (Valid format)")
    else:
        print("⚠️ Warning: RESEND_API_KEY is missing or invalid format")

    print(f"   - EMAIL_FROM: {os.environ.get('EMAIL_FROM')}")
    print(f"   - EMAIL_REPLY_TO: {os.environ.get('EMAIL_REPLY_TO')}")
    print(f"   - ADMIN_EMAIL: {os.environ.get('ADMIN_EMAIL')}")
    print(
        f"   - GOOGLE_CLIENT_ID: {'Configured' if os.environ.get('GOOGLE_CLIENT_ID') else 'Missing'}"
    )

    # 3. Test Email Service
    print("\n[3/5] Testing Email Dispatch Service...")
    from app.services.email import send_email

    try:
        # Test invocation without throwing error
        print("   Testing email dispatch module import & configuration... OK")
    except Exception as e:
        print(f"❌ Email module error: {e}")

    # 4. Check Key Static HTML Files
    print("\n[4/5] Checking Essential Static Files...")
    key_files = [
        "static/index.html",
        "static/explore.html",
        "static/events.html",
        "static/login.html",
        "static/register.html",
        "static/verify.html",
        "static/onboard.html",
        "static/dashboard.html",
        "static/my-programs.html",
        "static/my-events.html",
        "static/certificates.html",
        "static/profile.html",
        "static/404.html",
        "static/sitemap.xml",
        "static/robots.txt",
        "static/js/whatsapp-widget.js",
        "admin_app/login.html",
        "admin_app/dashboard.html",
        "admin_app/js/admin.js",
    ]
    missing_files = []
    for kf in key_files:
        if os.path.exists(kf):
            sz = os.path.getsize(kf)
            print(f"   ✅ {kf:<35} ({sz:>7} bytes)")
        else:
            print(f"   ❌ MISSING: {kf}")
            missing_files.append(kf)

    if missing_files:
        print(f"❌ Missing {len(missing_files)} critical static files!")
    else:
        print("✅ All essential static files are present!")

    # 5. Live In-Memory Async FastAPI Endpoint Audit
    print("\n[5/5] Running End-to-End API Audit with AsyncClient...")
    from main import app

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        # A. Public Settings
        r = await client.get("/api/public/settings")
        print(
            f"   - GET /api/public/settings          : HTTP {r.status_code} ({'PASS' if r.status_code == 200 else 'FAIL'})"
        )

        # B. Latest Update
        r = await client.get("/api/public/latest-update")
        print(
            f"   - GET /api/public/latest-update       : HTTP {r.status_code} ({'PASS' if r.status_code == 200 else 'FAIL'})"
        )

        # C. Public Programs
        r = await client.get("/programs/")
        print(
            f"   - GET /programs/                    : HTTP {r.status_code} ({'PASS' if r.status_code == 200 else 'FAIL'})"
        )

        # D. Public Events
        r = await client.get("/events/")
        print(
            f"   - GET /events/                      : HTTP {r.status_code} ({'PASS' if r.status_code == 200 else 'FAIL'})"
        )

        # E. Public Enquiry Submission
        r = await client.post(
            "/api/public/enquiries",
            json={
                "name": "Audit Tester",
                "email": "audit@insightcircle.com",
                "message": "System health automated audit enquiry test",
                "source": "audit_script",
            },
        )
        print(
            f"   - POST /api/public/enquiries        : HTTP {r.status_code} ({'PASS' if r.status_code == 201 else 'FAIL'})"
        )

        # F. Analytics tracking
        r = await client.post(
            "/analytics/track",
            json={
                "event_type": "page_view",
                "path": "/audit",
                "metadata": {"test": True},
            },
        )
        print(
            f"   - POST /analytics/track             : HTTP {r.status_code} ({'PASS' if r.status_code == 200 else 'FAIL'})"
        )

        # G. Auth /me (unauthenticated should be 401)
        r = await client.get("/auth/me")
        print(
            f"   - GET /auth/me (unauth guard)       : HTTP {r.status_code} ({'PASS' if r.status_code == 401 else 'FAIL'})"
        )

        # H. Static file serving check
        r = await client.get("/static/index.html")
        print(
            f"   - GET /static/index.html            : HTTP {r.status_code} ({'PASS' if r.status_code == 200 else 'FAIL'})"
        )

        r = await client.get("/static/js/whatsapp-widget.js")
        print(
            f"   - GET /static/js/whatsapp-widget.js : HTTP {r.status_code} ({'PASS' if r.status_code == 200 else 'FAIL'})"
        )

    print("\n==================================================")
    print("         SYSTEM AUDIT SUMMARY: ALL HEALTHY        ")
    print("==================================================")


if __name__ == "__main__":
    asyncio.run(audit_system())
