from datetime import date
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from pydantic import ValidationError

from app.schemas.bom import ConversionProfileCreate
from app.services.bom_scaling_service import _profile_effective_date


def test_conversion_profile_version_defaults_and_trims_family_code():
    request = ConversionProfileCreate(
        profile_code="  CONV-FAMILY  ",
        profile_name="Synthetic version family",
    )

    assert request.profile_code == "CONV-FAMILY"
    assert request.version_no == "1.0"
    assert request.effective_from is None
    assert request.effective_to is None


@pytest.mark.parametrize(
    "dates",
    [
        {"effective_from": date(2026, 11, 1), "effective_to": date(2026, 10, 31)},
    ],
)
def test_conversion_profile_rejects_reversed_effective_window(dates):
    with pytest.raises(ValidationError, match="effective_to must be on or after effective_from"):
        ConversionProfileCreate(profile_name="Invalid window", **dates)


def test_conversion_profile_rejects_blank_version():
    with pytest.raises(ValidationError, match="must not be blank"):
        ConversionProfileCreate(profile_name="Blank version", version_no="   ")


@pytest.mark.parametrize("as_of", [date(2026, 10, 1), date(2026, 10, 31)])
def test_effective_window_bounds_are_inclusive(as_of):
    profile = SimpleNamespace(
        is_active=True,
        effective_from=date(2026, 10, 1),
        effective_to=date(2026, 10, 31),
    )

    assert _profile_effective_date(profile, as_of) == as_of


@pytest.mark.parametrize(
    ("as_of", "message"),
    [
        (date(2026, 9, 30), "not effective until"),
        (date(2026, 11, 1), "expired on"),
    ],
)
def test_effective_window_rejects_out_of_range_date(as_of, message):
    profile = SimpleNamespace(
        is_active=True,
        effective_from=date(2026, 10, 1),
        effective_to=date(2026, 10, 31),
    )

    with pytest.raises(HTTPException) as exc_info:
        _profile_effective_date(profile, as_of)

    assert exc_info.value.status_code == 422
    assert message in exc_info.value.detail


def test_effective_window_rejects_inactive_profile():
    profile = SimpleNamespace(
        is_active=False,
        effective_from=None,
        effective_to=None,
    )

    with pytest.raises(HTTPException) as exc_info:
        _profile_effective_date(profile, date(2026, 10, 28))

    assert exc_info.value.status_code == 422
    assert "inactive" in exc_info.value.detail
