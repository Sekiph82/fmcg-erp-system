const BASE = "/api/v1/quotes";

export type QuoteStatus = "DRAFT" | "SENT" | "ACCEPTED" | "REJECTED" | "EXPIRED" | "CONVERTED";

export interface QuotationLine {
  id: string;
  line_no: number;
  product_id: string | null;
  product_sku: string | null;
  product_name: string | null;
  description: string | null;
  qty: number;
  unit: string;
  unit_price: number;
  discount_pct: number;
  tax_rate: number;
  line_total: number;
}

export interface Quotation {
  id: string;
  quote_no: string;
  version: number;
  customer_id: string;
  customer_name: string | null;
  customer_code: string | null;
  status: QuoteStatus;
  quote_date: string;
  valid_until: string | null;
  currency: string;
  discount_pct: number;
  total_amount: number | null;
  tax_amount: number | null;
  grand_total: number | null;
  sent_at: string | null;
  accepted_at: string | null;
  rejected_at: string | null;
  lost_reason: string | null;
  converted_so_id: string | null;
  created_by_id: string | null;
  notes: string | null;
  created_at: string;
  lines: QuotationLine[];
}

export interface QuoteDashboard {
  total_quotes: number;
  draft_count: number;
  sent_count: number;
  accepted_count: number;
  rejected_count: number;
  expired_count: number;
  converted_count: number;
  win_rate_pct: number | null;
  total_pipeline: number;
}

export interface QuoteLineCreate {
  line_no: number;
  product_id?: string;
  description?: string;
  qty: number;
  unit: string;
  unit_price: number;
  discount_pct: number;
  tax_rate: number;
}

export interface QuoteCreate {
  customer_id: string;
  quote_date: string;
  valid_until?: string;
  currency: string;
  discount_pct: number;
  notes?: string;
  internal_notes?: string;
  lines: QuoteLineCreate[];
}

async function req<T>(url: string, opts?: RequestInit): Promise<T> {
  const r = await fetch(url, { credentials: "include", ...opts });
  if (!r.ok) {
    const err = await r.json().catch(() => ({ detail: r.statusText }));
    throw new Error(err.detail ?? r.statusText);
  }
  return r.json();
}

export const quoteApi = {
  list: (params?: { status?: QuoteStatus; customer_id?: string }) => {
    const q = new URLSearchParams();
    if (params?.status) q.set("status", params.status);
    if (params?.customer_id) q.set("customer_id", params.customer_id);
    return req<Quotation[]>(`${BASE}/?${q}`);
  },
  dashboard: () => req<QuoteDashboard>(`${BASE}/dashboard`),
  get: (id: string) => req<Quotation>(`${BASE}/${id}`),
  create: (body: QuoteCreate) =>
    req<Quotation>(BASE + "/", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) }),
  send: (id: string) => req<Quotation>(`${BASE}/${id}/send`, { method: "POST" }),
  accept: (id: string) => req<Quotation>(`${BASE}/${id}/accept`, { method: "POST" }),
  reject: (id: string, reason?: string) =>
    req<Quotation>(`${BASE}/${id}/reject`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ lost_reason: reason }) }),
  expire: (id: string) => req<Quotation>(`${BASE}/${id}/expire`, { method: "POST" }),
  revise: (id: string) => req<Quotation>(`${BASE}/${id}/revise`, { method: "POST" }),
  convert: (id: string) => req<{ so_id: string; so_no: string; quote_no: string; version: number }>(`${BASE}/${id}/convert`, { method: "POST" }),
};

export const STATUS_COLORS: Record<QuoteStatus, string> = {
  DRAFT:     "bg-gray-100 text-gray-700",
  SENT:      "bg-blue-100 text-blue-700",
  ACCEPTED:  "bg-green-100 text-green-700",
  REJECTED:  "bg-red-100 text-red-700",
  EXPIRED:   "bg-yellow-100 text-yellow-700",
  CONVERTED: "bg-purple-100 text-purple-700",
};

export function fmtCcy(v: number | null, currency = "KES") {
  if (v == null) return "—";
  return new Intl.NumberFormat("en-KE", { style: "currency", currency, minimumFractionDigits: 0 }).format(v);
}

export function fmtDate(d: string | null) {
  if (!d) return "—";
  return new Date(d).toLocaleDateString("en-KE", { day: "2-digit", month: "short", year: "numeric" });
}
