"""Shared duplicate checks based on database-declared master keys.

The database unique constraints remain authoritative. This module surfaces those
same conflicts before writes so CRUD and imports can report them consistently;
it deliberately does not infer fuzzy matches from names or contact details.
"""
from __future__ import annotations

from typing import Any

from fastapi import HTTPException
from sqlalchemy import UniqueConstraint, and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession


def unique_key_groups(model: type) -> list[tuple[str, ...]]:
    """Return the model's single-column and composite unique keys."""
    table = model.__table__
    groups: set[tuple[str, ...]] = set()
    for column in table.columns:
        if column.unique and not column.primary_key:
            groups.add((column.name,))
    for constraint in table.constraints:
        if isinstance(constraint, UniqueConstraint):
            names = tuple(column.name for column in constraint.columns)
            if names:
                groups.add(names)
    return sorted(groups)


def duplicate_signature(
    key_groups: list[tuple[str, ...]], values: dict[str, Any]
) -> tuple[tuple[str, ...], tuple[Any, ...]] | None:
    """Return the first complete non-null natural-key signature, preserving equality semantics."""
    for fields in key_groups:
        if all(field in values and values[field] is not None for field in fields):
            return fields, tuple(values[field] for field in fields)
    return None


async def find_duplicate_key(
    db: AsyncSession,
    model: type,
    values: dict[str, Any],
    *,
    exclude_id: Any = None,
) -> tuple[str, ...] | None:
    """Find a row matching any declared unique key and return the matching fields."""
    predicates = []
    groups = unique_key_groups(model)
    for fields in groups:
        if not all(field in values and values[field] is not None for field in fields):
            continue
        predicates.append(and_(*(getattr(model, field) == values[field] for field in fields)))
    if not predicates:
        return None

    query = select(model.id).where(or_(*predicates)).limit(1)
    if exclude_id is not None:
        query = query.where(model.id != exclude_id)
    result = await db.execute(query)
    if result.scalar_one_or_none() is None:
        return None

    # Report the matching key, not a value that could expose owner data.
    for fields in groups:
        if not all(field in values and values[field] is not None for field in fields):
            continue
        match_query = select(model.id).where(
            and_(*(getattr(model, field) == values[field] for field in fields))
        )
        if exclude_id is not None:
            match_query = match_query.where(model.id != exclude_id)
        match = await db.execute(match_query.limit(1))
        if match.scalar_one_or_none() is not None:
            return fields
    return None


async def ensure_unique_record(
    db: AsyncSession,
    model: type,
    values: dict[str, Any],
    *,
    exclude_id: Any = None,
) -> None:
    """Raise a uniform HTTP 409 when a declared master key already exists."""
    fields = await find_duplicate_key(db, model, values, exclude_id=exclude_id)
    if fields:
        raise HTTPException(
            status_code=409,
            detail={
                "code": "duplicate_master_record",
                "resource": model.__tablename__,
                "fields": list(fields),
            },
        )
