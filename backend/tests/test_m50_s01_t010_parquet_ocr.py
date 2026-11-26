"""M50.S01.T010 typed Parquet (pyarrow) and business-card OCR (RapidOCR) with review and consent. DB part needs M50_DB=1.

Parquet: typed schema from the ERP table (decimal128, date32, timestamp, bool, masked -> string), metadata, round trip through
the warehouse export (LOCAL_DIR) and a data-sync read; invalid / oversize / not-Parquet input refused.
OCR: a synthetic card picture (drawn here, POVU demo data) is read; fields are suggested, nothing is a contact until the
reviewer confirms with consent; no consent, duplicate e-mail, wrong file type and oversized pictures are refused;
discarding erases the recognised text.
"""
import base64
import io
import os
import uuid
from datetime import date, datetime, timezone
from decimal import Decimal
from types import SimpleNamespace

import pyarrow as pa
import pytest
from fastapi import HTTPException, UploadFile
from PIL import Image, ImageDraw, ImageFont

from app.services import card_ocr_service as ocr
from app.services import data_sync_service as dss
from app.services import parquet_service as pqs
from app.services import warehouse_export_service as wes

DB = pytest.mark.skipif(os.environ.get("M50_DB") != "1", reason="requires the task-owned disposable PostgreSQL")


@pytest.fixture(autouse=True)
async def _dispose_engine():
    yield
    if os.environ.get("M50_DB") == "1":
        from app.db.session import engine
        await engine.dispose()


def _S():
    from sqlalchemy.ext.asyncio import async_sessionmaker
    from app.db.session import engine
    return async_sessionmaker(engine, expire_on_commit=False)()


def card_png(lines, size=(900, 520)) -> bytes:
    img = Image.new("RGB", size, "white")
    d, f, y = ImageDraw.Draw(img), ImageFont.load_default(size=44), 30
    for l in lines:
        d.text((40, y), l, fill="black", font=f)
        y += 80
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


# ── Parquet ──────────────────────────────────────────────────────────────────

ROWS = [{"id": uuid.uuid4(), "invoice_no": "INV-POVU-001", "invoice_date": date(2026, 11, 30), "status": "ISSUED", "total_amount": Decimal("1160.5"),
         "paid_amount": Decimal("0"), "updated_at": datetime(2026, 11, 30, 9, 0, 0)},
        {"id": uuid.uuid4(), "invoice_no": "INV-POVU-002", "invoice_date": date(2026, 12, 1), "status": "PAID", "total_amount": Decimal("99.99"),
         "paid_amount": Decimal("99.99"), "updated_at": datetime(2026, 12, 1, 10, 0, 0, tzinfo=timezone.utc)}]
COLS = ["id", "invoice_no", "invoice_date", "status", "total_amount", "paid_amount", "updated_at"]


def test_typed_parquet_round_trip_with_schema_from_the_erp_table():
    data = wes.serialize(ROWS, COLS, "parquet", "invoices", ("invoice_no",))
    assert data[:4] == b"PAR1"
    rows, info = pqs.read(data)
    types = {c["name"]: c["type"] for c in info["columns"]}
    assert types["invoice_date"] == "date32[day]" and types["total_amount"].startswith("decimal128(16, 4)")
    assert types["updated_at"].startswith("timestamp[us, tz=UTC]") and types["invoice_no"] == "string"      # masked column is text
    assert info["metadata"]["dataset"] == "invoices" and info["metadata"]["masked"] == "invoice_no" and info["rows"] == 2
    assert rows[0]["total_amount"] == Decimal("1160.5000") and rows[0]["invoice_date"] == date(2026, 11, 30)
    assert rows[1]["updated_at"] == datetime(2026, 12, 1, 10, 0, tzinfo=timezone.utc) and rows[0]["id"] == str(ROWS[0]["id"])
    assert pa.types.is_boolean(pqs.dataset_types("customers", ["is_active"])["is_active"])
    assert pa.types.is_int64(pqs.dataset_types("customers", ["payment_terms_days"])["payment_terms_days"])


def test_parquet_refusals():
    with pytest.raises(pqs.ParquetError, match="not a Parquet"):
        pqs.read(b"id,name\n1,x\n")
    with pytest.raises(pqs.ParquetError, match="larger than"):
        pqs.read(b"PAR1" + b"0" * (pqs.MAX_READ_BYTES + 1))
    with pytest.raises(pqs.ParquetError, match="could not be read"):
        pqs.read(b"PAR1" + b"garbage-not-a-footer" + b"PAR1")
    data = wes.serialize(ROWS, COLS, "parquet", "invoices")
    with pytest.raises(pqs.ParquetError, match="rows"):
        pqs.read(data, max_rows=1)
    with pytest.raises(pqs.ParquetError):
        pqs.dataset_types("no_such_table", ["x"])


def test_data_sync_reads_parquet_as_json_safe_rows():
    data = wes.serialize(ROWS, COLS, "parquet", "invoices")
    rows = dss.parse_upload(base64.b64encode(data).decode(), "parquet")
    assert rows[0]["total_amount"] == "1160.5" and rows[0]["invoice_date"] == "2026-11-30"
    import json
    json.dumps(rows)                                                  # storable in the run's input
    with pytest.raises(dss.SyncError):
        dss.parse_upload("not base64 !!", "parquet")
    with pytest.raises(dss.SyncError):
        dss.parse_upload(base64.b64encode(b"hello").decode(), "parquet")


@DB
@pytest.mark.asyncio
async def test_warehouse_export_writes_parquet_files(tmp_path):
    from sqlalchemy import select
    from app.models.master import Product
    from app.models.warehouse_export import ExportJob, ExportRun, ExportTarget
    s = uuid.uuid4().hex[:5].upper()
    async with _S() as db:
        db.add(Product(sku=f"POVU-ALC-{s}", name="POVU AllClean 1 L", category="HOUSEHOLD", selling_price=Decimal("350")))
        t = ExportTarget(name=f"local {s}", kind="LOCAL_DIR", config={"dir": str(tmp_path)}, created_by="t")
        db.add(t)
        await db.flush()
        j = ExportJob(target_id=t.id, dataset="products", file_format="parquet", known_ids=[], schema_cols=[])
        db.add(j)
        await db.commit()
        run = await wes.run_job(db, j)
        assert run.status == "DONE" and run.rows >= 1, run.error
    files = [p for p in tmp_path.rglob("*.parquet")]
    assert files
    rows, info = pqs.read(files[0].read_bytes())
    assert {"sku", "name", "is_active"} <= {c["name"] for c in info["columns"]}
    assert any(r["sku"] == f"POVU-ALC-{s}" and r["is_active"] is True for r in rows)
    types = {c["name"]: c["type"] for c in info["columns"]}
    assert types["is_active"] == "bool" and types["updated_at"].startswith("timestamp")


# ── OCR ──────────────────────────────────────────────────────────────────────

CARD = ["Amani Wekesa", "Sales Manager", "Wekesa Distributors Ltd", "amani.wekesa@povu-demo.test", "+254 712 345 678", "www.povu-demo.test"]


def test_ocr_engine_reads_a_synthetic_card_and_suggests_fields():
    st = ocr.status()
    assert st["available"] is True and "rapidocr" in st["engine"]
    text, lines = ocr.read_text(card_png(CARD))
    assert "amani.wekesa@povu-demo.test" in text and all(l["confidence"] > 0.8 for l in lines)
    f = ocr.suggest(text, lines)
    assert f["email"]["value"] == "amani.wekesa@povu-demo.test" and f["phone"]["value"] == "+254712345678"
    assert f["job_title"]["value"] == "Sales Manager" and f["full_name"]["value"] == "Amani Wekesa" and f["company"]["value"].startswith("Wekesa")
    assert all(0 < v["confidence"] <= 1 for v in f.values())


def test_ocr_refuses_bad_pictures():
    for data, status in ((b"", 413), (b"hello not a picture", 415), (b"\x89PNG\r\n\x1a\n" + b"0" * 50, 415),
                         (b"\xff\xd8\xff" + b"0" * (ocr.MAX_IMAGE_BYTES + 1), 413)):
        with pytest.raises(ocr.OcrError) as e:
            ocr.read_text(data)
        assert e.value.status == status
    big = io.BytesIO()
    Image.new("L", (4000, 3500), 255).save(big, format="PNG")                     # 14 MP of white, small file
    with pytest.raises(ocr.OcrError) as e:
        ocr.read_text(big.getvalue())
    assert e.value.status == 413 and "megapixels" in str(e.value)


async def _persona(db, perms=("crm.edit",)):
    from app.models.user import User
    u = User(username=f"ocr-{uuid.uuid4().hex[:6]}", email=f"ocr-{uuid.uuid4().hex[:6]}@povu-demo.test", full_name="Reviewer", hashed_password="x", is_active=True)
    db.add(u)
    await db.flush()
    plist = [SimpleNamespace(code=c, module=c.split(".")[0], action=c.split(".", 1)[1], is_active=True) for c in perms]
    return SimpleNamespace(id=u.id, username=u.username, email=u.email, full_name="Reviewer", is_superuser=False, access_scopes=[],
                           roles=[SimpleNamespace(name="r", is_active=True, permissions=plist, access_scopes=[])])


@DB
@pytest.mark.asyncio
async def test_card_becomes_a_contact_only_after_review_and_consent():
    from sqlalchemy import select
    from app.api.v1.endpoints import business_card_ocr as api
    from app.models.audit_log import AuditLog
    from app.models.crm import CRMContact
    s = uuid.uuid4().hex[:5]
    email = f"amani.{s}@povu-demo.test"
    async with _S() as db:
        me, other = await _persona(db), await _persona(db)
        await db.commit()
        png = card_png(["Amani Wekesa", "Sales Manager", "Wekesa Distributors Ltd", email, "+254 712 345 678"])
        d = await api.scan(UploadFile(file=io.BytesIO(png), filename="card.png"), db, me)
        assert d["status"] == "DRAFT" and d["fields"]["email"]["value"] == email and "image" not in d
        did = uuid.UUID(d["id"])
        assert (await db.execute(select(CRMContact).where(CRMContact.email == email))).first() is None      # not a contact yet
        # someone else cannot see or confirm my draft
        with pytest.raises(HTTPException) as e:
            await api.confirm(did, api.ConfirmIn(full_name="X", consent=True), db, other)
        assert e.value.status_code == 404
        await db.rollback()
        # no consent -> refused; the reviewed (edited) fields are what is saved
        with pytest.raises(HTTPException) as e:
            await api.confirm(did, api.ConfirmIn(full_name="Amani Wekesa", email=email, consent=False), db, me)
        assert e.value.status_code == 422 and "gave you their card" in e.value.detail
        out = await api.confirm(did, api.ConfirmIn(full_name="Amani W. Wekesa", email=email, phone="+254712345678", job_title="Sales Manager",
                                                   company="Wekesa Distributors Ltd", consent=True), db, me)
        assert out["status"] == "CONFIRMED" and out["consent_at"] and out["contact"]["full_name"] == "Amani W. Wekesa"
        c = (await db.execute(select(CRMContact).where(CRMContact.email == email))).scalar_one()
        assert c.source == "business-card-ocr" and c.owner_user_id == me.id and c.job_title == "Sales Manager"
        ev = (await db.execute(select(AuditLog).where(AuditLog.event_type == "CARD_OCR_CONTACT_CREATED", AuditLog.target_id == str(c.id)))).scalar_one()
        assert ev.details["consent"] is True
        # confirming twice, and a second card with the same e-mail, are refused
        with pytest.raises(HTTPException) as e:
            await api.confirm(did, api.ConfirmIn(full_name="Amani", consent=True), db, me)
        assert e.value.status_code == 409
        await db.rollback()
        d2 = await api.scan(UploadFile(file=io.BytesIO(png), filename="card2.png"), db, me)
        with pytest.raises(HTTPException) as e:
            await api.confirm(uuid.UUID(d2["id"]), api.ConfirmIn(full_name="Amani Wekesa", email=email, consent=True), db, me)
        assert e.value.status_code == 409 and "already exists" in e.value.detail
        await db.rollback()
        # discarding erases the recognised text
        gone = await api.discard(uuid.UUID(d2["id"]), db, me)
        assert gone["status"] == "DISCARDED" and gone["text"] == "" and gone["fields"] == {}
        # a non-picture upload is refused through the API too
        with pytest.raises(HTTPException) as e:
            await api.scan(UploadFile(file=io.BytesIO(b"<script>alert(1)</script>"), filename="x.png"), db, me)
        assert e.value.status_code == 415
        await db.rollback()
