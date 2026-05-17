import asyncio
from decimal import Decimal
from pathlib import Path
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.core.module_registry import registry_permission_codes
from app.db.seed import ROLE_DEFINITIONS
from app.models.finance import (
    AccountingPostingBatch,
    InventoryAccountMapping,
    OperationalPostingEvent,
    OperationalPostingStatus,
    PostingBatchStatus,
)
from app.models.inventory import StockMovement
from app.models.procurement import GRNLine
from app.models.production import FinishedGoodsReceipt, MaterialConsumption
from app.models.landed_cost import LandedCostAllocationLine, LCInventoryAdjustment
from app.schemas.finance import (
    InventoryAccountMappingCreate,
    OperationalPostingEventCreate,
    OperationalPostingLinkRead,
)
from app.services.finance_service import (
    _account_mapping_specificity,
    apply_operational_posting_link,
    build_operational_idempotency_key,
    mark_operational_posting_failed,
    mark_operational_posting_posted,
)


class _FlushOnlyDB:
    def __init__(self):
        self.flush_count = 0

    async def flush(self):
        self.flush_count += 1


def test_gap002_migration_contains_additive_posting_foundations():
    migration = Path("alembic/versions/20260511_0020_operational_posting_integration.py").read_text()

    assert "operational_posting_events" in migration
    assert "inventory_account_mappings" in migration
    assert "posting_batch_id" in migration
    assert "journal_entry_id" in migration
    assert "accounting_status" in migration
    assert "DROP TABLE" not in migration.split("def upgrade() -> None:", 1)[1].split("def downgrade() -> None:", 1)[0]


def test_gap002_models_expose_required_posting_columns():
    for model in (
        StockMovement,
        GRNLine,
        MaterialConsumption,
        FinishedGoodsReceipt,
        LandedCostAllocationLine,
        LCInventoryAdjustment,
    ):
        columns = model.__table__.columns.keys()
        assert "posting_batch_id" in columns
        assert "journal_entry_id" in columns
        assert "accounting_status" in columns
        assert "posting_error" in columns

    assert OperationalPostingEvent.__tablename__ == "operational_posting_events"
    assert InventoryAccountMapping.__tablename__ == "inventory_account_mappings"


def test_gap002_schemas_validate_operational_posting_payloads():
    event = OperationalPostingEventCreate(
        source_module="procurement",
        source_event="GRN_RECEIPT_POSTED",
        source_id=str(uuid4()),
        event_date="2026-05-11",
        amount=Decimal("123.45"),
        idempotency_key="procurement:GRN_RECEIPT_POSTED:line-1",
    )
    assert event.status == OperationalPostingStatus.PENDING

    link = OperationalPostingLinkRead(accounting_status=OperationalPostingStatus.POSTED)
    assert link.accounting_status == OperationalPostingStatus.POSTED

    mapping = InventoryAccountMappingCreate(stock_type="MATERIAL", inventory_account_id=uuid4())
    assert mapping.stock_type == "MATERIAL"

    with pytest.raises(ValidationError):
        InventoryAccountMappingCreate(inventory_account_id=uuid4())


def test_gap002_service_helpers_are_deterministic_and_safe():
    key = build_operational_idempotency_key("production", "MATERIAL_ISSUED_TO_WIP", "order-1", "line-9")
    assert key == "production:MATERIAL_ISSUED_TO_WIP:order-1:line-9"

    fallback_mapping = InventoryAccountMapping(stock_type="MATERIAL", priority=100)
    item_mapping = InventoryAccountMapping(stock_type="MATERIAL", material_id=uuid4(), priority=200)
    assert _account_mapping_specificity(item_mapping) > _account_mapping_specificity(fallback_mapping)

    event = OperationalPostingEvent(status=OperationalPostingStatus.FAILED, error_message="missing account")
    event.posting_batch_id = uuid4()
    target = GRNLine()
    apply_operational_posting_link(target, event)
    assert target.posting_batch_id == event.posting_batch_id
    assert target.accounting_status == OperationalPostingStatus.FAILED
    assert target.posting_error == "missing account"


def test_gap002_posting_state_helpers_update_event_and_batch():
    db = _FlushOnlyDB()
    event = OperationalPostingEvent(status=OperationalPostingStatus.PENDING)
    batch = AccountingPostingBatch(status=PostingBatchStatus.DRAFT)
    journal_entry_id = uuid4()
    posted_by_id = uuid4()

    asyncio.run(
        mark_operational_posting_posted(
            db,
            event,
            batch,
            journal_entry_id=journal_entry_id,
            posted_by_id=posted_by_id,
        )
    )
    assert event.status == OperationalPostingStatus.POSTED
    assert event.journal_entry_id == journal_entry_id
    assert batch.status == PostingBatchStatus.POSTED
    assert batch.journal_entry_id == journal_entry_id
    assert batch.posted_by_id == posted_by_id

    asyncio.run(mark_operational_posting_failed(db, event, batch, error_message="x" * 2500))
    assert event.status == OperationalPostingStatus.FAILED
    assert batch.status == PostingBatchStatus.FAILED
    assert len(event.error_message) == 2000
    assert db.flush_count == 2


def test_gap002_routes_and_permissions_are_registered():
    from app.api.v1.endpoints.finance import router

    route_paths = {route.path for route in router.routes}
    assert "/accounting/operational-posting-events/" in route_paths
    assert "/accounting/operational-posting-events/{event_id}" in route_paths
    assert "/accounting/inventory-account-mappings/" in route_paths
    assert "/accounting/inventory-account-mappings/{mapping_id}" in route_paths

    registry_codes = registry_permission_codes()
    assert "finance.view" in registry_codes
    assert "finance.configure" in registry_codes
    assert "finance.configure" in ROLE_DEFINITIONS["cfo"]["permissions"]
    assert "finance.configure" in ROLE_DEFINITIONS["finance_manager"]["permissions"]

