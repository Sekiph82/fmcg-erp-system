"""Order tracking for customers (M39.S02.T001): a simple status timeline and an estimated arrival time.

The estimate follows the driver's trip: stops are driven in their delivery sequence; each leg takes the straight-line
distance between the outlets' GPS points × a road factor at an average speed for the vehicle, plus a fixed time at each
stop. It starts from the last delivery on the trip (or the departure); while the trip has not left, only the planned
date is known. ponytail: straight-line × road factor, no traffic or road network — swap in a routing API when one is
contracted; the knobs below are the calibration.
"""
from __future__ import annotations

import math
from datetime import datetime, timedelta
from typing import Optional

ROAD_FACTOR = 1.3                 # straight line → road distance
SPEED_KMH = {"MOTORBIKE": 25.0}   # town average; anything else uses DEFAULT_SPEED_KMH
DEFAULT_SPEED_KMH = 30.0
STOP_MINUTES = 10                 # unloading / signing at each outlet
UNKNOWN_LEG_MINUTES = 20          # an outlet without GPS


def _km(a, b) -> Optional[float]:
    if not a or not b or None in (*a, *b):
        return None
    la1, lo1, la2, lo2 = map(math.radians, (float(a[0]), float(a[1]), float(b[0]), float(b[1])))
    h = math.sin((la2 - la1) / 2) ** 2 + math.cos(la1) * math.cos(la2) * math.sin((lo2 - lo1) / 2) ** 2
    return 6371.0 * 2 * math.asin(math.sqrt(h))


def stop_etas(stops: list[dict], departed_at: Optional[datetime], vehicle_type: Optional[str],
              now: datetime) -> dict[int, datetime]:
    """stops: [{"seq", "delivered_at" (or None), "pos" (lat, lng) or None}]. Returns {seq: eta} for undelivered stops,
    or {} when the trip has not left yet."""
    done = sorted((s for s in stops if s["delivered_at"]), key=lambda s: s["delivered_at"])
    t = done[-1]["delivered_at"] if done else departed_at
    if t is None:
        return {}
    pos = done[-1]["pos"] if done else None
    speed = SPEED_KMH.get((vehicle_type or "").upper(), DEFAULT_SPEED_KMH)
    out = {}
    for s in sorted((s for s in stops if not s["delivered_at"]), key=lambda s: s["seq"]):
        km = _km(pos, s["pos"])
        t = max(t + timedelta(minutes=UNKNOWN_LEG_MINUTES if km is None else km * ROAD_FACTOR / speed * 60), now)
        out[s["seq"]] = t
        t += timedelta(minutes=STOP_MINUTES)
        pos = s["pos"] or pos
    return out


STAGES = ("received", "confirmed", "preparing", "on_the_way", "delivered")


def stage_of(so_status: str, shipment_statuses: list[str], trip_status: Optional[str], stop_status: Optional[str]) -> str:
    if so_status == "CANCELLED":
        return "cancelled"
    live = [x for x in shipment_statuses if x != "CANCELLED"]
    if (live and all(x == "DELIVERED" for x in live)) or (stop_status == "DELIVERED" and len(live) <= 1):
        return "delivered"   # a split order is delivered only when every shipment is
    if trip_status == "IN_TRANSIT" or (not trip_status and "DISPATCHED" in shipment_statuses):
        return "on_the_way"
    if shipment_statuses or trip_status or so_status in ("ALLOCATED", "PICKING", "SHIPPED"):
        return "preparing"
    if so_status in ("CONFIRMED", "INVOICED"):
        return "confirmed"
    return "received"


async def order_tracking(db, so) -> dict:
    """Timeline stage + estimated arrival for one sales order (already scoped to the caller)."""
    from datetime import timezone

    from sqlalchemy import select

    from app.models.delivery import DeliveryTrip, ProofOfDelivery, TripOrder
    from app.models.sales import Customer, SalesOrder, Shipment

    ships = (await db.execute(select(Shipment).where(Shipment.so_id == so.id))).scalars().all()
    ship_status = [s.status.value for s in ships]
    stop = None
    if ships:
        stop = (await db.execute(select(TripOrder).where(TripOrder.shipment_id.in_([s.id for s in ships]))
                                 .order_by(TripOrder.created_at.desc()).limit(1))).scalar_one_or_none()
    trip = await db.get(DeliveryTrip, stop.trip_id) if stop else None
    stage = stage_of(so.status.value, ship_status, trip.status.value if trip else None, stop.status.value if stop else None)
    out = {"stage": stage, "stages": list(STAGES), "eta": None, "eta_date": None, "delivered_at": None,
           "stops_before": None, "vehicle": None}
    if stage == "delivered" and stop:
        pod = (await db.execute(select(ProofOfDelivery).where(ProofOfDelivery.trip_order_id == stop.id))).scalar_one_or_none()
        out["delivered_at"] = pod.delivered_at.isoformat() if pod and pod.delivered_at else None
        return out
    if stage == "cancelled":
        return out
    if not trip:
        out["eta_date"] = str(so.requested_delivery_date) if so.requested_delivery_date else None
        return out
    out["eta_date"], out["vehicle"] = str(trip.trip_date), trip.vehicle_type
    rows = (await db.execute(
        select(TripOrder.delivery_sequence, TripOrder.status, Customer.gps_lat, Customer.gps_lng, ProofOfDelivery.delivered_at)
        .join(Shipment, Shipment.id == TripOrder.shipment_id).join(SalesOrder, SalesOrder.id == Shipment.so_id)
        .join(Customer, Customer.id == SalesOrder.customer_id)
        .outerjoin(ProofOfDelivery, ProofOfDelivery.trip_order_id == TripOrder.id)
        .where(TripOrder.trip_id == trip.id))).all()
    failed = ("FAILED", "RESCHEDULED")
    stops = [{"seq": r.delivery_sequence,  # a failed stop was not reached: it gives no position to drive on from
              "pos": (r.gps_lat, r.gps_lng) if r.gps_lat is not None and r.status.value not in failed else None,
              # failed / rescheduled stops are passed: they no longer hold the driver up
              "delivered_at": r.delivered_at or (trip.departed_at if r.status.value in failed else None)}
             for r in rows]
    out["stops_before"] = sum(1 for s in stops if not s["delivered_at"] and s["seq"] < stop.delivery_sequence)
    etas = stop_etas(stops, trip.departed_at, trip.vehicle_type, datetime.now(timezone.utc))
    if stop.delivery_sequence in etas:
        out["eta"] = etas[stop.delivery_sequence].isoformat()
    return out


if __name__ == "__main__":  # self-check of the estimate
    from datetime import timezone
    t0 = datetime(2026, 11, 20, 8, 0, tzinfo=timezone.utc)
    a, b = (-1.2833, 36.8833), (-1.2800, 36.8950)  # ~1.35 km apart
    e = stop_etas([{"seq": 1, "delivered_at": t0, "pos": a}, {"seq": 2, "delivered_at": None, "pos": b},
                   {"seq": 3, "delivered_at": None, "pos": None}], None, "MOTORBIKE", t0)
    assert 3 <= (e[2] - t0).total_seconds() / 60 <= 6, e            # ~1.75 road km at 25 km/h ≈ 4 min
    assert (e[3] - e[2]).total_seconds() / 60 == STOP_MINUTES + UNKNOWN_LEG_MINUTES
    assert stop_etas([{"seq": 1, "delivered_at": None, "pos": a}], None, None, t0) == {}   # not left yet
    late = stop_etas([{"seq": 1, "delivered_at": None, "pos": a}], t0, None, t0 + timedelta(hours=2))
    assert late[1] == t0 + timedelta(hours=2)                         # running late: never in the past
    assert stage_of("DRAFT", [], None, None) == "received" and stage_of("CONFIRMED", ["PENDING"], None, None) == "preparing"
    assert stage_of("SHIPPED", ["DISPATCHED"], "IN_TRANSIT", "PENDING") == "on_the_way"
    assert stage_of("SHIPPED", ["DISPATCHED"], "COMPLETED", "DELIVERED") == "delivered"
    print("ok")
