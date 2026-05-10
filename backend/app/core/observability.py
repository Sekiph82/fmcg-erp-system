from __future__ import annotations

import json
import logging
import time
from collections import Counter
from threading import Lock
from typing import Any


REQUEST_ID_HEADER = "X-Request-ID"
PROCESS_TIME_HEADER = "X-Process-Time-Ms"

_metrics_lock = Lock()
_metrics_started_at = time.time()
_request_counts: Counter[str] = Counter()
_status_counts: Counter[str] = Counter()
_slow_request_count = 0
_error_request_count = 0
_error_tracking_ready = False


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        for key in ("request_id", "method", "path", "status_code", "duration_ms"):
            value = getattr(record, key, None)
            if value is not None:
                payload[key] = value
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, default=str, ensure_ascii=False)


def configure_logging(environment: str) -> None:
    if environment.lower() != "production":
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        return

    root = logging.getLogger()
    root.setLevel(logging.INFO)
    root.handlers.clear()
    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())
    root.addHandler(handler)


def init_error_tracking(dsn: str, environment: str) -> None:
    global _error_tracking_ready
    if not dsn:
        _error_tracking_ready = False
        return
    try:
        import sentry_sdk  # type: ignore

        sentry_sdk.init(dsn=dsn, environment=environment)
        _error_tracking_ready = True
    except Exception:
        logging.getLogger(__name__).exception("Error tracking initialization failed")
        _error_tracking_ready = False


def capture_exception(exc: Exception, context: dict[str, Any] | None = None) -> None:
    if not _error_tracking_ready:
        return
    try:
        import sentry_sdk  # type: ignore

        with sentry_sdk.push_scope() as scope:
            for key, value in (context or {}).items():
                scope.set_extra(key, value)
            sentry_sdk.capture_exception(exc)
    except Exception:
        logging.getLogger(__name__).exception("Error tracking capture failed")


def record_request(method: str, path: str, status_code: int, duration_ms: int) -> None:
    global _slow_request_count, _error_request_count
    key = f"{method.upper()} {path}"
    with _metrics_lock:
        _request_counts[key] += 1
        _status_counts[str(status_code)] += 1
        if duration_ms > 500:
            _slow_request_count += 1
        if status_code >= 500:
            _error_request_count += 1


def metrics_snapshot() -> dict[str, Any]:
    with _metrics_lock:
        return {
            "uptime_seconds": int(time.time() - _metrics_started_at),
            "requests_total": sum(_request_counts.values()),
            "requests_by_route": dict(_request_counts),
            "responses_by_status": dict(_status_counts),
            "slow_requests_total": _slow_request_count,
            "error_requests_total": _error_request_count,
        }
