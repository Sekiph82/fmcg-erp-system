from types import SimpleNamespace

from app.models.mps import MPSCapacityMode, MPSLine, MPSPlan, MPSStatus
from app.models.mrp import MRPRunStatus
from app.schemas.mps import GenerateFromMRPRequest
from app.services.mps_service import _next_seq, generate_mps_from_mrp, update_mps_line
from app.services.mps_whatif_service import _next_scenario_no
from app.services.mps_capacity_service import run_capacity_scheduling
from app.services.mps_campaign_service import run_campaign_grouping, run_campaign_grouping_validated
from app.services.mps_capacity_service import run_capacity_scheduling_validated
from app.services import mps_advanced_service


class _Result:
    def __init__(self, values):
        self.values = values

    def scalar_one(self):
        return self.values

    def scalar_one_or_none(self):
        return self.values

    def scalars(self):
        return SimpleNamespace(all=lambda: self.values)

    def first(self):
        return self.values.first()


class _Database:
    def __init__(self, dialect, values):
        self.bind = SimpleNamespace(dialect=SimpleNamespace(name=dialect))
        self.values = iter(values)
        self.statements = []

    def get_bind(self):
        return self.bind

    async def execute(self, statement, params=None):
        self.statements.append((statement, params))
        return _Result(next(self.values))

    async def flush(self):
        return None


async def _next(db, prefix, column):
    return await _next_seq(db, prefix, column)


def test_postgres_uses_migration_sequences_and_preserves_number_formats():
    import asyncio

    db = _Database("postgresql", [17, 204])
    assert asyncio.run(_next(db, "MPS-", MPSPlan.plan_no)) == "MPS-000017"
    assert asyncio.run(_next(db, "MPSL-", MPSLine.line_no)) == "MPSL-0000204"
    assert [params["sequence_name"] for _, params in db.statements] == [
        "mps_plan_no_seq",
        "mps_line_no_seq",
    ]


def test_non_postgres_fallback_uses_highest_existing_number_not_row_count():
    import asyncio

    db = _Database("sqlite", [["MPS-000001", "MPS-000009", "MPS-note", "other"]])
    assert asyncio.run(_next(db, "MPS-", MPSPlan.plan_no)) == "MPS-000010"


def test_postgres_whatif_scenarios_use_global_sequence_and_keep_plan_prefix():
    import asyncio
    from uuid import UUID

    db = _Database("postgresql", [7, 8])
    plan_id = UUID("abcdef12-3456-7890-abcd-ef1234567890")
    assert asyncio.run(_next_scenario_no(db, plan_id)) == "WI-ABCDEF-0007"
    assert asyncio.run(_next_scenario_no(db, plan_id)) == "WI-ABCDEF-0008"
    assert [params["sequence_name"] for _, params in db.statements] == [
        "mps_whatif_scenario_no_seq",
        "mps_whatif_scenario_no_seq",
    ]


def test_non_postgres_whatif_fallback_uses_highest_global_suffix():
    import asyncio
    from uuid import UUID

    db = _Database("sqlite", [["WI-ABCDEF-0001", "WI-123456-0009", "WI-not-a-number"]])
    plan_id = UUID("abcdef12-3456-7890-abcd-ef1234567890")
    assert asyncio.run(_next_scenario_no(db, plan_id)) == "WI-ABCDEF-0010"


def test_mps_regeneration_locks_plan_before_status_check():
    import asyncio

    approved_plan = SimpleNamespace(status=MPSStatus.APPROVED)

    class _PlanResult:
        def scalar_one_or_none(self):
            return approved_plan

    class _PlanDatabase:
        def __init__(self):
            self.statements = []

        async def execute(self, statement):
            self.statements.append(statement)
            return _PlanResult()

    db = _PlanDatabase()

    async def run():
        try:
            await generate_mps_from_mrp(db, None, None)
        except ValueError as error:
            assert "Can only generate lines for DRAFT plans" in str(error)
        else:
            raise AssertionError("Approved plan regeneration must be rejected")

    asyncio.run(run())
    assert len(db.statements) == 1
    assert db.statements[0]._for_update_arg is not None


def test_manual_line_update_locks_plan_then_line_in_consistent_order():
    import asyncio

    plan = SimpleNamespace(id="plan", status=MPSStatus.DRAFT)
    line = SimpleNamespace(is_locked=False)

    class _Result:
        def __init__(self, value):
            self.value = value

        def scalar_one_or_none(self):
            return self.value

    class _UpdateDatabase:
        def __init__(self):
            self.statements = []

        async def execute(self, statement):
            self.statements.append(statement)
            return _Result(plan if len(self.statements) == 1 else line)

        async def flush(self):
            return None

    class _EmptyUpdate:
        def model_dump(self, *, exclude_unset):
            return {}

    db = _UpdateDatabase()
    assert asyncio.run(update_mps_line(db, "plan", "line", _EmptyUpdate())) is line
    assert len(db.statements) == 2
    assert all(statement._for_update_arg is not None for statement in db.statements)
    assert "FROM mps_plans" in str(db.statements[0])
    assert "FROM mps_lines" in str(db.statements[1])


def test_manual_line_update_rejects_non_draft_plan_before_line_lookup():
    import asyncio

    plan = SimpleNamespace(status=MPSStatus.APPROVED)

    class _PlanResult:
        def scalar_one_or_none(self):
            return plan

    class _PlanDatabase:
        def __init__(self):
            self.statements = []

        async def execute(self, statement):
            self.statements.append(statement)
            return _PlanResult()

    db = _PlanDatabase()
    try:
        asyncio.run(update_mps_line(db, "plan", "line", SimpleNamespace()))
    except ValueError as error:
        assert "Only DRAFT MPS plans can be edited" in str(error)
    else:
        raise AssertionError("Approved MPS plans must not allow manual line edits")
    assert len(db.statements) == 1
    assert db.statements[0]._for_update_arg is not None


def test_capacity_scheduler_locks_plan_before_reading_lines():
    import asyncio

    class _FlushDatabase(_Database):
        async def flush(self):
            return None

    db = _FlushDatabase("sqlite", [SimpleNamespace(status=MPSStatus.DRAFT, capacity_mode=MPSCapacityMode.INFINITE), [], []])
    assert asyncio.run(run_capacity_scheduling(db, "plan"))["mode"] == "INFINITE"
    plan_statement = db.statements[0][0]
    assert "FROM mps_plans" in str(plan_statement)
    assert plan_statement._for_update_arg is not None


def test_campaign_grouping_locks_plan_before_reading_lines():
    import asyncio
    from datetime import date
    from uuid import uuid4

    plan = SimpleNamespace(
        id=uuid4(), status=MPSStatus.DRAFT,
        start_date=date(2026, 1, 1), end_date=date(2026, 1, 31),
    )
    db = _Database("sqlite", [plan, [], []])
    assert asyncio.run(run_campaign_grouping(db, plan.id)) == {
        "campaigns_created": 0,
        "lines_grouped": 0,
        "ungrouped_lines": 0,
        "locked_lines_preserved": 0,
        "changeover_state": "NOT_CONFIGURED",
    }
    plan_statement = db.statements[0][0]
    assert "FROM mps_plans" in str(plan_statement)
    assert plan_statement._for_update_arg is not None


def test_capacity_schedulers_reject_approved_plan_before_line_lookup():
    import asyncio

    approved = SimpleNamespace(status=MPSStatus.APPROVED)

    class _ApprovedPlanDatabase:
        def __init__(self):
            self.statements = []

        async def execute(self, statement):
            self.statements.append(statement)
            return _Result(approved)

    for scheduler in (run_capacity_scheduling, run_capacity_scheduling_validated):
        db = _ApprovedPlanDatabase()
        try:
            asyncio.run(scheduler(db, "plan"))
        except ValueError as error:
            assert "only allowed for DRAFT" in str(error)
        else:
            raise AssertionError("Approved MPS plans must reject capacity scheduling")
        assert len(db.statements) == 1
        assert db.statements[0]._for_update_arg is not None


def test_material_feasibility_rejects_approved_plan_before_line_lookup(monkeypatch):
    import asyncio

    approved = SimpleNamespace(status=MPSStatus.APPROVED)

    async def scoped_plan(_db, _mps_id):
        return approved, None, None

    monkeypatch.setattr(mps_advanced_service, "_scoped_plan", scoped_plan)

    class _NoQueryDatabase:
        async def execute(self, _statement):
            raise AssertionError("Approved plan guard must run before line lookup")

    try:
        asyncio.run(mps_advanced_service.evaluate_material_feasibility(_NoQueryDatabase(), "plan"))
    except ValueError as error:
        assert "only allowed for DRAFT" in str(error)
    else:
        raise AssertionError("Approved MPS plans must reject material feasibility writes")


def test_campaign_runners_reject_approved_plan_before_line_lookup():
    import asyncio

    approved = SimpleNamespace(status=MPSStatus.APPROVED)

    class _ApprovedPlanDatabase:
        def __init__(self):
            self.statements = []

        async def execute(self, statement):
            self.statements.append(statement)
            return _Result(approved)

    for runner in (run_campaign_grouping, run_campaign_grouping_validated):
        db = _ApprovedPlanDatabase()
        try:
            asyncio.run(runner(db, "plan"))
        except ValueError as error:
            assert "only for DRAFT" in str(error) or "only allowed for DRAFT" in str(error)
        else:
            raise AssertionError("Approved MPS plans must reject campaign grouping")
        assert len(db.statements) == 1
        assert db.statements[0]._for_update_arg is not None


def test_empty_mrp_regeneration_removes_stale_unlocked_lines_and_retains_locked_lines():
    import asyncio
    from uuid import uuid4

    run_id = uuid4()
    plan = SimpleNamespace(
        id=uuid4(), status=MPSStatus.DRAFT, mrp_run_id=run_id,
        total_lines=0, overloaded_lines=0, feasible_lines=0, locked_lines=0,
    )
    run = SimpleNamespace(status=MRPRunStatus.COMPLETED)
    unlocked = SimpleNamespace(is_locked=False)
    aggregate = SimpleNamespace(first=lambda: SimpleNamespace(total=1, over=0, feas=0, locked=1))
    queued = [plan, run, [], [unlocked], aggregate, plan]

    class _EmptyRunDatabase:
        def __init__(self):
            self.deleted = []

        async def execute(self, statement):
            return _Result(queued.pop(0))

        async def delete(self, value):
            self.deleted.append(value)

        async def flush(self):
            return None

    db = _EmptyRunDatabase()
    count = asyncio.run(generate_mps_from_mrp(db, plan.id, GenerateFromMRPRequest(mrp_run_id=run_id)))
    assert count == 0
    assert db.deleted == [unlocked]
    assert plan.mrp_run_id == run_id
    assert plan.total_lines == 1
    assert plan.locked_lines == 1
