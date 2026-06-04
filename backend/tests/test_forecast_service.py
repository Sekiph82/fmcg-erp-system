"""Unit tests for forecast_service — pure helper functions, no DB required."""
from __future__ import annotations

from decimal import Decimal

import pytest

from app.models.mrp import PeriodType
from app.services.forecast_service import (
    _exponential_smoothing,
    _holt_winters_forecast,
    _moving_average,
    _weighted_moving_average,
)


def _dl(values) -> list[Decimal]:
    return [Decimal(str(v)) for v in values]


class TestExponentialSmoothing:
    def test_returns_same_length(self):
        hist = _dl([100, 110, 120, 115, 125])
        assert len(_exponential_smoothing(hist, alpha=0.3)) == 5

    def test_empty(self):
        assert _exponential_smoothing([], alpha=0.3) == []

    def test_non_negative(self):
        result = _exponential_smoothing(_dl([50, 60, 70]), alpha=0.3)
        assert all(v >= 0 for v in result)


class TestHoltWinters:
    def test_returns_correct_length(self):
        hist = _dl([100] * 6)
        assert len(_holt_winters_forecast(hist, 4, PeriodType.MONTHLY)) == 4

    def test_non_negative(self):
        hist = _dl([50, 60, 70, 80, 90, 100])
        result = _holt_winters_forecast(hist, 6, PeriodType.MONTHLY)
        assert all(v >= Decimal("0") for v in result)

    def test_fallback_single_point(self):
        # 1 data point — must fall back to ES without raising
        result = _holt_winters_forecast(_dl([100]), 3, PeriodType.MONTHLY)
        assert len(result) == 3
        assert all(v >= Decimal("0") for v in result)

    def test_fallback_empty_history(self):
        result = _holt_winters_forecast([], 3, PeriodType.MONTHLY)
        assert len(result) == 3
        assert all(v == Decimal("0") for v in result)

    def test_insufficient_for_seasonality_no_crash(self):
        # 10 months — not enough for 2×12 seasonal cycles; should still work
        hist = _dl(range(100, 110))
        result = _holt_winters_forecast(hist, 6, PeriodType.MONTHLY)
        assert len(result) == 6

    def test_sufficient_for_monthly_seasonality(self):
        # 24+ points enables additive seasonality (2 × 12)
        hist = _dl(list(range(80, 104)))  # 24 values
        result = _holt_winters_forecast(hist, 6, PeriodType.MONTHLY)
        assert len(result) == 6
        assert all(v >= Decimal("0") for v in result)

    def test_no_external_api_call(self):
        # Import must not trigger any network I/O
        import socket
        original = socket.socket

        calls = []

        class _NoNetwork(socket.socket):
            def connect(self, *a, **kw):
                calls.append(a)
                raise AssertionError("network call detected in _holt_winters_forecast")

        socket.socket = _NoNetwork
        try:
            _holt_winters_forecast(_dl([10, 20, 30, 40]), 2, PeriodType.MONTHLY)
        finally:
            socket.socket = original

        assert calls == [], "unexpected network call"

    def test_weekly_period_type(self):
        hist = _dl([30] * 8)
        result = _holt_winters_forecast(hist, 4, PeriodType.WEEKLY)
        assert len(result) == 4

    def test_daily_period_type(self):
        hist = _dl([10] * 7)
        result = _holt_winters_forecast(hist, 3, PeriodType.DAILY)
        assert len(result) == 3


class TestMovingAverage:
    def test_window_of_three(self):
        hist = _dl([10, 20, 30, 40, 50])
        result = _moving_average(hist, 3)
        assert result == Decimal("40.000")  # avg(30, 40, 50)

    def test_empty(self):
        assert _moving_average([], 3) == Decimal("0")


class TestWeightedMovingAverage:
    def test_result_positive(self):
        result = _weighted_moving_average(_dl([10, 20, 30]), 3)
        assert result > Decimal("0")

    def test_empty(self):
        assert _weighted_moving_average([], 3) == Decimal("0")
