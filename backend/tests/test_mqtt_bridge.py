"""MQTT bridge message parsing and broker configuration (no broker, no database)."""
import json

import pytest

from app.models.iot import MachineState
from app.services.iot_ingest import parse_recorded_at
from app.services.mqtt_bridge import BridgeConfigError, broker_endpoint, parse_message


def test_reading_batch_state_and_bare_value_payloads():
    kind, items, mid, dev = parse_message("fmcg/iot/x", json.dumps({
        "machine_id": "FILLER-1", "metric_name": "temperature", "value": 72.5, "unit": "C",
        "message_id": "m-1", "device_code": "GW-1"}).encode())
    assert (kind, items[0].machine_id, items[0].value, items[0].source, mid, dev) == (
        "readings", "FILLER-1", 72.5, "MQTT", "m-1", "GW-1")

    kind, items, *_ = parse_message("fmcg/iot/x", json.dumps({"readings": [
        {"machine_id": "M1", "metric_name": "speed", "value": 10, "source": "SPOOFED"},
        {"machine_id": "M1", "metric_name": "speed", "value": 11}]}).encode())
    assert kind == "readings" and [r.value for r in items] == [10, 11] and {r.source for r in items} == {"MQTT"}

    kind, items, *_ = parse_message("fmcg/iot/x", b'{"machine_id": "M1", "state": "RUNNING"}')
    assert kind == "state" and items[0].state == MachineState.RUNNING and items[0].trigger_source == "mqtt"

    kind, items, *_ = parse_message("plant/line-2/CAPPER-3/torque", b"4.25")
    assert (items[0].machine_id, items[0].metric_name, items[0].value) == ("CAPPER-3", "torque", 4.25)


@pytest.mark.parametrize("topic,payload", [
    ("t/m/x", b"not json"),
    ("single", b"5"),                                   # bare value needs machine/metric topic levels
    ("t/m/x", b"true"),
    ("t/m/x", b'["list"]'),
    ("t/m/x", b'{"machine_id": "M1", "value": 1}'),     # metric missing
    ("t/m/x", b'{"machine_id": "M1", "state": "EXPLODED"}'),
    ("t/m/x", b'{"readings": []}'),
    ("t/m/x", json.dumps({"readings": [{"machine_id": "M", "metric_name": "x", "value": 1}] * 1001}).encode()),
    ("t/m/x", b"\xff\xfe"),
    ("t/m/x", b" " * (256 * 1024 + 1)),
], ids=["not-json", "short-topic", "bool", "list", "no-metric", "bad-state", "empty-batch", "big-batch",
        "not-utf8", "oversize"])
def test_unusable_payloads_are_rejected(topic, payload):
    with pytest.raises(ValueError):
        parse_message(topic, payload)


def test_broker_url_rules():
    assert broker_endpoint("mqtt://broker.local", "development") == ("broker.local", 1883, False)
    assert broker_endpoint("mqtts://broker.example:9883", "production") == ("broker.example", 9883, True)
    assert broker_endpoint("mqtts://broker.example", "production")[1] == 8883
    with pytest.raises(BridgeConfigError, match="TLS"):
        broker_endpoint("mqtt://broker.example", "production")
    with pytest.raises(BridgeConfigError):
        broker_endpoint("http://broker.example", "development")


def test_device_timestamps_become_naive_utc():
    assert parse_recorded_at("2026-11-12T10:00:00+03:00").isoformat() == "2026-11-12T07:00:00"
    assert parse_recorded_at("2026-11-12T07:00:00Z").isoformat() == "2026-11-12T07:00:00"
    assert parse_recorded_at("2026-11-12T07:00:00").isoformat() == "2026-11-12T07:00:00"
