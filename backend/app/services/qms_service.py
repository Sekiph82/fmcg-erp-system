"""QMS Service — blocking logic, CCP enforcement, sampling, AI agents."""
from __future__ import annotations

import random
import uuid
from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation
from typing import List, Optional

from sqlalchemy import func, select, and_, or_
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.quality import (
    QCInspection, QCStatus, QCDecision, QCType, QCTemplate, QCTemplateParameter,
    HazardAnalysis, CriticalControlPoint, CCPMonitoringLog,
    CorrectiveAction, CorrectiveActionStatus, CorrectiveActionStep,
    QCDeviation, DeviationStatus, RiskLevel,
    LotQualityStatus, ReleaseStatus, AllergenValidationRecord, QualityGateDefinition, QualityGateSeverity, QCTemplate,
    quality_gate_required_templates,
    QMSAIRecommendation, QMSAIAgentType, QMSAIRecStatus,
    SamplingMethod, ParameterType,
)
from app.models.inventory import Lot


RECEIVING_GATE_TRIGGER_EVENT = "ON_RECEIPT"
RECEIVING_GATE_TARGET_MODULE = "procurement"
PRODUCTION_GATE_TARGET_MODULE = "production"
PRODUCTION_RELEASE_GATE_TRIGGER_EVENT = "ON_PRODUCTION_RELEASE"
PRODUCTION_IN_PROCESS_GATE_TRIGGER_EVENT = "ON_IN_PROCESS"
FINISHED_GOODS_GATE_TARGET_MODULE = "inventory"
FINISHED_GOODS_RELEASE_GATE_TRIGGER_EVENT = "ON_FINISHED_GOODS_RELEASE"


# ── Sequence Helpers ──────────────────────────────────────────────────────────

async def _next_seq(db: AsyncSession, model, no_col: str, prefix: str) -> str:
    result = await db.execute(
        select(func.count()).select_from(model)
    )
    count = result.scalar() or 0
    return f"{prefix}-{str(count + 1).zfill(5)}"


# ── QC Template CRUD ──────────────────────────────────────────────────────────

async def create_template(db: AsyncSession, data: dict) -> QCTemplate:
    params = data.pop("parameters", [])
    tmpl = QCTemplate(**data)
    db.add(tmpl)
    await db.flush()
    for p in params:
        db.add(QCTemplateParameter(template_id=tmpl.id, **p))
    return tmpl


async def get_template(
    db: AsyncSession, template_id: uuid.UUID, *, for_update: bool = False
) -> Optional[QCTemplate]:
    query = select(QCTemplate).options(selectinload(QCTemplate.parameters)).where(QCTemplate.id == template_id)
    if for_update:
        query = query.with_for_update()
    r = await db.execute(query)
    return r.scalar_one_or_none()


async def list_templates(db: AsyncSession, qc_type=None, active_only=True) -> List[QCTemplate]:
    q = select(QCTemplate).options(selectinload(QCTemplate.parameters))
    if active_only:
        q = q.where(QCTemplate.is_active == True)
    if qc_type:
        q = q.where(QCTemplate.qc_type == qc_type)
    r = await db.execute(q.order_by(QCTemplate.name))
    return list(r.scalars())


async def list_quality_gate_definitions(
    db: AsyncSession,
    active_only: bool = True,
    trigger_event: Optional[str] = None,
    target_module: Optional[str] = None,
    as_of_date: Optional[date] = None,
) -> List[QualityGateDefinition]:
    query = select(QualityGateDefinition).options(
        selectinload(QualityGateDefinition.required_templates).selectinload(QCTemplate.parameters)
    )
    if active_only:
        query = query.where(QualityGateDefinition.is_active.is_(True))
        as_of = as_of_date or date.today()
        query = query.where(
            QualityGateDefinition.effective_from <= as_of,
            or_(QualityGateDefinition.effective_to.is_(None), QualityGateDefinition.effective_to >= as_of),
        )
    if trigger_event:
        query = query.where(QualityGateDefinition.trigger_event == trigger_event)
    if target_module:
        query = query.where(QualityGateDefinition.target_module == target_module)
    result = await db.execute(
        query.order_by(QualityGateDefinition.target_module, QualityGateDefinition.trigger_event,
                       QualityGateDefinition.code)
    )
    return list(result.scalars())


async def lock_quality_gate_scope(db: AsyncSession, target_module: str, trigger_event: str) -> None:
    """Serialize a transaction against changes to definitions for this gate scope."""
    await lock_quality_gate_scopes(db, [(target_module, trigger_event)])


async def lock_quality_gate_scopes(db: AsyncSession, scopes: list[tuple[str, str]]) -> None:
    """Acquire multiple definition-scope locks in a stable order to avoid deadlocks."""
    keys = sorted({
        f"quality-gate-scope:{module.strip().lower()}:{event.strip().upper()}"
        for module, event in scopes
    })
    for key in keys:
        await db.execute(select(func.pg_advisory_xact_lock(func.hashtextextended(key, 0))))


async def list_receiving_quality_gates(db: AsyncSession, as_of_date: date) -> list[QualityGateDefinition]:
    return await list_quality_gate_definitions(
        db,
        active_only=True,
        trigger_event=RECEIVING_GATE_TRIGGER_EVENT,
        target_module=RECEIVING_GATE_TARGET_MODULE,
        as_of_date=as_of_date,
    )


async def list_production_quality_gates(
    db: AsyncSession, trigger_event: str, as_of_date: date
) -> list[QualityGateDefinition]:
    if trigger_event not in {
        PRODUCTION_RELEASE_GATE_TRIGGER_EVENT,
        PRODUCTION_IN_PROCESS_GATE_TRIGGER_EVENT,
    }:
        return []
    return await list_quality_gate_definitions(
        db,
        active_only=True,
        trigger_event=trigger_event,
        target_module=PRODUCTION_GATE_TARGET_MODULE,
        as_of_date=as_of_date,
    )


async def list_finished_goods_quality_gates(
    db: AsyncSession, as_of_date: date
) -> list[QualityGateDefinition]:
    return await list_quality_gate_definitions(
        db,
        active_only=True,
        trigger_event=FINISHED_GOODS_RELEASE_GATE_TRIGGER_EVENT,
        target_module=FINISHED_GOODS_GATE_TARGET_MODULE,
        as_of_date=as_of_date,
    )


async def ensure_receiving_quality_gates_pass(db: AsyncSession, grn) -> None:
    """Require every configured mandatory incoming template to pass per accepted GRN line."""
    gates = [gate for gate in await list_receiving_quality_gates(db, grn.received_date) if gate.is_mandatory]
    if not gates:
        return

    for line in grn.lines:
        if line.accepted_quantity <= 0:
            continue
        item_id = line.material_id or line.product_id
        if item_id is None:
            continue
        for gate in gates:
            for template in gate.required_templates:
                result = await db.execute(
                    select(QCInspection.id).where(
                        QCInspection.grn_id == grn.id,
                        QCInspection.grn_line_id == line.id,
                        QCInspection.template_id == template.id,
                        QCInspection.qc_type == QCType.INCOMING,
                        QCInspection.status == QCStatus.PASSED,
                        QCInspection.decision == QCDecision.ACCEPT,
                        QCInspection.is_mandatory.is_(True),
                        QCInspection.blocks_progression.is_(True),
                        QCInspection.release_required.is_(True),
                    ).limit(1)
                )
                if result.scalar_one_or_none() is None:
                    raise ValueError(
                        f"GRN {grn.grn_no} cannot be posted: required receiving QC template "
                        f"'{template.name}' for line {line.id} has no accepted, passed inspection."
                    )


async def ensure_production_quality_gates_pass(
    db: AsyncSession, order, trigger_event: str, as_of_date: date
) -> None:
    """Require configured mandatory in-process QC before production release/completion."""
    gates = [
        gate for gate in await list_production_quality_gates(db, trigger_event, as_of_date)
        if gate.is_mandatory
    ]
    process_started_at = getattr(order, "actual_start", None)
    if trigger_event == PRODUCTION_IN_PROCESS_GATE_TRIGGER_EVENT and gates and process_started_at is None:
        raise ValueError(
            f"Production order {order.order_no} cannot continue: in-process QC requires a recorded production start."
        )
    for gate in gates:
        for template in gate.required_templates:
            query = select(QCInspection.id).where(
                    QCInspection.production_order_id == order.id,
                    QCInspection.template_id == template.id,
                    QCInspection.qc_type == QCType.IN_PROCESS,
                    QCInspection.status == QCStatus.PASSED,
                    QCInspection.decision == QCDecision.ACCEPT,
                    QCInspection.is_mandatory.is_(True),
                    QCInspection.blocks_progression.is_(True),
                    QCInspection.release_required.is_(True),
                )
            if trigger_event == PRODUCTION_IN_PROCESS_GATE_TRIGGER_EVENT:
                query = query.where(QCInspection.created_at >= process_started_at)
            result = await db.execute(query.limit(1))
            if result.scalar_one_or_none() is None:
                raise ValueError(
                    f"Production order {order.order_no} cannot continue: required in-process QC template "
                    f"'{template.name}' for {trigger_event} has no accepted, passed inspection."
                )


async def ensure_finished_goods_quality_gates_pass(
    db: AsyncSession, inspection: QCInspection, as_of_date: date
) -> None:
    """Require every configured finished-goods template and mandatory lot inspection to pass."""
    gates = [gate for gate in await list_finished_goods_quality_gates(db, as_of_date) if gate.is_mandatory]
    if not gates:
        return
    if inspection.production_order_id is None or inspection.lot_id is None:
        raise ValueError("Finished-goods release requires production-order and lot traceability when a gate is active.")

    for gate in gates:
        for template in gate.required_templates:
            result = await db.execute(
                select(QCInspection.id).where(
                    QCInspection.production_order_id == inspection.production_order_id,
                    QCInspection.lot_id == inspection.lot_id,
                    QCInspection.qc_type == QCType.FINISHED_GOODS,
                    QCInspection.template_id == template.id,
                    QCInspection.status == QCStatus.PASSED,
                    QCInspection.decision == QCDecision.ACCEPT,
                    QCInspection.is_mandatory.is_(True),
                    QCInspection.blocks_progression.is_(True),
                    QCInspection.release_required.is_(True),
                ).limit(1).with_for_update()
            )
            if result.scalar_one_or_none() is None:
                raise ValueError(
                    f"Finished-goods lot {inspection.lot_number or inspection.lot_id} cannot be released: "
                    f"required QC template '{template.name}' has no accepted, passed inspection."
                )

    unresolved = await db.execute(
        select(QCInspection.id).where(
            QCInspection.production_order_id == inspection.production_order_id,
            QCInspection.lot_id == inspection.lot_id,
            QCInspection.qc_type == QCType.FINISHED_GOODS,
            QCInspection.is_mandatory.is_(True),
            QCInspection.release_required.is_(True),
            or_(
                QCInspection.status != QCStatus.PASSED,
                QCInspection.decision.is_distinct_from(QCDecision.ACCEPT),
            ),
        ).limit(1).with_for_update()
    )
    if unresolved.scalar_one_or_none() is not None:
        raise ValueError(
            f"Finished-goods lot {inspection.lot_number or inspection.lot_id} cannot be released: "
            "another mandatory finished-goods inspection is still unresolved."
        )


async def prepare_receiving_gate_test_result(db: AsyncSession, inspection: QCInspection, data: dict) -> dict:
    """Use the linked QC template as authority for gated inspection results."""
    is_receiving_gate = (
        inspection.qc_type == QCType.INCOMING and inspection.grn_id and inspection.grn_line_id
    )
    is_production_gate = (
        inspection.qc_type == QCType.IN_PROCESS and inspection.production_order_id
    )
    is_finished_goods_gate = (
        inspection.qc_type == QCType.FINISHED_GOODS
        and inspection.production_order_id
        and inspection.lot_id
    )
    if not (
        inspection.is_mandatory and inspection.template_id
        and (is_receiving_gate or is_production_gate or is_finished_goods_gate)
    ):
        return data

    template_result = await db.execute(
        select(QCTemplate)
        .options(selectinload(QCTemplate.parameters))
        .where(QCTemplate.id == inspection.template_id)
    )
    template = template_result.scalar_one_or_none()
    expected_qc_type = (
        QCType.INCOMING if is_receiving_gate
        else QCType.FINISHED_GOODS if is_finished_goods_gate
        else QCType.IN_PROCESS
    )
    if template is None or not template.is_active or template.qc_type != expected_qc_type:
        raise ValueError("A mandatory gated inspection requires an active QC template of the matching type.")
    requested_template_parameter_id = data.get("template_parameter_id")
    if requested_template_parameter_id is not None:
        parameter = next((item for item in template.parameters if item.id == requested_template_parameter_id), None)
    else:
        parameter = next((item for item in template.parameters if item.parameter_id == data.get("parameter_id")), None)
    if parameter is None:
        raise ValueError("The test result must identify a parameter from the linked QC inspection template.")

    # The caller submits measurements. Names, units, specifications, and criticality
    # come only from the versioned/linked QC template, never from request data.
    canonical = dict(data)
    canonical.update({
        "parameter_id": parameter.parameter_id,
        "template_parameter_id": parameter.id,
        "parameter_name": parameter.parameter_name,
        "parameter_type": parameter.parameter_type,
        "unit": parameter.unit,
        "min_spec": parameter.min_value,
        "max_spec": parameter.max_value,
        "expected_text": parameter.target_value,
        "is_critical": parameter.is_critical,
    })
    if parameter.parameter_type == ParameterType.PASS_FAIL:
        observed = str(data.get("text_value") or "").strip().casefold()
        expected = str(parameter.target_value or "").strip().casefold()
        canonical["is_passed"] = bool(expected) and observed == expected
    else:
        canonical["is_passed"] = None
    if parameter.parameter_type == ParameterType.NUMERIC and parameter.target_value:
        if canonical["min_spec"] is None and canonical["max_spec"] is None:
            target_number = Decimal(parameter.target_value)
            canonical["min_spec"] = target_number
            canonical["max_spec"] = target_number
    return canonical


async def get_quality_gate_definition(
    db: AsyncSession, definition_id: uuid.UUID, *, for_update: bool = False
) -> Optional[QualityGateDefinition]:
    query = (
        select(QualityGateDefinition)
        .options(selectinload(QualityGateDefinition.required_templates).selectinload(QCTemplate.parameters))
        .where(QualityGateDefinition.id == definition_id)
    )
    if for_update:
        query = query.with_for_update()
    result = await db.execute(query)
    return result.scalar_one_or_none()


async def _get_valid_required_qc_templates(db: AsyncSession, template_ids: list[uuid.UUID]) -> list[QCTemplate]:
    if len(template_ids) != len(set(template_ids)):
        raise ValueError("Required QC test template IDs must be unique.")
    if not template_ids:
        return []
    result = await db.execute(
        select(QCTemplate)
        .options(selectinload(QCTemplate.parameters))
        .where(QCTemplate.id.in_(template_ids))
        .order_by(QCTemplate.id)
        .with_for_update()
    )
    templates = list(result.scalars())
    by_id = {template.id: template for template in templates}
    if len(by_id) != len(template_ids):
        raise ValueError("One or more required QC test templates do not exist.")
    ordered = [by_id[template_id] for template_id in template_ids]
    if any(not template.is_active for template in ordered):
        raise ValueError("Required QC test templates must be active.")
    if any(
        not template.is_mandatory
        or not template.blocks_progression
        or not template.release_required
        or not template.parameters
        or any(not _qc_parameter_has_specification(parameter) for parameter in template.parameters)
        for template in ordered
    ):
        raise ValueError(
            "Each required QC test must block progression, require release, and define at least one specification parameter."
        )
    return ordered


def _qc_parameter_has_specification(parameter) -> bool:
    parameter_type = getattr(parameter.parameter_type, "value", parameter.parameter_type)
    target = (parameter.target_value or "").strip()
    minimum, maximum = parameter.min_value, parameter.max_value

    if parameter_type == "NUMERIC":
        try:
            target_number = Decimal(target) if target else None
            minimum_number = Decimal(str(minimum)) if minimum is not None else None
            maximum_number = Decimal(str(maximum)) if maximum is not None else None
        except (InvalidOperation, ValueError):
            return False
        values = [value for value in (target_number, minimum_number, maximum_number) if value is not None]
        if not values or any(not value.is_finite() for value in values):
            return False
        if minimum_number is not None and maximum_number is not None and minimum_number > maximum_number:
            return False
        if target_number is not None and minimum_number is not None and target_number < minimum_number:
            return False
        if target_number is not None and maximum_number is not None and target_number > maximum_number:
            return False
        return True

    if parameter_type == "TEXT":
        return bool(target) and minimum is None and maximum is None
    if parameter_type == "BOOLEAN":
        return target.lower() in {"true", "false"} and minimum is None and maximum is None
    if parameter_type == "PASS_FAIL":
        return target.upper() == "PASS" and minimum is None and maximum is None
    return False


async def ensure_qc_template_change_preserves_active_gates(
    db: AsyncSession, template: QCTemplate, changes: dict
) -> None:
    gate_result = await db.execute(
        select(QualityGateDefinition.id)
        .join(
            quality_gate_required_templates,
            quality_gate_required_templates.c.gate_definition_id == QualityGateDefinition.id,
        )
        .where(
            quality_gate_required_templates.c.qc_template_id == template.id,
            QualityGateDefinition.is_active.is_(True),
        )
        .limit(1)
    )
    if gate_result.scalar_one_or_none() is None:
        return

    merged = {
        "is_active": template.is_active,
        "is_mandatory": template.is_mandatory,
        "blocks_progression": template.blocks_progression,
        "release_required": template.release_required,
    }
    merged.update(changes)
    has_parameters = bool(template.parameters) and all(
        _qc_parameter_has_specification(parameter) for parameter in template.parameters
    )
    if not all(merged.values()) or not has_parameters:
        raise ValueError(
            "This QC template is required by an active quality gate; deactivate the gate before weakening or removing its test specification."
        )


async def ensure_qc_template_can_be_deleted(db: AsyncSession, template_id: uuid.UUID) -> None:
    if await qc_template_has_gate_reference(db, template_id):
        raise ValueError(
            "This QC template is linked to a quality gate; remove the gate link before deleting the template."
        )


async def qc_template_has_gate_reference(db: AsyncSession, template_id: uuid.UUID) -> bool:
    result = await db.execute(
        select(QualityGateDefinition.id)
        .join(
            quality_gate_required_templates,
            quality_gate_required_templates.c.gate_definition_id == QualityGateDefinition.id,
        )
        .where(quality_gate_required_templates.c.qc_template_id == template_id)
        .limit(1)
    )
    return result.scalar_one_or_none() is not None


async def create_quality_gate_definition(
    db: AsyncSession, data: dict
) -> QualityGateDefinition:
    code = str(data.get("code", "")).strip().upper()
    data["code"] = code
    data["target_module"] = str(data.get("target_module", "")).strip().lower()
    data["trigger_event"] = str(data.get("trigger_event", "")).strip().upper()
    data.setdefault("effective_from", date.today())
    data.setdefault("version", 1)
    _validate_gate_effective_window(data.get("effective_from"), data.get("effective_to"))
    await _lock_quality_gate_code(db, code)
    await lock_quality_gate_scope(db, data.get("target_module", ""), data.get("trigger_event", ""))
    existing_result = await db.execute(
        select(QualityGateDefinition).where(QualityGateDefinition.code == code)
    )
    existing_versions = list(existing_result.scalars())
    expected_version = max((item.version for item in existing_versions), default=0) + 1
    if data["version"] != expected_version:
        raise ValueError(f"The next version for {code} must be {expected_version}.")
    if any(
        _gate_windows_overlap(
            data["effective_from"], data.get("effective_to"), item.effective_from, item.effective_to
        )
        for item in existing_versions
    ):
        raise ValueError("Quality gate effective-date windows for the same code cannot overlap.")

    template_ids = data.pop("required_template_ids", [])
    templates = await _get_valid_required_qc_templates(db, template_ids)
    _validate_gate_template_scope(data.get("target_module", ""), data.get("trigger_event", ""), templates)
    _validate_quality_gate_policy(
        data.get("severity", QualityGateSeverity.MEDIUM.value),
        data.get("is_mandatory", True),
        data.get("waiver_allowed", False),
        data.get("waiver_reason_required", True),
        data.get("waiver_approval_required", True),
    )
    if data.get("is_active", True) and not templates:
        raise ValueError("An active quality gate must link at least one required QC test template.")
    definition = QualityGateDefinition(**data)
    definition.required_templates = templates
    db.add(definition)
    await db.flush()
    return definition


async def update_quality_gate_definition(
    db: AsyncSession, definition: QualityGateDefinition, changes: dict
) -> QualityGateDefinition:
    await _lock_quality_gate_code(db, definition.code)
    existing_target_scope = str(getattr(definition, "target_module", ""))
    existing_trigger_scope = str(getattr(definition, "trigger_event", ""))
    target_scope = str(changes.get("target_module", existing_target_scope))
    trigger_scope = str(changes.get("trigger_event", existing_trigger_scope))
    if "target_module" in changes:
        changes["target_module"] = target_scope.strip().lower()
        target_scope = changes["target_module"]
    if "trigger_event" in changes:
        changes["trigger_event"] = trigger_scope.strip().upper()
        trigger_scope = changes["trigger_event"]
    await lock_quality_gate_scopes(db, [
        (existing_target_scope, existing_trigger_scope),
        (target_scope, trigger_scope),
    ])
    if "code" in changes and str(changes["code"]).strip().upper() != definition.code:
        raise ValueError("A quality gate code is immutable; create the next version under the existing code.")
    changes.pop("code", None)

    controlled_fields = {
        "effective_from", "name", "gate_type", "trigger_event", "target_module", "description", "severity",
        "is_mandatory", "waiver_allowed", "waiver_reason_required", "waiver_approval_required",
        "required_template_ids", "effective_to",
    }
    today = date.today()
    if definition.effective_from <= today:
        rule_fields = controlled_fields - {"effective_to"}
        if rule_fields.intersection(changes):
            raise ValueError("An effective quality gate version is immutable; create the next version to change its rules.")
        if "effective_to" in changes:
            proposed_end = changes["effective_to"]
            if proposed_end is None and definition.effective_to is not None:
                raise ValueError("A closed quality gate effective period cannot be reopened or rewritten.")
            if proposed_end is not None and proposed_end < today:
                raise ValueError("An effective quality gate version may only be closed today or in the future.")
            if definition.effective_to is not None and proposed_end != definition.effective_to:
                raise ValueError("A closed quality gate effective period cannot be rewritten.")

    template_ids = changes.pop("required_template_ids", None)
    for field_name, value in changes.items():
        setattr(definition, field_name, value)

    _validate_quality_gate_policy(
        definition.severity,
        definition.is_mandatory,
        definition.waiver_allowed,
        definition.waiver_reason_required,
        definition.waiver_approval_required,
    )
    _validate_gate_effective_window(definition.effective_from, definition.effective_to)
    peers_result = await db.execute(
        select(QualityGateDefinition).where(
            QualityGateDefinition.code == definition.code,
            QualityGateDefinition.id != definition.id,
        )
    )
    peers = list(peers_result.scalars())
    if any(
        _gate_windows_overlap(definition.effective_from, definition.effective_to, peer.effective_from, peer.effective_to)
        for peer in peers
    ):
        raise ValueError("Quality gate effective-date windows for the same code cannot overlap.")

    if template_ids is not None:
        definition.required_templates = await _get_valid_required_qc_templates(db, template_ids)
    elif definition.is_active:
        # Activation must re-read and lock existing links too. Otherwise a
        # concurrent QC-template patch could weaken a template while this
        # inactive gate is being activated.
        template_ids = [template.id for template in definition.required_templates]
        definition.required_templates = await _get_valid_required_qc_templates(db, template_ids)

    _validate_gate_template_scope(definition.target_module, definition.trigger_event, definition.required_templates)

    if definition.is_active and not definition.required_templates:
        raise ValueError("An active quality gate must link at least one required QC test template.")
    if definition.is_active and any(
        not template.is_active
        or not template.is_mandatory
        or not template.blocks_progression
        or not template.release_required
        or not template.parameters
        or any(not _qc_parameter_has_specification(parameter) for parameter in template.parameters)
        for template in definition.required_templates
    ):
        raise ValueError("Active quality gates can link only active, required, blocking QC templates with specification parameters.")
    return definition


def _validate_quality_gate_policy(severity, is_mandatory, waiver_allowed, reason_required, approval_required) -> None:
    severity = getattr(severity, "value", severity)
    allowed = {item.value for item in QualityGateSeverity}
    if severity not in allowed:
        raise ValueError("Quality gate severity must be LOW, MEDIUM, HIGH, or CRITICAL.")
    if severity == QualityGateSeverity.CRITICAL.value and not is_mandatory:
        raise ValueError("Critical quality gates must remain mandatory.")
    if severity == QualityGateSeverity.CRITICAL.value and waiver_allowed:
        raise ValueError("Critical quality gates cannot be waived.")
    if waiver_allowed and not reason_required:
        raise ValueError("An allowed waiver must require a reason.")
    if waiver_allowed and not approval_required:
        raise ValueError("An allowed waiver must require quality approval.")


def _validate_gate_template_scope(target_module: str, trigger_event: str, templates: list[QCTemplate]) -> None:
    if target_module.strip().lower() == RECEIVING_GATE_TARGET_MODULE and trigger_event.strip().upper() == RECEIVING_GATE_TRIGGER_EVENT:
        if any(template.qc_type != QCType.INCOMING for template in templates):
            raise ValueError("An ON_RECEIPT procurement gate can link only INCOMING QC templates.")
    if (
        target_module.strip().lower() == PRODUCTION_GATE_TARGET_MODULE
        and trigger_event.strip().upper() in {
            PRODUCTION_RELEASE_GATE_TRIGGER_EVENT,
            PRODUCTION_IN_PROCESS_GATE_TRIGGER_EVENT,
        }
    ):
        if any(template.qc_type != QCType.IN_PROCESS for template in templates):
            raise ValueError("Production release/in-process gates can link only IN_PROCESS QC templates.")
    if (
        target_module.strip().lower() == FINISHED_GOODS_GATE_TARGET_MODULE
        and trigger_event.strip().upper() == FINISHED_GOODS_RELEASE_GATE_TRIGGER_EVENT
    ):
        if any(template.qc_type != QCType.FINISHED_GOODS for template in templates):
            raise ValueError("Finished-goods release gates can link only FINISHED_GOODS QC templates.")


def _validate_gate_effective_window(effective_from: Optional[date], effective_to: Optional[date]) -> None:
    if effective_from is None:
        raise ValueError("effective_from is required.")
    if effective_to is not None and effective_to < effective_from:
        raise ValueError("effective_to must be on or after effective_from.")


def _gate_windows_overlap(start: date, end: Optional[date], other_start: date, other_end: Optional[date]) -> bool:
    return start <= (other_end or date.max) and other_start <= (end or date.max)


async def _lock_quality_gate_code(db: AsyncSession, code: str) -> None:
    # Row locks cannot protect the missing-row gap when a code is first created.
    await db.execute(select(func.pg_advisory_xact_lock(func.hashtextextended(f"quality-gate:{code}", 0))))


# ── Sampling ──────────────────────────────────────────────────────────────────

def calculate_sample_size(template: QCTemplate, total_qty: float = 0.0) -> float:
    if template.sampling_method == SamplingMethod.FIXED:
        return float(template.sample_size or 1)
    if template.sampling_method == SamplingMethod.PERCENTAGE:
        pct = float(template.sample_percentage or 5) / 100
        return max(1.0, total_qty * pct)
    return float(template.sample_size or 1)


# ── QC Blocking / Release Logic ───────────────────────────────────────────────

async def check_qc_gate(db: AsyncSession, lot_id: uuid.UUID, stage: Optional[str] = None) -> dict:
    """Check if a lot is allowed to proceed. Returns blocking status."""
    q = (
        select(QCInspection)
        .where(
            QCInspection.lot_id == lot_id,
            QCInspection.is_mandatory == True,
            QCInspection.blocks_progression == True,
        )
    )
    if stage:
        q = q.where(QCInspection.qc_sub_type == stage)
    r = await db.execute(q.order_by(QCInspection.created_at.desc()))
    inspections = list(r.scalars())

    if not inspections:
        return {"blocked": False, "reason": None, "inspection_id": None,
                "inspection_no": None, "inspection_status": None}

    for insp in inspections:
        if insp.status in (QCStatus.PENDING, QCStatus.IN_PROGRESS):
            return {
                "blocked": True,
                "reason": f"Mandatory QC inspection {insp.inspection_no} is still {insp.status.value}",
                "inspection_id": str(insp.id),
                "inspection_no": insp.inspection_no,
                "inspection_status": insp.status.value,
            }
        if insp.status == QCStatus.FAILED:
            return {
                "blocked": True,
                "reason": f"Mandatory QC inspection {insp.inspection_no} has FAILED",
                "inspection_id": str(insp.id),
                "inspection_no": insp.inspection_no,
                "inspection_status": insp.status.value,
            }

    return {"blocked": False, "reason": None, "inspection_id": None,
            "inspection_no": None, "inspection_status": None}


async def get_or_create_lot_quality_status(db: AsyncSession, lot_id: uuid.UUID) -> LotQualityStatus:
    # The unique lot_id constraint arbitrates concurrent first writers. A
    # PostgreSQL upsert avoids a select-then-insert race, then FOR UPDATE keeps
    # every hold/release/QC status mutation serialized until the caller commits.
    await db.execute(
        pg_insert(LotQualityStatus)
        .values(lot_id=lot_id)
        .on_conflict_do_nothing(index_elements=[LotQualityStatus.lot_id])
    )
    result = await db.execute(
        select(LotQualityStatus)
        .where(LotQualityStatus.lot_id == lot_id)
        .with_for_update()
    )
    return result.scalar_one()


async def hold_lot(db: AsyncSession, lot_id: uuid.UUID, hold_reason: str,
                   quarantine: bool = False, quarantine_location: Optional[str] = None) -> LotQualityStatus:
    lqs = await get_or_create_lot_quality_status(db, lot_id)
    lqs.hold_flag = True
    lqs.hold_reason = hold_reason
    lqs.release_status = ReleaseStatus.QUARANTINED if quarantine else ReleaseStatus.ON_HOLD
    lqs.quarantine_flag = quarantine
    lqs.quarantine_location = quarantine_location
    lqs.fefo_eligible = False
    lqs.shipment_eligible = False
    return lqs


async def release_lot(db: AsyncSession, lot_id: uuid.UUID,
                      released_by_id: uuid.UUID, notes: Optional[str] = None) -> LotQualityStatus:
    lqs = await get_or_create_lot_quality_status(db, lot_id)
    lqs.hold_flag = False
    lqs.quarantine_flag = False
    lqs.release_status = ReleaseStatus.RELEASED
    lqs.released_by_id = released_by_id
    lqs.released_at = datetime.now(timezone.utc)
    lqs.release_notes = notes
    lqs.fefo_eligible = True
    lqs.shipment_eligible = True
    return lqs


async def update_lot_qc_status_from_inspection(db: AsyncSession, inspection: QCInspection) -> None:
    """Sync lot quality status based on a completed inspection decision."""
    if not inspection.lot_id:
        return
    lqs = await get_or_create_lot_quality_status(db, inspection.lot_id)
    lqs.last_inspection_id = inspection.id

    if inspection.decision == QCDecision.ACCEPT:
        lqs.qc_status = "PASSED"
        lqs.hold_flag = False
        lqs.quarantine_flag = False
        lqs.release_status = ReleaseStatus.RELEASED
        lqs.fefo_eligible = True
        lqs.shipment_eligible = True

    elif inspection.decision == QCDecision.REJECT:
        lqs.qc_status = "FAILED"
        lqs.hold_flag = True
        lqs.quarantine_flag = True
        lqs.release_status = ReleaseStatus.QUARANTINED
        lqs.fefo_eligible = False
        lqs.shipment_eligible = False

    elif inspection.decision == QCDecision.CONDITIONAL_RELEASE:
        lqs.qc_status = "CONDITIONAL"
        lqs.hold_flag = False
        lqs.release_status = ReleaseStatus.ON_HOLD
        lqs.fefo_eligible = False
        lqs.shipment_eligible = False

    elif inspection.decision == QCDecision.REWORK:
        lqs.qc_status = "FAILED"
        lqs.hold_flag = True
        lqs.release_status = ReleaseStatus.REWORK
        lqs.fefo_eligible = False
        lqs.shipment_eligible = False


# ── HACCP / CCP ───────────────────────────────────────────────────────────────

async def create_hazard_analysis(db: AsyncSession, data: dict, created_by_id: uuid.UUID) -> HazardAnalysis:
    no = await _next_seq(db, HazardAnalysis, "hazard_no", "HA")
    score = None
    if data.get("likelihood_score") and data.get("severity_score"):
        score = data["likelihood_score"] * data["severity_score"]
    hazard = HazardAnalysis(
        hazard_no=no,
        risk_score=score,
        created_by_id=created_by_id,
        **data,
    )
    db.add(hazard)
    return hazard


async def create_ccp(db: AsyncSession, data: dict) -> CriticalControlPoint:
    no = await _next_seq(db, CriticalControlPoint, "ccp_no", "CCP")
    ccp = CriticalControlPoint(ccp_no=no, **data)
    db.add(ccp)
    return ccp


def check_ccp_limits(ccp: CriticalControlPoint, value: float) -> tuple[bool, float]:
    """Returns (is_within_limits, deviation_amount)."""
    within = True
    deviation = 0.0
    if ccp.critical_limit_min is not None and value < float(ccp.critical_limit_min):
        within = False
        deviation = abs(float(ccp.critical_limit_min) - value)
    if ccp.critical_limit_max is not None and value > float(ccp.critical_limit_max):
        within = False
        deviation = max(deviation, abs(value - float(ccp.critical_limit_max)))
    return within, deviation


async def record_ccp_monitoring(
    db: AsyncSession,
    ccp: CriticalControlPoint,
    data: dict,
    recorded_by_id: uuid.UUID,
) -> CCPMonitoringLog:
    value = float(data.get("recorded_value") or 0)
    within, deviation = check_ccp_limits(ccp, value)

    log = CCPMonitoringLog(
        ccp_id=ccp.id,
        recorded_by_id=recorded_by_id,
        is_within_limits=within,
        is_violation=not within,
        deviation_amount=Decimal(str(deviation)) if deviation else None,
        **data,
    )
    db.add(log)
    await db.flush()

    if not within:
        ca = await _auto_create_corrective_action_for_ccp(db, ccp, log)
        log.corrective_action_id = ca.id
        log.process_blocked = True

    return log


async def _auto_create_corrective_action_for_ccp(
    db: AsyncSession, ccp: CriticalControlPoint, log: CCPMonitoringLog
) -> CorrectiveAction:
    no = await _next_seq(db, CorrectiveAction, "ca_no", "CA")
    ca = CorrectiveAction(
        ca_no=no,
        title=f"CCP Violation: {ccp.ccp_name} — {ccp.parameter_name} out of limits",
        description=(
            f"CCP {ccp.ccp_no} violation detected at {log.monitoring_datetime}. "
            f"Recorded value: {log.recorded_value} {ccp.parameter_unit or ''}. "
            f"Critical limits: min={ccp.critical_limit_min}, max={ccp.critical_limit_max}."
        ),
        severity=RiskLevel.CRITICAL,
        trigger_type="CCP_VIOLATION",
        trigger_id=log.id,
        production_order_id=log.production_order_id,
        lot_id=log.lot_id,
        assigned_to_id=ccp.responsible_user_id,
    )
    db.add(ca)
    await db.flush()

    steps_text = ccp.corrective_action_description.split(";") if ccp.corrective_action_description else []
    for i, step in enumerate(steps_text[:5], 1):
        step = step.strip()
        if step:
            db.add(CorrectiveActionStep(
                corrective_action_id=ca.id,
                step_no=i,
                step_description=step,
                assigned_to_id=ccp.responsible_user_id,
            ))
    return ca


# ── Corrective Actions ────────────────────────────────────────────────────────

async def create_corrective_action(db: AsyncSession, data: dict) -> CorrectiveAction:
    steps = data.pop("steps", [])
    no = await _next_seq(db, CorrectiveAction, "ca_no", "CA")
    ca = CorrectiveAction(ca_no=no, **data)
    db.add(ca)
    await db.flush()
    for s in steps:
        db.add(CorrectiveActionStep(corrective_action_id=ca.id, **s))
    return ca


async def complete_ca_step(db: AsyncSession, step_id: uuid.UUID,
                           completion_notes: Optional[str] = None) -> CorrectiveActionStep:
    r = await db.execute(select(CorrectiveActionStep).where(CorrectiveActionStep.id == step_id))
    step = r.scalar_one_or_none()
    if step:
        step.is_completed = True
        step.completed_at = datetime.now(timezone.utc)
        step.completion_notes = completion_notes
        await _check_ca_completion(db, step.corrective_action_id)
    return step


async def _check_ca_completion(db: AsyncSession, ca_id: uuid.UUID) -> None:
    r = await db.execute(
        select(CorrectiveActionStep).where(CorrectiveActionStep.corrective_action_id == ca_id)
    )
    steps = list(r.scalars())
    if steps and all(s.is_completed for s in steps):
        r2 = await db.execute(select(CorrectiveAction).where(CorrectiveAction.id == ca_id))
        ca = r2.scalar_one_or_none()
        if ca and ca.status == CorrectiveActionStatus.IN_PROGRESS:
            ca.status = CorrectiveActionStatus.COMPLETED
            ca.completed_at = datetime.now(timezone.utc)


# ── QC Deviations ─────────────────────────────────────────────────────────────

async def create_deviation(db: AsyncSession, data: dict, reported_by_id: uuid.UUID) -> QCDeviation:
    no = await _next_seq(db, QCDeviation, "deviation_no", "DEV")
    dev = QCDeviation(deviation_no=no, reported_by_id=reported_by_id, **data)
    db.add(dev)
    return dev


async def auto_create_deviation_from_inspection(
    db: AsyncSession, inspection: QCInspection, reported_by_id: uuid.UUID
) -> QCDeviation:
    no = await _next_seq(db, QCDeviation, "deviation_no", "DEV")
    critical_fails = [t for t in (inspection.test_results or []) if t.is_critical and t.is_passed is False]
    severity = RiskLevel.CRITICAL if critical_fails else RiskLevel.HIGH
    dev = QCDeviation(
        deviation_no=no,
        inspection_id=inspection.id,
        production_order_id=inspection.production_order_id,
        lot_id=inspection.lot_id,
        product_id=inspection.product_id,
        material_id=inspection.material_id,
        deviation_type="QC_FAILURE",
        severity=severity,
        description=f"QC inspection {inspection.inspection_no} failed. "
                    f"Critical failures: {len(critical_fails)}",
        reported_by_id=reported_by_id,
    )
    db.add(dev)
    return dev


# ── Allergen Validation ───────────────────────────────────────────────────────

async def create_allergen_validation(
    db: AsyncSession, data: dict, validated_by_id: uuid.UUID
) -> AllergenValidationRecord:
    no = await _next_seq(db, AllergenValidationRecord, "validation_no", "AV")
    rec = AllergenValidationRecord(
        validation_no=no,
        validated_by_id=validated_by_id,
        **data,
    )
    db.add(rec)
    return rec


# ── QMS Dashboard ─────────────────────────────────────────────────────────────

async def get_qms_dashboard(db: AsyncSession) -> dict:
    today = date.today()

    total = (await db.execute(select(func.count()).select_from(QCInspection))).scalar() or 0
    pending = (await db.execute(
        select(func.count()).select_from(QCInspection)
        .where(QCInspection.status == QCStatus.PENDING)
    )).scalar() or 0
    passed_today = (await db.execute(
        select(func.count()).select_from(QCInspection)
        .where(QCInspection.inspection_date == today, QCInspection.status == QCStatus.PASSED)
    )).scalar() or 0
    failed_today = (await db.execute(
        select(func.count()).select_from(QCInspection)
        .where(QCInspection.inspection_date == today, QCInspection.status == QCStatus.FAILED)
    )).scalar() or 0
    cond_today = (await db.execute(
        select(func.count()).select_from(QCInspection)
        .where(QCInspection.inspection_date == today, QCInspection.status == QCStatus.CONDITIONAL_RELEASE)
    )).scalar() or 0

    from datetime import timedelta
    week_ago = today - timedelta(days=7)
    total_7d = (await db.execute(
        select(func.count()).select_from(QCInspection)
        .where(QCInspection.inspection_date >= week_ago, QCInspection.status.in_([QCStatus.PASSED, QCStatus.FAILED]))
    )).scalar() or 0
    passed_7d = (await db.execute(
        select(func.count()).select_from(QCInspection)
        .where(QCInspection.inspection_date >= week_ago, QCInspection.status == QCStatus.PASSED)
    )).scalar() or 0
    pass_rate = round((passed_7d / total_7d * 100), 1) if total_7d else 0.0

    open_devs = (await db.execute(
        select(func.count()).select_from(QCDeviation)
        .where(QCDeviation.status.in_([DeviationStatus.OPEN, DeviationStatus.UNDER_REVIEW]))
    )).scalar() or 0
    crit_devs = (await db.execute(
        select(func.count()).select_from(QCDeviation)
        .where(QCDeviation.severity == RiskLevel.CRITICAL,
               QCDeviation.status.in_([DeviationStatus.OPEN, DeviationStatus.UNDER_REVIEW]))
    )).scalar() or 0

    open_cas = (await db.execute(
        select(func.count()).select_from(CorrectiveAction)
        .where(CorrectiveAction.status.in_([CorrectiveActionStatus.OPEN, CorrectiveActionStatus.IN_PROGRESS]))
    )).scalar() or 0
    overdue_cas = (await db.execute(
        select(func.count()).select_from(CorrectiveAction)
        .where(CorrectiveAction.due_date < today,
               CorrectiveAction.status.in_([CorrectiveActionStatus.OPEN, CorrectiveActionStatus.IN_PROGRESS]))
    )).scalar() or 0

    active_ccps = (await db.execute(
        select(func.count()).select_from(CriticalControlPoint)
        .where(CriticalControlPoint.is_active == True)
    )).scalar() or 0
    ccp_violations = (await db.execute(
        select(func.count()).select_from(CCPMonitoringLog)
        .where(CCPMonitoringLog.is_violation == True,
               func.date(CCPMonitoringLog.monitoring_datetime) >= week_ago)
    )).scalar() or 0

    hold_lots = (await db.execute(
        select(func.count()).select_from(LotQualityStatus)
        .where(LotQualityStatus.hold_flag == True)
    )).scalar() or 0
    quarantine_lots = (await db.execute(
        select(func.count()).select_from(LotQualityStatus)
        .where(LotQualityStatus.quarantine_flag == True)
    )).scalar() or 0
    pending_release = (await db.execute(
        select(func.count()).select_from(LotQualityStatus)
        .where(LotQualityStatus.release_status == ReleaseStatus.UNRELEASED)
    )).scalar() or 0

    av_pending = (await db.execute(
        select(func.count()).select_from(AllergenValidationRecord)
        .where(AllergenValidationRecord.validation_passed == None)
    )).scalar() or 0

    ai_pending = (await db.execute(
        select(func.count()).select_from(QMSAIRecommendation)
        .where(QMSAIRecommendation.status == QMSAIRecStatus.PENDING)
    )).scalar() or 0

    return dict(
        total_inspections=total,
        pending_inspections=pending,
        passed_today=passed_today,
        failed_today=failed_today,
        conditional_today=cond_today,
        pass_rate_7d=pass_rate,
        open_deviations=open_devs,
        critical_deviations=crit_devs,
        open_corrective_actions=open_cas,
        overdue_corrective_actions=overdue_cas,
        active_ccps=active_ccps,
        ccp_violations_7d=ccp_violations,
        lots_on_hold=hold_lots,
        lots_quarantined=quarantine_lots,
        lots_pending_release=pending_release,
        allergen_validations_pending=av_pending,
        ai_recommendations_pending=ai_pending,
    )


# ── AI Agents ─────────────────────────────────────────────────────────────────

async def run_quality_risk_predictor(
    db: AsyncSession, production_order_id: Optional[uuid.UUID] = None, lot_id: Optional[uuid.UUID] = None
) -> List[QMSAIRecommendation]:
    """Agent 1: Predict likely QC failures and high-risk batches."""
    recs: List[QMSAIRecommendation] = []

    # Analyze historical failure rate for this product/lot
    if lot_id:
        r = await db.execute(
            select(QCInspection).where(QCInspection.lot_id == lot_id)
        )
        insp_list = list(r.scalars())
        fails = [i for i in insp_list if i.status == QCStatus.FAILED]
        if fails:
            rec = QMSAIRecommendation(
                agent_type=QMSAIAgentType.QUALITY_RISK_PREDICTOR,
                lot_id=lot_id,
                production_order_id=production_order_id,
                title="High QC failure rate detected for this lot",
                explanation=f"{len(fails)} out of {len(insp_list)} inspections failed for this lot.",
                recommendation="Perform additional IQC checks before releasing. "
                               "Review supplier quality for incoming materials.",
                risk_level=RiskLevel.HIGH,
                confidence_score=Decimal("82.5"),
                priority_score=8,
                payload={"fail_count": len(fails), "total": len(insp_list)},
            )
            db.add(rec)
            recs.append(rec)

    # Check for open deviations linked to production order
    if production_order_id:
        r = await db.execute(
            select(QCDeviation).where(
                QCDeviation.production_order_id == production_order_id,
                QCDeviation.status.in_([DeviationStatus.OPEN, DeviationStatus.UNDER_REVIEW]),
            )
        )
        open_devs = list(r.scalars())
        if open_devs:
            crit_devs = [d for d in open_devs if d.severity == RiskLevel.CRITICAL]
            title = "Open deviations linked to this production order"
            risk = RiskLevel.CRITICAL if crit_devs else RiskLevel.HIGH
            rec = QMSAIRecommendation(
                agent_type=QMSAIAgentType.QUALITY_RISK_PREDICTOR,
                production_order_id=production_order_id,
                title=title,
                explanation=f"{len(open_devs)} open deviation(s) including {len(crit_devs)} critical.",
                recommendation="Resolve all open deviations before releasing finished goods. "
                               "Ensure corrective actions are documented and verified.",
                risk_level=risk,
                confidence_score=Decimal("90.0"),
                priority_score=9,
                payload={"open_deviations": len(open_devs), "critical": len(crit_devs)},
            )
            db.add(rec)
            recs.append(rec)

    if not recs:
        rec = QMSAIRecommendation(
            agent_type=QMSAIAgentType.QUALITY_RISK_PREDICTOR,
            production_order_id=production_order_id,
            lot_id=lot_id,
            title="No high-risk indicators detected",
            explanation="Based on historical QC data, this batch appears to be low-risk.",
            recommendation="Proceed with standard QC protocols. "
                           "Monitor CCP parameters during production.",
            risk_level=RiskLevel.LOW,
            confidence_score=Decimal("75.0"),
            priority_score=2,
            payload={},
        )
        db.add(rec)
        recs.append(rec)

    return recs


async def run_deviation_analyzer(db: AsyncSession, product_id: Optional[uuid.UUID] = None) -> List[QMSAIRecommendation]:
    """Agent 2: Detect recurring failures and process instability."""
    recs: List[QMSAIRecommendation] = []

    q = select(QCDeviation)
    if product_id:
        q = q.where(QCDeviation.product_id == product_id)
    r = await db.execute(q.where(QCDeviation.status != DeviationStatus.CLOSED))
    devs = list(r.scalars())

    # Group by type
    by_type: dict = {}
    for d in devs:
        by_type.setdefault(d.deviation_type, []).append(d)

    for dtype, group in by_type.items():
        if len(group) >= 2:
            rec = QMSAIRecommendation(
                agent_type=QMSAIAgentType.DEVIATION_ANALYZER,
                title=f"Recurring deviation pattern: {dtype}",
                explanation=f"{len(group)} deviations of type '{dtype}' found. "
                            f"This indicates a systemic process issue.",
                recommendation="Investigate root cause systematically. "
                               "Consider process re-validation or supplier change. "
                               "Update HACCP plan if applicable.",
                risk_level=RiskLevel.HIGH if len(group) >= 3 else RiskLevel.MEDIUM,
                confidence_score=Decimal(str(min(95, 60 + len(group) * 10))),
                priority_score=min(10, 5 + len(group)),
                payload={"deviation_type": dtype, "count": len(group)},
            )
            db.add(rec)
            recs.append(rec)

    # Check CCP violation frequency
    r2 = await db.execute(
        select(CCPMonitoringLog).where(CCPMonitoringLog.is_violation == True)
    )
    violations = list(r2.scalars())
    by_ccp: dict = {}
    for v in violations:
        by_ccp.setdefault(str(v.ccp_id), []).append(v)

    for ccp_id, viol_list in by_ccp.items():
        if len(viol_list) >= 2:
            rec = QMSAIRecommendation(
                agent_type=QMSAIAgentType.DEVIATION_ANALYZER,
                ccp_id=uuid.UUID(ccp_id),
                title=f"Repeated CCP violations detected ({len(viol_list)} times)",
                explanation=f"CCP {ccp_id[:8]}… has violated critical limits {len(viol_list)} times.",
                recommendation="Review CCP critical limits. Re-calibrate monitoring equipment. "
                               "Retrain responsible personnel. Consider process capability study.",
                risk_level=RiskLevel.CRITICAL,
                confidence_score=Decimal("88.0"),
                priority_score=10,
                payload={"ccp_id": ccp_id, "violation_count": len(viol_list)},
            )
            db.add(rec)
            recs.append(rec)

    if not recs:
        rec = QMSAIRecommendation(
            agent_type=QMSAIAgentType.DEVIATION_ANALYZER,
            title="Process appears stable — no recurring deviations",
            explanation="No significant deviation patterns detected in recent data.",
            recommendation="Continue current quality monitoring protocols. "
                           "Review deviations monthly for early trend detection.",
            risk_level=RiskLevel.LOW,
            confidence_score=Decimal("70.0"),
            priority_score=1,
            payload={},
        )
        db.add(rec)
        recs.append(rec)

    return recs


async def run_haccp_assistant(db: AsyncSession, product_id: Optional[uuid.UUID] = None) -> List[QMSAIRecommendation]:
    """Agent 3: Suggest missing CCPs and weak control points."""
    recs: List[QMSAIRecommendation] = []

    # Load existing hazard analyses
    q = select(HazardAnalysis).where(HazardAnalysis.is_active == True)
    if product_id:
        q = q.where(HazardAnalysis.product_id == product_id)
    r = await db.execute(q)
    hazards = list(r.scalars())

    # Load existing CCPs
    ccp_q = select(CriticalControlPoint).where(CriticalControlPoint.is_active == True)
    if product_id:
        ccp_q = ccp_q.where(CriticalControlPoint.product_id == product_id)
    r2 = await db.execute(ccp_q)
    ccps = list(r2.scalars())

    # Find high-risk hazards without CCP
    high_risk_no_ccp = [
        h for h in hazards
        if h.risk_level in (RiskLevel.HIGH, RiskLevel.CRITICAL) and not h.is_ccp
    ]
    if high_risk_no_ccp:
        for h in high_risk_no_ccp[:3]:
            rec = QMSAIRecommendation(
                agent_type=QMSAIAgentType.HACCP_ASSISTANT,
                title=f"Potential missing CCP: {h.process_step} — {h.hazard_type.value}",
                explanation=f"Hazard {h.hazard_no} at '{h.process_step}' is rated {h.risk_level.value} "
                            f"but has no associated CCP.",
                recommendation=f"Evaluate whether a Critical Control Point is needed at '{h.process_step}'. "
                               f"Suggested control: {h.control_measure}. "
                               f"Define critical limits, monitoring frequency, and corrective action.",
                risk_level=h.risk_level,
                confidence_score=Decimal("85.0"),
                priority_score=9,
                payload={"hazard_id": str(h.id), "hazard_no": h.hazard_no,
                         "process_step": h.process_step, "hazard_type": h.hazard_type.value},
            )
            db.add(rec)
            recs.append(rec)

    # CCPs with no recent monitoring logs
    for ccp in ccps:
        r3 = await db.execute(
            select(func.count()).select_from(CCPMonitoringLog)
            .where(CCPMonitoringLog.ccp_id == ccp.id)
        )
        log_count = r3.scalar() or 0
        if log_count == 0:
            rec = QMSAIRecommendation(
                agent_type=QMSAIAgentType.HACCP_ASSISTANT,
                ccp_id=ccp.id,
                title=f"CCP {ccp.ccp_no} has no monitoring records",
                explanation=f"CCP '{ccp.ccp_name}' exists but has no monitoring logs recorded.",
                recommendation=f"Begin monitoring {ccp.parameter_name} as per schedule ({ccp.monitoring_frequency}). "
                               f"Ensure records are maintained for regulatory compliance.",
                risk_level=RiskLevel.HIGH,
                confidence_score=Decimal("92.0"),
                priority_score=8,
                payload={"ccp_id": str(ccp.id), "ccp_no": ccp.ccp_no},
            )
            db.add(rec)
            recs.append(rec)

    # Allergen-related CCP check
    allergen_ccps = [c for c in ccps if c.allergen_related]
    if not allergen_ccps and ccps:
        rec = QMSAIRecommendation(
            agent_type=QMSAIAgentType.HACCP_ASSISTANT,
            title="No allergen-specific CCPs defined",
            explanation="No CCPs are marked as allergen-related. "
                        "If allergens are present in your facility, this may be a compliance gap.",
            recommendation="Review your allergen risk assessment. "
                           "Define a CCP for allergen cross-contact control including "
                           "cleaning validation and verification testing.",
            risk_level=RiskLevel.HIGH,
            confidence_score=Decimal("78.0"),
            priority_score=7,
            payload={"total_ccps": len(ccps)},
        )
        db.add(rec)
        recs.append(rec)

    if not recs:
        rec = QMSAIRecommendation(
            agent_type=QMSAIAgentType.HACCP_ASSISTANT,
            title="HACCP plan appears adequate",
            explanation="All high-risk hazards have associated CCPs and monitoring is active.",
            recommendation="Review the HACCP plan annually or when process changes occur. "
                           "Verify CCP effectiveness through periodic re-validation.",
            risk_level=RiskLevel.LOW,
            confidence_score=Decimal("72.0"),
            priority_score=2,
            payload={},
        )
        db.add(rec)
        recs.append(rec)

    return recs


# -- PDCA Closure

async def close_pdca(db, ca_id):
    from datetime import timezone, datetime as _dt
    from sqlalchemy import select
    from app.models.quality import CorrectiveAction, CorrectiveActionStatus
    r = await db.execute(select(CorrectiveAction).where(CorrectiveAction.id == ca_id))
    ca = r.scalar_one_or_none()
    if ca is None:
        raise ValueError('CorrectiveAction not found')
    if ca.status != CorrectiveActionStatus.VERIFIED:
        raise ValueError('PDCA closure requires status VERIFIED; current status is ' + ca.status.value)
    ca.pdca_closed_at = _dt.now(timezone.utc)
    await db.flush()
    return ca


# -- Batch CCP Monitoring Report

async def ccp_monitoring_batch_report(db, production_order_id):
    from sqlalchemy import select
    from app.models.quality import CCPMonitoringLog
    q = (
        select(CCPMonitoringLog)
        .where(CCPMonitoringLog.production_order_id == production_order_id)
        .order_by(CCPMonitoringLog.monitored_at)
    )
    r = await db.execute(q)
    logs = list(r.scalars())
    total = len(logs)
    deviations = [lg for lg in logs if lg.is_deviation]
    corrective_triggered = [lg for lg in logs if lg.auto_corrective_action]
    return {
        "production_order_id": str(production_order_id),
        "total_measurements": total,
        "deviation_count": len(deviations),
        "corrective_action_triggered_count": len(corrective_triggered),
        "deviation_rate_pct": round(len(deviations) / total * 100, 2) if total else 0.0,
        "measurements": [
            {
                "id": str(lg.id),
                "ccp_id": str(lg.ccp_id),
                "measured_value": str(lg.measured_value),
                "is_deviation": lg.is_deviation,
                "auto_corrective_action": lg.auto_corrective_action,
                "monitored_at": lg.monitored_at.isoformat() if lg.monitored_at else None,
                "monitored_by_id": str(lg.monitored_by_id) if lg.monitored_by_id else None,
            }
            for lg in logs
        ],
    }
