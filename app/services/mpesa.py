import base64
from datetime import datetime, timedelta, timezone
import json
import logging
import os
import re
from typing import Any, Dict, Optional, Tuple
import uuid

import httpx
from sqlalchemy import desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.models import (
    AuditLog,
    Membership,
    MerchandiseOrder,
    MpesaTransaction,
    PaymentSubmission,
    User,
    utcnow,
)
from app.security import is_production, payment_simulation_allowed
from app.services.membership import check_user_membership

logger = logging.getLogger("mpesa_service")

# --- Constants & Configuration ---
MEMBERSHIP_FEE_KES = 250.0
DARASA_SANDBOX_URL = "https://sandbox.safaricom.co.ke"
DARASA_PRODUCTION_URL = "https://api.safaricom.co.ke"

# In-memory OAuth token cache
_token_cache: Dict[str, Any] = {
    "token": None,
    "expires_at": None,
}


def get_mpesa_env() -> str:
    return os.getenv("MPESA_ENV", "sandbox").strip().lower()


def get_daraja_base_url() -> str:
    env = get_mpesa_env()
    return DARASA_PRODUCTION_URL if env == "production" else DARASA_SANDBOX_URL


def get_callback_token() -> str:
    """Optional shared secret appended to the callback URL registered with Safaricom."""
    return os.getenv("MPESA_CALLBACK_TOKEN", "").strip()


def _with_callback_token(url: str) -> str:
    token = get_callback_token()
    if not token or "token=" in url:
        return url
    sep = "&" if "?" in url else "?"
    return f"{url}{sep}token={token}"


def get_daraja_credentials() -> Dict[str, str]:
    return {
        "env": get_mpesa_env(),
        "consumer_key": os.getenv("MPESA_CONSUMER_KEY", "").strip(),
        "consumer_secret": os.getenv("MPESA_CONSUMER_SECRET", "").strip(),
        "shortcode": os.getenv("MPESA_SHORTCODE", "174379").strip(),
        "passkey": os.getenv(
            "MPESA_PASSKEY",
            "bfb279f9aa9bdbcf158e97dd71a467cd2e0c893059b10f78e6b72ada1ed2c919",
        ).strip(),
        "callback_url": _with_callback_token(
            os.getenv(
                "MPESA_CALLBACK_URL",
                "https://insightcirclepalace.com/api/payments/mpesa/callback",
            ).strip()
        ),
        "transaction_type": os.getenv(
            "MPESA_TRANSACTION_TYPE", "CustomerPayBillOnline"
        ).strip(),
    }


def normalize_phone_number(phone: str) -> str:
    """
    Validates and normalizes Kenyan phone numbers to the official Safaricom 254XXXXXXXXX format.
    Accepts:
    - 07XXXXXXXX -> 2547XXXXXXXX
    - 01XXXXXXXX -> 2541XXXXXXXX
    - +2547XXXXXXXX -> 2547XXXXXXXX
    - +2541XXXXXXXX -> 2541XXXXXXXX
    - 2547XXXXXXXX -> 2547XXXXXXXX
    - 2541XXXXXXXX -> 2541XXXXXXXX
    - 7XXXXXXXX -> 2547XXXXXXXX
    - 1XXXXXXXX -> 2541XXXXXXXX
    """
    if not phone:
        raise ValueError("M-Pesa phone number is required.")

    cleaned = re.sub(r"[\s\-\+\(\)]", "", str(phone).strip())

    if cleaned.startswith("0") and len(cleaned) == 10:
        cleaned = "254" + cleaned[1:]
    elif (cleaned.startswith("7") or cleaned.startswith("1")) and len(cleaned) == 9:
        cleaned = "254" + cleaned
    elif cleaned.startswith("254") and len(cleaned) == 12:
        pass
    else:
        raise ValueError(
            "Invalid phone format. Please enter a valid 10-digit Kenyan number (e.g. 0712345678 or 0112345678)."
        )

    if not (cleaned.startswith("2547") or cleaned.startswith("2541")):
        raise ValueError(
            "M-Pesa STK Push is supported for Safaricom numbers starting with 07 or 01."
        )

    return cleaned


def generate_stk_timestamp() -> str:
    """
    Generates timestamp in East Africa Time (EAT = UTC+3) formatted as YYYYMMDDHHmmss.
    """
    eat_time = datetime.now(timezone(timedelta(hours=3)))
    return eat_time.strftime("%Y%m%d%H%M%S")


def generate_stk_password(shortcode: str, passkey: str, timestamp: str) -> str:
    raw_str = f"{shortcode}{passkey}{timestamp}"
    return base64.b64encode(raw_str.encode("utf-8")).decode("utf-8")


async def get_daraja_access_token() -> Optional[str]:
    """
    Generates or returns cached OAuth bearer token from Safaricom Daraja API.
    """
    global _token_cache
    now = datetime.now(timezone.utc)

    if (
        _token_cache["token"]
        and _token_cache["expires_at"]
        and _token_cache["expires_at"] > now + timedelta(seconds=60)
    ):
        return _token_cache["token"]

    creds = get_daraja_credentials()
    consumer_key = creds["consumer_key"]
    consumer_secret = creds["consumer_secret"]

    if not consumer_key or not consumer_secret:
        logger.info(
            "Daraja credentials not configured in environment. Using sandbox simulation mode."
        )
        return None

    auth_str = f"{consumer_key}:{consumer_secret}"
    b64_auth = base64.b64encode(auth_str.encode("utf-8")).decode("utf-8")

    url = f"{get_daraja_base_url()}/oauth/v1/generate?grant_type=client_credentials"
    headers = {"Authorization": f"Basic {b64_auth}"}

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(url, headers=headers)
            if resp.status_code == 200:
                data = resp.json()
                token = data.get("access_token")
                expires_in = int(data.get("expires_in", 3599))
                _token_cache["token"] = token
                _token_cache["expires_at"] = now + timedelta(seconds=expires_in)
                return token
            else:
                logger.error(
                    f"Failed to fetch Daraja access token: {resp.status_code} - {resp.text}"
                )
                return None
    except Exception as e:
        logger.error(f"Error fetching Daraja access token: {e}")
        return None


async def initiate_stk_push(
    user: Optional[User],
    phone_number: str,
    db: AsyncSession,
    amount: float = MEMBERSHIP_FEE_KES,
    purpose: str = "membership",
    order_number: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Initiates an M-Pesa Express (STK Push) payment request.
    Supports both Membership (KES 250) and Merchandise purchases.
    Saves the initial transaction record in 'initiated' status.
    """
    if purpose == "membership":
        if not user:
            raise ValueError("Authentication required to purchase membership.")
        if float(amount) != MEMBERSHIP_FEE_KES:
            raise ValueError(
                f"Invalid membership amount: KES {amount}. The membership fee is strictly KES {MEMBERSHIP_FEE_KES}."
            )
        mem_status = await check_user_membership(user, db)
        if mem_status.get("has_access") and mem_status.get("status") == "active":
            return {
                "success": True,
                "status": "already_active",
                "checkout_request_id": "ALREADY_ACTIVE",
                "customer_message": "Your membership is already active! You do not need to pay again.",
                "already_active": True,
            }
    elif purpose == "merchandise":
        if float(amount) <= 0:
            raise ValueError("Order total must be greater than zero.")
        if order_number:
            ord_res = await db.execute(
                select(MerchandiseOrder).where(MerchandiseOrder.order_number == order_number)
            )
            order = ord_res.scalars().first()
            if not order:
                raise ValueError(f"Merchandise order '{order_number}' not found.")
            if order.payment_status == "paid":
                return {
                    "success": True,
                    "status": "already_paid",
                    "checkout_request_id": "ALREADY_PAID",
                    "customer_message": f"Order {order_number} is already paid.",
                    "already_paid": True,
                }

    # 3. Validate and normalize phone
    normalized_phone = normalize_phone_number(phone_number)

    # 4. Prepare Daraja STK Push parameters
    creds = get_daraja_credentials()
    timestamp = generate_stk_timestamp()
    password = generate_stk_password(creds["shortcode"], creds["passkey"], timestamp)

    token = await get_daraja_access_token()

    merchant_req_id = None
    checkout_req_id = None
    customer_message = "Your payment request has been sent. Please check your phone."

    if token:
        # Call Safaricom Daraja API
        url = f"{get_daraja_base_url()}/mpesa/stkpush/v1/processrequest"
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }
        payload = {
            "BusinessShortCode": creds["shortcode"],
            "Password": password,
            "Timestamp": timestamp,
            "TransactionType": creds["transaction_type"],
            "Amount": int(amount),
            "PartyA": normalized_phone,
            "PartyB": creds["shortcode"],
            "PhoneNumber": normalized_phone,
            "CallBackURL": creds["callback_url"],
            "AccountReference": (order_number or "ICPalace")[:12],
            "TransactionDesc": ("ICP Merch " + (order_number or ""))[:20] if purpose == "merchandise" else "ICP Membership",
        }

        try:
            async with httpx.AsyncClient(timeout=20.0) as client:
                resp = await client.post(url, json=payload, headers=headers)
                data = resp.json()
                logger.info(f"Daraja STK Push response: {resp.status_code} - {data}")

                response_code = data.get("ResponseCode")
                if response_code == "0":
                    merchant_req_id = data.get("MerchantRequestID")
                    checkout_req_id = data.get("CheckoutRequestID")
                    customer_message = (
                        data.get("CustomerMessage")
                        or "Your payment request has been sent. Please check your phone."
                    )
                else:
                    err_msg = (
                        data.get("errorMessage")
                        or data.get("ResponseDescription")
                        or "Failed to initiate M-Pesa STK push."
                    )
                    raise RuntimeError(f"Daraja API error: {err_msg}")
        except httpx.RequestError as e:
            logger.error(f"Network error contacting Daraja API: {e}")
            raise RuntimeError(
                "Unable to connect to Safaricom Daraja API. Please try again shortly."
            )
    else:
        # Sandbox simulation mode is for local development / CI ONLY. In production a missing
        # Daraja configuration must fail loudly instead of pretending a payment was requested.
        if not payment_simulation_allowed():
            logger.error("M-Pesa Daraja credentials are not configured in production.")
            raise RuntimeError(
                "M-Pesa payments are temporarily unavailable. Please try again later or contact support."
            )
        unique_id = uuid.uuid4().hex[:12].upper()
        merchant_req_id = f"MERCH-SIM-{timestamp}-{unique_id[:6]}"
        checkout_req_id = f"ws_CO_{timestamp}_{unique_id}"
        customer_message = (
            "Your payment request has been sent. Please check your phone."
        )

    # 5. Record transaction in database
    tx = MpesaTransaction(
        user_id=user.id if user else None,
        order_number=order_number,
        purpose=purpose,
        phone_number=normalized_phone,
        amount=amount,
        currency="KES",
        merchant_request_id=merchant_req_id,
        checkout_request_id=checkout_req_id,
        status="initiated",
        result_desc="Payment request initiated, awaiting customer PIN",
        created_at=utcnow(),
        updated_at=utcnow(),
    )
    db.add(tx)
    await db.commit()
    await db.refresh(tx)

    return {
        "success": True,
        "status": "initiated",
        "checkout_request_id": checkout_req_id,
        "merchant_request_id": merchant_req_id,
        "customer_message": customer_message,
        "phone_number": normalized_phone,
        "amount": amount,
    }


async def query_stk_status(checkout_request_id: str) -> Optional[Dict[str, Any]]:
    """Ask Safaricom directly whether an STK Push succeeded (Daraja 'STK Push Query').

    Daraja callbacks are not signed, so anyone who knows a CheckoutRequestID could POST a fake
    "success" callback. We therefore never trust the callback body alone: the real result is
    confirmed with Safaricom before any membership or order is activated.
    Returns the parsed JSON response, or None when it cannot be determined.
    """
    token = await get_daraja_access_token()
    if not token:
        return None
    creds = get_daraja_credentials()
    timestamp = generate_stk_timestamp()
    payload = {
        "BusinessShortCode": creds["shortcode"],
        "Password": generate_stk_password(creds["shortcode"], creds["passkey"], timestamp),
        "Timestamp": timestamp,
        "CheckoutRequestID": checkout_request_id,
    }
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(
                f"{get_daraja_base_url()}/mpesa/stkpushquery/v1/query",
                json=payload,
                headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            )
            return resp.json()
    except Exception as e:
        logger.error(f"STK query failed for {checkout_request_id}: {e}")
        return None


async def process_stk_callback(
    callback_data: Dict[str, Any],
    db: AsyncSession,
    skip_verification: bool = False,
) -> Dict[str, Any]:
    """
    Securely processes Daraja STK Push callback.
    - Matches expected amount of KES 250.
    - Prevents duplicate callback processing (idempotent).
    - Prevents one receipt from activating multiple accounts.
    - Automatically activates membership and registers payment submission upon success.
    """
    logger.info(f"Processing M-Pesa callback: {json.dumps(callback_data)}")

    body = callback_data.get("Body", {})
    stk_callback = body.get("stkCallback", {})

    merchant_req_id = stk_callback.get("MerchantRequestID")
    checkout_req_id = stk_callback.get("CheckoutRequestID")
    result_code = stk_callback.get("ResultCode")
    result_desc = stk_callback.get("ResultDesc", "")
    metadata = stk_callback.get("CallbackMetadata", {})

    if not checkout_req_id:
        logger.warning("Callback received without CheckoutRequestID")
        return {"ResultCode": 1, "ResultDesc": "Missing CheckoutRequestID"}

    # Find the corresponding transaction
    stmt = select(MpesaTransaction).where(
        MpesaTransaction.checkout_request_id == checkout_req_id
    )
    res = await db.execute(stmt)
    tx = res.scalars().first()

    if not tx:
        logger.error(
            f"Transaction with CheckoutRequestID {checkout_req_id} not found."
        )
        return {"ResultCode": 0, "ResultDesc": "Accepted"}

    # Idempotency check: prevent duplicate callback execution
    if tx.status == "successful":
        logger.info(
            f"Transaction {checkout_req_id} has already been verified and processed. Skipping duplicate."
        )
        return {"ResultCode": 0, "ResultDesc": "Already processed"}

    # A "success" callback is only honoured after Safaricom confirms it (see query_stk_status).
    if result_code == 0 and not skip_verification:
        creds = get_daraja_credentials()
        if creds["consumer_key"] and creds["consumer_secret"]:
            confirmation = await query_stk_status(checkout_req_id)
            if not confirmation or str(confirmation.get("ResultCode")) != "0":
                logger.warning(
                    f"Success callback for {checkout_req_id} NOT confirmed by Safaricom "
                    f"(query response: {confirmation}). Leaving transaction unchanged."
                )
                return {"ResultCode": 0, "ResultDesc": "Accepted"}
        elif is_production():
            logger.error(
                f"Cannot verify callback for {checkout_req_id}: Daraja credentials missing in production."
            )
            return {"ResultCode": 0, "ResultDesc": "Accepted"}

    now = utcnow()
    tx.raw_callback = json.dumps(callback_data)
    tx.result_code = result_code
    tx.result_desc = result_desc
    tx.updated_at = now

    # Check ResultCode (0 = Success)
    if result_code == 0:
        # Extract metadata items
        items = metadata.get("Item", [])
        meta_dict = {}
        for item in items:
            name = item.get("Name")
            val = item.get("Value")
            if name:
                meta_dict[name] = val

        amount_paid = float(meta_dict.get("Amount") or tx.amount or MEMBERSHIP_FEE_KES)
        receipt_num = str(meta_dict.get("MpesaReceiptNumber", "")).strip().upper()
        phone_val = str(meta_dict.get("PhoneNumber", tx.phone_number))
        tx_date_raw = str(meta_dict.get("TransactionDate", ""))

        # Parse transaction date
        tx_date = None
        if tx_date_raw and len(tx_date_raw) >= 14:
            try:
                tx_date = datetime.strptime(tx_date_raw[:14], "%Y%m%d%H%M%S").replace(
                    tzinfo=timezone(timedelta(hours=3))
                )
            except Exception:
                tx_date = now

        # Validate amount
        expected_amount = tx.amount or (MEMBERSHIP_FEE_KES if tx.purpose == "membership" else 0.0)
        if amount_paid < expected_amount:
            logger.warning(
                f"Amount mismatch for {checkout_req_id}: expected {expected_amount}, got {amount_paid}"
            )
            tx.status = "failed"
            tx.result_desc = f"Payment amount KES {amount_paid} is less than required fee of KES {expected_amount}."
            await db.commit()
            return {"ResultCode": 0, "ResultDesc": "Amount mismatch"}

        # Prevent duplicate receipt usage across different accounts
        if receipt_num:
            receipt_check = await db.execute(
                select(MpesaTransaction).where(
                    MpesaTransaction.mpesa_receipt_number == receipt_num,
                    MpesaTransaction.id != tx.id,
                    MpesaTransaction.status == "successful",
                )
            )
            if receipt_check.scalars().first():
                logger.warning(
                    f"Receipt {receipt_num} has already activated another membership."
                )
                tx.status = "failed"
                tx.result_desc = f"M-Pesa receipt {receipt_num} has already been claimed."
                await db.commit()
                return {"ResultCode": 0, "ResultDesc": "Duplicate receipt"}

        # Mark transaction as successful
        tx.status = "successful"
        tx.mpesa_receipt_number = receipt_num or f"MP{now.strftime('%y%m%d%H%M%S')}"
        tx.amount = amount_paid
        tx.transaction_date = tx_date or now

        # Check if transaction is for merchandise order
        if tx.purpose == "merchandise" and tx.order_number:
            ord_res = await db.execute(
                select(MerchandiseOrder).where(MerchandiseOrder.order_number == tx.order_number)
            )
            order = ord_res.scalars().first()
            if order:
                order.payment_status = "paid"
                order.payment_method = "mpesa"
                order.payment_reference = tx.mpesa_receipt_number
                order.status = "confirmed"
                order.updated_at = now

                audit = AuditLog(
                    id=str(uuid.uuid4()),
                    admin_id=order.id,
                    action="merchandise_order_paid_mpesa",
                    target_resource="merchandise_orders",
                    target_id=order.id,
                    details=f"Order {order.order_number} marked as paid via M-Pesa receipt {tx.mpesa_receipt_number}",
                    created_at=now,
                )
                db.add(audit)
            await db.commit()
            logger.info(f"Merchandise order {tx.order_number} marked paid via M-Pesa receipt {tx.mpesa_receipt_number}")
            return {"ResultCode": 0, "ResultDesc": "Merchandise order paid successfully"}

        # 1. Activate User Membership
        user_res = await db.execute(select(User).where(User.id == tx.user_id))
        target_user = user_res.scalars().first()

        mem_res = await db.execute(
            select(Membership)
            .where(Membership.user_id == tx.user_id)
            .order_by(desc(Membership.created_at))
        )
        existing_mem = mem_res.scalars().first()

        if not existing_mem or existing_mem.status in ["expired", "revoked", "rejected"]:
            membership = Membership(
                user_id=tx.user_id,
                status="active",
                fee_paid=amount_paid,
                currency="KES",
                activated_at=now,
                expires_at=None,  # No forced expiry per ICP policy
                notes=f"Activated via M-Pesa STK Push ({tx.mpesa_receipt_number})",
                created_at=now,
                updated_at=now,
            )
            db.add(membership)
            await db.flush()
            membership_id = membership.id
        else:
            existing_mem.status = "active"
            if not existing_mem.activated_at:
                existing_mem.activated_at = now
            existing_mem.expires_at = None
            existing_mem.fee_paid = amount_paid
            existing_mem.currency = "KES"
            existing_mem.notes = f"Activated via M-Pesa STK Push ({tx.mpesa_receipt_number})"
            existing_mem.updated_at = now
            membership_id = existing_mem.id

        # 2. Record PaymentSubmission for audit and administrative payment history
        pay_res = await db.execute(
            select(PaymentSubmission).where(
                PaymentSubmission.transaction_reference == tx.mpesa_receipt_number
            )
        )
        existing_pay = pay_res.scalars().first()
        if not existing_pay:
            pay_sub = PaymentSubmission(
                user_id=tx.user_id,
                membership_id=membership_id,
                transaction_reference=tx.mpesa_receipt_number,
                payment_method="mpesa",
                amount=amount_paid,
                currency="KES",
                payer_name=target_user.full_name if target_user else "M-Pesa Member",
                payer_phone=tx.phone_number,
                status="approved",
                submitted_at=now,
                verified_at=now,
                admin_notes=f"Automated verification via Daraja STK Push (CheckoutRequestID: {checkout_req_id})",
            )
            db.add(pay_sub)

        # 3. Create Audit Log
        audit = AuditLog(
            admin_id=tx.user_id,
            action="M-Pesa STK Payment Verified & Membership Activated",
            target_resource="Membership",
            target_id=membership_id,
            details=(
                f"STK Push payment {tx.mpesa_receipt_number} of KES {amount_paid} verified for user {tx.user_id}. "
                f"Membership activated successfully without expiration."
            ),
            created_at=now,
        )
        db.add(audit)
        await db.commit()

        logger.info(
            f"Successfully activated membership for user {tx.user_id} via receipt {tx.mpesa_receipt_number}"
        )
        return {"ResultCode": 0, "ResultDesc": "Payment processed and membership activated"}

    else:
        # Failure or cancellation
        if result_code == 1032:
            tx.status = "cancelled"
            tx.result_desc = "Payment was cancelled on phone by user."
        elif result_code == 1037:
            tx.status = "failed"
            tx.result_desc = "Payment timed out waiting for customer PIN."
        else:
            tx.status = "failed"
            tx.result_desc = result_desc or f"Payment failed with code {result_code}."

        await db.commit()
        logger.info(f"M-Pesa STK Push {checkout_req_id} marked as {tx.status}: {tx.result_desc}")
        return {"ResultCode": 0, "ResultDesc": "Failure recorded"}


async def get_mpesa_status(
    checkout_request_id: str,
    user_id: Optional[str],
    db: AsyncSession,
) -> Dict[str, Any]:
    """
    Returns real-time status of an M-Pesa transaction for frontend polling.
    """
    stmt = select(MpesaTransaction).where(
        MpesaTransaction.checkout_request_id == checkout_request_id
    )
    res = await db.execute(stmt)
    tx = res.scalars().first()

    if not tx:
        return {
            "status": "not_found",
            "checkout_request_id": checkout_request_id,
            "has_access": False,
            "membership_status": "unpaid",
            "message": "Transaction reference not found.",
        }

    # For merchandise orders, allow lookup without strict user ownership
    if tx.purpose == "merchandise":
        is_paid = (tx.status == "successful")
        msg = "Payment confirmed! Your order is being processed." if is_paid else (
            "Payment cancelled." if tx.status == "cancelled" else (
                "Payment failed." if tx.status == "failed" else "Awaiting M-Pesa PIN confirmation..."
            )
        )
        return {
            "checkout_request_id": checkout_request_id,
            "status": tx.status,
            "is_paid": is_paid,
            "order_number": tx.order_number,
            "receipt_number": tx.mpesa_receipt_number,
            "amount": tx.amount,
            "currency": tx.currency,
            "customer_message": msg,
        }

    # Verify user ownership for membership
    if tx.user_id and tx.user_id != user_id:
        return {
            "status": "unauthorized",
            "checkout_request_id": checkout_request_id,
            "has_access": False,
            "membership_status": "unpaid",
            "message": "Access denied.",
        }

    user_res = await db.execute(select(User).where(User.id == user_id))
    user = user_res.scalars().first()
    mem_status = await check_user_membership(user, db)

    # Standard user-facing message mapping
    user_message = ""
    if tx.status == "initiated":
        user_message = "Your payment request has been sent. Please check your phone."
    elif tx.status == "pending":
        user_message = (
            "Waiting for M-Pesa confirmation. Please complete the payment on your phone."
        )
    elif tx.status == "successful":
        user_message = (
            "Payment successful! Welcome to Insight Circle Palace. Your membership is now active."
        )
    elif tx.status == "cancelled":
        user_message = "Payment was cancelled on your phone. Please try again."
    elif tx.status == "failed":
        user_message = "Your payment could not be completed. Please try again."

    return {
        "checkout_request_id": tx.checkout_request_id,
        "status": tx.status,
        "phone_number": tx.phone_number,
        "amount": tx.amount,
        "currency": tx.currency,
        "receipt_number": tx.mpesa_receipt_number,
        "result_desc": tx.result_desc,
        "customer_message": user_message,
        "has_access": mem_status.get("has_access", False),
        "membership_status": mem_status.get("status", "none"),
        "created_at": tx.created_at.isoformat() if tx.created_at else None,
        "updated_at": tx.updated_at.isoformat() if tx.updated_at else None,
    }


async def simulate_mock_callback(
    checkout_request_id: str,
    db: AsyncSession,
    success: bool = True,
    mock_receipt: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Simulation utility for local testing and automated sandbox tests.
    Disabled in production: it would let anyone mark any payment as paid.
    """
    if not payment_simulation_allowed():
        raise RuntimeError("Payment simulation is disabled in production.")

    stmt = select(MpesaTransaction).where(
        MpesaTransaction.checkout_request_id == checkout_request_id
    )
    res = await db.execute(stmt)
    tx = res.scalars().first()

    if not tx:
        raise ValueError(f"Transaction {checkout_request_id} not found")

    receipt = mock_receipt or f"SIM{uuid.uuid4().hex[:8].upper()}"

    if success:
        mock_payload = {
            "Body": {
                "stkCallback": {
                    "MerchantRequestID": tx.merchant_request_id or "MERCH-SIM",
                    "CheckoutRequestID": tx.checkout_request_id,
                    "ResultCode": 0,
                    "ResultDesc": "The service request is processed successfully.",
                    "CallbackMetadata": {
                        "Item": [
                            {"Name": "Amount", "Value": tx.amount},
                            {"Name": "MpesaReceiptNumber", "Value": receipt},
                            {"Name": "Balance"},
                            {"Name": "TransactionDate", "Value": int(datetime.now().strftime("%Y%m%d%H%M%S"))},
                            {"Name": "PhoneNumber", "Value": int(tx.phone_number)},
                        ]
                    },
                }
            }
        }
    else:
        mock_payload = {
            "Body": {
                "stkCallback": {
                    "MerchantRequestID": tx.merchant_request_id or "MERCH-SIM",
                    "CheckoutRequestID": tx.checkout_request_id,
                    "ResultCode": 1032,
                    "ResultDesc": "Request cancelled by user.",
                }
            }
        }

    return await process_stk_callback(mock_payload, db, skip_verification=True)

