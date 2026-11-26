"""M47.S01.T011 dataset blending for the report builder.

A dataset is a CSV uploaded by a user (e.g. a distributor's sell-out sheet), stored as typed rows (≤ MAX_ROWS). It can
be blended with any catalog source the user can run (left join dataset column = source field); blended columns are
prefixed "src.". The source side is read through the report builder itself, so the same permissions and row-level
rules apply (custom objects and datasets need a signed-in user). Datasets appear in the catalog as "ds:<key>".
"""
from __future__ import annotations

import csv
import io
import re
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.m47_datasets import ReportDataset

MAX_ROWS = 20_000
MAX_COLS = 40
JOIN_FETCH = 20_000


class DatasetError(ValueError):
    pass


def _num(v: str):
    try:
        return float(v.replace(",", "")) if re.fullmatch(r"-?[\d,]*\.?\d+", v.strip()) else None
    except ValueError:
        return None


def parse_csv(text: str) -> tuple[list[dict], list[dict]]:
    reader = csv.reader(io.StringIO(text))
    try:
        head = next(reader)
    except StopIteration:
        raise DatasetError("The file is empty")
    keys = []
    for h in head[:MAX_COLS]:
        k = re.sub(r"[^a-z0-9_]", "_", h.strip().lower()).strip("_")[:40] or f"col{len(keys) + 1}"
        while k in keys:
            k += "_2"
        keys.append(k)
    raw = []
    for i, line in enumerate(reader):
        if i >= MAX_ROWS:
            raise DatasetError(f"At most {MAX_ROWS} rows")
        if any(c.strip() for c in line):
            raw.append({k: (line[j].strip() if j < len(line) else "") for j, k in enumerate(keys)})
    if not raw:
        raise DatasetError("No data rows")
    cols = []
    for k, h in zip(keys, head):
        numeric = all(_num(r[k]) is not None for r in raw if r[k] != "")
        cols.append({"path": k, "label": h.strip()[:60] or k, "type": "number" if numeric else "string"})
    types = {c["path"]: c["type"] for c in cols}
    rows = [{k: (None if v == "" else _num(v) if types[k] == "number" else v[:500]) for k, v in r.items()} for r in raw]
    return cols, rows


async def catalog(db: AsyncSession, user) -> dict:
    from app.services.report_builder_service import DATA_SOURCES
    out = {}
    for d in (await db.execute(select(ReportDataset).order_by(ReportDataset.name))).scalars():
        fields = list(d.columns)
        if d.join_source in DATA_SOURCES:
            fields += [{"path": f"src.{f['path']}", "label": f"{DATA_SOURCES[d.join_source]['label']}: {f['label']}", "type": f["type"]}
                       for f in DATA_SOURCES[d.join_source]["fields"]]
        out[f"ds:{d.key}"] = {"label": f"{d.name} (dataset)", "module": "reports", "table": None, "fields": fields}
    return out


async def blended(db: AsyncSession, d: ReportDataset, user) -> list[dict]:
    rows = [dict(r) for r in d.rows]
    if not (d.join_source and d.join_local and d.join_remote):
        return rows
    from app.services.report_builder_service import DATA_SOURCES, _execute_query
    src = DATA_SOURCES.get(d.join_source)
    if not src:
        return rows
    res = await _execute_query(db, d.join_source, [{"path": f["path"]} for f in src["fields"]], [], JOIN_FETCH, 0, user)
    index: dict[str, dict] = {}
    for r in res.get("rows", []):
        key = r.get(d.join_remote)
        if key is not None:
            index.setdefault(str(key).strip().lower(), r)
    out = []
    for r in rows:
        match = index.get(str(r.get(d.join_local) or "").strip().lower(), {})
        out.append({**r, **{f"src.{f['path']}": match.get(f["path"]) for f in src["fields"]}})
    return out


async def report_rows(db: AsyncSession, key: str, user, paths: list[str], filters: list[dict], limit: int, offset: int) -> dict:
    from app.services.report_builder_service import _apply_filter_python
    d = (await db.execute(select(ReportDataset).where(ReportDataset.key == key))).scalar_one_or_none()
    if d is None:
        return {"columns": [], "rows": [], "total": 0, "error": "Not found"}
    rows = await blended(db, d, user)
    allowed = list(rows[0].keys()) if rows else [c["path"] for c in d.columns]
    cols = [p for p in paths if p in allowed] or allowed[:8]
    for f in filters:
        if f.get("field_path") in allowed:
            rows = _apply_filter_python(rows, f["field_path"], f["operator"], f.get("value", ""), f.get("value_to"))
    total = len(rows)
    page = [{c: (None if r.get(c) is None else str(r.get(c))) for c in cols} for r in rows[offset: offset + limit]]
    return {"columns": [{"path": c, "label": c, "type": "string"} for c in cols], "rows": page, "total": total}


def validate_join(d: ReportDataset, source: Optional[str], local: Optional[str], remote: Optional[str]) -> None:
    from app.services.report_builder_service import DATA_SOURCES
    if not source:
        d.join_source = d.join_local = d.join_remote = None
        return
    if source not in DATA_SOURCES:
        raise DatasetError("Unknown source to blend with")
    if local not in {c["path"] for c in d.columns}:
        raise DatasetError("The dataset has no such column")
    if remote not in {f["path"] for f in DATA_SOURCES[source]["fields"]}:
        raise DatasetError("The source has no such field")
    d.join_source, d.join_local, d.join_remote = source, local, remote
