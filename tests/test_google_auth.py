import pytest
import asyncio
import uuid
from unittest.mock import patch
from httpx import AsyncClient, ASGITransport
from main import app

def test_google_config_endpoint():
    async def _run():
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            response = await ac.get("/auth/google/config")
            assert response.status_code == 200
            data = response.json()
            assert "client_id" in data
            assert "326628685130-e65tfg5ldhpj8vhje2ucufv9q95d8t19" in data["client_id"]
    asyncio.run(_run())

def test_google_auth_new_user_and_existing_user():
    async def _run():
        transport = ASGITransport(app=app)
        test_email = f"google_user_{uuid.uuid4().hex[:8]}@example.com"
        test_name = "Google Auth Tester"
        
        mock_id_info = {
            "email": test_email,
            "name": test_name,
            "picture": "https://example.com/avatar.png",
            "aud": "326628685130-e65tfg5ldhpj8vhje2ucufv9q95d8t19.apps.googleusercontent.com",
            "iss": "https://accounts.google.com"
        }

        # Test 1: New user provisioned via Google Auth
        with patch("google.oauth2.id_token.verify_oauth2_token", return_value=mock_id_info):
            async with AsyncClient(transport=transport, base_url="http://test") as ac:
                response = await ac.post("/auth/google", json={"credential": "mock_valid_google_jwt_token"})
                assert response.status_code == 200, f"Google auth failed: {response.text}"
                data = response.json()
                assert data["message"] == "Logged in successfully"
                assert data["is_new_user"] is True
                assert data["user"]["email"] == test_email
                assert "insight_session" in response.cookies

                # Verify session works for /auth/me
                me_res = await ac.get("/auth/me")
                assert me_res.status_code == 200
                assert me_res.json()["email"] == test_email

        # Test 2: Existing user logging in via Google Auth
        with patch("google.oauth2.id_token.verify_oauth2_token", return_value=mock_id_info):
            async with AsyncClient(transport=transport, base_url="http://test") as ac:
                response = await ac.post("/auth/google", json={"credential": "mock_valid_google_jwt_token"})
                assert response.status_code == 200
                data = response.json()
                assert data["message"] == "Logged in successfully"
                assert data["is_new_user"] is False
                assert data["user"]["email"] == test_email
    asyncio.run(_run())

def test_google_auth_invalid_token():
    async def _run():
        transport = ASGITransport(app=app)
        with patch("google.oauth2.id_token.verify_oauth2_token", side_effect=ValueError("Invalid token")):
            async with AsyncClient(transport=transport, base_url="http://test") as ac:
                response = await ac.post("/auth/google", json={"credential": "invalid_jwt"})
                assert response.status_code == 400
                assert "Invalid Google authentication token" in response.json()["detail"]
    asyncio.run(_run())

