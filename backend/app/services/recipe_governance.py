"""Shared recipe version/effective-date rules used by planning consumers."""
from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Iterable, Optional

from app.models.recipe import Recipe, RecipeStatus


def recipe_precedence_ordering():
    """Database ordering matching the accepted MPS recipe-version policy."""
    return (
        Recipe.valid_from.desc().nulls_last(),
        Recipe.created_at.desc(),
        Recipe.id.desc(),
    )


def recipe_is_effective_on(recipe: Recipe, as_of: date) -> bool:
    status = getattr(recipe, "status", None)
    status_value = getattr(status, "value", status)
    return (
        status_value == RecipeStatus.APPROVED.value
        and bool(getattr(recipe, "is_active", False))
        and (recipe.valid_from is None or recipe.valid_from <= as_of)
        and (recipe.valid_to is None or recipe.valid_to >= as_of)
    )


def recipe_required_date(planned_start_date: Optional[date], period_start: date) -> date:
    """Use the scheduled date, or the line's own period start consistently."""
    return planned_start_date or period_start


def _created_at_key(value: Optional[datetime]) -> datetime:
    if value is None:
        return datetime.min.replace(tzinfo=timezone.utc)
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _recipe_precedence_key(recipe: Recipe) -> tuple[bool, date, datetime, str]:
    return (
        recipe.valid_from is not None,
        recipe.valid_from or date.min,
        _created_at_key(getattr(recipe, "created_at", None)),
        str(getattr(recipe, "id", "")),
    )


def select_effective_approved_recipe(
    candidates: Iterable[Recipe], as_of: date
) -> Optional[Recipe]:
    """Choose the most recently effective approved recipe, then newest created.

    Effective boundaries are inclusive and null endpoints are unbounded. The
    UUID tie-break makes otherwise equal persisted rows deterministic too.
    """
    eligible = [candidate for candidate in candidates if recipe_is_effective_on(candidate, as_of)]
    return max(eligible, key=_recipe_precedence_key, default=None)
