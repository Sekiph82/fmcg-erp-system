from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import HTTPException
from fastapi.routing import APIRoute
from sqlalchemy.dialects import postgresql

from app.api.v1.endpoints import webhooks
from app.core.deps import get_current_active_superuser
from app.models.webhook import DeliveryStatus
from app.schemas.webhook import ReplayRequest
from app.services import webhook_service


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"event_ids": []},
        {"event_code": "   "},
        {"event_code": "invoice.posted", "subscription_ids": []},
        {
            "from_dt": "2026-10-31T00:00:00Z",
            "to_dt": "2026-10-30T00:00:00Z",
        },
        {"from_dt": datetime(2026, 10, 30)},
        {"from_dt": datetime(2026, 10, 30), "to_dt": "2026-10-31T00:00:00Z"},
        {"event_ids": [str(uuid4()) for _ in range(201)]},
        {"event_code": "invoice.posted", "subscription_ids": [str(uuid4()) for _ in range(101)]},
    ],
)
def test_replay_requires_a_bounded_non_empty_scope(payload):
    with pytest.raises(ValueError):
        ReplayRequest.model_validate(payload)


def test_delivery_read_and_replay_routes_require_superuser():
    secured_paths = {
        "/events/replay",
        "/deliveries",
        "/deliveries/dead-letter",
        "/deliveries/{delivery_id}/retry",
    }
    routes = {
        route.path: route
        for route in webhooks.router.routes
        if isinstance(route, APIRoute) and route.path in secured_paths
    }

    assert set(routes) == secured_paths
    for route in routes.values():
        assert any(
            dependency.call is get_current_active_superuser
            for dependency in route.dependant.dependencies
        ), route.path


class _Result:
    def __init__(self, value):
        self.value = value

    def scalar_one_or_none(self):
        return self.value

    def scalars(self):
        return self

    def all(self):
        return self.value


class _Database:
    def __init__(self, results):
        self.results = iter(results)
        self.statements = []
        self.added = []
        self.committed = False

    async def execute(self, statement):
        self.statements.append(statement)
        return _Result(next(self.results))

    def add(self, value):
        self.added.append(value)

    async def flush(self):
        return None

    async def commit(self):
        self.committed = True


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "status",
    [DeliveryStatus.PENDING, DeliveryStatus.RETRYING, DeliveryStatus.SENT],
)
async def test_manual_retry_rejects_attempts_that_are_not_failed(status):
    old = SimpleNamespace(status=status)
    db = _Database([old])

    result = await webhook_service.manual_retry_delivery(db, uuid4())

    assert result is None
    assert len(db.statements) == 1
    assert not db.added
    assert not db.committed


@pytest.mark.asyncio
async def test_manual_retry_spawns_a_new_attempt_only_for_active_subscription(monkeypatch):
    event_id = uuid4()
    subscription_id = uuid4()
    old = SimpleNamespace(
        id=uuid4(),
        event_log_id=event_id,
        subscription_id=subscription_id,
        attempt_no=4,
        status=DeliveryStatus.DEAD_LETTER,
    )
    event = SimpleNamespace(id=event_id)
    subscription = SimpleNamespace(id=subscription_id, active_flag=True)
    db = _Database([old, None, event, subscription])
    monkeypatch.setattr(webhook_service, "_deliver_attempt", _no_op_delivery)
    result = await webhook_service.manual_retry_delivery(db, old.id)

    assert result is db.added[0]
    assert result.attempt_no == 5
    assert result.status == DeliveryStatus.PENDING
    assert old.status == DeliveryStatus.DEAD_LETTER
    assert result.replay_of_id == old.id
    assert db.statements[0]._for_update_arg is not None
    assert db.committed


@pytest.mark.asyncio
async def test_manual_retry_refuses_a_delivery_that_already_has_a_replay_child():
    old = SimpleNamespace(id=uuid4(), status=DeliveryStatus.DEAD_LETTER)
    db = _Database([old, uuid4()])

    assert await webhook_service.manual_retry_delivery(db, old.id) is None
    assert len(db.statements) == 2
    assert not db.added
    assert not db.committed


@pytest.mark.asyncio
async def test_dead_letter_list_excludes_attempts_that_already_have_a_successor():
    db = _Database([[]])

    assert await webhook_service.list_dead_letter_deliveries(db) == []
    sql = str(db.statements[0].compile(dialect=postgresql.dialect()))
    assert "webhook_delivery_attempts.replay_of_id IS NOT NULL" in sql
    assert "webhook_delivery_attempts.status =" in sql


async def _no_op_delivery(_db, _attempt, _event, _subscription):
    return None


@pytest.mark.asyncio
async def test_manual_retry_does_not_send_to_inactive_subscription(monkeypatch):
    old = SimpleNamespace(
        id=uuid4(),
        event_log_id=uuid4(),
        subscription_id=uuid4(),
        attempt_no=1,
        status=DeliveryStatus.FAILED,
    )
    event = SimpleNamespace(id=old.event_log_id)
    subscription = SimpleNamespace(id=old.subscription_id, active_flag=False)
    db = _Database([old, None, event, subscription])
    monkeypatch.setattr(webhook_service, "_deliver_attempt", _no_op_delivery)

    assert await webhook_service.manual_retry_delivery(db, old.id) is None
    assert not db.added
    assert not db.committed


@pytest.mark.asyncio
async def test_replay_queues_only_matching_active_subscription_events():
    event = SimpleNamespace(id=uuid4(), event_code="invoice.posted")
    matching_subscription = SimpleNamespace(
        id=uuid4(), event_codes=["invoice.posted"]
    )
    non_matching_subscription = SimpleNamespace(
        id=uuid4(), event_codes=["shipment.created"]
    )
    db = _Database([[event], [matching_subscription, non_matching_subscription], []])

    count = await webhook_service.replay_events(
        db, ReplayRequest(event_code=" invoice.posted ")
    )

    assert count == 1
    assert len(db.added) == 1
    assert db.added[0].event_log_id == event.id
    assert db.added[0].subscription_id == matching_subscription.id
    assert db.added[0].status == DeliveryStatus.PENDING
    assert db.added[0].replay_of_id is None
    assert db.statements[0]._for_update_arg is not None
    assert db.committed


@pytest.mark.asyncio
async def test_bulk_replay_links_dead_letter_and_skips_an_in_flight_successor():
    event_id = uuid4()
    subscription_id = uuid4()
    event = SimpleNamespace(id=event_id, event_code="invoice.posted")
    subscription = SimpleNamespace(id=subscription_id, event_codes=["invoice.posted"])
    dead_letter = SimpleNamespace(
        id=uuid4(),
        event_log_id=event_id,
        subscription_id=subscription_id,
        attempt_no=6,
        status=DeliveryStatus.DEAD_LETTER,
    )
    db = _Database([[event], [subscription], [dead_letter]])

    count = await webhook_service.replay_events(
        db,
        ReplayRequest(event_ids=[event_id], subscription_ids=[subscription_id]),
    )

    assert count == 1
    successor = db.added[0]
    assert successor.replay_of_id == dead_letter.id
    assert successor.attempt_no == 7
    assert dead_letter.status == DeliveryStatus.DEAD_LETTER

    in_flight = SimpleNamespace(
        id=successor.id,
        event_log_id=event_id,
        subscription_id=subscription_id,
        attempt_no=7,
        status=DeliveryStatus.PENDING,
    )
    repeated_db = _Database([[event], [subscription], [in_flight]])
    repeated_count = await webhook_service.replay_events(
        repeated_db,
        ReplayRequest(event_ids=[event_id], subscription_ids=[subscription_id]),
    )
    assert repeated_count == 0
    assert not repeated_db.added
    assert repeated_db.committed


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "events,subscriptions,expected_message",
    [
        (
            [SimpleNamespace(id=uuid4(), event_code="invoice.posted") for _ in range(201)],
            [],
            "more than 200 events",
        ),
        (
            [SimpleNamespace(id=uuid4(), event_code="invoice.posted")],
            [SimpleNamespace(id=uuid4(), event_codes=[]) for _ in range(101)],
            "more than 100 active subscriptions",
        ),
        (
            [SimpleNamespace(id=uuid4(), event_code="invoice.posted") for _ in range(11)],
            [SimpleNamespace(id=uuid4(), event_codes=[]) for _ in range(100)],
            "more than 1000 delivery attempts",
        ),
    ],
)
async def test_replay_rejects_requests_over_the_event_subscription_or_fanout_limit(
    events, subscriptions, expected_message
):
    from app.api.v1.endpoints.webhooks import replay_events as replay_endpoint

    db = _Database([events, subscriptions, []] if len(events) <= 200 else [events])

    with pytest.raises(webhook_service.EventReplayLimitError, match=expected_message):
        await webhook_service.replay_events(db, ReplayRequest(event_code="invoice.posted"))

    assert not db.added
    assert not db.committed

    if expected_message == "more than 100 active subscriptions":
        endpoint_db = _Database([events, subscriptions, []])
        with pytest.raises(HTTPException) as exc_info:
            await replay_endpoint(
                ReplayRequest(event_code="invoice.posted"), endpoint_db, None
            )
        assert exc_info.value.status_code == 422


def test_replay_date_range_can_be_single_sided_or_ordered():
    assert ReplayRequest(from_dt=datetime(2026, 10, 1, tzinfo=timezone.utc))
    assert ReplayRequest(
        from_dt=datetime(2026, 10, 1, tzinfo=timezone.utc),
        to_dt=datetime(2026, 10, 31, tzinfo=timezone.utc),
    )
