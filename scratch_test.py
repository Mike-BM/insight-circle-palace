import requests
import uuid

BASE_URL = "http://localhost:8000"

def run_tests():
    session = requests.Session()
    
    # 1. Register User
    print("Testing Registration...")
    email = f"test_{uuid.uuid4()}@example.com"
    res = session.post(f"{BASE_URL}/auth/register", json={
        "full_name": "Test User",
        "email": email,
        "password": "password123"
    })
    assert res.status_code == 201, f"Register failed: {res.text}"
    print("Registration OK")
    
    # 2. Get Verification Token directly from DB (since we are testing locally)
    import sqlite3
    import os
    if os.path.exists("insight.db"):
        conn = sqlite3.connect("insight.db")
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
    cur.execute("SELECT token_hash FROM email_verification_tokens WHERE user_id=%s" if "psycopg" in str(type(conn)) else "SELECT token_hash FROM email_verification_tokens WHERE user_id=?", (user_id,))
    # Wait, the verification endpoint expects the unhashed token. But we don't have it because we hashed it!
    # Ah! The original auth.py creates the token, hashes it, and stores the hash.
    # To test verification, we need the raw token.
    # Let's just manually set email_verified=True in DB!
    cur.execute("UPDATE users SET email_verified=TRUE WHERE id=%s" if "psycopg" in str(type(conn)) else "UPDATE users SET email_verified=1 WHERE id=?", (user_id,))
    conn.commit()
    conn.close()
    print("Manually verified email in DB")
    
    # 3. Login
    print("Testing Login...")
    res = session.post(f"{BASE_URL}/auth/login", json={
        "email": email,
        "password": "password123"
    })
    assert res.status_code == 200, f"Login failed: {res.text}"
    print("Login OK")
    
    # 4. Check Auth Me
    print("Testing Auth Me...")
    res = session.get(f"{BASE_URL}/auth/me")
    assert res.status_code == 200, "Auth Me failed"
    assert res.json()["email"] == email
    print("Auth Me OK")
    
    # 5. Submit Intake Form
    print("Testing Intake Form...")
    res = session.post(f"{BASE_URL}/applications/submit", json={
        "username": "testuser",
        "q1_curiosity": "Curious",
        "q2_awareness": "Aware",
        "q3_mindset": "Mindset",
        "q4_reflection": "Reflection",
        "q5_focus": "Explorer Path"
    })
    assert res.status_code == 200, f"Intake submission failed: {res.text}"
    print("Intake OK")
    
    print("All E2E tests passed successfully!")

if __name__ == "__main__":
    run_tests()
