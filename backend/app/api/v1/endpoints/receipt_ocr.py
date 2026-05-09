"""AI-Powered Receipt OCR endpoints.

Prefix: /api/v1/receipt-ocr

Stub implementation: simulates OCR extraction from image URL/filename.
Production: integrate Google Cloud Vision API, AWS Textract, or Azure Form Recognizer.
"""
from __future__ import annotations

import hashlib
import re
import uuid
from datetime import datetime, date
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, get_db
from app.models.receipt_ocr import ReceiptOCRRecord, OCRStatus

router = APIRouter()


# ── Schemas ───────────────────────────────────────────────────────────────────

class ReceiptSubmitIn(BaseModel):
    image_url: str
    file_name: Optional[str] = None
    mime_type: Optional[str] = None
    submitted_by: Optional[str] = None


class LinkExpenseIn(BaseModel):
    expense_claim_id: str


# ── Stub OCR Engine ───────────────────────────────────────────────────────────

def _stub_extract(image_url: str, file_name: Optional[str]) -> dict:
    """
    Stub OCR extraction.
    In production: POST image to Google Vision / AWS Textract / Azure Form Recognizer.
    Simulates extraction by parsing URL/filename patterns.
    Returns: {vendor, amount, currency, date, category, confidence, raw_text}
    """
    name = (file_name or image_url).lower()

    # ── Vendor detection from filename ────────────────────────────────────────
    vendor_patterns = {
        "naivas": "Naivas Supermarket",
        "quickmart": "Quickmart",
        "carrefour": "Carrefour Kenya",
        "java": "Java House",
        "kfc": "KFC Kenya",
        "shell": "Shell Petrol Station",
        "total": "TotalEnergies",
        "safaricom": "Safaricom",
        "kplc": "Kenya Power",
        "uber": "Uber",
        "grab": "Grab",
        "airbnb": "Airbnb",
        "hotel": "Hotel",
        "pharmacy": "Pharmacy",
        "chemist": "Chemist",
    }
    vendor = "Unknown Vendor"
    for key, label in vendor_patterns.items():
        if key in name:
            vendor = label
            break

    # ── Amount detection from filename (e.g. receipt_1250.50_naivas.jpg) ─────
    amount_match = re.search(r"(\d{1,6}(?:[.,]\d{2})?)", name)
    amount = float(amount_match.group(1).replace(",", "")) if amount_match else None
    if amount and amount > 999999:
        amount = None  # implausible

    # ── Category from vendor ──────────────────────────────────────────────────
    category_map = {
        "Safaricom": "Airtime/Data",
        "Kenya Power": "Utilities",
        "Shell Petrol Station": "Fuel",
        "TotalEnergies": "Fuel",
        "Naivas Supermarket": "Grocery",
        "Quickmart": "Grocery",
        "Carrefour Kenya": "Grocery",
        "Java House": "Meals & Entertainment",
        "KFC Kenya": "Meals & Entertainment",
        "Hotel": "Accommodation",
        "Airbnb": "Accommodation",
        "Uber": "Transport",
        "Grab": "Transport",
        "Pharmacy": "Medical",
        "Chemist": "Medical",
    }
    category = category_map.get(vendor, "Other")

    # Confidence: higher if amount found, higher if vendor matched
    confidence = 55
    if vendor != "Unknown Vendor":
        confidence += 20
    if amount is not None:
        confidence += 15
    confidence = min(confidence, 92)

    raw_text = (
        f"[OCR STUB — Production: integrate Google Vision/AWS Textract]\n"
        f"Vendor: {vendor}\n"
        f"Amount: KES {amount or '?'}\n"
        f"Date: {date.today().isoformat()}\n"
        f"Category: {category}\n"
        f"Extracted from: {image_url}"
    )

    return {
        "vendor": vendor,
        "amount": amount,
        "currency": "KES",
        "date": date.today().isoformat(),
        "category": category,
        "confidence": confidence,
        "raw_text": raw_text,
    }


def _duplicate_hash(vendor: str, amount: Optional[float], extracted_date: str) -> str:
    payload = f"{vendor.lower().strip()}|{amount or ''}|{extracted_date}"
    return hashlib.sha256(payload.encode()).hexdigest()


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post("/", status_code=201)
async def submit_receipt(
    payload: ReceiptSubmitIn,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    Submit receipt image for OCR processing.
    Returns extracted fields + confidence score.
    Checks for duplicate receipts (same vendor + amount + date).
    """
    # Run stub OCR
    extracted = _stub_extract(payload.image_url, payload.file_name)

    # Duplicate detection
    dup_hash = _duplicate_hash(
        extracted["vendor"],
        extracted["amount"],
        extracted["date"],
    )
    dup_r = await db.execute(
        select(ReceiptOCRRecord).where(
            ReceiptOCRRecord.duplicate_hash == dup_hash,
            ReceiptOCRRecord.is_duplicate == False,
        ).limit(1)
    )
    existing = dup_r.scalar_one_or_none()
    is_dup = existing is not None
    dup_id = existing.id if existing else None

    record = ReceiptOCRRecord(
        submitted_by=payload.submitted_by or getattr(current_user, "username", None) or str(current_user.id),
        user_id=str(current_user.id),
        image_url=payload.image_url,
        file_name=payload.file_name,
        mime_type=payload.mime_type,
        extracted_date=extracted["date"],
        extracted_vendor=extracted["vendor"],
        extracted_amount=extracted["amount"],
        extracted_currency=extracted["currency"],
        extracted_category=extracted["category"],
        raw_extracted_text=extracted["raw_text"],
        confidence_score=extracted["confidence"],
        status=OCRStatus.PROCESSED,
        duplicate_hash=dup_hash,
        is_duplicate=is_dup,
        duplicate_of_id=dup_id,
        processed_at=datetime.utcnow(),
        processing_notes=(
            "STUB mode — wire Google Vision/AWS Textract for production OCR."
            + (" | DUPLICATE DETECTED — matches existing record." if is_dup else "")
        ),
    )
    db.add(record)
    await db.commit()
    await db.refresh(record)

    return {
        "id": str(record.id),
        "status": record.status,
        "extracted": {
            "vendor": record.extracted_vendor,
            "amount": float(record.extracted_amount) if record.extracted_amount else None,
            "currency": record.extracted_currency,
            "date": record.extracted_date,
            "category": record.extracted_category,
            "confidence_score": record.confidence_score,
        },
        "is_duplicate": record.is_duplicate,
        "duplicate_of_id": str(record.duplicate_of_id) if record.duplicate_of_id else None,
        "processing_notes": record.processing_notes,
    }


@router.get("/")
async def list_receipts(
    user_id: Optional[str] = None,
    status: Optional[str] = None,
    is_duplicate: Optional[bool] = None,
    limit: int = Query(50, le=200),
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user),
):
    """List OCR receipt records."""
    q = select(ReceiptOCRRecord)
    if user_id:
        q = q.where(ReceiptOCRRecord.user_id == user_id)
    if status:
        q = q.where(ReceiptOCRRecord.status == status)
    if is_duplicate is not None:
        q = q.where(ReceiptOCRRecord.is_duplicate == is_duplicate)
    q = q.order_by(desc(ReceiptOCRRecord.created_at)).limit(limit)
    rows = (await db.execute(q)).scalars().all()
    return [
        {
            "id": str(r.id),
            "file_name": r.file_name,
            "extracted_vendor": r.extracted_vendor,
            "extracted_amount": float(r.extracted_amount) if r.extracted_amount else None,
            "extracted_date": r.extracted_date,
            "extracted_category": r.extracted_category,
            "confidence_score": r.confidence_score,
            "status": r.status,
            "is_duplicate": r.is_duplicate,
            "linked_expense_claim_id": r.linked_expense_claim_id,
            "submitted_by": r.submitted_by,
            "created_at": r.created_at.isoformat() if r.created_at else "",
        }
        for r in rows
    ]


@router.get("/{record_id}")
async def get_receipt(
    record_id: str,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user),
):
    r = await db.execute(select(ReceiptOCRRecord).where(ReceiptOCRRecord.id == uuid.UUID(record_id)))
    rec = r.scalar_one_or_none()
    if not rec:
        raise HTTPException(404, "Receipt OCR record not found")
    return {
        "id": str(rec.id),
        "image_url": rec.image_url,
        "file_name": rec.file_name,
        "extracted_vendor": rec.extracted_vendor,
        "extracted_amount": float(rec.extracted_amount) if rec.extracted_amount else None,
        "extracted_date": rec.extracted_date,
        "extracted_category": rec.extracted_category,
        "extracted_currency": rec.extracted_currency,
        "confidence_score": rec.confidence_score,
        "raw_extracted_text": rec.raw_extracted_text,
        "status": rec.status,
        "is_duplicate": rec.is_duplicate,
        "linked_expense_claim_id": rec.linked_expense_claim_id,
        "processing_notes": rec.processing_notes,
        "created_at": rec.created_at.isoformat() if rec.created_at else "",
    }


@router.post("/{record_id}/link-expense")
async def link_to_expense(
    record_id: str,
    payload: LinkExpenseIn,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user),
):
    """Link an OCR record to an existing expense claim."""
    r = await db.execute(select(ReceiptOCRRecord).where(ReceiptOCRRecord.id == uuid.UUID(record_id)))
    rec = r.scalar_one_or_none()
    if not rec:
        raise HTTPException(404, "Receipt not found")
    rec.linked_expense_claim_id = payload.expense_claim_id
    rec.status = OCRStatus.LINKED
    rec.linked_at = datetime.utcnow()
    await db.commit()
    return {"record_id": record_id, "linked_to": payload.expense_claim_id, "status": "LINKED"}


@router.get("/stats/summary")
async def ocr_stats(db: AsyncSession = Depends(get_db), _=Depends(get_current_user)):
    from sqlalchemy import func
    total_r = await db.execute(select(func.count()).select_from(ReceiptOCRRecord))
    dup_r = await db.execute(
        select(func.count()).select_from(ReceiptOCRRecord).where(ReceiptOCRRecord.is_duplicate == True)
    )
    linked_r = await db.execute(
        select(func.count()).select_from(ReceiptOCRRecord).where(ReceiptOCRRecord.status == OCRStatus.LINKED)
    )
    avg_conf_r = await db.execute(
        select(func.avg(ReceiptOCRRecord.confidence_score)).where(ReceiptOCRRecord.confidence_score.isnot(None))
    )
    return {
        "total_receipts": total_r.scalar() or 0,
        "duplicates_caught": dup_r.scalar() or 0,
        "linked_to_expenses": linked_r.scalar() or 0,
        "avg_confidence_score": round(float(avg_conf_r.scalar()), 1) if avg_conf_r.scalar() else None,
    }
