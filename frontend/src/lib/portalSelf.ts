// Distributor / customer self-service portal client (own sign-in cookie, never the staff session).
import { API_ORIGIN } from "@/lib/api";

export class PortalError extends Error {
  constructor(public status: number, message: string) { super(message); }
}

export async function partnerFetch<T>(base: "portal-self" | "supplier-self", path: string, init: RequestInit = {}): Promise<T> {
  const res = await fetch(`${API_ORIGIN}/api/v1/${base}${path}`, {
    ...init, credentials: "include",
    // FormData (file uploads) sets its own multipart boundary header
    headers: init.body instanceof FormData ? init.headers : { "Content-Type": "application/json", ...(init.headers ?? {}) },
  });
  const body = await res.json().catch(() => ({}));
  if (!res.ok) {
    const d = (body as { detail?: unknown }).detail;
    const msg = typeof d === "string" ? d : Array.isArray(d) ? d.map((x) => (x as { msg?: string }).msg).join("; ") : "Request failed.";
    throw new PortalError(res.status, msg);
  }
  return body as T;
}

export const ps = <T,>(path: string, init: RequestInit = {}) => partnerFetch<T>("portal-self", path, init);
export const post = <T,>(path: string, data?: unknown) => ps<T>(path, { method: "POST", body: JSON.stringify(data ?? {}) });

export interface PortalMe {
  id: string; full_name: string; email: string; role: string; can_order: boolean; account_code: string;
  account_type: string; can_view_prices: boolean; customer_name: string | null; currency: string; linked: boolean;
}
export interface CatalogItem { product_id: string; sku: string; name: string; uom: string; units_per_carton: number; unit_price: number | null }
export interface PortalOrder {
  id: string; order_no: string; order_date: string; requested_delivery_date: string; status: string; currency: string;
  payment_status: string; line_count: number; total: number | null;
}
export interface PortalOrderDetail extends PortalOrder {
  lines: { product_id: string; product_name: string; sku: string; ordered_quantity: number; shipped_quantity: number; unit: string; unit_price: number | null }[];
  shipments: { id: string; shipment_no: string; status: string; scheduled_date: string }[];
  invoices: { id: string; invoice_no: string; status: string; total_amount: number }[];
}
export interface PortalInvoice {
  id: string; invoice_no: string; invoice_date: string; due_date: string; status: string; currency: string;
  total_amount: number; paid_amount: number; outstanding: number;
}
export interface PortalStatement { total_invoiced: number; total_paid: number; outstanding_balance: number; invoices: PortalInvoice[] }
export interface PortalClaim { id: string; claim_no: string; claim_type: string; status: string; reason: string; linked_order_id: string | null; resolution_notes: string | null; created_at: string | null }

export const STATUS_TEXT: Record<string, string> = {
  DRAFT: "Received — awaiting confirmation", CONFIRMED: "Confirmed", ALLOCATED: "Stock reserved", PICKING: "Being prepared",
  SHIPPED: "Shipped", INVOICED: "Invoiced", CANCELLED: "Cancelled",
};
export const statusText = (s: string) => STATUS_TEXT[s.replace(/^.*\./, "")] ?? s;
export const money = (n: number | null | undefined, cur: string) =>
  n == null ? "—" : `${cur} ${n.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
