import csv
import io
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy import desc, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.auth import get_current_admin, get_optional_user
from app.database import get_db
from app.models import MerchandiseOrder, User, utcnow
from app.schemas import (MerchandiseItemOut, MerchandiseOrderCreate,
                         MerchandiseOrderOut, MerchandiseOrderUpdate)

router = APIRouter(prefix="/api/merchandise", tags=["merchandise"])
admin_merchandise_router = APIRouter(
    prefix="/api/admin/merchandise", tags=["admin-merchandise"]
)
limiter = Limiter(key_func=get_remote_address)

# Official ICP Payment & Support Details
PAYMENT_CONFIG = {
    "mpesa_till_number": "3491023",
    "mpesa_till_name": "Insight Circle Palace",
    "mpesa_paybill_business_no": "522522",
    "mpesa_paybill_account_no": "1314902847",
    "whatsapp_phone": "254768371417",
    "display_phone": "+254 768 371 417",
    "support_email": "Insightcirclepalace@gmail.com",
    "currency": "KES"
}

# The 11 Official Merchandise Items exactly matching specifications
MERCHANDISE_CATALOG: List[Dict[str, Any]] = [
    {
        "id": "tumbler",
        "name": "Insulated Tumbler / Travel Cup",
        "category": "Drinkware & Stationery",
        "price_min": 1100.0,
        "price_max": 1100.0,
        "price_display": "KSh 1,100",
        "description": "Double-wall stainless steel thermal tumbler with gold laser-engraved ICP seal. Keeps drinks hot for 12 hours and chilled for 24 hours.",
        "image": "/static/assets/merchandise/tumbler.jpg",
        "webp_image": "/static/assets/merchandise/tumbler.webp",
        "badge": "Popular Drinkware",
        "variants": [
            {"id": "standard", "name": "500ml Pro Thermal Travel Cup", "price": 1100.0}
        ],
        "colors": ["Midnight Navy", "Matte Black", "Stainless Silver"],
        "sizes": None
    },
    {
        "id": "round_neck_tshirt",
        "name": "Round-neck T-shirt",
        "category": "Apparel",
        "price_min": 750.0,
        "price_max": 750.0,
        "price_display": "KSh 750",
        "description": "Ultra-comfortable breathable combed cotton crewneck t-shirt featuring the signature circular Insight Circle Palace gold crest.",
        "image": "/static/assets/merchandise/tshirt.jpg",
        "webp_image": "/static/assets/merchandise/tshirt.webp",
        "badge": "Everyday Essential",
        "variants": [
            {"id": "standard", "name": "Premium Combed Cotton (200 GSM)", "price": 750.0}
        ],
        "colors": ["Classic White", "Midnight Navy", "Pitch Black"],
        "sizes": ["S", "M", "L", "XL", "XXL"]
    },
    {
        "id": "hoodie",
        "name": "Hoodie",
        "category": "Apparel",
        "price_min": 2500.0,
        "price_max": 2500.0,
        "price_display": "KSh 2,500",
        "description": "Luxury heavyweight fleece pullover hoodie with brushed interior, kangaroo pocket, braided white drawstrings, and radiant metallic gold ICP chest embroidery.",
        "image": "/static/assets/merchandise/hoodie.jpg",
        "webp_image": "/static/assets/merchandise/hoodie.webp",
        "badge": "Member Signature",
        "variants": [
            {"id": "standard", "name": "Signature Heavyweight Fleece Hoodie", "price": 2500.0}
        ],
        "colors": ["Midnight Navy", "Deep Black", "Heather Grey"],
        "sizes": ["S", "M", "L", "XL", "XXL"]
    },
    {
        "id": "sweatshirt",
        "name": "Sweatshirt",
        "category": "Apparel",
        "price_min": 1500.0,
        "price_max": 1500.0,
        "price_display": "KSh 1,500",
        "description": "Comfortable French terry crewneck sweatshirt with ribbed cuffs and hem, sporting the gold-embossed ICP emblem across the chest.",
        "image": "/static/assets/merchandise/sweatshirt.jpg",
        "webp_image": "/static/assets/merchandise/sweatshirt.webp",
        "badge": "Core Collection",
        "variants": [
            {"id": "standard", "name": "Classic French Terry Sweatshirt", "price": 1500.0}
        ],
        "colors": ["Midnight Navy", "Oatmeal Cream", "Pitch Black"],
        "sizes": ["S", "M", "L", "XL", "XXL"]
    },
    {
        "id": "polo_tshirt",
        "name": "Polo T-shirt",
        "category": "Apparel",
        "price_min": 1000.0,
        "price_max": 1000.0,
        "price_display": "KSh 1,000",
        "description": "Executive piqué knit polo shirt with contrast collar tipping, clean two-button placket, and precision embroidered gold ICP seal on the chest.",
        "image": "/static/assets/merchandise/polo.jpg",
        "webp_image": "/static/assets/merchandise/polo.webp",
        "badge": "Smart Casual",
        "variants": [
            {"id": "standard", "name": "Executive Piqué Knit Polo", "price": 1000.0}
        ],
        "colors": ["Navy with White Trim", "Crisp White", "Deep Black"],
        "sizes": ["S", "M", "L", "XL", "XXL"]
    },
    {
        "id": "baseball_cap",
        "name": "Baseball cap",
        "category": "Bags & Accessories",
        "price_min": 500.0,
        "price_max": 500.0,
        "price_display": "KSh 500",
        "description": "Structured 6-panel heavy cotton twill cap with curved visor, adjustable antique brass buckle strap, and 3D metallic gold embroidered ICP insignia.",
        "image": "/static/assets/merchandise/cap.jpg",
        "webp_image": "/static/assets/merchandise/cap.webp",
        "badge": "Street Style",
        "variants": [
            {"id": "standard", "name": "Structured 6-Panel Twill Cap", "price": 500.0}
        ],
        "colors": ["Pitch Black", "Midnight Navy", "Stone Cream"],
        "sizes": ["One Size (Adjustable)"]
    },
    {
        "id": "canvas_tote_bag",
        "name": "Canvas tote bag",
        "category": "Bags & Accessories",
        "price_min": 500.0,
        "price_max": 500.0,
        "price_display": "KSh 500",
        "description": "Heavy-duty 12oz natural organic canvas tote bag with reinforced cross-stitched handles and radiant gold screen-printed ICP emblem. Roomy and durable.",
        "image": "/static/assets/merchandise/tote.jpg",
        "webp_image": "/static/assets/merchandise/tote.webp",
        "badge": "Eco Friendly",
        "variants": [
            {"id": "standard", "name": "Heavyweight 12oz Canvas Tote", "price": 500.0}
        ],
        "colors": ["Natural Cream / Ecru", "Midnight Navy"],
        "sizes": ["Standard (38cm x 42cm)"]
    },
    {
        "id": "black_drawstring_bag",
        "name": "Black drawstring bag",
        "category": "Bags & Accessories",
        "price_min": 700.0,
        "price_max": 700.0,
        "price_display": "KSh 700",
        "description": "Water-resistant matte black nylon cinch backpack with thick braided cords and luminous gold ICP insignia. Perfect for daily active commute and sessions.",
        "image": "/static/assets/merchandise/drawstring.jpg",
        "webp_image": "/static/assets/merchandise/drawstring.webp",
        "badge": "Active Utility",
        "variants": [
            {"id": "standard", "name": "Water-Resistant Cinch Backpack", "price": 700.0}
        ],
        "colors": ["Matte Black"],
        "sizes": ["Standard (35cm x 45cm)"]
    },
    {
        "id": "notebook_pen",
        "name": "Notebook + pen",
        "category": "Drinkware & Stationery",
        "price_min": 700.0,
        "price_max": 700.0,
        "price_display": "KSh 700",
        "description": "Executive hardcover faux-leather journal with ribbon bookmark, 192 bleed-resistant ivory ruled pages, paired with a weighted twist-action gold ICP ballpoint pen.",
        "image": "/static/assets/merchandise/notebook.jpg",
        "webp_image": "/static/assets/merchandise/notebook.webp",
        "badge": "Fellowship Set",
        "variants": [
            {"id": "standard", "name": "Executive Journal + Gold Metal Pen Set", "price": 700.0}
        ],
        "colors": ["Midnight Navy & Gold", "Classic Black & Gold"],
        "sizes": ["A5 (148 x 210 mm)"]
    },
    {
        "id": "keychain",
        "name": "Keychain",
        "category": "Bags & Accessories",
        "price_min": 300.0,
        "price_max": 300.0,
        "price_display": "KSh 300",
        "description": "High-polish commemorative keepsake keychain featuring the circular Insight Circle Palace crest with reinforced key loop.",
        "image": "/static/assets/merchandise/keychain.jpg",
        "webp_image": "/static/assets/merchandise/keychain.webp",
        "badge": "Keepsake",
        "variants": [
            {"id": "standard", "name": "Heavy Gold-Plated Metallic Medallion", "price": 300.0}
        ],
        "colors": ["Gold & Navy", "All-Gold Mirror"],
        "sizes": None
    },
    {
        "id": "woven_handkerchief",
        "name": "Woven handkerchief",
        "category": "Bags & Accessories",
        "price_min": 100.0,
        "price_max": 100.0,
        "price_display": "KSh 100",
        "description": "100% fine cotton woven pocket square handkerchief with hand-rolled borders and embroidered woven ICP authenticity badge.",
        "image": "/static/assets/merchandise/handkerchief.jpg",
        "webp_image": "/static/assets/merchandise/handkerchief.webp",
        "badge": "Heritage Pocket",
        "variants": [
            {"id": "standard", "name": "100% Cotton Woven Pocket Handkerchief", "price": 100.0}
        ],
        "colors": ["Navy Windowpane Plaid", "Pure White with Gold Border"],
        "sizes": ["40cm x 40cm"]
    }
]

# Quick lookup dictionary by product ID
CATALOG_BY_ID = {item["id"]: item for item in MERCHANDISE_CATALOG}


def _find_product(product_id: str) -> Optional[Dict[str, Any]]:
    # Case-insensitive or slug lookup
    pid = product_id.strip().lower().replace("-", "_")
    return CATALOG_BY_ID.get(pid)


def _generate_order_number() -> str:
    now = datetime.now(timezone.utc)
    token = uuid.uuid4().hex[:5].upper()
    return f"ICP-ORD-{now.strftime('%y%m')}-{token}"


# --- Public Endpoints ---

@router.get("/catalog")
async def get_merchandise_catalog():
    """Returns the full official ICP merchandise collection."""
    return {
        "catalog": MERCHANDISE_CATALOG,
        "categories": [
            "All Items",
            "Apparel",
            "Bags & Accessories",
            "Drinkware & Stationery"
        ],
        "payment_config": PAYMENT_CONFIG,
        "total_items": len(MERCHANDISE_CATALOG)
    }


@router.get("/catalog/{product_id}")
async def get_merchandise_item(product_id: str):
    """Returns a single merchandise item by ID with full variants."""
    product = _find_product(product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found.")
    return {"product": product, "payment_config": PAYMENT_CONFIG}


@router.post("/orders", status_code=201)
@limiter.limit("15/minute")
async def place_merchandise_order(
    request: Request,
    order_in: MerchandiseOrderCreate,
    db: AsyncSession = Depends(get_db)
):
    """
    Submits a merchandise order from the pop-up or dedicated catalogue page.
    Validates variants, sizes, quantities, and calculates the official unit & total price.
    Returns the generated order reference, M-Pesa instructions, and WhatsApp confirmation link.
    """
    clean_name = (order_in.customer_name or order_in.full_name or "").strip()
    clean_phone = (order_in.customer_phone or order_in.phone or "").strip()
    clean_email = (str(order_in.customer_email or order_in.email).strip().lower()) if (order_in.customer_email or order_in.email) else None
    clean_fulfillment = order_in.fulfillment_type.strip().lower()

    if len(clean_name) < 2:
        raise HTTPException(status_code=400, detail="Please provide a valid full name.")
    if len(clean_phone) < 7:
        raise HTTPException(status_code=400, detail="Please provide a valid phone number.")

    product = _find_product(order_in.product_id)
    if not product:
        raise HTTPException(status_code=404, detail=f"Product '{order_in.product_id}' not found in catalog.")

    # Determine variant and unit price
    selected_variant_id = None
    selected_variant_name = None
    unit_price = product["price_min"]

    if product["variants"]:
        # Find matching variant
        matched_variant = None
        if order_in.variant_id:
            for v in product["variants"]:
                if v["id"].lower() == order_in.variant_id.strip().lower():
                    matched_variant = v
                    break
        elif order_in.variant_name:
            for v in product["variants"]:
                if v["name"].lower() == order_in.variant_name.strip().lower():
                    matched_variant = v
                    break

        if not matched_variant:
            # Default to first variant if not explicitly given
            matched_variant = product["variants"][0]

        selected_variant_id = matched_variant["id"]
        selected_variant_name = matched_variant["name"]
        unit_price = float(matched_variant["price"])

    # Validate size for apparel
    selected_size = order_in.size.strip() if order_in.size else None
    if product.get("sizes"):
        if not selected_size or selected_size not in product["sizes"]:
            # Pick default size if apparel
            selected_size = selected_size or product["sizes"][0]

    # Validate color
    selected_color = order_in.color.strip() if order_in.color else None
    if product.get("colors") and not selected_color:
        selected_color = product["colors"][0]

    # Delivery address optional (no delivery location required)
    delivery_address = (order_in.delivery_address or order_in.delivery_location or "").strip() or None

    quantity = max(1, min(order_in.quantity, 50))
    total_price = round(unit_price * quantity, 2)
    order_number = _generate_order_number()

    # Create Order in DB
    order = MerchandiseOrder(
        order_number=order_number,
        full_name=clean_name,
        phone=clean_phone,
        email=clean_email,
        product_id=product["id"],
        product_name=product["name"],
        variant_id=selected_variant_id,
        variant_name=selected_variant_name,
        size=selected_size,
        color=selected_color,
        quantity=quantity,
        unit_price=unit_price,
        total_price=total_price,
        currency="KES",
        fulfillment_type=clean_fulfillment or "direct",
        delivery_location=delivery_address,
        notes=(order_in.notes or "").strip() or None,
        status="pending",
        payment_status="unpaid",
        payment_method="whatsapp",
        payment_reference=None,
        admin_notes=None
    )

    db.add(order)
    await db.commit()
    await db.refresh(order)

    # Build clean WhatsApp pre-filled booking message (No delivery / location mentions)
    wa_msg = (
        f"Hi Insight Circle Palace! 👋\n"
        f"I would like to book official merchandise:\n\n"
        f"📋 *Booking Ref:* {order_number}\n"
        f"📦 *Item:* {product['name']}\n"
        f"{f'🏷️ *Variant:* {selected_variant_name}' + chr(10) if selected_variant_name and selected_variant_name != 'Standard' else ''}"
        f"{f'📏 *Size:* {selected_size}' + chr(10) if selected_size else ''}"
        f"{f'🎨 *Color:* {selected_color}' + chr(10) if selected_color else ''}"
        f"🔢 *Qty:* {quantity}\n"
        f"💰 *Total:* KSh {total_price:,.0f}\n\n"
        f"👤 *Name:* {clean_name}\n"
        f"📞 *Phone:* {clean_phone}\n\n"
        f"Kindly confirm my booking. Thank you!"
    )
    import urllib.parse
    wa_url = f"https://wa.me/{PAYMENT_CONFIG['whatsapp_phone']}?text={urllib.parse.quote(wa_msg)}"

    return {
        "status": "success",
        "message": "Your merchandise booking has been received! Proceed to WhatsApp to complete your order.",
        "order": {
            "id": order.id,
            "order_number": order.order_number,
            "customer_name": order.customer_name,
            "customer_phone": order.customer_phone,
            "customer_email": order.customer_email,
            "product_id": order.product_id,
            "product_name": order.product_name,
            "variant_name": order.variant_name,
            "size": order.size,
            "color": order.color,
            "quantity": order.quantity,
            "unit_price": order.unit_price,
            "total_price": order.total_price,
            "currency": order.currency,
            "fulfillment_type": order.fulfillment_type,
            "delivery_address": order.delivery_address,
            "notes": order.notes,
            "status": order.status,
            "payment_status": order.payment_status,
            "created_at": order.created_at.isoformat() if order.created_at else None
        },
        "payment_instructions": {
            "method": "M-Pesa (Buy Goods or Paybill)",
            "till_number": PAYMENT_CONFIG["mpesa_till_number"],
            "till_name": PAYMENT_CONFIG["mpesa_till_name"],
            "paybill_business_no": PAYMENT_CONFIG["mpesa_paybill_business_no"],
            "paybill_account_no": PAYMENT_CONFIG["mpesa_paybill_account_no"],
            "amount": total_price,
            "reference": order_number,
            "instructions": f"Go to M-Pesa > Lipa na M-Pesa > Buy Goods and enter Till Number {PAYMENT_CONFIG['mpesa_till_number']} ({PAYMENT_CONFIG['mpesa_till_name']}) or Paybill {PAYMENT_CONFIG['mpesa_paybill_business_no']} Acc {order_number}. Enter Amount KSh {total_price:,.0f}."
        },
        "whatsapp_confirmation_url": wa_url
    }


@router.get("/orders/{order_number}")
async def lookup_order(
    order_number: str,
    phone: Optional[str] = Query(None, description="Last digits or full phone number for privacy"),
    db: AsyncSession = Depends(get_db)
):
    """Lookup order status by reference number."""
    clean_ord = order_number.strip().upper()
    stmt = select(MerchandiseOrder).where(MerchandiseOrder.order_number == clean_ord)
    res = await db.execute(stmt)
    order = res.scalars().first()

    if not order:
        raise HTTPException(status_code=404, detail="Order reference not found.")

    # If phone was provided, verify partial match
    if phone:
        clean_p = phone.strip()[-6:]
        clean_db_p = (order.customer_phone or "").strip()[-6:]
        if clean_p != clean_db_p:
            raise HTTPException(status_code=403, detail="Phone number does not match order record.")

    return {
        "order_number": order.order_number,
        "product_name": order.product_name,
        "variant_name": order.variant_name,
        "size": order.size,
        "color": order.color,
        "quantity": order.quantity,
        "unit_price": order.unit_price,
        "total_price": order.total_price,
        "currency": order.currency,
        "fulfillment_type": order.fulfillment_type,
        "status": order.status,
        "payment_status": order.payment_status,
        "created_at": order.created_at.isoformat() if order.created_at else None
    }


# --- Admin Order Management Endpoints ---

@admin_merchandise_router.get("/orders")
async def list_admin_orders(
    request: Request,
    status: Optional[str] = Query(None),
    payment_status: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db)
):
    """Admin view for managing merchandise customer orders."""
    admin = await get_optional_user(request, db)
    valid_roles = ["admin", "super_admin", "editor", "event_manager", "program_manager"]
    if not admin or admin.role not in valid_roles:
        raise HTTPException(status_code=401, detail="Unauthorized")

    stmt = select(MerchandiseOrder)

    if status and status.lower() != "all":
        stmt = stmt.where(MerchandiseOrder.status == status.lower())
    if payment_status and payment_status.lower() != "all":
        stmt = stmt.where(MerchandiseOrder.payment_status == payment_status.lower())

    if search:
        s = f"%{search.strip()}%"
        stmt = stmt.where(
            (MerchandiseOrder.order_number.ilike(s))
            | (MerchandiseOrder.full_name.ilike(s))
            | (MerchandiseOrder.phone.ilike(s))
            | (MerchandiseOrder.email.ilike(s))
            | (MerchandiseOrder.product_name.ilike(s))
            | (MerchandiseOrder.payment_reference.ilike(s))
        )

    # Count total
    count_stmt = select(func.count()).select_from(stmt.subquery())
    total_count = (await db.execute(count_stmt)).scalar() or 0

    stmt = stmt.order_by(desc(MerchandiseOrder.created_at)).limit(limit).offset(offset)
    res = await db.execute(stmt)
    orders = res.scalars().all()

    return {
        "total": total_count,
        "orders": [
            {
                "id": o.id,
                "order_number": o.order_number,
                "customer_name": o.customer_name,
                "customer_phone": o.customer_phone,
                "customer_email": o.customer_email,
                "product_id": o.product_id,
                "product_name": o.product_name,
                "variant_name": o.variant_name,
                "size": o.size,
                "color": o.color,
                "quantity": o.quantity,
                "unit_price": o.unit_price,
                "total_price": o.total_price,
                "currency": o.currency,
                "fulfillment_type": o.fulfillment_type,
                "delivery_address": o.delivery_address,
                "notes": o.notes,
                "status": o.status,
                "payment_status": o.payment_status,
                "payment_method": o.payment_method,
                "payment_reference": o.payment_reference,
                "admin_notes": o.admin_notes,
                "created_at": o.created_at.isoformat() if o.created_at else None,
                "updated_at": o.updated_at.isoformat() if o.updated_at else None
            }
            for o in orders
        ]
    }


@admin_merchandise_router.patch("/orders/{order_id}")
async def update_admin_order(
    order_id: str,
    update_in: MerchandiseOrderUpdate,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """Admin endpoint to update order status, payment status, or notes."""
    admin = await get_optional_user(request, db)
    valid_roles = ["admin", "super_admin", "editor", "event_manager", "program_manager"]
    if not admin or admin.role not in valid_roles:
        raise HTTPException(status_code=401, detail="Unauthorized")

    stmt = select(MerchandiseOrder).where(MerchandiseOrder.id == order_id)
    res = await db.execute(stmt)
    order = res.scalars().first()

    if not order:
        raise HTTPException(status_code=404, detail="Order not found.")

    if update_in.status is not None:
        order.status = update_in.status
    if update_in.payment_status is not None:
        order.payment_status = update_in.payment_status
    if update_in.payment_reference is not None:
        order.payment_reference = update_in.payment_reference.strip() or None
    if update_in.admin_notes is not None:
        order.admin_notes = update_in.admin_notes.strip() or None

    order.updated_at = utcnow()
    await db.commit()
    await db.refresh(order)

    return {"status": "success", "message": "Order updated successfully."}


@admin_merchandise_router.get("/export")
async def export_orders_csv(
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """Exports all merchandise orders to CSV format for administration."""
    admin = await get_optional_user(request, db)
    valid_roles = ["admin", "super_admin"]
    if not admin or admin.role not in valid_roles:
        raise HTTPException(status_code=401, detail="Unauthorized")

    stmt = select(MerchandiseOrder).order_by(desc(MerchandiseOrder.created_at))
    res = await db.execute(stmt)
    orders = res.scalars().all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "Order Ref", "Date", "Customer Name", "Phone", "Email",
        "Product", "Variant", "Size", "Color", "Quantity",
        "Unit Price (KES)", "Total Price (KES)", "Fulfillment",
        "Address", "Status", "Payment Status", "Payment Ref", "Customer Notes", "Admin Notes"
    ])

    for o in orders:
        writer.writerow([
            o.order_number,
            o.created_at.strftime("%Y-%m-%d %H:%M") if o.created_at else "",
            o.customer_name,
            o.customer_phone,
            o.customer_email or "",
            o.product_name,
            o.variant_name or "",
            o.size or "",
            o.color or "",
            o.quantity,
            o.unit_price,
            o.total_price,
            o.fulfillment_type,
            o.delivery_address or "",
            o.status,
            o.payment_status,
            o.payment_reference or "",
            o.notes or "",
            o.admin_notes or ""
        ])

    csv_data = output.getvalue()
    filename = f"icp_merchandise_orders_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    return Response(
        content=csv_data,
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )
