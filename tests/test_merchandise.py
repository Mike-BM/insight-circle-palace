import asyncio
import os
import sys

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from httpx import ASGITransport, AsyncClient
from app.database import Base, engine
from main import app


def test_merchandise_catalog():
    async def _run():
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            response = await ac.get("/api/merchandise/catalog")
            assert response.status_code == 200
            data = response.json()
            assert "catalog" in data
            assert data["total_items"] == 11
            catalog = data["catalog"]

            items_by_id = {item["id"]: item for item in catalog}

            assert "tumbler" in items_by_id
            assert items_by_id["tumbler"]["price_min"] == 1100.0
            assert items_by_id["tumbler"]["price_max"] == 1100.0

            assert "round_neck_tshirt" in items_by_id
            assert items_by_id["round_neck_tshirt"]["price_min"] == 750.0
            assert items_by_id["round_neck_tshirt"]["price_max"] == 750.0

            assert "hoodie" in items_by_id
            assert items_by_id["hoodie"]["price_min"] == 2500.0

            assert "sweatshirt" in items_by_id
            assert items_by_id["sweatshirt"]["price_min"] == 1500.0

            assert "polo_tshirt" in items_by_id
            assert items_by_id["polo_tshirt"]["price_min"] == 1000.0
            assert items_by_id["polo_tshirt"]["price_max"] == 1000.0

            assert "baseball_cap" in items_by_id
            assert items_by_id["baseball_cap"]["price_min"] == 500.0

            assert "canvas_tote_bag" in items_by_id
            assert items_by_id["canvas_tote_bag"]["price_min"] == 500.0

            assert "black_drawstring_bag" in items_by_id
            assert items_by_id["black_drawstring_bag"]["price_min"] == 700.0

            assert "notebook_pen" in items_by_id
            assert items_by_id["notebook_pen"]["price_min"] == 700.0

            assert "keychain" in items_by_id
            assert items_by_id["keychain"]["price_min"] == 300.0
            assert items_by_id["keychain"]["price_max"] == 300.0

            assert "woven_handkerchief" in items_by_id
            assert items_by_id["woven_handkerchief"]["price_min"] == 100.0

            assert data["payment_config"]["mpesa_till_number"] == "3491023"

    asyncio.run(_run())


def test_place_order_and_lookup():
    async def _run():
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            order_payload = {
                "product_id": "tumbler",
                "quantity": 2,
                "color": "Midnight Navy",
                "customer_name": "Wanjiku Kamau",
                "customer_phone": "+254712345678",
                "customer_email": "wanjiku@example.com",
                "notes": "Please call before dispatching"
            }
            res = await ac.post("/api/merchandise/orders", json=order_payload)
            assert res.status_code == 201
            data = res.json()
            assert data["status"] == "success"
            order = data["order"]
            assert order["unit_price"] == 1100.0
            assert order["total_price"] == 2200.0
            assert order["order_number"].startswith("ICP-ORD-")
            assert "whatsapp_confirmation_url" in data
            assert "payment_instructions" in data

            order_num = order["order_number"]

            lookup_res = await ac.get(f"/api/merchandise/orders/{order_num}?phone=345678")
            assert lookup_res.status_code == 200
            l_data = lookup_res.json()
            assert l_data["order_number"] == order_num
            assert l_data["total_price"] == 2200.0
            assert l_data["status"] == "pending"

    asyncio.run(_run())


def test_order_validation_errors():
    async def _run():
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            bad_payload = {
                "product_id": "hoodie",
                "quantity": 1,
                "customer_name": "T",
                "customer_phone": "+254700000000"
            }
            res = await ac.post("/api/merchandise/orders", json=bad_payload)
            assert res.status_code == 400
            assert "full name" in res.json()["detail"].lower()

            fake_payload = {
                "product_id": "non_existent_space_suit",
                "quantity": 1,
                "customer_name": "Test User",
                "customer_phone": "+254700000000"
            }
            res2 = await ac.post("/api/merchandise/orders", json=fake_payload)
            assert res2.status_code == 404

    asyncio.run(_run())


def test_admin_merchandise_protection_and_management():
    async def _run():
        import uuid
        from sqlalchemy.future import select
        from app.database import AsyncSessionLocal
        from app.models import User

        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as anon_client, \
                   AsyncClient(transport=transport, base_url="http://test") as admin_client:

            # 1. Unauthenticated request to admin endpoint is blocked (401)
            unauth_res = await anon_client.get("/api/admin/merchandise/orders")
            assert unauth_res.status_code == 401

            unauth_export = await anon_client.get("/api/admin/merchandise/export")
            assert unauth_export.status_code == 401

            # 2. Place an order to test management
            place_res = await anon_client.post("/api/merchandise/orders", json={
                "product_id": "baseball_cap",
                "quantity": 1,
                "customer_name": "Admin Test Customer",
                "customer_phone": "+254799999999",
                "fulfillment_type": "pickup"
            })
            assert place_res.status_code == 201
            order_data = place_res.json()["order"]
            order_id = order_data["id"]

            # 3. Create & Login real admin user
            admin_email = f"admin_merch_{uuid.uuid4().hex[:6]}@example.com"
            reg_res = await admin_client.post("/auth/register", json={
                "full_name": "Brian Admin",
                "email": admin_email,
                "password": "Password123!"
            })
            assert reg_res.status_code == 201

            async with AsyncSessionLocal() as session:
                u = (await session.execute(select(User).where(User.email == admin_email))).scalars().first()
                u.email_verified = True
                u.role = "admin"
                await session.commit()

            login_res = await admin_client.post("/auth/login", json={"email": admin_email, "password": "Password123!"})
            assert login_res.status_code == 200

            # 4. Fetch orders as admin
            admin_res = await admin_client.get("/api/admin/merchandise/orders")
            assert admin_res.status_code == 200
            data = admin_res.json()
            assert "orders" in data
            assert data["total"] >= 1

            # 5. Patch order status and payment
            patch_res = await admin_client.patch(
                f"/api/admin/merchandise/orders/{order_id}",
                json={
                    "status": "confirmed",
                    "payment_status": "paid",
                    "payment_reference": "QK12345678",
                    "admin_notes": "Verified by Brian Muema via M-Pesa"
                }
            )
            assert patch_res.status_code == 200
            assert patch_res.json()["status"] == "success"

            # 6. Verify export CSV works
            export_res = await admin_client.get("/api/admin/merchandise/export")
            assert export_res.status_code == 200
            assert "text/csv" in export_res.headers["content-type"]
            csv_text = export_res.text
            assert "Order Ref" in csv_text
            assert "Admin Test Customer" in csv_text

    asyncio.run(_run())

