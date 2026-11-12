"""MQTT -> native IoT ingest bridge (broker-agnostic: Mosquitto, EMQX, HiveMQ, AWS IoT, ...).

Enabled by MQTT_BROKER_URL (mqtt://host:1883 or mqtts://host:8883; production requires mqtts).
Subscribes to MQTT_TOPICS (comma separated, QoS 1). With MQTT_SHARED_GROUP set the subscription is
shared ($share/<group>/<topic>), so several API workers split the stream instead of each storing
every message.

Accepted payloads (UTF-8 JSON unless noted), at most 256 KiB:
  reading  {"machine_id", "metric_name", "value", "unit"?, "sensor_id"?, "recorded_at"?, ...}
  batch    {"readings": [reading, ...]}             (at most 1000)
  state    {"machine_id", "state": "RUNNING"|..., "trigger_metric"?, "notes"?, ...}
  number   bare value on .../<machine_id>/<metric_name>, e.g. "plant/filler-1/temperature" -> 72.5
Optional "message_id" makes redelivery idempotent (per device_code, else per topic); optional
"device_code" links a registered device. Every message gets an IoTIngestMessage audit row
(ACCEPTED / DUPLICATE / REJECTED with payload hash), including messages that fail to store.

Delivery: paho acknowledges QoS 1 when the message reaches the in-memory buffer (bounded to 64 MiB),
before it is committed, and sessions are clean. Messages buffered during a crash, or published while
no worker is connected, are lost: at-most-once end to end. Devices that cannot lose readings should
buffer and resend with a message_id (duplicates are then dropped).
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import ssl
from datetime import datetime, timezone
from typing import Any, Optional
from urllib.parse import urlparse

from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.iot import IoTDevice, IoTIngestMessage, IoTIngestStatus
from app.services.iot_ingest import SensorIn, StateIn, ingest_reading, parse_recorded_at, record_machine_state

logger = logging.getLogger(__name__)

SOURCE = "MQTT"
MAX_PAYLOAD = 256 * 1024
MAX_READINGS = 1000
QUEUE_SIZE = 10_000
QUEUE_BYTES = 64 * 1024 * 1024

STATUS: dict[str, Any] = {"enabled": False, "connected": False, "broker": None, "topics": [], "received": 0,
                          "accepted": 0, "duplicates": 0, "rejected": 0, "dropped": 0, "errors": 0,
                          "last_message_at": None, "last_error": None}


class BridgeConfigError(ValueError):
    pass


def broker_endpoint(url: str, environment: str) -> tuple[str, int, bool]:
    parsed = urlparse(url)
    if parsed.scheme not in {"mqtt", "mqtts"} or not parsed.hostname:
        raise BridgeConfigError("MQTT_BROKER_URL must look like mqtt://host:1883 or mqtts://host:8883.")
    tls = parsed.scheme == "mqtts"
    if environment == "production" and not tls:
        raise BridgeConfigError("Production requires an mqtts:// (TLS) broker URL.")
    return parsed.hostname, parsed.port or (8883 if tls else 1883), tls


def parse_message(topic: str, payload: bytes) -> tuple[str, list, Optional[str], Optional[str]]:
    """Return (kind, items, message_id, device_code); raise ValueError for anything unusable."""
    if len(payload) > MAX_PAYLOAD:
        raise ValueError(f"payload larger than {MAX_PAYLOAD} bytes")
    try:
        data = json.loads(payload.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("payload is not UTF-8 JSON or a number") from exc
    if isinstance(data, (int, float)) and not isinstance(data, bool):
        levels = [part for part in topic.split("/") if part]
        if len(levels) < 2:
            raise ValueError("a bare value needs a .../<machine_id>/<metric_name> topic")
        return "readings", [SensorIn(machine_id=levels[-2], metric_name=levels[-1], value=data, source=SOURCE)], None, None
    if not isinstance(data, dict):
        raise ValueError("payload must be a JSON object or a number")
    message_id = str(data["message_id"])[:255] if data.get("message_id") not in (None, "") else None
    device_code = str(data["device_code"])[:100] if data.get("device_code") not in (None, "") else None
    meta = {"message_id", "device_code"}
    try:
        if "readings" in data:
            rows = data["readings"]
            if not isinstance(rows, list) or not rows or len(rows) > MAX_READINGS:
                raise ValueError(f"readings must be a list of 1..{MAX_READINGS} items")
            return "readings", [SensorIn(**{**r, "source": SOURCE}) for r in rows], message_id, device_code
        body = {k: v for k, v in data.items() if k not in meta}
        if "state" in data:
            return "state", [StateIn(**{"trigger_source": "mqtt", **body})], message_id, device_code
        return "readings", [SensorIn(**{**body, "source": SOURCE})], message_id, device_code
    except (ValidationError, TypeError) as exc:
        raise ValueError(f"invalid payload: {exc}"[:500]) from exc


async def _audit(db: AsyncSession, status: IoTIngestStatus, digest: str, error: Optional[str] = None,
                 message_key: Optional[str] = None) -> None:
    db.add(IoTIngestMessage(source=SOURCE, message_id=message_key, received_at=datetime.now(timezone.utc),
                            record_count=0, status=status, error_message=error, raw_payload_hash=digest))
    await db.commit()


async def handle_message(db: AsyncSession, topic: str, payload: bytes) -> IoTIngestStatus:
    """Store one MQTT message through the native ingest path and audit it. Commits."""
    digest = hashlib.sha256(payload).hexdigest()
    try:
        kind, items, message_id, device_code = parse_message(topic, payload)
        for item in items:  # reject bad device timestamps before anything is written
            parse_recorded_at(item.recorded_at if kind == "readings" else item.changed_at)
    except ValueError as exc:
        await _audit(db, IoTIngestStatus.REJECTED, digest, f"{topic}: {exc}"[:2000])
        return IoTIngestStatus.REJECTED
    # message ids are only unique per device (counters restart at 1), so scope them
    key = f"{device_code or topic}|{message_id}"[:255] if message_id is not None else None
    if key is not None and (await db.execute(select(IoTIngestMessage.id).where(
            IoTIngestMessage.source == SOURCE, IoTIngestMessage.message_id == key,
            IoTIngestMessage.status == IoTIngestStatus.ACCEPTED).limit(1))).first():
        await _audit(db, IoTIngestStatus.DUPLICATE, digest, message_key=key)
        return IoTIngestStatus.DUPLICATE  # QoS 1 redelivery or a device retry
    device = None
    if device_code is not None:
        device = (await db.execute(select(IoTDevice).where(IoTDevice.device_code == device_code))).scalar_one_or_none()
    now = datetime.now(timezone.utc)
    audit = IoTIngestMessage(source=SOURCE, message_id=key, received_at=now, record_count=len(items),
                             status=IoTIngestStatus.ACCEPTED, raw_payload_hash=digest,
                             device_id=device.id if device else None)
    try:
        db.add(audit)
        await db.flush()
    except IntegrityError:  # another worker accepted the same redelivered message a moment ago
        await db.rollback()
        await _audit(db, IoTIngestStatus.DUPLICATE, digest, message_key=key)
        return IoTIngestStatus.DUPLICATE
    for item in items:
        if kind == "state":
            await record_machine_state(db, item)
        else:
            await ingest_reading(db, item, ingest_message_id=audit.id, device_id=device.id if device else None)
    if device is not None:
        device.last_seen_at = now
        device.last_message_id = message_id
    await db.commit()
    return IoTIngestStatus.ACCEPTED


def _make_client(host: str, port: int, tls: bool, topics: list[str], loop: asyncio.AbstractEventLoop,
                 queue: "asyncio.Queue[tuple[str, bytes]]", queued: dict):
    import paho.mqtt.client as mqtt

    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=settings.MQTT_CLIENT_ID or "",
                         clean_session=True)
    if settings.MQTT_USERNAME:
        client.username_pw_set(settings.MQTT_USERNAME, settings.MQTT_PASSWORD or None)
    if tls:
        client.tls_set_context(ssl.create_default_context(cafile=settings.MQTT_CA_FILE or None))
    group = settings.MQTT_SHARED_GROUP.strip()
    filters = [f"$share/{group}/{t}" if group else t for t in topics]

    def on_connect(c, _userdata, _flags, reason_code, _props):
        if reason_code.is_failure:
            STATUS["last_error"] = f"connect refused: {reason_code}"
            return
        STATUS["connected"] = True
        c.subscribe([(f, 1) for f in filters])

    def on_disconnect(_c, _userdata, _flags, reason_code, _props):
        STATUS["connected"] = False
        if reason_code.is_failure:
            STATUS["last_error"] = f"disconnected: {reason_code}"

    def drop():  # event loop thread
        STATUS["dropped"] += 1

    def enqueue(item):  # event loop thread
        size = len(item[1])
        if size > MAX_PAYLOAD or queued["bytes"] + size > QUEUE_BYTES or queue.full():
            drop()  # ponytail: in-memory buffer; persist to disk if bursts outrun the DB
            return
        queued["bytes"] += size
        queue.put_nowait(item)

    def on_message(_c, _userdata, msg):  # paho network thread
        try:
            if len(msg.payload) > MAX_PAYLOAD:  # don't copy oversized payloads into the loop
                loop.call_soon_threadsafe(drop)
            else:
                loop.call_soon_threadsafe(enqueue, (msg.topic, bytes(msg.payload)))
        except RuntimeError:  # event loop already closed during shutdown
            pass

    client.on_connect, client.on_disconnect, client.on_message = on_connect, on_disconnect, on_message
    client.reconnect_delay_set(min_delay=1, max_delay=60)
    client.connect_async(host, port, keepalive=60)
    return client


async def run_mqtt_bridge() -> None:
    """Long-running task started with the app; returns at once when MQTT is not configured."""
    if not settings.MQTT_BROKER_URL:
        return
    try:
        host, port, tls = broker_endpoint(settings.MQTT_BROKER_URL, settings.ENVIRONMENT)
    except BridgeConfigError as exc:
        STATUS["last_error"] = str(exc)
        logger.error("MQTT bridge not started: %s", exc)
        return
    from app.db.session import AsyncSessionLocal

    topics = [t.strip() for t in settings.MQTT_TOPICS.split(",") if t.strip()]
    loop = asyncio.get_running_loop()
    queue: asyncio.Queue[tuple[str, bytes]] = asyncio.Queue(maxsize=QUEUE_SIZE)
    queued = {"bytes": 0}
    try:
        client = _make_client(host, port, tls, topics, loop, queue, queued)
    except Exception as exc:  # bad CA file, topic filter, ...: report instead of dying silently
        STATUS["last_error"] = f"bridge not started: {exc.__class__.__name__}"
        logger.exception("MQTT bridge not started")
        return
    STATUS.update(enabled=True, broker=f"{'mqtts' if tls else 'mqtt'}://{host}:{port}", topics=topics)
    client.loop_start()  # paho's network thread handles reconnects
    logger.info("MQTT bridge started for %s (%s)", STATUS["broker"], ", ".join(topics))
    try:
        while True:
            topic, payload = await queue.get()
            queued["bytes"] -= len(payload)
            STATUS["received"] += 1
            STATUS["last_message_at"] = datetime.now(timezone.utc).isoformat()
            try:
                async with AsyncSessionLocal() as db:
                    outcome = await handle_message(db, topic, payload)
                STATUS[{IoTIngestStatus.ACCEPTED: "accepted", IoTIngestStatus.DUPLICATE: "duplicates"}.get(
                    outcome, "rejected")] += 1
            except Exception as exc:  # keep the bridge alive; audit the failure, then move on
                STATUS["errors"] += 1
                STATUS["last_error"] = exc.__class__.__name__  # details (may hold payload data) go to the log
                logger.exception("MQTT message on %s could not be stored", topic)
                try:
                    async with AsyncSessionLocal() as db:
                        await _audit(db, IoTIngestStatus.REJECTED, hashlib.sha256(payload).hexdigest(),
                                     f"{topic}: not stored ({exc.__class__.__name__})"[:2000])
                except Exception:
                    logger.exception("MQTT failure audit could not be written")
    finally:
        client.disconnect()  # sends DISCONNECT while the network thread still runs
        await asyncio.to_thread(client.loop_stop)
        STATUS.update(enabled=False, connected=False)
