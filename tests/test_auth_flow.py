import pytest
import requests
import uuid
import os

BASE_URL = os.environ.get("BASE_URL", "http://localhost:8000")

def test_auth_flow():
    session = requests.Session()
    
    # 1. Register User
    email = f"test_{uuid.uuid4()}@example.com"
    res = session.post(f"{BASE_URL}/auth/register", json={
        "full_name": "Test User",
        "email": email,
        "password": "password123"
    })
    assert res.status_code == 201, f"Register failed: {res.text}"
    
    # 2. Get Verification Token directly from DB (since we are testing locally)
    import sqlite3
    if os.path.exists("insight_circle.db"):
        conn = sqlite3.connect("insight_circle.db")
    else:
        import psycopg
        # We might be using Neon DB. We can use the connection string from .env
        from dotenv import load_dotenv
        load_dotenv()
        conn = psycopg.connect(os.environ["DATABASE_URL"])
    
    cur = conn.cursor()
    # Find user
    cur.execute("SELECT id FROM users WHERE email=%s" if "psycopg" in str(type(conn)) else "SELECT id FROM users WHERE email=?", (email,))
    user_id = cur.fetchone()[0]
    
    # Find token
    cur.execute("UPDATE users SET email_verified=TRUE WHERE id=%s" if "psycopg" in str(type(conn)) else "UPDATE users SET email_verified=1 WHERE id=?", (user_id,))
    conn.commit()
    conn.close()
    
    # 3. Login
    res = session.post(f"{BASE_URL}/auth/login", json={
        "email": email,
        "password": "password123"
    })
    assert res.status_code == 200, f"Login failed: {res.text}"
    
    # 4. Check Auth Me
    res = session.get(f"{BASE_URL}/auth/me")
    assert res.status_code == 200, "Auth Me failed"
    assert res.json()["email"] == email
    
    # 5. Submit Intake Form
    res = session.post(f"{BASE_URL}/applications/submit", json={
        "username": "testuser",
        "q1_curiosity": "Curious",
        "q2_awareness": "Aware",
        "q3_mindset": "Mindset",
        "q4_reflection": "Reflection",
        "q5_focus": "Explorer Path"
    })
    assert res.status_code == 200, f"Intake submission failed: {res.text}"
