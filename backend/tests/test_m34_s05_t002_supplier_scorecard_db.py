"""M34.S05.T002: DB-backed supplier scorecard source and scope coverage."""
from __future__ import annotations

import os
import re
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from uuid import UUID, uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import delete, select
from sqlalchemy.engine import URL

from app.core.config import settings
from app.core.security import create_access_token
from app.db.session import AsyncSessionLocal, engine
from app.main import app
from app.models.company import Branch, Company
from app.models.esg import (
    SupplierSustainabilityRisk,
    SupplierSustainabilityScore,
    SupplierSustainabilityStatus,
)
from app.models.master import Supplier, Warehouse, WarehouseType
from app.models.procurement import (
    GRNLine,
    GRNStatus,
    GoodsReceipt,
    POStatus,
    POLine,
    PurchaseOrder,
    SupplierEvaluation,
)
from app.models.quality import SupplierFoodSafetyApproval, SupplierFoodSafetyStatus
from app.models.role import AccessScope, Permission, Role
from app.models.two_factor import TwoFAMethod, User2FASettings
from app.models.user import User


TASK_DB_ENV = "M34_S05_T002_DISPOSABLE_TEST_DATABASE"
TASK_DB_NAME_ENV = "M34_S05_T002_DISPOSABLE_TEST_DATABASE_NAME"
TASK_DB_PATTERN = re.compile(r"fmcg_m34_s05_t002_[a-f0-9]{24}")


def _is_task_database(url, expected_name: str | None) -> bool:
    return bool(
        url.drivername in {"postgresql", "postgresql+asyncpg"}
        and url.host in {"127.0.0.1", "localhost", "::1"}
        and url.password is None
        and isinstance(expected_name, str)
        and TASK_DB_PATTERN.fullmatch(expected_name)
        and url.database == expected_name
    )


def _require_task_database() -> None:
    expected_name = os.environ.get(TASK_DB_NAME_ENV)
    if os.environ.get(TASK_DB_ENV) != "1":
        pytest.skip(f"Run only with {TASK_DB_ENV}=1 for this task-owned disposable PostgreSQL database.")
    if not _is_task_database(engine.url, expected_name):
        pytest.fail(
            "Refusing integration writes: DATABASE_URL must match this task's exact passwordless loopback database."
        )


def _auth_cookies(user: User) -> dict[str, str]:
    return {
        settings.AUTH_COOKIE_NAME: create_access_token(
            str(user.id), session_version=user.auth_session_version
        )
    }


def _evaluation(
    *,
    supplier_id: UUID,
    evaluator_id: UUID,
    branch_id: UUID,
    day: date,
    on_time: str,
    quality: str,
    price: str,
    responsiveness: str,
    overall: str,
) -> SupplierEvaluation:
    return SupplierEvaluation(
        supplier_id=supplier_id,
        evaluator_id=evaluator_id,
        branch_id=branch_id,
        evaluation_date=day,
        on_time_delivery_score=Decimal(on_time),
        quality_score=Decimal(quality),
        price_competitiveness_score=Decimal(price),
        responsiveness_score=Decimal(responsiveness),
        overall_score=Decimal(overall),
        notes="Synthetic scorecard test input.",
    )


def test_database_guard_rejects_non_task_targets():
    name = "fmcg_m34_s05_t002_0123456789abcdef01234567"
    assert _is_task_database(URL.create("postgresql+asyncpg", host="127.0.0.1", database=name), name)
    assert not _is_task_database(URL.create("postgresql+asyncpg", host="db.invalid", database=name), name)
    assert not _is_task_database(
        URL.create("postgresql+asyncpg", username="postgres", password="secret", host="127.0.0.1", database=name),
        name,
    )
    assert not _is_task_database(URL.create("sqlite+aiosqlite", database=name), name)


@pytest.mark.asyncio(loop_scope="session")
@pytest.mark.skipif(os.environ.get(TASK_DB_ENV) != "1", reason="requires this task's disposable PostgreSQL database")
async def test_supplier_dashboard_rolls_up_linked_sources_and_hides_out_of_scope_signals(monkeypatch):
    _require_task_database()
    monkeypatch.setattr(settings, "SECRET_KEY", "M34-S05-T002-SYNTHETIC-TEST-SECRET-KEY-ONLY")
    suffix = uuid4().hex[:16]
    today = date.today()
    target = Supplier(code=f"M34S05-{suffix}-A", name="Synthetic scorecard supplier", is_active=True)
    unrelated = Supplier(code=f"M34S05-{suffix}-B", name="Synthetic unrelated supplier", is_active=True)
    owner = User(
        email=f"m34-s05-scorecard-owner-{suffix}@example.invalid",
        username=f"m34s05scowner{suffix}",
        full_name="Synthetic scorecard owner",
        hashed_password="not-a-login-credential",
        is_active=True,
        is_superuser=True,
    )
    scoped_user = User(
        email=f"m34-s05-scorecard-scoped-{suffix}@example.invalid",
        username=f"m34s05scscoped{suffix}",
        full_name="Synthetic scoped scorecard viewer",
        hashed_password="not-a-login-credential",
        is_active=True,
        is_superuser=False,
    )
    company = Company(name=f"Synthetic scorecard company {suffix}", short_code=f"S05{suffix[:8]}")
    branch_a = Branch(company=company, name="Synthetic authorized branch", branch_code=f"A{suffix[:8]}")
    branch_b = Branch(company=company, name="Synthetic other branch", branch_code=f"B{suffix[:8]}")
    warehouse_a_id = None
    warehouse_b_id = None
    permission_id = None
    po_ids: list[UUID] = []

    async with AsyncSessionLocal() as db:
        permission = await db.scalar(
            select(Permission).where(Permission.code == "procurement.view_own_scope")
        )
        if permission is None:
            permission = Permission(
                code="procurement.view_own_scope",
                name="View procurement in own scope",
                module="procurement",
                action="view_own_scope",
                is_active=True,
            )
            db.add(permission)
            await db.flush()
            permission_id = permission.id
        scope_role = Role(
            name=f"m34_s05_t002_scope_{suffix}",
            description="Synthetic task test role.",
            is_active=True,
            permissions=[permission],
        )
        scoped_user.roles.append(scope_role)
        db.add_all([target, unrelated, owner, scoped_user, company, branch_a, branch_b, scope_role])
        await db.flush()
        target_id = target.id
        unrelated_id = unrelated.id
        owner_id = owner.id
        scoped_user_id = scoped_user.id
        company_id = company.id
        branch_a_id = branch_a.id
        branch_b_id = branch_b.id
        role_id = scope_role.id
        warehouse_a = Warehouse(
            code=f"S05A{suffix[:8]}",
            name="Synthetic authorized warehouse",
            warehouse_type=WarehouseType.RAW_MATERIAL,
            company_id=company_id,
            branch_id=branch_a_id,
            is_active=True,
        )
        warehouse_b = Warehouse(
            code=f"S05B{suffix[:8]}",
            name="Synthetic other warehouse",
            warehouse_type=WarehouseType.RAW_MATERIAL,
            company_id=company_id,
            branch_id=branch_b_id,
            is_active=True,
        )
        db.add_all([warehouse_a, warehouse_b])
        await db.flush()
        warehouse_a_id = warehouse_a.id
        warehouse_b_id = warehouse_b.id
        scope_id = uuid4()
        db.add_all(
            [
                User2FASettings(
                    user_id=owner_id,
                    is_enabled=True,
                    method=TwoFAMethod.TOTP,
                    secret_key=f"SYNTHETIC-{suffix}-OWNER",
                ),
                AccessScope(
                    id=scope_id,
                    user_id=scoped_user_id,
                    scope_type="branch",
                    scope_id=str(branch_a_id),
                    scope_name="Synthetic authorized branch",
                    can_view=True,
                    is_active=True,
                ),
            ]
        )
        await db.flush()

        evaluations = [
            _evaluation(
                supplier_id=target_id,
                evaluator_id=owner_id,
                branch_id=branch_a_id,
                day=today - timedelta(days=2),
                on_time="80",
                quality="70",
                price="60",
                responsiveness="90",
                overall="75",
            ),
            _evaluation(
                supplier_id=target_id,
                evaluator_id=owner_id,
                branch_id=branch_a_id,
                day=today - timedelta(days=1),
                on_time="100",
                quality="90",
                price="80",
                responsiveness="70",
                overall="85",
            ),
            _evaluation(
                supplier_id=target_id,
                evaluator_id=owner_id,
                branch_id=branch_b_id,
                day=today,
                on_time="10",
                quality="20",
                price="30",
                responsiveness="40",
                overall="25",
            ),
        ]
        esg_rows = [
            SupplierSustainabilityScore(
                supplier_id=target_id,
                supplier_name=target.name,
                assessment_period_start=today - timedelta(days=90),
                assessment_period_end=today - timedelta(days=30),
                overall_score=Decimal("71.00"),
                risk_level=SupplierSustainabilityRisk.MEDIUM,
                status=SupplierSustainabilityStatus.ACTIVE,
            ),
            SupplierSustainabilityScore(
                supplier_id=target_id,
                supplier_name=target.name,
                assessment_period_start=today - timedelta(days=30),
                assessment_period_end=today - timedelta(days=1),
                overall_score=Decimal("88.00"),
                risk_level=SupplierSustainabilityRisk.LOW,
                status=SupplierSustainabilityStatus.ACTIVE,
            ),
            SupplierSustainabilityScore(
                supplier_id=target_id,
                supplier_name=target.name,
                assessment_period_start=today,
                assessment_period_end=today + timedelta(days=1),
                overall_score=Decimal("99.00"),
                risk_level=SupplierSustainabilityRisk.LOW,
                status=SupplierSustainabilityStatus.ACTIVE,
            ),
            SupplierSustainabilityScore(
                supplier_id=target_id,
                supplier_name=target.name,
                assessment_period_start=today - timedelta(days=60),
                assessment_period_end=today - timedelta(days=2),
                overall_score=Decimal("100.00"),
                risk_level=SupplierSustainabilityRisk.LOW,
                status=SupplierSustainabilityStatus.ARCHIVED,
            ),
        ]
        food_safety_rows = [
            SupplierFoodSafetyApproval(
                supplier_id=str(target_id),
                supplier_name=target.name,
                approval_type="BRC",
                status=SupplierFoodSafetyStatus.PENDING,
                audit_score=Decimal("45.00"),
                expiry_date=today + timedelta(days=30),
                created_at=datetime.now(timezone.utc) - timedelta(days=10),
            ),
            SupplierFoodSafetyApproval(
                supplier_id=str(target_id),
                supplier_name=target.name,
                approval_type="BRC",
                status=SupplierFoodSafetyStatus.APPROVED,
                audit_score=Decimal("95.00"),
                expiry_date=today + timedelta(days=30),
                created_at=datetime.now(timezone.utc) - timedelta(days=1),
            ),
            SupplierFoodSafetyApproval(
                supplier_id=str(target_id),
                supplier_name=target.name,
                approval_type="HALAL",
                status=SupplierFoodSafetyStatus.APPROVED,
                audit_score=Decimal("84.00"),
                expiry_date=today - timedelta(days=1),
            ),
            SupplierFoodSafetyApproval(
                supplier_id=str(target_id),
                supplier_name=target.name,
                approval_type="ISO22000",
                status=SupplierFoodSafetyStatus.CONDITIONAL,
                audit_score=Decimal("72.00"),
                expiry_date=None,
            ),
            SupplierFoodSafetyApproval(
                supplier_id=str(unrelated_id),
                supplier_name=target.name,
                approval_type="FSSC",
                status=SupplierFoodSafetyStatus.APPROVED,
                audit_score=Decimal("100.00"),
                expiry_date=today + timedelta(days=365),
            ),
        ]
        db.add_all([*evaluations, *esg_rows, *food_safety_rows])

        for label, branch_id, order_offset, expected_offset, received_offset, status, include_receipt in (
            ("ONTIME", branch_a_id, 30, 10, 10, POStatus.RECEIVED, True),
            ("LATE", branch_a_id, 20, 5, 3, POStatus.RECEIVED, True),
            ("OUTSCOPE", branch_b_id, 2, -2, None, POStatus.DRAFT, False),
        ):
            order = PurchaseOrder(
                po_no=f"M34S05-{suffix}-{label}",
                supplier_id=target_id,
                company_id=company_id,
                branch_id=branch_id,
                order_date=today - timedelta(days=order_offset),
                expected_delivery_date=today - timedelta(days=expected_offset),
                currency="KES",
                status=status,
                created_by_id=owner_id,
            )
            db.add(order)
            await db.flush()
            po_ids.append(order.id)
            if include_receipt:
                line = POLine(
                    po_id=order.id,
                    line_no=1,
                    description=f"Synthetic {label.lower()} scorecard line",
                    ordered_quantity=Decimal("10.000"),
                    unit="KG",
                    unit_price=Decimal("2.5000"),
                    received_quantity=Decimal("10.000"),
                )
                db.add(line)
                await db.flush()
                receipt = GoodsReceipt(
                    grn_no=f"M34S05-{suffix}-{label}-GRN",
                    po_id=order.id,
                    company_id=company_id,
                    branch_id=branch_id,
                    received_date=today - timedelta(days=received_offset),
                    warehouse_id=warehouse_a_id if branch_id == branch_a_id else warehouse_b_id,
                    status=GRNStatus.POSTED,
                    notes="Synthetic scorecard OTIF input.",
                )
                db.add(receipt)
                await db.flush()
                db.add(
                    GRNLine(
                        grn_id=receipt.id,
                        po_line_id=line.id,
                        received_quantity=Decimal("10.000"),
                        accepted_quantity=Decimal("10.000"),
                        unit="KG",
                    )
                )
        await db.commit()

        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://m34-s05-scorecard.test") as anonymous:
                unauthenticated = await anonymous.get("/api/v1/procurement/suppliers/dashboard")
            assert unauthenticated.status_code == 401

            async with AsyncClient(
                transport=transport,
                base_url="http://m34-s05-scorecard.test",
                cookies=_auth_cookies(owner),
            ) as owner_client:
                broad_response = await owner_client.get("/api/v1/procurement/suppliers/dashboard")
            assert broad_response.status_code == 200, broad_response.text
            broad_rows = {row["supplier_id"]: row for row in broad_response.json()}
            target_row = broad_rows[str(target_id)]
            assert target_row["supplier_signals_restricted"] is False
            assert target_row["total_pos"] == 3
            assert target_row["open_pos"] == 1
            assert target_row["otif_order_count"] == 2
            assert target_row["otif_met_order_count"] == 1
            assert Decimal(str(target_row["otif_rate"])) == Decimal("50.00")
            assert target_row["evaluation_count"] == 3
            assert target_row["latest_evaluation_id"] == str(evaluations[2].id)
            assert target_row["last_evaluation_date"] == today.isoformat()
            assert Decimal(str(target_row["avg_on_time_delivery"])) == Decimal("63.33")
            assert Decimal(str(target_row["avg_quality"])) == Decimal("60.00")
            assert Decimal(str(target_row["avg_price_competitiveness"])) == Decimal("56.67")
            assert Decimal(str(target_row["avg_responsiveness"])) == Decimal("66.67")
            assert Decimal(str(target_row["avg_overall"])) == Decimal("61.67")
            assert Decimal(str(target_row["esg_overall_score"])) == Decimal("88.00")
            assert target_row["esg_assessment_period_end"] == (today - timedelta(days=1)).isoformat()
            approvals = {row["approval_type"]: row for row in target_row["food_safety_approvals"]}
            assert set(approvals) == {"BRC", "HALAL", "ISO22000"}
            assert approvals["BRC"]["status"] == SupplierFoodSafetyStatus.APPROVED.value
            assert Decimal(str(approvals["BRC"]["audit_score"])) == Decimal("95.00")
            assert approvals["BRC"]["is_current"] is True
            assert approvals["HALAL"]["is_expired"] is True
            assert approvals["HALAL"]["is_current"] is False
            assert approvals["ISO22000"]["is_current"] is None

            async with AsyncClient(
                transport=transport,
                base_url="http://m34-s05-scorecard.test",
                cookies=_auth_cookies(scoped_user),
            ) as scoped_client:
                scoped_response = await scoped_client.get("/api/v1/procurement/suppliers/dashboard")
            assert scoped_response.status_code == 200, scoped_response.text
            scoped_rows = scoped_response.json()
            assert [row["supplier_id"] for row in scoped_rows] == [str(target_id)]
            scoped_row = scoped_rows[0]
            assert scoped_row["supplier_signals_restricted"] is True
            assert scoped_row["esg_overall_score"] is None
            assert scoped_row["food_safety_approvals"] == []
            assert scoped_row["total_pos"] == 2
            assert scoped_row["evaluation_count"] == 2
            assert scoped_row["latest_evaluation_id"] == str(evaluations[1].id)
            assert Decimal(str(scoped_row["avg_overall"])) == Decimal("80.00")
        finally:
            await db.rollback()
            grn_ids = select(GoodsReceipt.id).where(GoodsReceipt.po_id.in_(po_ids))
            await db.execute(delete(GRNLine).where(GRNLine.grn_id.in_(grn_ids)))
            await db.execute(delete(GoodsReceipt).where(GoodsReceipt.po_id.in_(po_ids)))
            await db.execute(delete(POLine).where(POLine.po_id.in_(po_ids)))
            await db.execute(delete(PurchaseOrder).where(PurchaseOrder.id.in_(po_ids)))
            await db.execute(delete(SupplierEvaluation).where(SupplierEvaluation.supplier_id == target_id))
            await db.execute(
                delete(SupplierSustainabilityScore).where(
                    SupplierSustainabilityScore.supplier_id == target_id
                )
            )
            await db.execute(
                delete(SupplierFoodSafetyApproval).where(
                    SupplierFoodSafetyApproval.supplier_id.in_([str(target_id), str(unrelated_id)])
                )
            )
            await db.execute(delete(Warehouse).where(Warehouse.id.in_([warehouse_a_id, warehouse_b_id])))
            await db.execute(delete(AccessScope).where(AccessScope.id == scope_id))
            await db.execute(delete(User2FASettings).where(User2FASettings.user_id == owner_id))
            await db.execute(delete(User).where(User.id.in_([owner_id, scoped_user_id])))
            await db.execute(delete(Role).where(Role.id == role_id))
            if permission_id is not None:
                await db.execute(delete(Permission).where(Permission.id == permission_id))
            await db.execute(delete(Branch).where(Branch.id.in_([branch_a_id, branch_b_id])))
            await db.execute(delete(Company).where(Company.id == company_id))
            await db.execute(delete(Supplier).where(Supplier.id.in_([target_id, unrelated_id])))
            await db.commit()
