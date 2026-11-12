"""M17.S02.T005 — MQTT bridge end to end: a real local broker into native IoT ingest on disposable PostgreSQL."""
from __future__ import annotations

import asyncio
import json
import os
import re
from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy import func, select

from app.core.config import settings
from app.db.session import AsyncSessionLocal, engine
from app.models.iot import (
    IoTAlert, IoTAlertThreshold, IoTDevice, IoTDeviceProtocol, IoTDeviceType, IoTIngestMessage, IoTIngestStatus,
    MachineState, MachineStateEvent, SensorDataPoint,
)
from app.services import mqtt_bridge

TASK_DB_ENV = "M17_S02_T005_DISPOSABLE_TEST_DATABASE"
TASK_DB_NAME_ENV = "M17_S02_T005_DISPOSABLE_TEST_DATABASE_NAME"
TASK_DB_PATTERN = re.compile(r"fmcg_m17_s02_t005_[a-f0-9]{24}")
BROKER = os.environ.get("MQTT_TEST_BROKER_URL", "")  # e.g. mqtt://127.0.0.1:51883 (local test broker)

pytestmark = pytest.mark.skipif(os.environ.get(TASK_DB_ENV) != "1" or not BROKER.startswith("mqtt://127.0.0.1:"),
                                reason="requires the task-owned disposable PostgreSQL and a local test MQTT broker")


@pytest_asyncio.fixture(autouse=True)
async def _dispose_engine():
    yield
    await engine.dispose()


async def _until(predicate, timeout=15.0):
    deadline = asyncio.get_running_loop().time() + timeout
    while asyncio.get_running_loop().time() < deadline:
        if await predicate():
            return True
        await asyncio.sleep(0.2)
    return False


@pytest.mark.asyncio
async def test_broker_messages_flow_into_native_iot_ingest(monkeypatch):
    import paho.mqtt.publish as publish

    s = uuid4().hex[:10]
    machine, device_code, root = f"FILLER-{s}", f"GW-{s}", f"fmcg-test-{s}"
    async with AsyncSessionLocal() as db:
        assert engine.url.host in {"127.0.0.1", "localhost", "::1"} and engine.url.password is None
        assert TASK_DB_PATTERN.fullmatch(os.environ.get(TASK_DB_NAME_ENV, ""))
        assert (await db.execute(select(func.current_database()))).scalar_one() == os.environ[TASK_DB_NAME_ENV]
        device = IoTDevice(device_code=device_code, name="Synthetic gateway", protocol=IoTDeviceProtocol.MQTT,
                           device_type=IoTDeviceType.GATEWAY)
        db.add_all([device, IoTAlertThreshold(machine_id=machine, metric_name="temperature", max_threshold=80)])
        await db.commit()
        device_id = device.id

    monkeypatch.setattr(settings, "MQTT_BROKER_URL", BROKER)
    monkeypatch.setattr(settings, "MQTT_TOPICS", f"{root}/#")
    monkeypatch.setattr(settings, "MQTT_SHARED_GROUP", "fmcg-erp")  # broker splits the stream across workers
    monkeypatch.setattr(settings, "MQTT_CLIENT_ID", f"fmcg-erp-test-{s}")
    for key in ("received", "accepted", "duplicates", "rejected", "errors"):
        monkeypatch.setitem(mqtt_bridge.STATUS, key, 0)
    bridge = asyncio.create_task(mqtt_bridge.run_mqtt_bridge())
    try:
        assert await _until(lambda: _true(mqtt_bridge.STATUS["connected"]), 10), mqtt_bridge.STATUS
        await asyncio.sleep(0.5)  # subscription acknowledged
        host, port = BROKER.removeprefix("mqtt://").split(":")
        reading = {"machine_id": machine, "metric_name": "temperature", "value": 91.5, "unit": "C",
                   "recorded_at": "2026-11-12T10:00:00+03:00", "message_id": f"msg-{s}", "device_code": device_code}
        msgs = [
            {"topic": f"{root}/telemetry", "payload": json.dumps(reading), "qos": 1},
            {"topic": f"{root}/telemetry", "payload": json.dumps(reading), "qos": 1},  # redelivered duplicate
            {"topic": f"{root}/{machine}/speed", "payload": "120", "qos": 1},
            # another gateway reusing the same message id is a different message
            {"topic": f"{root}/telemetry", "payload": json.dumps({**reading, "device_code": f"OTHER-{s}",
                                                                  "metric_name": "pressure", "value": 2}), "qos": 1},
            {"topic": f"{root}/state", "payload": json.dumps({"machine_id": machine, "state": "DOWN",
                                                              "changed_at": "2026-11-12T06:00:00Z"}), "qos": 1},
            {"topic": f"{root}/state", "payload": json.dumps({"machine_id": machine, "state": "RUNNING",
                                                              "changed_at": "2026-11-12T06:30:00Z"}), "qos": 1},
            {"topic": f"{root}/telemetry", "payload": "{broken", "qos": 1},
        ]
        await asyncio.to_thread(publish.multiple, msgs, hostname=host, port=int(port), client_id=f"pub-{s}")
        assert await _until(lambda: _true(mqtt_bridge.STATUS["received"] >= 7)), mqtt_bridge.STATUS
    finally:
        bridge.cancel()
        with pytest.raises(asyncio.CancelledError):
            await bridge

    assert (mqtt_bridge.STATUS["accepted"], mqtt_bridge.STATUS["duplicates"], mqtt_bridge.STATUS["rejected"],
            mqtt_bridge.STATUS["errors"]) == (5, 1, 1, 0)
    async with AsyncSessionLocal() as db:
        points = {p.metric_name: p for p in (await db.execute(
            select(SensorDataPoint).where(SensorDataPoint.machine_id == machine))).scalars()}
        assert set(points) == {"temperature", "speed", "pressure"}  # the duplicate was not stored twice
        temp = points["temperature"]
        assert (float(temp.value), temp.source, temp.device_id) == (91.5, "MQTT", device_id)
        assert temp.recorded_at.isoformat() == "2026-11-12T07:00:00"  # stored as UTC
        assert float(points["speed"].value) == 120
        audit = await db.get(IoTIngestMessage, temp.ingest_message_id)
        assert (audit.status, audit.message_id, audit.record_count, audit.device_id) == (
            IoTIngestStatus.ACCEPTED, f"{device_code}|msg-{s}", 1, device_id)
        dup = (await db.execute(select(IoTIngestMessage).where(
            IoTIngestMessage.message_id == f"{device_code}|msg-{s}",
            IoTIngestMessage.status == IoTIngestStatus.DUPLICATE))).scalar_one()
        assert dup.raw_payload_hash == audit.raw_payload_hash
        alert = (await db.execute(select(IoTAlert).where(IoTAlert.machine_id == machine))).scalar_one()
        assert float(alert.triggered_value) == 91.5  # threshold max 80 breached
        states = (await db.execute(select(MachineStateEvent).where(MachineStateEvent.machine_id == machine)
                                   .order_by(MachineStateEvent.changed_at))).scalars().all()
        assert [(e.state, e.trigger_source) for e in states] == [(MachineState.DOWN, "mqtt"), (MachineState.RUNNING, "mqtt")]
        assert (states[1].previous_state, states[1].duration_seconds) == (MachineState.DOWN, 1800)  # device time
        rejected = (await db.execute(select(IoTIngestMessage).where(
            IoTIngestMessage.status == IoTIngestStatus.REJECTED,
            IoTIngestMessage.error_message.like(f"{root}/telemetry:%")))).scalar_one()
        assert rejected.record_count == 0 and rejected.raw_payload_hash
        gateway = await db.get(IoTDevice, device_id)
        assert gateway.last_message_id == f"msg-{s}" and gateway.last_seen_at is not None


async def _true(value):
    return value
