"""M50.S01.T010 typed Parquet read / write (pyarrow). Apache Parquet format, pyarrow 26 (Apache-2.0).

Write: a column's Arrow type comes from the ERP table column (UUID/text/enum -> string, integer -> int64, numeric(p,s) ->
decimal128(p,s), boolean, date -> date32, timestamp -> timestamp[us, UTC]); masked (sensitive) columns are written as strings.
The file carries the dataset name, export time and column list as schema metadata, zstd-compressed.
Read: size / row-group / row limits are checked from the footer before any data is decoded; an upload that is not valid Parquet
or exceeds the limits is refused. Nothing is executed from the file (Parquet carries data, not code).
"""
from __future__ import annotations

import io
import uuid
from datetime import date, datetime, timezone
from decimal import ROUND_HALF_EVEN, Decimal
from typing import Any, Iterable, Optional

import pyarrow as pa
import pyarrow.parquet as pq

MAX_READ_BYTES = 20 * 1024 * 1024
MAX_READ_ROWS = 200_000


class ParquetError(ValueError):
    pass


def arrow_type(col, masked: bool = False) -> pa.DataType:
    """Arrow type of a SQLAlchemy column."""
    from sqlalchemy import Boolean, Date, DateTime, Integer, Numeric
    t = col.type
    if masked:
        return pa.string()
    if isinstance(t, Boolean):
        return pa.bool_()
    if isinstance(t, Integer):
        return pa.int64()
    if isinstance(t, Numeric):
        p, s = int(t.precision or 18), int(t.scale if t.scale is not None else 4)
        return pa.decimal128(min(p, 38), s)
    if isinstance(t, DateTime):
        return pa.timestamp("us", tz="UTC")
    if isinstance(t, Date):
        return pa.date32()
    return pa.string()


def dataset_types(table: str, cols: Iterable[str], masked: Iterable[str] = ()) -> dict[str, pa.DataType]:
    from app.db.base import Base
    import app.models  # noqa: F401  (registers tables)
    tbl = Base.metadata.tables.get(table)
    if tbl is None:
        raise ParquetError(f"Unknown table {table!r}.")
    masked = set(masked)
    return {c: arrow_type(tbl.c[c], c in masked) for c in cols}


def _py(v: Any, t: pa.DataType):
    if v is None:
        return None
    if pa.types.is_string(t):
        return getattr(v, "value", v) if not isinstance(v, (uuid.UUID, Decimal, date, datetime)) else str(v)
    if pa.types.is_decimal(t):
        return Decimal(str(v)).quantize(Decimal(1).scaleb(-t.scale), rounding=ROUND_HALF_EVEN)
    if pa.types.is_timestamp(t) and isinstance(v, datetime) and v.tzinfo is None:
        return v.replace(tzinfo=timezone.utc)
    if pa.types.is_integer(t):
        return int(v)
    return v


def write(rows: list[dict], types: dict[str, pa.DataType], meta: Optional[dict[str, str]] = None) -> bytes:
    cols = list(types)
    schema = pa.schema([pa.field(c, types[c]) for c in cols], metadata={k.encode(): str(v).encode() for k, v in (meta or {}).items()})
    arrays = [pa.array([_py(r.get(c), types[c]) for r in rows], type=types[c]) for c in cols]
    buf = io.BytesIO()
    pq.write_table(pa.Table.from_arrays(arrays, schema=schema), buf, compression="zstd", use_dictionary=True)
    return buf.getvalue()


def read(data: bytes, max_rows: int = MAX_READ_ROWS) -> tuple[list[dict], dict]:
    """→ (rows as dicts of plain Python values, {"columns": [{"name","type"}], "rows": n, "metadata": {...}})."""
    if len(data) > MAX_READ_BYTES:
        raise ParquetError(f"The file is larger than {MAX_READ_BYTES // (1024 * 1024)} MB.")
    if not data.startswith(b"PAR1"):
        raise ParquetError("This is not a Parquet file.")
    try:
        pf = pq.ParquetFile(io.BytesIO(data))
        n = pf.metadata.num_rows
        if n > max_rows:
            raise ParquetError(f"The file has {n} rows; the limit is {max_rows}.")
        table = pf.read()
    except ParquetError:
        raise
    except Exception as e:
        raise ParquetError(f"The Parquet file could not be read: {type(e).__name__}.")
    info = {"columns": [{"name": f.name, "type": str(f.type)} for f in table.schema], "rows": n,
            "metadata": {k.decode(): v.decode() for k, v in (table.schema.metadata or {}).items() if not k.startswith(b"ARROW:")}}
    return table.to_pylist(), info
