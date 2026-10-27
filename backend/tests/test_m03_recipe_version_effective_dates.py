"""Recipe version/effective-date governance regression tests."""
from __future__ import annotations

from datetime import date, datetime, timezone
import os
import re
from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest
import pytest_asyncio
from pydantic import ValidationError
from sqlalchemy.exc import IntegrityError

from app.api.v1.endpoints.bulk_import import _RecipeImport
from app.db.session import AsyncSessionLocal, engine
from app.models.master import Product, ProductCategory, UnitOfMeasure
from app.models.recipe import Recipe, RecipeStatus
from app.schemas.recipe import (
    RecipeCreate,
    RecipeDuplicateRequest,
    RecipeUpdate,
    validate_recipe_update_window,
)
from app.services.recipe_governance import (
    recipe_is_effective_on,
    recipe_required_date,
    select_effective_approved_recipe,
)


@pytest_asyncio.fixture(autouse=True)
async def _dispose_async_engine_after_test():
    yield
    await engine.dispose()


def _require_task_owned_database() -> None:
    expected = os.environ.get("M03_DISPOSABLE_TEST_DATABASE_NAME", "")
    if os.environ.get("M03_DISPOSABLE_TEST_DATABASE") != "1":
        pytest.skip("Set M03_DISPOSABLE_TEST_DATABASE=1 only for the task-owned disposable PostgreSQL database.")
    if (
        engine.url.drivername not in {"postgresql", "postgresql+asyncpg"}
        or engine.url.host not in {"127.0.0.1", "localhost", "::1"}
        or not re.fullmatch(r"fmcg_m03_t003_[a-f0-9]{20,32}", expected)
        or engine.url.database != expected
    ):
        pytest.fail("Refusing integration writes: DATABASE_URL must match the exact loopback T003 disposable database.")


def _recipe(
    *,
    id: str,
    valid_from: date | None = None,
    valid_to: date | None = None,
    created_at: datetime | None = None,
    status=RecipeStatus.APPROVED,
    is_active: bool = True,
):
    return SimpleNamespace(
        id=UUID(id),
        status=status,
        is_active=is_active,
        valid_from=valid_from,
        valid_to=valid_to,
        created_at=created_at,
    )


def test_recipe_create_rejects_blank_or_overlength_version():
    common = {"product_id": "00000000-0000-0000-0000-000000000001", "name": "Recipe"}
    for version in ("", "   ", "x" * 21):
        with pytest.raises(ValidationError):
            RecipeCreate(**common, version=version)


def test_recipe_duplicate_rejects_blank_or_overlength_version():
    for version in ("", "   ", "x" * 21):
        with pytest.raises(ValidationError):
            RecipeDuplicateRequest(new_version=version)


def test_recipe_bulk_import_rejects_whitespace_only_version():
    with pytest.raises(ValidationError):
        _RecipeImport(product_sku="SKU", version="\t\n", name="Recipe")


def test_recipe_create_and_update_reject_reversed_inclusive_window():
    common = {"product_id": "00000000-0000-0000-0000-000000000001", "name": "Recipe", "version": "v1"}
    with pytest.raises(ValidationError, match="valid_to"):
        RecipeCreate(**common, valid_from=date(2026, 2, 2), valid_to=date(2026, 2, 1))
    with pytest.raises(ValidationError, match="valid_to"):
        RecipeUpdate(valid_from=date(2026, 2, 2), valid_to=date(2026, 2, 1))


def test_partial_update_validates_resulting_window_and_explicit_nulls():
    with pytest.raises(ValueError, match="valid_to"):
        validate_recipe_update_window(
            date(2026, 2, 1), date(2026, 2, 28), {"valid_from": date(2026, 3, 1)}
        )
    validate_recipe_update_window(
        date(2026, 2, 1), date(2026, 2, 28), {"valid_from": date(2026, 3, 1), "valid_to": None}
    )


def test_recipe_required_date_uses_same_line_period_fallback_for_planning_and_release():
    period_start = date(2026, 5, 1)
    assert recipe_required_date(None, period_start) == period_start
    assert recipe_required_date(date(2026, 5, 4), period_start) == date(2026, 5, 4)


def test_recipe_effective_dates_are_inclusive_and_null_endpoints_unbounded():
    bounded = _recipe(
        id="00000000-0000-0000-0000-000000000001",
        valid_from=date(2026, 1, 1),
        valid_to=date(2026, 1, 31),
    )
    open_start = _recipe(
        id="00000000-0000-0000-0000-000000000002",
        valid_to=date(2026, 1, 31),
    )
    assert recipe_is_effective_on(bounded, date(2026, 1, 1))
    assert recipe_is_effective_on(bounded, date(2026, 1, 31))
    assert not recipe_is_effective_on(bounded, date(2025, 12, 31))
    assert not recipe_is_effective_on(bounded, date(2026, 2, 1))
    assert recipe_is_effective_on(open_start, date(2025, 1, 1))


def test_effective_recipe_selection_uses_latest_start_then_created_then_id():
    older_start = _recipe(
        id="00000000-0000-0000-0000-000000000009",
        valid_from=date(2026, 1, 1),
        created_at=datetime(2026, 3, 1, tzinfo=timezone.utc),
    )
    newer_created = _recipe(
        id="00000000-0000-0000-0000-000000000002",
        valid_from=date(2026, 2, 1),
        created_at=datetime(2026, 3, 1, tzinfo=timezone.utc),
    )
    newest_created = _recipe(
        id="00000000-0000-0000-0000-000000000003",
        valid_from=date(2026, 2, 1),
        created_at=datetime(2026, 3, 2, tzinfo=timezone.utc),
    )
    uuid_tie_winner = _recipe(
        id="00000000-0000-0000-0000-000000000004",
        valid_from=date(2026, 2, 1),
        created_at=datetime(2026, 3, 2, tzinfo=timezone.utc),
    )
    inactive = _recipe(
        id="00000000-0000-0000-0000-000000000010",
        valid_from=date(2026, 2, 2),
        status=RecipeStatus.DRAFT,
    )
    assert select_effective_approved_recipe(
        [older_start, newer_created, newest_created, uuid_tie_winner, inactive],
        date(2026, 2, 2),
    ) is uuid_tie_winner


def test_recipe_model_declares_database_date_and_version_guards():
    from app.models.recipe import Recipe

    constraints = {
        constraint.name: str(constraint.sqltext)
        for constraint in Recipe.__table__.constraints
        if getattr(constraint, "sqltext", None) is not None
    }
    assert "ck_recipes_version_not_blank" in constraints
    assert "[:space:]" in constraints["ck_recipes_version_not_blank"]
    assert "ck_recipes_effective_window" in constraints
    assert "valid_to" in constraints["ck_recipes_effective_window"]
    assert "valid_from" in constraints["ck_recipes_effective_window"]


@pytest.mark.asyncio
async def test_postgres_guards_reject_blank_version_and_reversed_window():
    _require_task_owned_database()
    suffix = uuid4().hex[:18]
    invalid_recipes = (
        {"version": "\t\n", "valid_from": date(2026, 1, 1), "valid_to": date(2026, 1, 31)},
        {"version": "v2", "valid_from": date(2026, 2, 1), "valid_to": date(2026, 1, 31)},
    )
    for index, invalid in enumerate(invalid_recipes):
        async with AsyncSessionLocal() as db:
            product = Product(
                sku=f"T003-{suffix}-{index}",
                name="Synthetic recipe governance product",
                category=ProductCategory.OTHER,
                uom=UnitOfMeasure.PCS,
            )
            db.add(product)
            await db.flush()
            db.add(Recipe(product_id=product.id, name="Synthetic recipe", **invalid))
            with pytest.raises(IntegrityError):
                await db.flush()
            await db.rollback()
