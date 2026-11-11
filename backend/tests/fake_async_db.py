"""In-memory stand-in for AsyncSession used by service/API tests that have no PostgreSQL.

It evaluates the simple `select(Model)...where(...)` shapes the services use
(comparisons, IS, IN, AND/OR, sum/max/count). Anything else raises
NotImplementedError so a test never silently passes on an unsupported query.
It proves application logic only — not SQL, constraints, locking or indexes.
"""
from __future__ import annotations

import uuid
from collections import defaultdict
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy.sql import operators
from sqlalchemy.sql.elements import BinaryExpression, BindParameter, BooleanClauseList, Grouping, Null, True_, False_
from sqlalchemy.sql.functions import FunctionElement

import app.models  # noqa: F401 - register all mappers
from app.db.base import Base

_TABLE_TO_MODEL = {m.local_table.name: m.class_ for m in Base.registry.mappers}

_OPS = {
    operators.eq: lambda a, b: a == b,
    operators.ne: lambda a, b: a != b,
    operators.ge: lambda a, b: a is not None and a >= b,
    operators.le: lambda a, b: a is not None and a <= b,
    operators.gt: lambda a, b: a is not None and a > b,
    operators.lt: lambda a, b: a is not None and a < b,
    operators.is_: lambda a, b: a is b or a == b,
    operators.is_not: lambda a, b: not (a is b or a == b),
    operators.in_op: lambda a, b: a in b,
}


def _value(expr):
    if isinstance(expr, BindParameter):
        return expr.effective_value
    if isinstance(expr, Null):
        return None
    if isinstance(expr, True_):
        return True
    if isinstance(expr, False_):
        return False
    if isinstance(expr, Grouping):
        return _value(expr.element)
    raise NotImplementedError(f"unsupported right-hand side: {expr!r}")


def _match(expr, obj) -> bool:
    if expr is None:
        return True
    if isinstance(expr, BooleanClauseList):
        results = [_match(c, obj) for c in expr.clauses]
        return any(results) if expr.operator is operators.or_ else all(results)
    if isinstance(expr, Grouping):
        return _match(expr.element, obj)
    if isinstance(expr, BinaryExpression) and expr.operator in _OPS:
        left = getattr(obj, expr.left.key)
        right = _value(expr.right)
        left, right = getattr(left, "value", left), getattr(right, "value", right)
        if isinstance(right, (list, tuple)):
            right = [getattr(r, "value", r) for r in right]
        return _OPS[expr.operator](left, right)
    raise NotImplementedError(f"unsupported where clause: {expr!r}")


class _Result:
    def __init__(self, rows):
        self._rows = list(rows)

    def scalars(self):
        return self

    def all(self):
        return list(self._rows)

    def first(self):
        return self._rows[0] if self._rows else None

    def scalar(self):
        return self._rows[0] if self._rows else None

    scalar_one_or_none = scalar

    def scalar_one(self):
        assert len(self._rows) == 1, self._rows
        return self._rows[0]


class FakeDB:
    def __init__(self):
        self.rows: dict[type, list] = defaultdict(list)
        self.commits = 0
        self.rollbacks = 0

    def add(self, obj):
        mapper = type(obj).__mapper__
        for col in mapper.columns:
            key = mapper.get_property_by_column(col).key
            if getattr(obj, key, None) is not None:
                continue
            if col.default is not None:
                arg = col.default.arg
                setattr(obj, key, arg(None) if callable(arg) else arg)
            elif col.name in {"created_at", "updated_at"}:
                setattr(obj, key, datetime.now(timezone.utc))
        if obj not in self.rows[type(obj)]:
            self.rows[type(obj)].append(obj)
        return obj

    def add_all(self, objs):
        for o in objs:
            self.add(o)

    async def get(self, model, ident):
        return next((r for r in self.rows[model] if r.id == ident), None)

    def _entity(self, stmt):
        desc = stmt.column_descriptions[0]
        if desc.get("entity") is not None:
            return desc["entity"], desc["expr"]
        froms = stmt.get_final_froms()
        return _TABLE_TO_MODEL[froms[0].name], desc["expr"]

    async def execute(self, stmt):
        if getattr(stmt, "_setup_joins", ()):
            raise NotImplementedError("joins are not supported by FakeDB")
        entity, expr = self._entity(stmt)
        matched = [r for r in self.rows[entity] if _match(stmt.whereclause, r)]
        for clause in reversed(getattr(stmt, "_order_by_clauses", ())):  # stable sort, last key first
            modifier = getattr(clause, "modifier", None)
            column = clause.element if modifier is not None else clause
            descending = getattr(modifier, "__name__", "") == "desc_op"
            key = getattr(column, "key", None)
            if key is None:
                continue
            present = [r for r in matched if getattr(r, key, None) is not None]
            missing = [r for r in matched if getattr(r, key, None) is None]
            present.sort(key=lambda r: getattr(r, key), reverse=descending)
            matched = present + missing if not descending else missing + present  # PostgreSQL NULL ordering
        offset = getattr(stmt, "_offset", None)
        if offset:
            matched = matched[offset:]
        limit = getattr(stmt, "_limit", None)
        if limit is not None:
            matched = matched[:limit]
        if isinstance(expr, FunctionElement):
            if expr.name == "count":
                return _Result([len(matched)])
            col = list(expr.clauses)[0].key
            vals = [getattr(r, col) for r in matched if getattr(r, col) is not None]
            if expr.name == "sum":
                return _Result([sum(vals, Decimal("0")) if vals else None])
            if expr.name == "max":
                return _Result([max(vals) if vals else None])
            raise NotImplementedError(expr.name)
        if len(stmt.column_descriptions) > 1 or desc_is_column(stmt):
            keys = [d["expr"].key for d in stmt.column_descriptions]
            if len(keys) == 1:
                return _Result([getattr(r, keys[0]) for r in matched])
            return _Result([tuple(getattr(r, k) for k in keys) for r in matched])
        return _Result(matched)

    async def delete(self, obj):
        self.rows[type(obj)].remove(obj)

    async def flush(self):
        for objs in list(self.rows.values()):
            for o in objs:
                self.add(o)

    async def commit(self):
        await self.flush()
        self.commits += 1

    async def rollback(self):
        self.rollbacks += 1

    async def refresh(self, obj):
        pass


def desc_is_column(stmt) -> bool:
    desc = stmt.column_descriptions[0]
    return desc.get("entity") is not None and desc["expr"] is not desc["entity"] and hasattr(desc["expr"], "key")


def new_id():
    return uuid.uuid4()
