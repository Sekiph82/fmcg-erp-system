from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace

import pytest

from app.models.webhook import DeliveryStatus
from app.services import webhook_service


@pytest.mark.parametrize(
    ("attempt_no", "max_retries", "expected_ceiling"),
    [
        (1, 5, 60),
        (2, 5, 120),
        (3, 5, 240),
        (7, 10, 3600),
    ],
)
def test_retry_schedule_uses_bounded_exponential_equal_jitter(
    monkeypatch, attempt_no, max_retries, expected_ceiling
):
    attempt = SimpleNamespace(
        attempt_no=attempt_no,
        status=DeliveryStatus.PENDING,
        next_retry_at=None,
    )
    observed_bounds = []

    def choose_upper_bound(lower, upper):
        observed_bounds.append((lower, upper))
        return upper

    monkeypatch.setattr(webhook_service.random, "uniform", choose_upper_bound)
    before = datetime.now(timezone.utc)

    webhook_service._schedule_retry(
        attempt, SimpleNamespace(max_retries=max_retries)
    )

    after = datetime.now(timezone.utc)
    assert attempt.status == DeliveryStatus.RETRYING
    assert observed_bounds == [(expected_ceiling * 0.5, expected_ceiling)]
    assert before.timestamp() + expected_ceiling <= attempt.next_retry_at.timestamp()
    assert attempt.next_retry_at.timestamp() <= after.timestamp() + expected_ceiling


def test_max_retries_counts_additional_attempts_after_the_initial_request(monkeypatch):
    monkeypatch.setattr(webhook_service.random, "uniform", lambda lower, upper: lower)
    subscription = SimpleNamespace(max_retries=2)
    attempts = [
        SimpleNamespace(attempt_no=n, status=None, next_retry_at=None)
        for n in (1, 2, 3)
    ]

    for attempt in attempts:
        webhook_service._schedule_retry(attempt, subscription)

    assert [attempt.status for attempt in attempts] == [
        DeliveryStatus.RETRYING,
        DeliveryStatus.RETRYING,
        DeliveryStatus.DEAD_LETTER,
    ]
    assert attempts[0].next_retry_at is not None
    assert attempts[1].next_retry_at is not None
    assert attempts[2].next_retry_at is None


def test_zero_retries_dead_letters_the_initial_failed_delivery():
    attempt = SimpleNamespace(
        attempt_no=1,
        status=DeliveryStatus.PENDING,
        next_retry_at=None,
    )

    webhook_service._schedule_retry(attempt, SimpleNamespace(max_retries=0))

    assert attempt.status == DeliveryStatus.DEAD_LETTER
    assert attempt.next_retry_at is None
