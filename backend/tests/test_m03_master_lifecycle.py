"""M03 T002 lifecycle rules against an explicitly task-owned PostgreSQL database."""
from __future__ import annotations

import os
import re
from uuid import uuid4

import pytest
from sqlalchemy import delete, select, update
from sqlalchemy.exc import IntegrityError

from app.db.session import AsyncSessionLocal, engine
from app.models.company import Branch, Company
from app.models.master import (
    Material,
    MaterialType,
    Product,
    ProductCategory,
    Supplier,
    UnitOfMeasure,
    Warehouse,
    WarehouseType,
)
from app.models.master_lifecycle import MasterLifecycleEvent
from app.models.recipe import Recipe, RecipeItem, RecipeStatus
from app.services.master_lifecycle import MasterLifecycleError, deactivate_master, merge_master


def _require_task_owned_database() -> None:
    expected = os.environ.get("M03_DISPOSABLE_TEST_DATABASE_NAME", "")
    if os.environ.get("M03_DISPOSABLE_TEST_DATABASE") != "1":
        pytest.skip("Set M03_DISPOSABLE_TEST_DATABASE=1 only for a task-owned disposable PostgreSQL database.")
    if (
        engine.url.drivername not in {"postgresql", "postgresql+asyncpg"}
        or engine.url.host not in {"127.0.0.1", "localhost", "::1"}
        or not re.fullmatch(r"fmcg_m03_t002_[a-f0-9]{20,32}", expected)
        or engine.url.database != expected
    ):
        pytest.fail("Refusing integration writes: DATABASE_URL must match the exact loopback T002 disposable database.")


@pytest.mark.asyncio
async def test_merge_preserves_history_and_inactive_masters_cannot_be_newly_referenced():
    _require_task_owned_database()
    suffix = uuid4().hex[:18]
    actor_id = None

    async with AsyncSessionLocal() as db:
        # User FK is nullable by policy; use no fabricated actor identity here.
        company = Company(name=f"Synthetic lifecycle {suffix}", short_code=f"L{suffix[:10]}")
        db.add(company)
        await db.flush()

        product = Product(
            sku=f"P-{suffix}", name="Synthetic product", category=ProductCategory.OTHER,
            uom=UnitOfMeasure.PCS,
        )
        material_source = Material(
            code=f"MS-{suffix}", name="Synthetic source material", material_type=MaterialType.RAW,
            uom=UnitOfMeasure.KG,
        )
        material_survivor = Material(
            code=f"MT-{suffix}", name="Synthetic survivor material", material_type=MaterialType.RAW,
            uom=UnitOfMeasure.KG,
        )
        supplier_source = Supplier(code=f"SS-{suffix}", name="Synthetic source supplier")
        supplier_survivor = Supplier(code=f"ST-{suffix}", name="Synthetic survivor supplier")
        warehouse = Warehouse(
            code=f"W-{suffix}", name="Synthetic warehouse", warehouse_type=WarehouseType.RAW_MATERIAL,
            company_id=company.id,
        )
        branch = Branch(company_id=company.id, name="Synthetic branch", branch_code=f"B-{suffix[:10]}")
        recipe = Recipe(
            product=product, version=f"v-{suffix[:8]}", name="Synthetic recipe", status=RecipeStatus.DRAFT,
        )
        db.add_all([
            product, material_source, material_survivor, supplier_source, supplier_survivor,
            warehouse, branch, recipe,
        ])
        await db.flush()
        historical_item = RecipeItem(
            recipe_id=recipe.id, material_id=material_source.id, line_no=1,
            quantity=1, unit="KG",
        )
        db.add(historical_item)
        await db.commit()
        actor_id = company.created_by_id  # None: lifecycle actor is nullable, with no made-up user.

        source_id, survivor_id = material_source.id, material_survivor.id
        supplier_source_id, supplier_survivor_id = supplier_source.id, supplier_survivor.id
        material_entity_id = source_id
        item_id = historical_item.id

    async with AsyncSessionLocal() as db:
        merged_source, survivor = await merge_master(
            db, Material, "material", source_id, survivor_id, actor_id
        )
        assert merged_source is not None and survivor is not None
        await db.commit()

        # Historical recipe references remain attached to the source record.
        existing_item = await db.scalar(select(RecipeItem).where(RecipeItem.id == item_id))
        assert existing_item is not None and existing_item.material_id == material_entity_id
        historical_recipe_id = existing_item.recipe_id
        existing_item.notes = "Historical reference remains editable"
        await db.flush()
        event = await db.scalar(select(MasterLifecycleEvent).where(
            MasterLifecycleEvent.entity_type == "material",
            MasterLifecycleEvent.record_id == source_id,
        ))
        assert event is not None and event.event_type == "MERGED" and event.merged_into_id == survivor_id

        # A merged source cannot be reactivated through direct database writes.
        with pytest.raises(IntegrityError, match="merged master record cannot be reactivated"):
            await db.execute(update(Material).where(Material.id == source_id).values(is_active=True))
        await db.rollback()

    async with AsyncSessionLocal() as db:
        # Lifecycle evidence is append-only at the database boundary as well.
        with pytest.raises(IntegrityError, match="lifecycle history is append-only"):
            await db.execute(delete(MasterLifecycleEvent).where(
                MasterLifecycleEvent.entity_type == "material",
                MasterLifecycleEvent.record_id == source_id,
            ))
        await db.rollback()

    async with AsyncSessionLocal() as db:
        # A new operational reference to an inactive master fails at the DB guard.
        db.add(RecipeItem(
            recipe_id=historical_recipe_id, material_id=source_id, line_no=2,
            quantity=1, unit="KG",
        ))
        with pytest.raises(IntegrityError, match="Inactive material record"):
            await db.flush()
        await db.rollback()

    async with AsyncSessionLocal() as db:
        # Self-merges and inactive targets are rejected without changing state.
        with pytest.raises(MasterLifecycleError, match="cannot be merged into itself"):
            await merge_master(db, Supplier, "supplier", supplier_source_id, supplier_source_id, actor_id)
        await db.rollback()
        await deactivate_master(db, Supplier, "supplier", supplier_survivor_id, actor_id)
        await db.commit()
        await deactivate_master(db, Supplier, "supplier", supplier_survivor_id, actor_id)
        events = (await db.scalars(select(MasterLifecycleEvent).where(
            MasterLifecycleEvent.entity_type == "supplier",
            MasterLifecycleEvent.record_id == supplier_survivor_id,
            MasterLifecycleEvent.event_type == "DEACTIVATED",
        ))).all()
        assert len(events) == 1
        await db.commit()
        with pytest.raises(MasterLifecycleError, match="surviving record must be active"):
            await merge_master(db, Supplier, "supplier", supplier_source_id, supplier_survivor_id, actor_id)
        await db.rollback()


def test_merge_request_requires_an_explicit_survivor_id():
    from pydantic import ValidationError

    from app.schemas.master import MasterMergeRequest

    with pytest.raises(ValidationError):
        MasterMergeRequest.model_validate({})
