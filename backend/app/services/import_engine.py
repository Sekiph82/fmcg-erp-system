"""
Universal Bulk Import Engine
────────────────────────────
• Template generation  – dynamically derived from Pydantic Create schemas
• CSV parsing          – handles BOM, CRLF, blank rows
• Row-level validation – Pydantic validation + relation resolution
• Duplicate detection  – within CSV and against DB
• Import modes         – validate_only | import_valid_only | strict
• Audit trail          – writes ImportHistory after every run
"""
from __future__ import annotations

import csv
import enum
import inspect
import io
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Any, Optional, get_args, get_origin

from pydantic import BaseModel, ValidationError
from pydantic_core import PydanticUndefinedType
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.import_history import ImportHistory, ImportStatus


# ── Public enums / result types ───────────────────────────────────────────────

class ImportMode(str, enum.Enum):
    VALIDATE_ONLY       = "validate_only"
    IMPORT_VALID_ONLY   = "import_valid_only"
    STRICT              = "strict"


@dataclass
class RowError:
    row:     int
    field:   Optional[str]
    message: str

    def to_dict(self) -> dict:
        return {"row": self.row, "field": self.field, "message": self.message}


@dataclass
class ImportResult:
    total_rows:    int
    valid_rows:    int
    failed_rows:   int
    errors:        list[RowError] = field(default_factory=list)
    imported:      bool = False       # True only when DB writes happened
    import_mode:   ImportMode = ImportMode.VALIDATE_ONLY
    module:        str = ""

    def to_response(self) -> dict:
        return {
            "total_rows":  self.total_rows,
            "valid_rows":  self.valid_rows,
            "failed_rows": self.failed_rows,
            "imported":    self.imported,
            "import_mode": self.import_mode,
            "module":      self.module,
            "errors": [e.to_dict() for e in self.errors],
        }


# ── Field metadata for template generation ───────────────────────────────────

@dataclass
class FieldMeta:
    name:        str
    required:    bool
    type_hint:   str
    enum_values: Optional[list[str]]
    default:     Optional[str]


_NoneType = type(None)


def _unwrap_optional(annotation: Any) -> tuple[Any, bool]:
    """Return (inner_type, is_optional). Handles Optional[X] = Union[X, None]."""
    origin = get_origin(annotation)
    # Union
    if origin is not None and hasattr(origin, "__mro__") is False:
        args = get_args(annotation)
        non_none = [a for a in args if a is not _NoneType]
        if _NoneType in args and non_none:
            return non_none[0], True
    # straight Optional via typing (Union with NoneType)
    import typing
    if hasattr(annotation, "__args__"):
        args = annotation.__args__
        if args and _NoneType in args:
            non_none = [a for a in args if a is not _NoneType]
            if non_none:
                return non_none[0], True
    return annotation, False


def get_field_metadata(schema_class: type[BaseModel]) -> list[FieldMeta]:
    """Introspect a Pydantic Create schema and return structured field info."""
    from pydantic_core import PydanticUndefinedType
    metas: list[FieldMeta] = []

    for name, field_info in schema_class.model_fields.items():
        annotation = field_info.annotation
        inner, is_opt = _unwrap_optional(annotation)

        has_default = not isinstance(field_info.default, PydanticUndefinedType)
        required = not (is_opt or has_default)

        # Enum values
        enum_values = None
        if inspect.isclass(inner) and issubclass(inner, enum.Enum):
            enum_values = [e.value for e in inner]

        type_hint = inner.__name__ if hasattr(inner, "__name__") else str(inner)

        default = None
        if has_default and field_info.default is not None:
            default = str(field_info.default)

        metas.append(FieldMeta(
            name=name,
            required=required,
            type_hint=type_hint,
            enum_values=enum_values,
            default=default,
        ))
    return metas


# ── CSV template generation ───────────────────────────────────────────────────

def generate_csv_template(
    schema_class: type[BaseModel],
    overrides: Optional[dict[str, str]] = None,
    example: Optional[dict[str, Any]] = None,
) -> bytes:
    """
    Generate a downloadable CSV template.

    Row 1  – field names (headers). Required fields prefixed with *.
    Row 2  – type/enum hints  (starts with  __type__  so the importer skips it).
    Row 3  – example data row (starts with __example__ sentinel cell, stripped before import).

    The overrides dict lets adapters substitute business-key fields:
        {"supplier_id": "supplier_code"}  → replaces the UUID field with a readable key.
    """
    metas = get_field_metadata(schema_class)
    overrides = overrides or {}
    example   = example or {}

    # Apply field overrides (UUID → business key substitution)
    final_metas: list[FieldMeta] = []
    for m in metas:
        if m.name in overrides:
            replacement = overrides[m.name]
            final_metas.append(FieldMeta(
                name=replacement,
                required=m.required,
                type_hint="str",
                enum_values=None,
                default=None,
            ))
        else:
            final_metas.append(m)

    buf = io.StringIO()
    writer = csv.writer(buf)

    # Row 1: headers  (* = required)
    headers = [f"*{m.name}" if m.required else m.name for m in final_metas]
    writer.writerow(headers)

    # Row 2: type hints.
    # First cell is replaced with __type__ sentinel so the importer skips this row.
    type_hints = []
    for m in final_metas:
        if m.enum_values:
            type_hints.append(f"ENUM:{','.join(m.enum_values)}")
        else:
            hint = m.type_hint
            if m.default is not None:
                hint += f" (default:{m.default})"
            type_hints.append(hint)
    if type_hints:
        type_hints[0] = "__type__"
    writer.writerow(type_hints)

    # Row 3: example row.
    # First cell is replaced with __example__ sentinel so the importer skips this row.
    ex_row = []
    for m in final_metas:
        key = m.name  # post-override name
        if key in example:
            ex_row.append(str(example[key]))
        elif m.enum_values:
            ex_row.append(m.enum_values[0])
        elif m.type_hint in ("int", "Integer"):
            ex_row.append("1")
        elif m.type_hint in ("Decimal", "float"):
            ex_row.append("0.00")
        elif m.type_hint == "bool":
            ex_row.append("true")
        elif m.type_hint == "date":
            ex_row.append(date.today().isoformat())
        else:
            ex_row.append("")
    if ex_row:
        ex_row[0] = "__example__"
    writer.writerow(ex_row)

    return buf.getvalue().encode("utf-8-sig")  # BOM for Excel compatibility


# ── CSV parsing ───────────────────────────────────────────────────────────────

def parse_csv_rows(content: bytes) -> tuple[list[str], list[dict]]:
    """
    Return (headers, rows).
    Skips blank rows and rows where first cell starts with __ (hint rows).
    Strips the * prefix from required-field headers.
    """
    text = content.decode("utf-8-sig").replace("\r\n", "\n").replace("\r", "\n")
    reader = csv.DictReader(io.StringIO(text))

    if not reader.fieldnames:
        return [], []

    # Normalise headers: strip * prefix, strip whitespace
    clean_headers = [h.lstrip("*").strip() for h in (reader.fieldnames or [])]
    reader.fieldnames = clean_headers

    rows: list[dict] = []
    for raw in reader:
        # Skip hint/comment rows
        first_val = next(iter(raw.values()), "")
        if str(first_val).startswith("__"):
            continue
        # Skip completely blank rows
        if all(v is None or str(v).strip() == "" for v in raw.values()):
            continue
        # Clean values
        rows.append({k: (str(v).strip() if v is not None else "") for k, v in raw.items()})

    return clean_headers, rows


# ── Type coercion ─────────────────────────────────────────────────────────────

def _coerce(value: str, meta: FieldMeta) -> Any:
    """Best-effort coercion from CSV string to Python type."""
    if value == "" or value is None:
        return None

    t = meta.type_hint.lower()

    if t in ("bool",):
        return value.lower() in ("true", "1", "yes", "y")

    if t in ("int", "integer"):
        try:
            return int(value)
        except ValueError:
            raise ValueError(f"expected integer, got '{value}'")

    if t in ("decimal", "float", "numeric"):
        try:
            return Decimal(value)
        except InvalidOperation:
            raise ValueError(f"expected number, got '{value}'")

    if t == "date":
        for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%m/%d/%Y"):
            try:
                return datetime.strptime(value, fmt).date()
            except ValueError:
                continue
        raise ValueError(f"invalid date '{value}' — use YYYY-MM-DD")

    if meta.enum_values and value not in meta.enum_values:
        raise ValueError(f"must be one of {meta.enum_values}, got '{value}'")

    return value  # str passthrough


# ── Base adapter ──────────────────────────────────────────────────────────────

class BaseImportAdapter(ABC):
    """
    Subclass one adapter per importable entity.
    Adapters are stateless singletons — register them in ADAPTER_REGISTRY.
    """
    module:          str               # URL segment, e.g. "products"
    perm_module:     str               # permission prefix, e.g. "products"
    schema_class:    type[BaseModel]   # Pydantic Create schema
    unique_key:      list[str]         # fields used for CSV-level dup detection
    field_overrides: dict[str, str]    # {"supplier_id": "supplier_code"}
    example_row:     dict[str, Any]    # example values for template

    # ── Override in subclasses ────────────────────────────────────────────────

    async def resolve_relations(
        self, row: dict, db: AsyncSession
    ) -> tuple[dict, list[str]]:
        """
        Replace business keys with UUIDs.
        Return (updated_row, list_of_error_strings).
        """
        return row, []

    async def exists_in_db(self, row: dict, db: AsyncSession) -> bool:
        """Return True if the record already exists (based on unique key)."""
        return False

    @abstractmethod
    async def insert(self, data: dict, db: AsyncSession) -> Any:
        """Insert one validated, relation-resolved row. Called only in non-validate mode."""
        ...

    # ── Engine-facing helpers (not normally overridden) ───────────────────────

    def build_template(self) -> bytes:
        return generate_csv_template(
            self.schema_class,
            overrides=getattr(self, "field_overrides", {}),
            example=getattr(self, "example_row", {}),
        )

    def field_metas(self) -> list[FieldMeta]:
        return get_field_metadata(self.schema_class)


# ── Core engine ───────────────────────────────────────────────────────────────

class ImportEngine:
    """Stateless engine — call run() for each import request."""

    async def run(
        self,
        *,
        content:    bytes,
        adapter:    BaseImportAdapter,
        mode:       ImportMode,
        db:         AsyncSession,
        user_id:    Optional[uuid.UUID],
        username:   str,
        user_roles: list[str],
        file_name:  str = "upload.csv",
    ) -> ImportResult:
        headers, raw_rows = parse_csv_rows(content)

        if not headers:
            result = ImportResult(
                total_rows=0, valid_rows=0, failed_rows=0,
                imported=False, import_mode=mode, module=adapter.module,
                errors=[RowError(row=0, field=None, message="CSV is empty or has no headers")],
            )
            await self._record_history(result, adapter, user_id, username, user_roles, file_name, db)
            return result

        metas_by_name: dict[str, FieldMeta] = {}
        for m in adapter.field_metas():
            override = getattr(adapter, "field_overrides", {})
            mapped_name = override.get(m.name, m.name)
            metas_by_name[mapped_name] = m

        errors: list[RowError] = []
        valid_payloads: list[dict] = []
        seen_keys: set[tuple] = set()

        for idx, raw in enumerate(raw_rows, start=2):  # row 1 = header
            row_errors: list[str] = []
            coerced: dict = {}

            # 1. Coerce types
            for col, raw_val in raw.items():
                meta = metas_by_name.get(col)
                if meta is None:
                    continue  # unknown column — ignore
                try:
                    coerced[col] = _coerce(raw_val, meta)
                except ValueError as exc:
                    row_errors.append(f"{col}: {exc}")

            # 2. Check required fields (post-coerce)
            for col, meta in metas_by_name.items():
                if meta.required and coerced.get(col) in (None, ""):
                    row_errors.append(f"{col}: required field is missing")

            if row_errors:
                for msg in row_errors:
                    errors.append(RowError(row=idx, field=None, message=msg))
                continue

            # 3. Separate business-key columns from schema fields.
            #    field_overrides = {"supplier_id": "supplier_code"} means the CSV column
            #    is "supplier_code" (the value) and the schema field is "supplier_id" (the key).
            #    We must NOT pass business-key values through Pydantic as UUID fields — that
            #    would fail validation. Instead, keep them aside and re-attach before
            #    resolve_relations so adapters can find them.
            override = getattr(adapter, "field_overrides", {})
            biz_key_cols: set[str] = set(override.values())  # {"supplier_code"}

            schema_coerced = {k: v for k, v in coerced.items() if k not in biz_key_cols}
            biz_coerced    = {k: v for k, v in coerced.items() if k in biz_key_cols}

            # 4. Pydantic schema validation (schema fields only, no business keys)
            try:
                validated = adapter.schema_class(
                    **{k: v for k, v in schema_coerced.items() if v is not None and v != ""}
                )
            except ValidationError as exc:
                for e in exc.errors():
                    loc = ".".join(str(l) for l in e["loc"])
                    errors.append(RowError(row=idx, field=loc, message=e["msg"]))
                continue

            payload = validated.model_dump()

            # Re-attach business keys so resolve_relations can find them
            payload.update(biz_coerced)

            # 5. Relation resolution (business key → UUID)
            payload, rel_errors = await adapter.resolve_relations(payload, db)
            if rel_errors:
                for msg in rel_errors:
                    errors.append(RowError(row=idx, field=None, message=msg))
                continue

            # 6. CSV-level duplicate detection.
            #    Use the pre-resolve_relations coerced values so that business-key
            #    fields (e.g. product_sku) are still available even after adapters
            #    pop and replace them with UUIDs.
            uk = getattr(adapter, "unique_key", [])
            if uk:
                dup_key = tuple(str(coerced.get(k, payload.get(k))) for k in uk)
                if dup_key in seen_keys:
                    errors.append(RowError(row=idx, field=None,
                                           message=f"Duplicate in CSV: {dict(zip(uk, dup_key))}"))
                    continue
                seen_keys.add(dup_key)

            # 7. DB-level duplicate detection
            if await adapter.exists_in_db(payload, db):
                errors.append(RowError(row=idx, field=None,
                                       message=f"Already exists in database: {dict(zip(uk, [payload.get(k) for k in uk]))}"))
                continue

            valid_payloads.append(payload)

        total     = len(raw_rows)
        valid_ct  = len(valid_payloads)
        failed_ct = total - valid_ct

        # 8. Fail early for strict mode
        if mode == ImportMode.STRICT and errors:
            result = ImportResult(
                total_rows=total, valid_rows=valid_ct, failed_rows=failed_ct,
                errors=errors, imported=False, import_mode=mode, module=adapter.module,
            )
            await self._record_history(result, adapter, user_id, username, user_roles, file_name, db)
            return result

        # 9. Write to DB
        imported = False
        if mode != ImportMode.VALIDATE_ONLY and valid_payloads:
            for payload in valid_payloads:
                await adapter.insert(payload, db)
            await db.flush()
            imported = True

        result = ImportResult(
            total_rows=total, valid_rows=valid_ct, failed_rows=failed_ct,
            errors=errors, imported=imported, import_mode=mode, module=adapter.module,
        )
        await self._record_history(result, adapter, user_id, username, user_roles, file_name, db)
        return result

    # ── Internal ──────────────────────────────────────────────────────────────

    @staticmethod
    async def _record_history(
        result:     ImportResult,
        adapter:    BaseImportAdapter,
        user_id:    Optional[uuid.UUID],
        username:   str,
        user_roles: list[str],
        file_name:  str,
        db:         AsyncSession,
    ) -> None:
        if result.imported:
            status = ImportStatus.COMPLETED if result.failed_rows == 0 else ImportStatus.PARTIAL
        elif result.import_mode == ImportMode.VALIDATE_ONLY:
            status = ImportStatus.VALIDATED
        else:
            status = ImportStatus.FAILED

        record = ImportHistory(
            user_id=user_id,
            username=username,
            user_roles=",".join(user_roles),
            module=adapter.module,
            file_name=file_name,
            import_mode=result.import_mode,
            total_rows=result.total_rows,
            success_count=result.valid_rows if result.imported else 0,
            failure_count=result.failed_rows,
            status=status,
            errors_json=[e.to_dict() for e in result.errors[:500]],  # cap stored errors
        )
        db.add(record)
        # Caller commits the transaction


# ── Error CSV generation ──────────────────────────────────────────────────────

def generate_error_csv(original_rows: list[dict], errors: list[RowError]) -> bytes:
    """
    Produce a CSV of failed rows with an _error column appended.
    original_rows: the raw dicts from parse_csv_rows (row index 2-based)
    errors:        list of RowError with 1-based row numbers (2 = first data row)
    """
    if not original_rows:
        return b""

    # Group errors by row number
    err_map: dict[int, list[str]] = {}
    for e in errors:
        err_map.setdefault(e.row, []).append(
            f"{e.field + ': ' if e.field else ''}{e.message}"
        )

    failed_indices = set(err_map.keys())
    buf = io.StringIO()
    headers = list(original_rows[0].keys()) + ["_import_error"]
    writer = csv.DictWriter(buf, fieldnames=headers)
    writer.writeheader()

    for i, row in enumerate(original_rows, start=2):
        if i in failed_indices:
            row["_import_error"] = " | ".join(err_map[i])
            writer.writerow(row)

    return buf.getvalue().encode("utf-8-sig")


# ── Singleton engine ──────────────────────────────────────────────────────────

import_engine = ImportEngine()
