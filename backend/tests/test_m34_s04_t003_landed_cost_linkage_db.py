"""PostgreSQL linkage-integrity regressions for M34.S04.T003."""
from __future__ import annotations

import importlib.util
import os
import re
from decimal import Decimal
from pathlib import Path
from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy import select, text

from app.db.session import AsyncSessionLocal, engine
from app.models.landed_cost import LandedCostAllocationLine, LandedCostHeader
from app.models.logistics import InternationalShipment, ShipmentPOLink
from app.models.procurement import GRNStatus
from app.schemas.landed_cost import (
    LandedCostGRNLinkCreate,
    LandedCostHeaderCreate,
    LandedCostLineCreate,
)
from app.services import landed_cost_service

_seed_module_spec = importlib.util.spec_from_file_location(
    "m06_three_way_match_seed",
    Path(__file__).with_name("test_m06_s03_t001_three_way_match_db.py"),
)
if _seed_module_spec is None or _seed_module_spec.loader is None:
    raise RuntimeError("Unable to load the established synthetic PO/GRN fixture")
_seed_module = importlib.util.module_from_spec(_seed_module_spec)
_seed_module_spec.loader.exec_module(_seed_module)
_seed_chain = _seed_module._seed_chain

pytestmark = pytest.mark.skipif(
    os.environ.get("M34_S04_T003_DISPOSABLE_TEST_DATABASE") != "1",
    reason="requires the M34.S04.T003 task-owned disposable PostgreSQL database",
)


def _require_task_database() -> str:
    expected = os.environ.get("M34_S04_T003_DISPOSABLE_TEST_DATABASE_NAME")
    url = engine.url
    valid_name = isinstance(expected, str) and re.fullmatch(
        r"fmcg_m34_s04_t003_[a-f0-9]{24}", expected,
    ) is not None
    if not (
        url.drivername in {"postgresql", "postgresql+asyncpg"}
        and url.host in {"127.0.0.1", "localhost", "::1"}
        and url.password is None
        and valid_name
        and url.database == expected
    ):
        pytest.fail(
            "Refusing integration writes: DATABASE_URL must match the exact loopback "
            "M34.S04.T003 disposable database without a password."
        )
    return expected


@pytest_asyncio.fixture(autouse=True)
async def _dispose_engine_after_test():
    yield
    await engine.dispose()


def _cost_line(amount: str = "100") -> LandedCostLineCreate:
    return LandedCostLineCreate(
        cost_type="FREIGHT_LAND",
        description="Synthetic inbound freight",
        amount_fc=Decimal(amount),
        currency_code="KES",
        allocation_method="BY_QUANTITY",
        is_included_in_valuation=True,
    )


@pytest.mark.asyncio
async def test_header_link_uses_canonical_po_grn_snapshots_and_allocates_source():
    expected_database = _require_task_database()
    suffix = uuid4().hex[:16]
    async with AsyncSessionLocal() as db:
        assert (await db.execute(text("SELECT current_database()"))).scalar_one() == expected_database
        _, _, _, _, _, po, _, grn, _, _, _ = await _seed_chain(db, suffix)
        grn.status = GRNStatus.POSTED
        shipment = InternationalShipment(shipment_no=f"M34-T003-SHP-{suffix}")
        db.add(shipment)
        await db.flush()
        db.add(ShipmentPOLink(shipment_id=shipment.id, po_id=po.id))
        await db.commit()

        header = await landed_cost_service.create_header(
            db,
            LandedCostHeaderCreate(
                reference_type="PO",
                shipment_id=shipment.id,
                po_id=po.id,
                currency_code="KES",
                cost_lines=[_cost_line()],
                grn_links=[LandedCostGRNLinkCreate(
                    grn_id=grn.id,
                    grn_no="forged-grn-snapshot",
                    po_no="forged-po-snapshot",
                )],
            ),
        )
        assert len(header.grn_links) == 1
        assert header.grn_links[0].grn_id == grn.id
        assert header.grn_links[0].grn_no == grn.grn_no
        assert header.grn_links[0].po_no == po.po_no

        allocated = await landed_cost_service.run_allocation(db, header.id)
        assert allocated.status == "VALIDATED"
        assert len(allocated.allocation_lines) == 1
        assert allocated.allocation_lines[0].grn_id == grn.id


@pytest.mark.asyncio
async def test_po_scoped_header_rejects_foreign_grn_on_create_and_add():
    expected_database = _require_task_database()
    suffix_a, suffix_b = uuid4().hex[:16], uuid4().hex[:16]
    async with AsyncSessionLocal() as db:
        assert (await db.execute(text("SELECT current_database()"))).scalar_one() == expected_database
        _, _, _, _, _, po_a, _, grn_a, _, _, _ = await _seed_chain(db, suffix_a)
        _, _, _, _, _, po_b, _, grn_b, _, _, _ = await _seed_chain(db, suffix_b)
        grn_a.status = GRNStatus.POSTED
        grn_b.status = GRNStatus.POSTED
        await db.commit()

        with pytest.raises(ValueError, match="must belong to the landed-cost purchase order"):
            await landed_cost_service.create_header(
                db,
                LandedCostHeaderCreate(
                    po_id=po_a.id,
                    currency_code="KES",
                    cost_lines=[_cost_line()],
                    grn_links=[LandedCostGRNLinkCreate(grn_id=grn_b.id)],
                ),
            )
        assert await db.scalar(
            select(LandedCostHeader.id).where(LandedCostHeader.po_id == po_a.id)
        ) is None

        header = await landed_cost_service.create_header(
            db,
            LandedCostHeaderCreate(po_id=po_a.id, currency_code="KES", cost_lines=[_cost_line()]),
        )
        with pytest.raises(ValueError, match="must belong to the landed-cost purchase order"):
            await landed_cost_service.add_grn_link(
                db,
                header.id,
                LandedCostGRNLinkCreate(grn_id=grn_b.id),
            )
        assert header.grn_links == []
        await landed_cost_service.add_grn_link(
            db,
            header.id,
            LandedCostGRNLinkCreate(grn_id=grn_a.id),
        )
        with pytest.raises(ValueError, match="already linked"):
            await landed_cost_service.add_grn_link(
                db,
                header.id,
                LandedCostGRNLinkCreate(grn_id=grn_a.id),
            )
        refreshed = await landed_cost_service.get_header(db, header.id)
        assert refreshed is not None
        assert len(refreshed.grn_links) == 1
        assert refreshed.grn_links[0].po_no == po_a.po_no
        assert po_b.id != po_a.id


@pytest.mark.asyncio
async def test_shipment_scope_rejects_grn_from_unlinked_purchase_order():
    expected_database = _require_task_database()
    suffix_a, suffix_b = uuid4().hex[:16], uuid4().hex[:16]
    async with AsyncSessionLocal() as db:
        assert (await db.execute(text("SELECT current_database()"))).scalar_one() == expected_database
        _, _, _, _, _, po_a, _, grn_a, _, _, _ = await _seed_chain(db, suffix_a)
        _, _, _, _, _, po_b, _, grn_b, _, _, _ = await _seed_chain(db, suffix_b)
        grn_a.status = GRNStatus.POSTED
        grn_b.status = GRNStatus.POSTED
        shipment = InternationalShipment(shipment_no=f"M34-T003-SHP-{suffix_a}")
        db.add(shipment)
        await db.flush()
        db.add(ShipmentPOLink(shipment_id=shipment.id, po_id=po_a.id))
        await db.commit()

        with pytest.raises(ValueError, match="purchase order on the landed-cost shipment"):
            await landed_cost_service.create_header(
                db,
                LandedCostHeaderCreate(
                    shipment_id=shipment.id,
                    currency_code="KES",
                    cost_lines=[_cost_line()],
                    grn_links=[LandedCostGRNLinkCreate(grn_id=grn_b.id)],
                ),
            )
        assert po_a.id != po_b.id
        assert await db.scalar(
            select(LandedCostHeader.id).where(LandedCostHeader.shipment_id == shipment.id)
        ) is None


@pytest.mark.asyncio
async def test_duplicate_grn_entries_in_header_payload_are_rejected_before_write():
    expected_database = _require_task_database()
    suffix = uuid4().hex[:16]
    async with AsyncSessionLocal() as db:
        assert (await db.execute(text("SELECT current_database()"))).scalar_one() == expected_database
        _, _, _, _, _, po, _, grn, _, _, _ = await _seed_chain(db, suffix)
        with pytest.raises(ValueError, match="more than once"):
            await landed_cost_service.create_header(
                db,
                LandedCostHeaderCreate(
                    po_id=po.id,
                    currency_code="KES",
                    cost_lines=[_cost_line()],
                    grn_links=[
                        LandedCostGRNLinkCreate(grn_id=grn.id),
                        LandedCostGRNLinkCreate(grn_id=grn.id),
                    ],
                ),
            )
        assert await db.scalar(
            select(LandedCostHeader.id).where(LandedCostHeader.po_id == po.id)
        ) is None


@pytest.mark.asyncio
async def test_all_linked_grns_must_be_posted_before_reallocation_and_prior_rows_survive():
    expected_database = _require_task_database()
    suffix_a, suffix_b = uuid4().hex[:16], uuid4().hex[:16]
    async with AsyncSessionLocal() as db:
        assert (await db.execute(text("SELECT current_database()"))).scalar_one() == expected_database
        _, _, _, _, _, _, _, grn_a, _, _, _ = await _seed_chain(db, suffix_a)
        _, _, _, _, _, _, _, grn_b, _, _, _ = await _seed_chain(db, suffix_b)
        header = await landed_cost_service.create_header(
            db,
            LandedCostHeaderCreate(
                currency_code="KES",
                allocation_method="EQUAL_SPLIT",
                cost_lines=[_cost_line()],
                grn_links=[
                    LandedCostGRNLinkCreate(grn_id=grn_a.id),
                    LandedCostGRNLinkCreate(grn_id=grn_b.id),
                ],
            ),
        )
        grn_a.status = GRNStatus.POSTED
        grn_b.status = GRNStatus.POSTED
        await db.commit()
        await landed_cost_service.run_allocation(db, header.id)
        before = list((await db.execute(
            select(LandedCostAllocationLine.id)
            .where(LandedCostAllocationLine.header_id == header.id)
            .order_by(LandedCostAllocationLine.id)
        )).scalars().all())
        assert len(before) == 2

        grn_b.status = GRNStatus.DRAFT
        await db.commit()
        with pytest.raises(ValueError, match="All linked goods receipts must be posted"):
            await landed_cost_service.run_allocation(db, header.id)

        after = list((await db.execute(
            select(LandedCostAllocationLine.id)
            .where(LandedCostAllocationLine.header_id == header.id)
            .order_by(LandedCostAllocationLine.id)
        )).scalars().all())
        persisted_header = await db.get(LandedCostHeader, header.id)
        assert after == before
        assert persisted_header is not None
        assert persisted_header.status == "VALIDATED"
