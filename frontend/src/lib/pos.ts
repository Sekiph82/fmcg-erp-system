const BASE = "/api/v1/pos";

export type POSSessionStatus = "OPEN" | "CLOSED";
export type POSPaymentMethod = "CASH" | "MPESA" | "CARD" | "SPLIT";
export type POSSaleStatus    = "COMPLETED" | "VOIDED";

export interface POSSaleLineCreate {
  product_id:   string;
  qty:          number;
  unit_price:   number;
  discount_pct: number;
  tax_rate:     number;
}

export interface POSSaleLine extends POSSaleLineCreate {
  id:           string;
  line_no:      number;
  product_name: string | null;
  product_sku:  string | null;
  line_total:   number;
}

export interface POSSale {
  id:             string;
  sale_no:        string;
  session_id:     string;
  cashier_id:     string | null;
  cashier_name:   string | null;
  customer_id:    string | null;
  customer_name:  string | null;
  payment_method: POSPaymentMethod;
  status:         POSSaleStatus;
  subtotal:       number;
  discount_total: number;
  tax_total:      number;
  sale_total:     number;
  amount_paid:    number | null;
  change_given:   number | null;
  mpesa_ref:      string | null;
  notes:          string | null;
  created_at:     string;
  lines:          POSSaleLine[];
}

export interface POSSession {
  id:                 string;
  session_no:         string;
  cashier_id:         string | null;
  cashier_name:       string | null;
  register_id:        string;
  status:             POSSessionStatus;
  opened_at:          string;
  closed_at:          string | null;
  opening_float:      number;
  closing_cash:       number | null;
  expected_cash:      number | null;
  cash_difference:    number | null;
  total_sales:        number;
  total_transactions: number;
  notes:              string | null;
  created_at:         string;
}

export interface POSDashboard {
  today_sales_count:  number;
  today_sales_total:  number;
  today_cash_total:   number;
  today_mpesa_total:  number;
  today_card_total:   number;
  open_sessions:      number;
  avg_basket_value:   number | null;
}

async function req<T>(url: string, opts?: RequestInit): Promise<T> {
  const r = await fetch(url, { credentials: "include", ...opts });
  if (!r.ok) {
    const err = await r.json().catch(() => ({ detail: r.statusText }));
    throw new Error(err.detail ?? r.statusText);
  }
  return r.json();
}

const json = (body: unknown, method = "POST") => ({
  method,
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify(body),
});

export const posApi = {
  dashboard: () => req<POSDashboard>(`${BASE}/dashboard`),

  currentSession: () => req<POSSession | null>(`${BASE}/sessions/current`),
  listSessions: (status?: POSSessionStatus) => {
    const q = status ? `?status=${status}` : "";
    return req<POSSession[]>(`${BASE}/sessions${q}`);
  },
  openSession: (register_id: string, opening_float: number) =>
    req<POSSession>(BASE + "/sessions", json({ register_id, opening_float })),
  closeSession: (id: string, closing_cash: number, notes?: string) =>
    req<POSSession>(`${BASE}/sessions/${id}/close`, json({ closing_cash, notes })),

  createSale: (body: {
    customer_id?: string;
    payment_method: POSPaymentMethod;
    amount_paid?: number;
    mpesa_ref?: string;
    lines: POSSaleLineCreate[];
  }) => req<POSSale>(BASE + "/sales", json(body)),

  listSales: () => req<POSSale[]>(`${BASE}/sales`),
  voidSale: (id: string) => req<POSSale>(`${BASE}/sales/${id}/void`, { method: "POST" }),
};

export function fmtKES(v: number) {
  return new Intl.NumberFormat("en-KE", { style: "currency", currency: "KES", minimumFractionDigits: 2 }).format(v);
}
