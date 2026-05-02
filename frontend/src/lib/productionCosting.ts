/**
 * Production Costing Engine — TypeScript types and API client.
 *
 * Costing data flows:
 *   MaterialConsumption × Material.standard_cost → total_material_cost
 *   LaborLog × WorkCenter.labor_rate_per_hour     → total_labor_cost
 *   WorkOrder duration × machine_cost_per_hour    → total_machine_cost
 *   UtilityTransaction (by batch_id)              → total_energy_cost
 */
import { apiClient } from "./api";

// ── Types ──────────────────────────────────────────────────────────────────────

export interface OrderCostBreakdown {
  order_id:                string;
  order_no:                string;
  product_name:            string | null;
  product_sku:             string | null;
  status:                  string;
  actual_quantity:         number | null;
  uom:                     string;

  total_material_cost:     number | null;
  total_labor_cost:        number | null;
  total_machine_cost:      number | null;
  total_energy_cost:       number | null;
  total_cost:              number | null;
  cost_per_unit:           number | null;
  standard_cost_per_unit:  number | null;
  cost_variance_pct:       number | null;
  costing_finalized_at:    string | null;

  material_row_count:      number | null;
  labor_row_count:         number | null;
}

export interface CostReportRow {
  product_id:              string;
  sku:                     string;
  product_name:            string;
  standard_cost_per_unit:  number;
  order_count:             number;
  total_qty:               number;
  total_material_cost:     number;
  total_labor_cost:        number;
  total_machine_cost:      number;
  total_energy_cost:       number;
  total_cost:              number;
  avg_cost_per_unit:       number;
  avg_variance_pct:        number;
  material_pct:            number;
  labor_pct:               number;
  machine_pct:             number;
  energy_pct:              number;
}

export interface CostTrendPoint {
  date:              string;
  material_cost:     number;
  labor_cost:        number;
  machine_cost:      number;
  energy_cost:       number;
  total_cost:        number;
  total_qty:         number;
  avg_cost_per_unit: number;
  order_count:       number;
}

export interface CostKPIs {
  order_count:           number;
  total_qty:             number;
  total_material_cost:   number;
  total_labor_cost:      number;
  total_machine_cost:    number;
  total_energy_cost:     number;
  total_cost:            number;
  avg_cost_per_unit:     number;
  avg_variance_pct:      number;
  over_budget_count:     number;
  material_pct:          number;
  labor_pct:             number;
  machine_pct:           number;
  energy_pct:            number;
  flag_high_variance:    boolean;
  flag_high_material:    boolean;
}

export interface CostFilters {
  date_from?:  string;
  date_to?:    string;
  product_id?: string;
}

// ── API client ─────────────────────────────────────────────────────────────────

export const productionCostApi = {
  async kpis(params?: Pick<CostFilters, "date_from" | "date_to">): Promise<CostKPIs> {
    const r = await apiClient.get<CostKPIs>("/api/v1/production-cost/kpis", { params });
    return r.data;
  },

  async report(params?: CostFilters): Promise<CostReportRow[]> {
    const r = await apiClient.get<CostReportRow[]>("/api/v1/production-cost/report", { params });
    return r.data;
  },

  async trend(params?: CostFilters): Promise<CostTrendPoint[]> {
    const r = await apiClient.get<CostTrendPoint[]>("/api/v1/production-cost/trend", { params });
    return r.data;
  },

  async getOrderCost(orderId: string): Promise<OrderCostBreakdown> {
    const r = await apiClient.get<OrderCostBreakdown>(
      `/api/v1/production-cost/orders/${orderId}/cost`,
    );
    return r.data;
  },

  async finalizeOrderCost(orderId: string): Promise<OrderCostBreakdown> {
    const r = await apiClient.post<OrderCostBreakdown>(
      `/api/v1/production-cost/orders/${orderId}/finalize`,
    );
    return r.data;
  },
};

// ── Formatting helpers ──────────────────────────────────────────────────────────

export function fmtKES(v: number | null | undefined): string {
  if (v == null) return "—";
  return new Intl.NumberFormat("en-KE", {
    style: "currency", currency: "KES", maximumFractionDigits: 2,
  }).format(v);
}

export function fmtVariance(v: number | null | undefined): {
  text: string; color: string;
} {
  if (v == null) return { text: "—", color: "text-slate-400" };
  const sign = v > 0 ? "+" : "";
  const color = v > 10 ? "text-red-400" : v > 0 ? "text-amber-400" : "text-emerald-400";
  return { text: `${sign}${v.toFixed(1)}%`, color };
}

// Recharts pie data for cost breakdown
export function buildBreakdownPie(kpis: CostKPIs) {
  return [
    { name: "Materials",  value: kpis.total_material_cost, pct: kpis.material_pct, fill: "#6366f1" },
    { name: "Labor",      value: kpis.total_labor_cost,    pct: kpis.labor_pct,    fill: "#22d3ee" },
    { name: "Machine",    value: kpis.total_machine_cost,  pct: kpis.machine_pct,  fill: "#f59e0b" },
    { name: "Energy",     value: kpis.total_energy_cost,   pct: kpis.energy_pct,   fill: "#10b981" },
  ].filter(d => d.value > 0);
}
