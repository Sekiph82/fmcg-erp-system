"""Read-only schema parity check for the M01.S03.T002 disposable PostgreSQL DB."""

from __future__ import annotations

import asyncio
import json
import os
import sys
from pathlib import Path
from urllib.parse import urlsplit

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "backend"))

from sqlalchemy import inspect, text
from sqlalchemy.ext.asyncio import create_async_engine

from app.db.base import Base
import app.models  # noqa: F401 - register all application models


EXPECTED_HEAD = "20261029_0025"
EXPECTED_LEGACY_TABLES = {
    "ai_anomalies",
    "ai_suggestions",
    "iot_alert_thresholds",
    "iot_alerts",
    "iot_channels",
    "iot_devices",
    "iot_ingest_messages",
    "iot_machine_states",
    "iot_sensor_data",
    "kb_article_revisions",
    "kb_articles",
    "kb_categories",
    "npd_pilot_batches",
    "npd_projects",
    "npd_stage_gates",
}
SELECTED_TABLES = [
    "users",
    "roles",
    "stocks",
    "stock_movements",
    "cost_layers",
    "journal_entries",
    "journal_lines",
    "webhook_event_logs",
    "webhook_delivery_attempts",
]


def expected_foreign_keys(table):
    return {
        (element.parent.name, element.column.table.name, element.column.name)
        for constraint in table.foreign_key_constraints
        for element in constraint.elements
    }


async def main() -> None:
    url = os.environ.get("DATABASE_URL", "")
    parsed = urlsplit(url)
    expected_name = os.environ.get("M01_S03_T002_DISPOSABLE_TEST_DATABASE_NAME", "")
    if os.environ.get("M01_S03_T002_DISPOSABLE_TEST_DATABASE") != "1":
        raise SystemExit("Refusing DB access without the exact M01 task opt-in.")
    if parsed.hostname not in {"127.0.0.1", "localhost", "::1"}:
        raise SystemExit("Refusing DB access unless DATABASE_URL is loopback-only.")
    if parsed.password is not None:
        raise SystemExit("Refusing DB access when a database password is present.")
    if not expected_name.startswith("fmcg_m01_s03_t002_") or parsed.path.lstrip("/") != expected_name:
        raise SystemExit("Refusing DB access unless the URL matches the exact task DB name.")

    engine = create_async_engine(url)
    try:
        async with engine.connect() as connection:
            public_tables = await connection.run_sync(
                lambda sync_connection: set(
                    inspect(sync_connection).get_table_names(schema="public")
                )
            )
            model_tables = set(Base.metadata.tables)
            current_revision = (
                await connection.execute(text("SELECT version_num FROM alembic_version"))
            ).scalar_one()
            missing = sorted(model_tables - public_tables)
            legacy = sorted(public_tables - model_tables - {"alembic_version"})
            assert current_revision == EXPECTED_HEAD, current_revision
            assert not missing, missing
            assert set(legacy) == EXPECTED_LEGACY_TABLES, legacy

            selected = {}
            for table_name in SELECTED_TABLES:
                model_table = Base.metadata.tables[table_name]
                actual = await connection.run_sync(
                    lambda sync_connection, name=table_name: {
                        "primary_key": inspect(sync_connection)
                        .get_pk_constraint(name, schema="public")
                        .get("constrained_columns")
                        or [],
                        "foreign_keys": inspect(sync_connection).get_foreign_keys(
                            name, schema="public"
                        ),
                        "indexes": inspect(sync_connection).get_indexes(
                            name, schema="public"
                        ),
                    }
                )
                expected_pk = [column.name for column in model_table.primary_key.columns]
                actual_fks = {
                    (column, foreign_key["referred_table"], referenced_column)
                    for foreign_key in actual["foreign_keys"]
                    for column, referenced_column in zip(
                        foreign_key["constrained_columns"],
                        foreign_key["referred_columns"],
                    )
                }
                expected_indexes = {
                    index.name for index in model_table.indexes if index.name
                }
                actual_indexes = {
                    index["name"] for index in actual["indexes"] if index["name"]
                }
                missing_fks = sorted(expected_foreign_keys(model_table) - actual_fks)
                missing_indexes = sorted(expected_indexes - actual_indexes)
                assert actual["primary_key"] == expected_pk, table_name
                assert not missing_fks, (table_name, missing_fks)
                assert not missing_indexes, (table_name, missing_indexes)
                selected[table_name] = {
                    "pk_matches": True,
                    "missing_orm_foreign_keys": missing_fks,
                    "missing_orm_indexes": missing_indexes,
                }

            print(
                json.dumps(
                    {
                        "database": expected_name,
                        "current_revision": current_revision,
                        "model_tables": len(model_tables),
                        "public_tables": len(public_tables),
                        "missing_model_tables": missing,
                        "legacy_tables_not_in_current_model": legacy,
                        "selected_schema_checks": selected,
                        "result": "PASS",
                    },
                    indent=2,
                    sort_keys=True,
                )
            )
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
