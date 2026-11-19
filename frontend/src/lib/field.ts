// Field app client (staff session): rep "my day", orders, collections, driver trips, outlet audits, supervision.
import { apiFetch } from "@/lib/api";

export class FieldError extends Error {
  constructor(public status: number, message: string) { super(message); }
}

export async function fx<T>(path: string, init: RequestInit = {}): Promise<T> {
  const isForm = init.body instanceof FormData;
  const res = await apiFetch(`/api/v1${path}`, { ...init, headers: isForm ? init.headers : { "Content-Type": "application/json", ...(init.headers ?? {}) } });
  const body = await res.json().catch(() => ({}));
  if (!res.ok) {
    const d = (body as { detail?: unknown }).detail;
    throw new FieldError(res.status, typeof d === "string" ? d : Array.isArray(d) ? d.map((x) => (x as { msg?: string }).msg).join("; ") : "Request failed.");
  }
  return body as T;
}
export const fpost = <T,>(path: string, data: unknown) => fx<T>(path, { method: "POST", body: data instanceof FormData ? data : JSON.stringify(data) });

/** A fresh idempotency key; keep it until the server answered, so a resend after a dropped connection is not a duplicate. */
export const newRef = () => (typeof crypto !== "undefined" && "randomUUID" in crypto ? crypto.randomUUID() : `${Date.now()}-${Math.random().toString(36).slice(2)}`);

export function currentPosition(): Promise<{ lat: number; lng: number } | null> {
  return new Promise((resolve) => {
    if (typeof navigator === "undefined" || !navigator.geolocation) return resolve(null);
    navigator.geolocation.getCurrentPosition((p) => resolve({ lat: +p.coords.latitude.toFixed(7), lng: +p.coords.longitude.toFixed(7) }),
      () => resolve(null), { enableHighAccuracy: true, timeout: 10000, maximumAge: 60000 });
  });
}

export interface FieldMe {
  full_name: string; rep: { id: string; code: string; name: string; vehicle_type: string; region: string | null } | null;
  van: { id: string; van_code: string } | null; is_driver: boolean; can_audit: boolean; can_supervise: boolean;
}
export interface Stop {
  customer_id: string; name: string; contact: string | null; phone: string | null; address: string | null; route: string; sequence: number;
  lat: number | null; lng: number | null; visit: { id: string; outcome: string; order_id: string | null } | null; open_balance: number; currency: string;
}
export interface Today { date: string; stops: Stop[]; visited: number; sold_today: number; target_amount: number | null }
export interface CatalogItem { product_id: string; sku: string; name: string; uom: string; unit_price: number }
export interface OpenInvoice { id: string; invoice_no: string; due_date: string; currency: string; total: number; outstanding: number; overdue: boolean }
export interface TripStop { id: string; sequence: number; status: string; failure_reason: string | null; shipment_no: string; order_no: string; customer: string; phone: string | null; address: string | null; lat: number | null; lng: number | null }
export interface Trip { id: string; trip_no: string; trip_date: string; status: string; vehicle: string | null; stops: TripStop[] }
export interface AuditRow { id: string; audit_no: string; date: string; outlet: string; rep: string | null; score: number; photos: number; failed: string[] }
export interface ComplianceRow {
  rep_id: string; rep: string; code: string; vehicle: string; route_stops: number; visits: number; outlets_visited: number;
  coverage_pct: number | null; visits_with_gps_pct: number | null; last_visit_at: string | null; orders: number; order_value: number;
  collections: number; collected: number; audits: number; audit_score: number | null;
}
export const kes = (n: number | null | undefined, cur = "KES") => n == null ? "—" : `${cur} ${n.toLocaleString(undefined, { maximumFractionDigits: 2 })}`;
export const mapsLink = (lat: number | null, lng: number | null, address: string | null) =>
  lat != null && lng != null ? `https://www.google.com/maps/dir/?api=1&destination=${lat},${lng}` : address ? `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(address)}` : null;
