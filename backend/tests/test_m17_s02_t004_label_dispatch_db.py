"""M17.S02.T004 — GS1 print job dispatch to a network printer on disposable PostgreSQL.

A local TCP listener stands in for the printer (raw port-9100 protocol); no physical device.
"""
from __future__ import annotations

import asyncio
import os
import re
from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy import func, select

from app.db.session import AsyncSessionLocal, engine
from app.models.gs1 import (
    BarcodeType, LabelPrinter, LabelPrintJob, LotBarcodeRecord, PrintJobStatus, ProductGS1Config, SSCCPallet,
)
from app.models.master import Product, ProductCategory, UnitOfMeasure
from app.services import gs1_service
from app.services.label_printer_service import PrinterError
from test_label_printer_service import FakePrinter

TASK_DB_ENV = "M17_S02_T004_DISPOSABLE_TEST_DATABASE"
TASK_DB_NAME_ENV = "M17_S02_T004_DISPOSABLE_TEST_DATABASE_NAME"
TASK_DB_PATTERN = re.compile(r"fmcg_m17_s02_t004_[a-f0-9]{24}")

pytestmark = pytest.mark.skipif(os.environ.get(TASK_DB_ENV) != "1", reason="requires the task-owned disposable PostgreSQL")


@pytest_asyncio.fixture(autouse=True)
async def _dispose_engine():
    yield
    await engine.dispose()


@pytest.mark.asyncio
async def test_dispatch_prints_job_marks_records_and_retries_after_failure():
    s = uuid4().hex[:10]
    async with AsyncSessionLocal() as db:
        assert engine.url.host in {"127.0.0.1", "localhost", "::1"} and engine.url.password is None
        assert TASK_DB_PATTERN.fullmatch(os.environ.get(TASK_DB_NAME_ENV, ""))
        assert (await db.execute(select(func.current_database()))).scalar_one() == os.environ[TASK_DB_NAME_ENV]
        product = Product(sku=f"LBL-{s}", name=f"Synthetic juice {s}", category=ProductCategory.BEVERAGE, uom=UnitOfMeasure.PCS)
        db.add(product)
        await db.flush()
        config = ProductGS1Config(product_id=product.id)
        db.add(config)
        await db.flush()
        lot = LotBarcodeRecord(product_config_id=config.id, gtin="06123456789012", lot_number=f"LOT{s}",
                               barcode_type=list(BarcodeType)[0], gs1_ai_string=f"(01)06123456789012(10)LOT{s}")
        pallet = SSCCPallet(sscc_code="1" + s[:8].translate(str.maketrans("abcdef", "123456")).ljust(17, "0")[:17],
                            company_prefix="0614141", serial_reference="123456789", check_digit=7)
        db.add_all([lot, pallet])
        await db.flush()
        job = await gs1_service.create_print_job(db, {"items": [{"lot_barcode_id": lot.id, "copies": 2},
                                                                {"sscc_id": pallet.id, "copies": 1}]})
        dead = LabelPrinter(name=f"Offline {s}", host="127.0.0.1", port=9, protocol="ZPL")
        db.add(dead)
        await db.commit()
        job_id, dead_id, lot_id, pallet_id = job.id, dead.id, lot.id, pallet.id

    async with AsyncSessionLocal() as db:
        with pytest.raises(PrinterError):
            await gs1_service.dispatch_print_job(db, job_id, dead_id, "operator")
        await db.commit()
        failed = await db.get(LabelPrintJob, job_id)
        assert failed.status == PrintJobStatus.FAILED and "Cannot connect" in failed.error_message

    async with FakePrinter() as fake:
        async with AsyncSessionLocal() as db:
            live = LabelPrinter(name=f"Line 1 {s}", host="127.0.0.1", port=fake.port, protocol="ZPL")
            db.add(live)
            await db.commit()
            done = await gs1_service.dispatch_print_job(db, job_id, live.id, "operator")
            await db.commit()
            assert done.status == PrintJobStatus.COMPLETED and done.printer_name == live.name
            assert done.error_message is None and done.printed_by == "operator" and done.printed_at is not None
        for _ in range(50):
            if b"^XZ" in fake.received and fake.received.count(b"^XZ") == 2:
                break
            await asyncio.sleep(0.02)
    zpl = bytes(fake.received).decode()
    assert f"(01)06123456789012(10)LOT{s}" in zpl and "^PQ2" in zpl and "(00)" in zpl

    async with AsyncSessionLocal() as db:
        assert (await db.get(LotBarcodeRecord, lot_id)).is_printed is True
        assert (await db.get(SSCCPallet, pallet_id)).label_printed is True
        with pytest.raises(ValueError, match="COMPLETED"):
            await gs1_service.dispatch_print_job(db, job_id, dead_id, "operator")

    async with AsyncSessionLocal() as db:
        # A job left PRINTING by a crash mid-send is claimable again once stale, not before.
        from datetime import datetime, timedelta, timezone

        from sqlalchemy import update

        stuck = await gs1_service.create_print_job(db, {"items": [{"sscc_id": pallet_id}]})
        await db.commit()
        stuck_id = stuck.id
        await db.execute(update(LabelPrintJob).where(LabelPrintJob.id == stuck_id).values(status=PrintJobStatus.PRINTING))
        await db.commit()
        with pytest.raises(ValueError, match="PRINTING"):
            await gs1_service.dispatch_print_job(db, stuck_id, dead_id, "operator")
        await db.rollback()
        old = datetime.now(timezone.utc) - timedelta(minutes=gs1_service.STALE_PRINTING_MINUTES + 1)
        await db.execute(update(LabelPrintJob).where(LabelPrintJob.id == stuck_id).values(updated_at=old))
        await db.commit()
        with pytest.raises(PrinterError):
            await gs1_service.dispatch_print_job(db, stuck_id, dead_id, "operator")
        await db.commit()
        assert (await db.get(LabelPrintJob, stuck_id)).status == PrintJobStatus.FAILED

    async with AsyncSessionLocal() as db:
        # Browser-print completion path writes the same timestamp columns.
        other = await gs1_service.create_print_job(db, {"items": [{"lot_barcode_id": lot_id}]})
        await db.commit()
        completed = await gs1_service.complete_print_job(db, other.id, "browser")
        await db.commit()
        assert completed.status == PrintJobStatus.COMPLETED
