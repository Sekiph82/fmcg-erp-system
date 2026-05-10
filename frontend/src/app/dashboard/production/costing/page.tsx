"use client";

import { useState, useMemo } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  AreaChart, Area, BarChart, Bar, PieChart, Pie, Cell,
  XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer,
} from "recharts";
import {
  productionCostApi,
  fmtKES, fmtVariance, buildBreakdownPie,
  type CostFilters, type CostReportRow, type OrderCostBreakdown,
} from "@/lib/productionCosting";
import { productsApi } from "@/lib/products";
import { extractApiError } from "@/lib/inventory";
import { ToastContainer } from "@/components/ui/Toast";
import { useToast } from "@/hooks/useToast";

// ── helpers ───────────────────────────────────────────────────────────────────

const fmt2 = (v: number | null | undefined) =>
  v != null ? v.toFixed(2) : "—";

const today = new Date().toISOString().slice(0, 10);
const monthAgo = new Date(Date.now() - 30 * 86400 * 1000).toISOString().slice(0, 10);

function KpiCard({
  label, value, sub, alert,
}: { label: string; value: string; sub?: string; alert?: boolean }) {
  return (
    <div className={`rounded-xl border p-4 flex flex-col gap-1 bg-slate-900
      ${alert ? "border-red-500/50" : "border-slate-700/50"}`}>
      <span className="text-xs text-slate-400">{label}</span>
      <span className={`text-2xl font-bold ${alert ? "text-red-400" : "text-white"}`}>
        {value}
      </span>
      {sub && <span className="text-xs text-slate-500">{sub}</span>}
    </div>
  );
}

// ── page ──────────────────────────────────────────────────────────────────────

export default function ProductionCostingPage() {
  const qc = useQueryClient();
  const { toasts, toast, dismiss } = useToast();

  const [dateFrom, setDateFrom]     = useState(monthAgo);
  const [dateTo, setDateTo]         = useState(today);
  const [productId, setProductId]   = useState("");
  const [detailOrder, setDetailOrder] = useState<OrderCostBreakdown | null>(null);
  const [detailOpen, setDetailOpen] = useState(false);
  const [finalizeId, setFinalizeId] = useState("");
  const [finalizeOpen, setFinalizeOpen] = useState(false);

  const params: CostFilters = {
    date_from: dateFrom || undefined,
    date_to:   dateTo   || undefined,
    product_id: productId || undefined,
  };

  const { data: kpis, isLoading: kpisLoading } = useQuery({
    queryKey: ["cost-kpis", params],
    queryFn: () => productionCostApi.kpis({ date_from: params.date_from, date_to: params.date_to }),
  });

  const { data: report = [], isLoading: reportLoading } = useQuery({
    queryKey: ["cost-report", params],
    queryFn: () => productionCostApi.report(params),
  });

  const { data: trend = [] } = useQuery({
    queryKey: ["cost-trend", params],
    queryFn: () => productionCostApi.trend(params),
  });

  const { data: products = [] } = useQuery({
    queryKey: ["products-list"],
    queryFn: () => productsApi.list(0, 200),
  });

  const pieData = useMemo(() => (kpis ? buildBreakdownPie(kpis) : []), [kpis]);

  // Finalize cost for one order
  const finalizeMut = useMutation({
    mutationFn: (id: string) => productionCostApi.finalizeOrderCost(id),
    onSuccess: (data) => {
      qc.invalidateQueries({ queryKey: ["cost-kpis"] });
      qc.invalidateQueries({ queryKey: ["cost-report"] });
      qc.invalidateQueries({ queryKey: ["cost-trend"] });
      setFinalizeOpen(false);
      setFinalizeId("");
      toast("success", "Cost finalized", `Order ${data.order_no} — ${fmtKES(data.total_cost)}`);
    },
    onError: (err) => toast("error", "Failed", extractApiError(err)),
  });

  return (
    <div className="space-y-6">
      <ToastContainer toasts={toasts} onDismiss={dismiss} />

      {/* ── Header ── */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Production Costing</h1>
          <p className="text-slate-400 text-sm mt-0.5">
            Actual vs standard cost per batch · material, labor, machine, energy breakdown
          </p>
        </div>
        <button
          onClick={() => setFinalizeOpen(true)}
          className="bg-indigo-600 hover:bg-indigo-700 text-white text-sm px-4 py-2 rounded-lg"
        >
          Finalize Order Cost
        </button>
      </div>

      {/* ── Filters ── */}
      <div className="flex flex-wrap gap-3 p-4 bg-slate-900 rounded-xl border border-slate-700/50">
        <div className="flex flex-col gap-1">
          <label className="text-xs text-slate-400">Date From</label>
          <input
            type="date" value={dateFrom} onChange={e => setDateFrom(e.target.value)}
            className="bg-slate-800 border border-slate-700 rounded-lg px-3 py-1.5 text-sm text-white"
          />
        </div>
        <div className="flex flex-col gap-1">
          <label className="text-xs text-slate-400">Date To</label>
          <input
            type="date" value={dateTo} onChange={e => setDateTo(e.target.value)}
            className="bg-slate-800 border border-slate-700 rounded-lg px-3 py-1.5 text-sm text-white"
          />
        </div>
        <div className="flex flex-col gap-1">
          <label className="text-xs text-slate-400">Product</label>
          <select
            value={productId} onChange={e => setProductId(e.target.value)}
            className="bg-slate-800 border border-slate-700 rounded-lg px-3 py-1.5 text-sm text-white"
          >
            <option value="">All Products</option>
            {products.map((p: any) => (
              <option key={p.id} value={p.id}>{p.sku} — {p.name}</option>
            ))}
          </select>
        </div>
      </div>

      {/* ── KPI Cards ── */}
      {kpisLoading ? (
        <div className="text-slate-400 text-sm">Loading KPIs…</div>
      ) : kpis ? (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <KpiCard label="Total Production Cost"   value={fmtKES(kpis.total_cost)}      sub={`${kpis.order_count} orders`} />
          <KpiCard label="Avg Cost per Unit"        value={fmtKES(kpis.avg_cost_per_unit)} />
          <KpiCard label="Avg Cost Variance"        value={fmtVariance(kpis.avg_variance_pct).text}
            alert={kpis.flag_high_variance}
            sub={`${kpis.over_budget_count} orders >5% over budget`}
          />
          <KpiCard label="Over-Budget Orders"       value={String(kpis.over_budget_count)} alert={kpis.over_budget_count > 0} />
          <KpiCard label="Material Cost"            value={fmtKES(kpis.total_material_cost)} sub={`${kpis.material_pct.toFixed(1)}% of total`} alert={kpis.flag_high_material} />
          <KpiCard label="Labor Cost"               value={fmtKES(kpis.total_labor_cost)}    sub={`${kpis.labor_pct.toFixed(1)}% of total`} />
          <KpiCard label="Machine Cost"             value={fmtKES(kpis.total_machine_cost)}  sub={`${kpis.machine_pct.toFixed(1)}% of total`} />
          <KpiCard label="Energy Cost"              value={fmtKES(kpis.total_energy_cost)}   sub={`${kpis.energy_pct.toFixed(1)}% of total`} />
        </div>
      ) : null}

      {/* ── Charts row ── */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Cost breakdown pie */}
        <div className="bg-slate-900 rounded-xl border border-slate-700/50 p-4">
          <h3 className="text-sm font-medium text-slate-300 mb-3">Cost Breakdown</h3>
          {pieData.length > 0 ? (
            <ResponsiveContainer width="100%" height={220}>
              <PieChart>
                <Pie
                  data={pieData} cx="50%" cy="50%" innerRadius={55} outerRadius={85}
                  dataKey="value" nameKey="name" stroke="none"
                  label={({ name, payload }: any) =>
                    `${name} ${(payload?.pct ?? 0).toFixed(1)}%`
                  }
                  labelLine={false}
                >
                  {pieData.map((d, i) => (
                    <Cell key={i} fill={d.fill} />
                  ))}
                </Pie>
                <Tooltip formatter={(v: unknown) => fmtKES(v as number)} />
              </PieChart>
            </ResponsiveContainer>
          ) : (
            <div className="h-[220px] flex items-center justify-center text-slate-500 text-sm">
              No finalized cost data yet
            </div>
          )}
          {/* Legend */}
          <div className="mt-2 grid grid-cols-2 gap-1">
            {pieData.map(d => (
              <div key={d.name} className="flex items-center gap-1.5 text-xs text-slate-400">
                <span className="w-2.5 h-2.5 rounded-full" style={{ background: d.fill }} />
                {d.name}
              </div>
            ))}
          </div>
        </div>

        {/* Cost trend stacked area */}
        <div className="lg:col-span-2 bg-slate-900 rounded-xl border border-slate-700/50 p-4">
          <h3 className="text-sm font-medium text-slate-300 mb-3">Daily Cost Trend</h3>
          {trend.length > 0 ? (
            <ResponsiveContainer width="100%" height={220}>
              <AreaChart data={trend} margin={{ top: 5, right: 10, left: 0, bottom: 0 }}>
                <defs>
                  <linearGradient id="gMat" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%"  stopColor="#6366f1" stopOpacity={0.4} />
                    <stop offset="95%" stopColor="#6366f1" stopOpacity={0.05} />
                  </linearGradient>
                  <linearGradient id="gLab" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%"  stopColor="#22d3ee" stopOpacity={0.4} />
                    <stop offset="95%" stopColor="#22d3ee" stopOpacity={0.05} />
                  </linearGradient>
                  <linearGradient id="gMach" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%"  stopColor="#f59e0b" stopOpacity={0.4} />
                    <stop offset="95%" stopColor="#f59e0b" stopOpacity={0.05} />
                  </linearGradient>
                  <linearGradient id="gEng" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%"  stopColor="#10b981" stopOpacity={0.4} />
                    <stop offset="95%" stopColor="#10b981" stopOpacity={0.05} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                <XAxis dataKey="date" tick={{ fill: "#94a3b8", fontSize: 10 }} tickLine={false} />
                <YAxis tick={{ fill: "#94a3b8", fontSize: 10 }} tickLine={false}
                  tickFormatter={v => `${(v/1000).toFixed(0)}k`} />
                <Tooltip
                  contentStyle={{ background: "#0f172a", border: "1px solid #334155" }}
                  formatter={(v: unknown) => fmtKES(v as number)}
                />
                <Legend wrapperStyle={{ fontSize: 11 }} />
                <Area type="monotone" dataKey="material_cost"  name="Materials" stackId="1" stroke="#6366f1" fill="url(#gMat)"  />
                <Area type="monotone" dataKey="labor_cost"     name="Labor"     stackId="1" stroke="#22d3ee" fill="url(#gLab)"  />
                <Area type="monotone" dataKey="machine_cost"   name="Machine"   stackId="1" stroke="#f59e0b" fill="url(#gMach)" />
                <Area type="monotone" dataKey="energy_cost"    name="Energy"    stackId="1" stroke="#10b981" fill="url(#gEng)"  />
              </AreaChart>
            </ResponsiveContainer>
          ) : (
            <div className="h-[220px] flex items-center justify-center text-slate-500 text-sm">
              No trend data in selected period
            </div>
          )}
        </div>
      </div>

      {/* ── Product Cost Report Table ── */}
      <div className="bg-slate-900 rounded-xl border border-slate-700/50 overflow-hidden">
        <div className="p-4 border-b border-slate-700/50 flex items-center justify-between">
          <h3 className="font-medium text-white">Cost by Product</h3>
          <span className="text-xs text-slate-400">
            {report.length} product{report.length !== 1 ? "s" : ""}
          </span>
        </div>
        {reportLoading ? (
          <div className="p-6 text-center text-slate-400 text-sm">Loading…</div>
        ) : report.length === 0 ? (
          <div className="p-6 text-center text-slate-500 text-sm">
            No finalized cost data for this period.
            Use &quot;Finalize Order Cost&quot; to compute and persist costs for completed orders.
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="bg-slate-800/60">
                  {["SKU", "Product", "Orders", "Total Qty", "Material", "Labor", "Machine", "Energy", "Total Cost", "Cost/Unit", "vs Standard", "Mat%"].map(h => (
                    <th key={h} className="px-3 py-2 text-left text-xs text-slate-400 font-medium whitespace-nowrap">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {report.map((row: CostReportRow) => {
                  const v = fmtVariance(row.avg_variance_pct);
                  return (
                    <tr key={row.product_id} className="border-t border-slate-800 hover:bg-slate-800/40">
                      <td className="px-3 py-2 font-mono text-indigo-400 text-xs">{row.sku}</td>
                      <td className="px-3 py-2 text-white">{row.product_name}</td>
                      <td className="px-3 py-2 text-slate-300 text-center">{row.order_count}</td>
                      <td className="px-3 py-2 text-slate-300">{row.total_qty.toLocaleString()} kg</td>
                      <td className="px-3 py-2 text-slate-300">{fmtKES(row.total_material_cost)}</td>
                      <td className="px-3 py-2 text-slate-300">{fmtKES(row.total_labor_cost)}</td>
                      <td className="px-3 py-2 text-slate-300">{fmtKES(row.total_machine_cost)}</td>
                      <td className="px-3 py-2 text-slate-300">{fmtKES(row.total_energy_cost)}</td>
                      <td className="px-3 py-2 font-semibold text-white">{fmtKES(row.total_cost)}</td>
                      <td className="px-3 py-2 text-slate-300">{fmtKES(row.avg_cost_per_unit)}</td>
                      <td className={`px-3 py-2 font-medium ${v.color}`}>{v.text}</td>
                      <td className={`px-3 py-2 text-xs ${row.material_pct > 70 ? "text-amber-400" : "text-slate-400"}`}>
                        {row.material_pct.toFixed(1)}%
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* ── Finalize Order Modal ── */}
      {finalizeOpen && (
        <div className="fixed inset-0 z-50 bg-black/60 flex items-center justify-center p-4">
          <div className="bg-slate-900 rounded-2xl border border-slate-700 w-full max-w-md p-6 space-y-4">
            <h2 className="text-lg font-semibold text-white">Finalize Order Cost</h2>
            <p className="text-sm text-slate-400">
              Enter the Production Order ID to compute and persist costs.
              Only COMPLETED orders can be finalized.
            </p>
            <div className="flex flex-col gap-1">
              <label className="text-xs text-slate-400">Production Order ID (UUID)</label>
              <input
                value={finalizeId} onChange={e => setFinalizeId(e.target.value)}
                placeholder="e.g. 550e8400-e29b-41d4-a716-..."
                className="bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm text-white"
              />
            </div>
            <div className="flex gap-2 justify-end">
              <button
                onClick={() => { setFinalizeOpen(false); setFinalizeId(""); }}
                className="px-4 py-2 text-sm text-slate-400 hover:text-white"
              >
                Cancel
              </button>
              <button
                onClick={() => finalizeId && finalizeMut.mutate(finalizeId)}
                disabled={!finalizeId || finalizeMut.isPending}
                className="bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 text-white text-sm px-4 py-2 rounded-lg"
              >
                {finalizeMut.isPending ? "Computing…" : "Finalize"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
