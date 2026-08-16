import uuid
from app import schemas  # noqa: F401 (ensure imports used in app if needed)


def test_auth_flow(client):
    """End-to-end auth flow using TestClient and a real PostgreSQL test DB.

    Assumptions:
    - TEST_DATABASE_URL is set in the environment (CI provides it)
    - send_email is mocked via conftest so no external SMTP calls
    """
    # 1. Register User
    email = f"test_{uuid.uuid4()}@example.com"
    res = client.post("/auth/register", json={
        "full_name": "Test User",
        "email": email,
        "password": "password123"
    })
    assert res.status_code == 201, f"Register failed: {res.text}"

    # 2. Mark user as verified directly in the test DB
    from app.database import engine
    import asyncio

    async def _verify():
        async with engine.begin() as conn:
            # Use textual SQL to find and update the user record
            row = await conn.execute("SELECT id FROM users WHERE email = :email", {"email": email})
            user_id = row.scalar()
            if user_id:
                await conn.execute(
                    "UPDATE users SET email_verified = TRUE WHERE id = :id",
                    {"id": user_id},
                )
    asyncio.run(_verify())

    # 3. Login (TestClient preserves cookies)
    res = client.post("/auth/login", json={"email": email, "password": "password123"})
    assert res.status_code == 200, f"Login failed: {res.text}"

    # 4. Auth Me should return the user
    res = client.get("/auth/me")
    assert res.status_code == 200, f"Auth Me failed: {res.text}"
    assert res.json().get("email") == email

    # 5. Submit Intake Form (authenticated via cookie)
    res = client.post(
        "/applications/submit",
        json={
            "username": "testuser",
            "q1_curiosity": "Curious",
            "q2_awareness": "Aware",
            "q3_mindset": "Mindset",
            "q4_reflection": "Reflection",
            "q5_focus": "Explorer Path",
        },
    )
    assert res.status_code == 200, f"Intake submission failed: {res.text}"
