"""BOM version and effective-date validation at the API/service boundary."""
from datetime import date
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException
from pydantic import ValidationError

from app.models.bom import AdvancedBOM
from app.schemas.bom import BOMCreate, BOMUpdate
from app.services.bom_service import clone_bom, update_bom


def test_bom_model_declares_database_governance_checks():
    checks = {
        constraint.name: str(constraint.sqltext)
        for constraint in AdvancedBOM.__table__.constraints
        if getattr(constraint, "sqltext", None) is not None
    }
    assert "ck_advanced_boms_version_not_blank" in checks
    assert "ck_advanced_boms_revision_not_blank" in checks
    assert "ck_advanced_boms_effective_window" in checks
    assert "effective_to" in checks["ck_advanced_boms_effective_window"]
    assert "effective_from" in checks["ck_advanced_boms_effective_window"]


def test_bom_version_is_trimmed_but_remains_an_opaque_identifier():
    request = BOMCreate(bom_name="Synthetic", version_no="  rev/A-01  ")
    assert request.version_no == "rev/A-01"
    assert BOMCreate(bom_name="Synthetic").version_no == "1.0"


@pytest.mark.parametrize("version", ["", " \t\n ", "x" * 21])
def test_bom_rejects_blank_or_overlength_version(version):
    with pytest.raises(ValidationError):
        BOMCreate(bom_name="Synthetic", version_no=version)


def test_bom_create_rejects_reversed_effective_window_but_accepts_equal_or_open_bounds():
    with pytest.raises(ValidationError, match="effective_to must be on or after effective_from"):
        BOMCreate(
            bom_name="Synthetic",
            effective_from=date(2026, 11, 2),
            effective_to=date(2026, 11, 1),
        )

    equal_day = date(2026, 11, 1)
    assert BOMCreate(bom_name="Synthetic", effective_from=equal_day, effective_to=equal_day)
    assert BOMCreate(bom_name="Synthetic", effective_from=equal_day).effective_to is None
    assert BOMCreate(bom_name="Synthetic", effective_to=equal_day).effective_from is None


def test_bom_update_rejects_reversed_window_when_both_bounds_are_provided():
    with pytest.raises(ValidationError, match="effective_to must be on or after effective_from"):
        BOMUpdate(effective_from=date(2026, 11, 2), effective_to=date(2026, 11, 1))


@pytest.mark.asyncio
async def test_partial_bom_update_validates_merged_persisted_window_before_mutation():
    bom = SimpleNamespace(
        effective_from=date(2026, 11, 1),
        effective_to=date(2026, 11, 30),
        bom_name="Original",
    )
    db = SimpleNamespace(flush=AsyncMock(), refresh=AsyncMock())

    with pytest.raises(HTTPException) as exc_info:
        await update_bom(db, bom, BOMUpdate(effective_from=date(2026, 12, 1)))

    assert exc_info.value.status_code == 422
    assert bom.effective_from == date(2026, 11, 1)
    db.flush.assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize("new_version", ["", " \t ", "x" * 21])
async def test_bom_clone_rejects_invalid_version_before_writing(new_version):
    source = SimpleNamespace(
        effective_from=date(2026, 11, 1),
        effective_to=date(2026, 11, 30),
    )
    db = SimpleNamespace(add=pytest.fail, flush=AsyncMock())

    with pytest.raises(HTTPException) as exc_info:
        await clone_bom(db, source, new_version, None)

    assert exc_info.value.status_code == 422
    db.flush.assert_not_awaited()


@pytest.mark.asyncio
async def test_bom_clone_rejects_reversed_source_window_before_writing():
    source = SimpleNamespace(
        effective_from=date(2026, 11, 2),
        effective_to=date(2026, 11, 1),
    )
    db = SimpleNamespace(add=pytest.fail, flush=AsyncMock())

    with pytest.raises(HTTPException) as exc_info:
        await clone_bom(db, source, "next/v1", None)

    assert exc_info.value.status_code == 422
    db.flush.assert_not_awaited()
