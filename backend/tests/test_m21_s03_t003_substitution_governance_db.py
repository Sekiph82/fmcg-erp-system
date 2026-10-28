"""Disposable PostgreSQL integration for policy-gated material substitutions."""
from __future__ import annotations

import os
import re
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy import select, text

from app.db.session import AsyncSessionLocal, engine
from app.models.audit_log import AuditLog
from app.models.bom import (
    AdvancedBOM,
    AdvancedBOMLine,
    BOMSubstitute,
    BOMSubstituteGroup,
    BOMSubstitutionDecision,
    BOMSubstitutionRequest,
    BOMType,
    BasisType,
    ComponentType,
    ItemLinkType,
    SubstitutionPolicy,
)
from app.models.user import User
from app.models.master import Material, MaterialType, UnitOfMeasure
from app.schemas.bom import SubstitutionRequestCreate
from app.services.bom_explosion_service import BOMExplosionError, explode_bom
from app.services.bom_substitution_service import (
    SubstitutionWorkflowError,
    create_request,
    decide_request,
    required_approver_roles,
)


pytestmark = pytest.mark.skipif(
    os.environ.get("M21_DISPOSABLE_TEST_DATABASE") != "1",
    reason="requires the task-owned disposable PostgreSQL runner",
)


@pytest.mark.asyncio
async def test_emergency_substitution_requires_shortage_evidence_and_independent_approvals():
    expected_database = os.environ.get("M21_DISPOSABLE_TEST_DATABASE_NAME", "")
    assert re.fullmatch(r"fmcg_m21_s03_t003_[a-f0-9]{20,32}", expected_database)
    assert engine.url.drivername in {"postgresql", "postgresql+asyncpg"}
    assert engine.url.host in {"127.0.0.1", "localhost", "::1"}
    assert engine.url.database == expected_database
    suffix = uuid4().hex[:12]

    async with AsyncSessionLocal() as db:
        try:
            assert (await db.execute(text("SELECT current_database()"))).scalar_one() == expected_database
            requester = User(
                email=f"requester-{suffix}@example.invalid", username=f"requester-{suffix}",
                full_name="Synthetic Requester", hashed_password="synthetic-test-only",
            )
            planner = User(
                email=f"planner-{suffix}@example.invalid", username=f"planner-{suffix}",
                full_name="Synthetic Planner", hashed_password="synthetic-test-only",
            )
            quality = User(
                email=f"quality-{suffix}@example.invalid", username=f"quality-{suffix}",
                full_name="Synthetic QA", hashed_password="synthetic-test-only",
            )
            db.add_all([requester, planner, quality])
            bom = AdvancedBOM(
                bom_code=f"M21-T003-BOM-{suffix}", bom_name="Synthetic emergency substitution BOM",
                bom_type=BOMType.FORMULA, base_qty=Decimal("100"), base_uom="KG",
            )
            group = BOMSubstituteGroup(
                group_code=f"M21-T003-GRP-{suffix}", group_name="Synthetic emergency group",
                policy=SubstitutionPolicy.EMERGENCY_ONLY,
            )
            db.add_all([bom, group])
            await db.flush()
            line = AdvancedBOMLine(
                bom_id=bom.id, line_no=1, component_type=ComponentType.RAW,
                item_type=ItemLinkType.MATERIAL, item_id=uuid4(), item_name="Primary material",
                required_qty=Decimal("10"), required_uom="KG", basis_type=BasisType.PER_BATCH,
                wastage_pct=Decimal("5"), process_loss_pct=Decimal("5"),
                substitute_group_id=group.id, substitution_policy=SubstitutionPolicy.EMERGENCY_ONLY,
            )
            alternate_master = Material(
                code=f"ALT-{suffix}", name="Emergency alternate", material_type=MaterialType.RAW,
                uom=UnitOfMeasure.KG, is_active=True,
            )
            db.add(alternate_master)
            await db.flush()
            substitute = BOMSubstitute(
                group_id=group.id, item_type=ItemLinkType.MATERIAL, item_id=alternate_master.id,
                item_name="Emergency alternate", item_code=f"ALT-{suffix}", priority=1,
                qty_ratio=Decimal("0.85"), is_active=True,
            )
            db.add_all([line, substitute])
            await db.flush()

            assert required_approver_roles(SubstitutionPolicy.EMERGENCY_ONLY) == ("PLANNER", "QUALITY")
            emergency_request_body = SubstitutionRequestCreate(
                bom_id=bom.id, bom_line_id=line.id, substitute_id=substitute.id, target_qty=Decimal("100"),
                context_reference=f"PO-{suffix}",
                reason="Primary material is unavailable for the scheduled batch.",
                shortage_evidence_reference=f"SHORTAGE-RECORD-{suffix}",
            )
            line.substitution_policy = SubstitutionPolicy.NO_SUB
            await db.flush()
            with pytest.raises(SubstitutionWorkflowError, match="policies differ"):
                await create_request(db, emergency_request_body, requester)
            line.substitution_policy = SubstitutionPolicy.EMERGENCY_ONLY
            await db.flush()

            with pytest.raises(SubstitutionWorkflowError, match="traceable shortage evidence"):
                await create_request(
                    db,
                    SubstitutionRequestCreate(
                        bom_id=bom.id, bom_line_id=line.id, substitute_id=substitute.id, target_qty=Decimal("100"),
                        context_reference=f"PO-{suffix}",
                        reason="Emergency alternate needed because primary material is unavailable for the scheduled batch.",
                    ),
                    requester,
                )

            request = await create_request(
                db,
                SubstitutionRequestCreate(
                    bom_id=bom.id, bom_line_id=line.id, substitute_id=substitute.id, target_qty=Decimal("100"),
                    context_reference=f"PO-{suffix}",
                    reason="Primary material cannot meet the scheduled quantity and delivery date; use the recorded shortage evidence.",
                    shortage_evidence_reference=f"SHORTAGE-RECORD-{suffix}",
                ),
                requester,
            )
            await db.flush()
            assert request.substitute_qty == Decimal("9.3500")
            with pytest.raises(BOMExplosionError, match="fully approved"):
                await explode_bom(db, bom.id, Decimal("100"), [request.id], f"PO-{suffix}")
            request.status = "APPROVED"
            await db.flush()
            with pytest.raises(BOMExplosionError, match="required approval evidence"):
                await explode_bom(db, bom.id, Decimal("100"), [request.id], f"PO-{suffix}")
            request.status = "PENDING"
            await db.flush()

            with pytest.raises(SubstitutionWorkflowError, match="requester cannot"):
                await decide_request(
                    db, request.id, approver_role="PLANNER", decision="APPROVED",
                    reason="Requester must not self-approve.", actor=requester,
                )

            line.substitution_policy = SubstitutionPolicy.NO_SUB
            await db.flush()
            with pytest.raises(SubstitutionWorkflowError, match="policy or group changed"):
                await decide_request(
                    db, request.id, approver_role="PLANNER", decision="APPROVED",
                    reason="A stale request cannot be approved after the line policy changes.", actor=planner,
                )
            line.substitution_policy = SubstitutionPolicy.EMERGENCY_ONLY
            await db.flush()

            await decide_request(
                db, request.id, approver_role="PLANNER", decision="APPROVED",
                reason="Planner confirms no timely primary-material supply.", actor=planner,
            )
            await db.flush()
            assert request.status == "PENDING"
            with pytest.raises(SubstitutionWorkflowError, match="different users"):
                await decide_request(
                    db, request.id, approver_role="QUALITY", decision="APPROVED",
                    reason="Synthetic quality approval attempt by same actor.", actor=planner,
                )

            line.process_loss_pct = Decimal("6")
            await db.flush()
            with pytest.raises(SubstitutionWorkflowError, match="changed; submit a new request"):
                await decide_request(
                    db, request.id, approver_role="QUALITY", decision="APPROVED",
                    reason="Stale planner approval must not approve changed recipe inputs.", actor=quality,
                )
            line.process_loss_pct = Decimal("5")
            await db.flush()

            await decide_request(
                db, request.id, approver_role="QUALITY", decision="APPROVED",
                reason="QA reviewed specification and allergen impacts.", actor=quality,
            )
            await db.flush()
            assert request.status == "APPROVED"
            assert {row.approver_role for row in request.decisions} == {"PLANNER", "QUALITY"}

            result = await explode_bom(db, bom.id, Decimal("100"), [request.id], f"PO-{suffix}")
            assert len(result.flat_requirements) == 1
            assert result.flat_requirements[0]["item_name"] == "Emergency alternate"
            assert Decimal(str(result.flat_requirements[0]["total_adjusted_qty"])) == Decimal("9.35")
            assert result.nodes[0].substitution_request_id == str(request.id)
            substitute.qty_ratio = Decimal("0.90")
            await db.flush()
            with pytest.raises(BOMExplosionError, match="changed after the request"):
                await explode_bom(db, bom.id, Decimal("100"), [request.id], f"PO-{suffix}")
            substitute.qty_ratio = Decimal("0.85")
            line.process_loss_pct = Decimal("6")
            await db.flush()
            with pytest.raises(BOMExplosionError, match="changed after the request"):
                await explode_bom(db, bom.id, Decimal("100"), [request.id], f"PO-{suffix}")
            line.process_loss_pct = Decimal("5")
            await db.flush()
            line.substitution_policy = SubstitutionPolicy.NO_SUB
            await db.flush()
            with pytest.raises(BOMExplosionError, match="active group"):
                await explode_bom(db, bom.id, Decimal("100"), [request.id], f"PO-{suffix}")
            line.substitution_policy = SubstitutionPolicy.EMERGENCY_ONLY
            await db.flush()
            with pytest.raises(BOMExplosionError, match="different production/order context"):
                await explode_bom(db, bom.id, Decimal("100"), [request.id], f"OTHER-{suffix}")

            wrong_uom_master = Material(
                code=f"ALT-L-{suffix}", name="Wrong-UOM alternate", material_type=MaterialType.RAW,
                uom=UnitOfMeasure.L, is_active=True,
            )
            db.add(wrong_uom_master)
            await db.flush()
            wrong_uom_substitute = BOMSubstitute(
                group_id=group.id, item_type=ItemLinkType.MATERIAL, item_id=wrong_uom_master.id,
                item_name=wrong_uom_master.name, item_code=wrong_uom_master.code, priority=2, is_active=True,
            )
            db.add(wrong_uom_substitute)
            await db.flush()
            with pytest.raises(SubstitutionWorkflowError, match="does not match BOM line UOM"):
                await create_request(
                    db,
                    SubstitutionRequestCreate(
                        bom_id=bom.id, bom_line_id=line.id, substitute_id=wrong_uom_substitute.id,
                        target_qty=Decimal("100"),
                        context_reference=f"PO-UOM-{suffix}", reason="Use a material with a mismatched unit.",
                        shortage_evidence_reference=f"SHORTAGE-UOM-{suffix}",
                    ),
                    requester,
                )

            # Requests may only be applied to lines directly owned by their BOM, even
            # when a nested child line occurs once and the persisted row is malformed.
            child_bom = AdvancedBOM(
                bom_code=f"M21-T003-CHILD-{suffix}", bom_name="Synthetic repeated child",
                bom_type=BOMType.FORMULA, base_qty=Decimal("100"), base_uom="KG",
            )
            root_bom = AdvancedBOM(
                bom_code=f"M21-T003-ROOT-{suffix}", bom_name="Synthetic repeated root",
                bom_type=BOMType.MULTILEVEL, base_qty=Decimal("100"), base_uom="KG",
            )
            db.add_all([child_bom, root_bom])
            await db.flush()
            child_line = AdvancedBOMLine(
                bom_id=child_bom.id, line_no=1, component_type=ComponentType.RAW,
                item_type=ItemLinkType.MATERIAL, item_id=uuid4(), item_name="Nested primary",
                required_qty=Decimal("10"), required_uom="KG", basis_type=BasisType.PER_BATCH,
                substitute_group_id=group.id, substitution_policy=SubstitutionPolicy.EMERGENCY_ONLY,
            )
            db.add_all([
                child_line,
                AdvancedBOMLine(
                    bom_id=root_bom.id, line_no=1, component_type=ComponentType.INTERMEDIATE,
                    item_type=ItemLinkType.PRODUCT, item_id=uuid4(), item_name="Single intermediate",
                    child_bom_id=child_bom.id, required_qty=Decimal("100"), required_uom="KG",
                    basis_type=BasisType.PER_BATCH,
                ),
            ])
            await db.flush()
            nested_context = f"PO-NESTED-{suffix}"
            nested_request = await create_request(
                db,
                SubstitutionRequestCreate(
                    bom_id=child_bom.id, bom_line_id=child_line.id, substitute_id=substitute.id, target_qty=Decimal("100"),
                    context_reference=nested_context,
                    reason="Primary is unavailable for this synthetic nested production batch.",
                    shortage_evidence_reference=f"SHORTAGE-NESTED-{suffix}",
                ),
                requester,
            )
            await decide_request(
                db, nested_request.id, approver_role="PLANNER", decision="APPROVED",
                reason="Planner confirms synthetic nested shortage.", actor=planner,
            )
            await decide_request(
                db, nested_request.id, approver_role="QUALITY", decision="APPROVED",
                reason="QA approves synthetic alternate specification.", actor=quality,
            )
            with pytest.raises(BOMExplosionError, match="different BOM"):
                await explode_bom(db, root_bom.id, Decimal("100"), [nested_request.id], nested_context)

            # Even a malformed row carrying the root BOM ID cannot bind approval to
            # a line actually owned by its nested child.
            malformed_request = BOMSubstitutionRequest(
                bom_id=root_bom.id, bom_line_id=child_line.id, substitute_id=substitute.id,
                policy=SubstitutionPolicy.EMERGENCY_ONLY.value, target_qty=Decimal("100"),
                substitute_qty=Decimal("8.5"), context_reference=nested_context,
                reason="Synthetic malformed duplicate occurrence test.",
                shortage_evidence_reference=f"SHORTAGE-MALFORMED-{suffix}",
                requested_by_id=requester.id, requester_email=requester.email,
                requester_name=requester.full_name, status="APPROVED",
            )
            db.add(malformed_request)
            await db.flush()
            db.add_all([
                BOMSubstitutionDecision(
                    request_id=malformed_request.id, approver_role="PLANNER", decision="APPROVED",
                    actor_id=planner.id, actor_email=planner.email, actor_name=planner.full_name,
                    reason="Planner approved malformed synthetic record.",
                ),
                BOMSubstitutionDecision(
                    request_id=malformed_request.id, approver_role="QUALITY", decision="APPROVED",
                    actor_id=quality.id, actor_email=quality.email, actor_name=quality.full_name,
                    reason="QA approved malformed synthetic record.",
                ),
            ])
            await db.flush()
            with pytest.raises(BOMExplosionError, match="does not directly own"):
                await explode_bom(db, root_bom.id, Decimal("100"), [malformed_request.id], nested_context)

            decisions = await db.scalars(
                select(BOMSubstitutionDecision).where(BOMSubstitutionDecision.request_id == request.id)
            )
            assert len(list(decisions)) == 2
            audit_events = await db.scalars(
                select(AuditLog).where(
                    AuditLog.target_type == "bom_substitution_request",
                    AuditLog.target_id == str(request.id),
                )
            )
            assert {event.event_type for event in audit_events} == {
                "BOM_SUBSTITUTION_REQUESTED", "BOM_SUBSTITUTION_APPROVED",
            }
        finally:
            await db.rollback()
