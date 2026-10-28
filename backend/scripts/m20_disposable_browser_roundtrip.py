"""Disposable PostgreSQL fixture and identity proof for the M20 browser roundtrip.

This helper refuses non-loopback or incorrectly named databases. It never prints
DATABASE_URL or a password. Use only with a task-owned disposable PostgreSQL DB.
"""

from __future__ import annotations

import asyncio
import os
import re
import subprocess
import sys
import uuid
from datetime import date
from decimal import Decimal
from pathlib import Path
from urllib.parse import urlsplit

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import text
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import create_async_engine

from app.core.config import settings


def _identity_settings():
    if os.environ.get("M20_DISPOSABLE_TEST_DATABASE") != "1":
        raise SystemExit("Refusing: M20_DISPOSABLE_TEST_DATABASE=1 is required.")
    expected = os.environ.get("M20_DISPOSABLE_TEST_DATABASE_NAME", "")
    if not re.fullmatch(r"fmcg_m20_t004_[a-f0-9]{20,32}", expected):
        raise SystemExit("Refusing: expected a unique fmcg_m20_t004_<hex> database name.")
    url = make_url(settings.DATABASE_URL)
    if url.drivername not in {"postgresql", "postgresql+asyncpg"}:
        raise SystemExit("Refusing: only PostgreSQL is accepted.")
    if url.host not in {"127.0.0.1", "localhost", "::1"} or url.database != expected:
        raise SystemExit("Refusing: DATABASE_URL must name the exact loopback disposable database.")
    return expected, url


async def _print_database_identity() -> None:
    expected, url = _identity_settings()
    engine = create_async_engine(settings.DATABASE_URL)
    try:
        async with engine.connect() as connection:
            row = (await connection.execute(text(
                "SELECT current_database(), COALESCE(inet_server_addr()::text, 'local'), "
                "inet_server_port(), current_user"
            ))).one()
    finally:
        await engine.dispose()
    actual_name, server_address, server_port, role = row
    if actual_name != expected or role != "m20_task":
        raise SystemExit("Refusing: PostgreSQL identity does not match the named disposable database and task-owned role.")
    print(
        "M20 API database identity: "
        f"configured_host={url.host} database={actual_name} server={server_address}:{server_port} "
        f"database_role={role} credentials=REDACTED",
        flush=True,
    )


def _verified_api_listener() -> tuple[str, str]:
    endpoint = os.environ.get("M20_BACKEND_URL", "")
    port = os.environ.get("M20_API_PORT", "")
    parsed = urlsplit(endpoint)
    if (
        parsed.scheme != "http"
        or parsed.hostname != "localhost"
        or parsed.username
        or parsed.password
        or parsed.path not in {"", "/"}
        or parsed.query
        or parsed.fragment
        or not re.fullmatch(r"\d{4,5}", port)
        or str(parsed.port) != port
    ):
        raise SystemExit("Refusing: browser API URL must be credential-free localhost at the runner's explicit port.")
    return endpoint, port


def _print_api_listener() -> None:
    endpoint, port = _verified_api_listener()
    print(
        f"M20 API listener: browser_endpoint={endpoint} bound_host=127.0.0.1 port={port}",
        flush=True,
    )


async def _seed() -> None:
    expected, _ = _identity_settings()
    await _print_database_identity()
    username = os.environ.get("M20_TEST_USERNAME", "")
    password = os.environ.get("E2E_PASSWORD", "")
    if not re.fullmatch(r"m20-planner-[a-f0-9]{12}", username) or len(password) < 16:
        raise SystemExit("Refusing: provide a synthetic m20-planner-<12 hex> username and an ephemeral 16+ char password.")

    from app.core.security import hash_password
    from app.db.session import AsyncSessionLocal
    from app.models.company import Company, CompanyUserRole, UserCompanyAccess
    from app.models.master import Product, ProductCategory, UnitOfMeasure, Warehouse, WarehouseType
    from app.models.mps import MPSCapacityMode, MPSFeasibilityStatus, MPSLine, MPSPlan
    from app.models.mrp import MRPRun, MRPRunStatus, MRPTrigger
    from app.models.planning import ResourceCalendar
    from app.models.production_advanced import WorkCenter, WorkCenterType
    from app.models.role import AccessScope, Permission, Role
    from app.models.user import User

    suffix = uuid.uuid4().hex[:12]
    day = date(2026, 11, 3)
    async with AsyncSessionLocal() as db:
        user = User(
            email=f"{username}@example.invalid", username=username,
            full_name="Synthetic M20 Planner", hashed_password=hash_password(password),
            is_active=True, is_superuser=False,
        )
        company = Company(name=f"M20 Synthetic {suffix}", short_code=f"M20{suffix[:8].upper()}", base_currency="KES")
        role = Role(name=f"M20 synthetic planner {suffix}", description="Disposable M20 E2E role", is_system_role=False)
        role.permissions = [
            Permission(code="mps.view", name="View MPS", module="mps", action="view"),
            Permission(code="mps.simulate", name="Simulate MPS", module="mps", action="simulate"),
            Permission(
                code="mps.edit_own_warehouse", name="Edit own warehouse MPS plans",
                module="mps", action="edit_own_warehouse",
            ),
        ]
        user.roles = [role]
        db.add_all([user, company])
        await db.flush()

        warehouse = Warehouse(
            code=f"M20-WH-{suffix}", name=f"M20 Synthetic Warehouse {suffix}",
            warehouse_type=WarehouseType.FINISHED_GOODS, company_id=company.id,
        )
        product = Product(
            sku=f"M20-SKU-{suffix}", name="Synthetic Beverage", category=ProductCategory.BEVERAGE,
            uom=UnitOfMeasure.KG, standard_cost=Decimal("12.5000"), standard_cost_currency="KES",
        )
        work_center = WorkCenter(
            work_center_id=f"M20-WC-{suffix}", name=f"Synthetic Line {suffix}",
            type=WorkCenterType.LINE, capacity=Decimal("10"), capacity_uom="KG/HR",
        )
        db.add_all([warehouse, product, work_center])
        await db.flush()

        run = MRPRun(
            run_no=f"M20-RUN-{suffix}", run_date=day, status=MRPRunStatus.COMPLETED,
            trigger=MRPTrigger.MANUAL, warehouse_id=warehouse.id, triggered_by_id=user.id,
        )
        db.add(run)
        await db.flush()
        plan = MPSPlan(
            plan_no=f"M20-OPS-PLAN-{suffix}", plan_name="Synthetic finite M20 plan",
            start_date=day, end_date=day, mrp_run_id=run.id,
            capacity_mode=MPSCapacityMode.FINITE, created_by_id=user.id,
        )
        db.add(plan)
        await db.flush()
        line = MPSLine(
            line_no=f"M20-LINE-{suffix}", mps_id=plan.id, product_id=product.id,
            period_start=day, period_end=day, planned_start_date=day, planned_end_date=day,
            planned_production_qty=Decimal("40.000"), work_center_id=work_center.id,
            priority_score=Decimal("50"), feasibility_status=MPSFeasibilityStatus.PENDING,
        )
        db.add_all([
            line,
            ResourceCalendar(
                work_center_id=work_center.id, calendar_date=day, available_hours=8,
                shift_1_start="08:00", shift_1_end="16:00", is_holiday=False, is_maintenance=False,
            ),
            UserCompanyAccess(user_id=user.id, company_id=company.id, role=CompanyUserRole.USER, is_default=True),
            AccessScope(
                user_id=user.id, scope_type="warehouse", scope_id=str(warehouse.id),
                scope_name=warehouse.name, can_view=True, can_edit=True, is_active=True,
            ),
        ])
        await db.commit()

    print(
        f"M20 fixture seeded: database={expected} principal={username} superuser=false "
        "permissions=mps.view,mps.simulate,mps.edit_own_warehouse warehouse_scopes=1 "
        f"warehouse_scope_id={warehouse.id} plan={plan.plan_no} line={line.line_no} password=REDACTED",
        flush=True,
    )


async def _verify_scenario(scenario_id: str) -> None:
    expected, _ = _identity_settings()
    username = os.environ.get("M20_TEST_USERNAME", "")
    scenario_uuid = uuid.UUID(scenario_id)
    engine = create_async_engine(settings.DATABASE_URL)
    try:
        async with engine.connect() as connection:
            database, database_role = (await connection.execute(text(
                "SELECT current_database(), current_user"
            ))).one()
            row = (await connection.execute(text(
                "SELECT s.id::text, u.username, p.plan_no, s.scenario_name, "
                "s.impact_service_level_pct::text, s.impact_delay_count::text "
                "FROM mps_whatif_scenarios s "
                "JOIN users u ON u.id = s.created_by_id "
                "JOIN mps_plans p ON p.id = s.mps_id "
                "WHERE s.id = :scenario_id"
            ), {"scenario_id": str(scenario_uuid)})).one_or_none()
    finally:
        await engine.dispose()
    if database != expected or database_role != "m20_task" or row is None or row.username != username or not row.plan_no.startswith("M20-OPS-PLAN-"):
        raise SystemExit("Roundtrip proof failed: created scenario is not present in the exact named DB under the synthetic planner.")
    print(
        f"M20 PostgreSQL persistence proof: database={database} scenario_id={row.id} "
        f"principal={row.username} plan={row.plan_no} name={row.scenario_name} "
        f"service_level={row.impact_service_level_pct} delay_count={row.impact_delay_count}",
        flush=True,
    )


async def main() -> None:
    if len(sys.argv) < 2 or sys.argv[1] not in {"identity", "seed", "serve", "verify"}:
        raise SystemExit("usage: python scripts/m20_disposable_browser_roundtrip.py identity|seed|serve|verify [scenario-id]")
    action = sys.argv[1]
    if action == "identity":
        await _print_database_identity()
        if os.environ.get("M20_BACKEND_URL"):
            _print_api_listener()
    elif action == "seed":
        await _seed()
    elif action == "verify":
        if len(sys.argv) != 3:
            raise SystemExit("verify requires the browser-created scenario UUID")
        await _verify_scenario(sys.argv[2])
    else:
        await _print_database_identity()
        _, port = _verified_api_listener()
        _print_api_listener()
        completed = subprocess.run([
            sys.executable, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1",
            "--port", port, "--lifespan", "off",
        ], check=False)
        raise SystemExit(completed.returncode)


if __name__ == "__main__":
    asyncio.run(main())
