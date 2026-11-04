import json
import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel
from sqlalchemy import desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload

from app.auth import get_current_admin, get_current_user
from app.database import get_db
from app.models import MpesaTransaction, User
from app.schemas import (
    MpesaSTKPushRequest,
    MpesaSTKPushResponse,
    MpesaStatusResponse,
    MpesaTransactionOut,
)
from app.services.mpesa import (
    MEMBERSHIP_FEE_KES,
    get_mpesa_status,
    initiate_stk_push,
    normalize_phone_number,
    process_stk_callback,
    simulate_mock_callback,
)

logger = logging.getLogger("mpesa_router")

router = APIRouter(prefix="/api/payments/mpesa", tags=["mpesa"])
admin_mpesa_router = APIRouter(prefix="/api/admin/mpesa", tags=["admin-mpesa"])


@router.post("/stkpush")
async def request_mpesa_stk_push(
    payload: MpesaSTKPushRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Initiates an M-Pesa STK Push prompt on the customer's phone for KES 250.
    The customer enters their M-Pesa PIN securely on their device.
    """
    try:
        norm_phone = normalize_phone_number(payload.phone_number)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )

    try:
        result = await initiate_stk_push(
            user=current_user,
            phone_number=norm_phone,
            db=db,
            amount=MEMBERSHIP_FEE_KES,
        )
        return result
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except RuntimeError as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Unexpected error in STK push: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while preparing your M-Pesa payment request.",
        )


@router.post("/callback")
async def mpesa_daraja_callback(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """
    Unauthenticated webhook called by Safaricom Daraja API upon customer entering PIN.
    Safaricom requires a 200 OK response with ResultCode 0.
    """
    try:
        data = await request.json()
    except Exception:
        logger.error("Failed to parse JSON body from Daraja callback")
        return {"ResultCode": 0, "ResultDesc": "Invalid JSON but acknowledged"}

    try:
        res = await process_stk_callback(data, db)
        return res
    except Exception as e:
        logger.error(f"Error handling M-Pesa callback: {e}", exc_info=True)
        return {"ResultCode": 0, "ResultDesc": "Error handled"}


@router.get("/status/{checkout_request_id}")
async def check_mpesa_transaction_status(
    checkout_request_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Real-time status check for an initiated STK push transaction.
    Called by frontend polling every 2-3 seconds until resolved.
    """
    clean_id = checkout_request_id.strip()
    if clean_id == "ALREADY_ACTIVE":
        return {
            "checkout_request_id": "ALREADY_ACTIVE",
            "status": "successful",
            "has_access": True,
            "membership_status": "active",
            "customer_message": "Your membership is active.",
        }

    status_data = await get_mpesa_status(clean_id, current_user.id, db)
    return status_data


class SimulateCallbackPayload(BaseModel):
    checkout_request_id: str
    success: bool = True
    receipt_number: Optional[str] = None


@router.post("/simulate-callback")
async def simulate_callback_endpoint(
    payload: SimulateCallbackPayload,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Testing utility for sandbox and local developer environments.
    Simulates a Safaricom callback for a given checkout_request_id.
    """
    try:
        res = await simulate_mock_callback(
            payload.checkout_request_id,
            db,
            success=payload.success,
            mock_receipt=payload.receipt_number,
        )
        return {
            "status": "simulated",
            "result": res,
            "message": "Mock callback executed successfully.",
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Simulation error: {str(e)}",
        )


# --- Administrator M-Pesa Endpoints ---


@admin_mpesa_router.get("/transactions", response_model=List[MpesaTransactionOut])
async def admin_list_mpesa_transactions(
    status_filter: Optional[str] = Query(None, alias="status"),
    search: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    admin_user: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """
    Lists recent M-Pesa STK push transactions with audit details,
    receipt numbers, phone numbers, timestamps, and customer info.
    """
    stmt = (
        select(MpesaTransaction)
        .options(selectinload(MpesaTransaction.user))
        .order_by(desc(MpesaTransaction.created_at))
        .limit(limit)
    )

    if status_filter and status_filter.lower() != "all":
        stmt = stmt.where(MpesaTransaction.status == status_filter.lower())

    res = await db.execute(stmt)
    records = res.scalars().all()

    out = []
    for r in records:
        user_name = r.user.full_name if r.user else "Unknown"
        user_email = r.user.email if r.user else "Unknown"

        if search:
            s = search.lower().strip()
            name_match = s in user_name.lower()
            email_match = s in user_email.lower()
            phone_match = s in r.phone_number
            ref_match = bool(
                r.mpesa_receipt_number and s in r.mpesa_receipt_number.lower()
            )
            if not (name_match or email_match or phone_match or ref_match):
                continue

        out.append(
            MpesaTransactionOut(
                id=r.id,
                user_id=r.user_id,
                user_name=user_name,
                user_email=user_email,
                phone_number=r.phone_number,
                amount=r.amount,
                currency=r.currency,
                checkout_request_id=r.checkout_request_id,
                merchant_request_id=r.merchant_request_id,
                mpesa_receipt_number=r.mpesa_receipt_number,
                status=r.status,
                result_code=r.result_code,
                result_desc=r.result_desc,
                created_at=r.created_at,
                updated_at=r.updated_at,
            )
        )

    return out

