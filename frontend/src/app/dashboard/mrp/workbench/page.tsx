"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { mrpApi, MRPException, MRPResult, MRPSuggestion } from "@/lib/mrp";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";

const SEV_COLOR: Record<string, "red" | "yellow" | "gray" | "blue"> = {
  CRITICAL: "red",
  HIGH:     "red",
  MEDIUM:   "yellow",
  LOW:      "gray",
};

const EXC_ICON: Record<string, string> = {
  SHORTAGE:     "⚠",
  EXCESS_STOCK: "📦",
  LATE_ORDER:   "🕐",
  DEMAND_SPIKE: "📈",
  FROZEN_DEMAND:"🔒",
};

function fmtDate(s?: string | null) {
  if (!s) return "—";
  return new Date(s).toLocaleDateString("en-KE", { day: "2-digit", month: "short", year: "numeric" });
}

function fmtQty(n?: number | null) {
  if (n == null) return "—";
  return n.toLocaleString(undefined, { maximumFractionDigits: 0 });
}

export default function PlannerWorkbenchPage() {
  const qc = useQueryClient();
  const [tab, setTab] = useState<"exceptions" | "supply_demand" | "suggestions">("exceptions");
  const [showAcknowledged, setShowAcknowledged] = useState(false);

  const { data: dashboard } = useQuery({
    queryKey: ["mrp-dashboard"],
    queryFn: () => mrpApi.getDashboard(),
  });

  const lastRunId = dashboard?.last_run?.id;

  const { data: exceptions = [], isLoading: excLoading } = useQuery({
    queryKey: ["mrp-exceptions", lastRunId, showAcknowledged],
    queryFn: () => mrpApi.getExceptions(lastRunId, !showAcknowledged),
    enabled: !!lastRunId && tab === "exceptions",
  });

  const { data: results = [], isLoading: resLoading } = useQuery({
    queryKey: ["mrp-results", lastRunId],
    queryFn: () => mrpApi.getRunResults(lastRunId!),
    enabled: !!lastRunId && tab === "supply_demand",
  });

  const { data: suggestions = [], isLoading: sugLoading } = useQuery({
    queryKey: ["mrp-suggestions", lastRunId],
    queryFn: () => mrpApi.listSuggestions({ run_id: lastRunId, status: "DRAFT" }),
    enabled: !!lastRunId && tab === "suggestions",
  });

  const ackException = useMutation({
    mutationFn: (id: string) => mrpApi.acknowledgeException(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["mrp-exceptions"] }),
  });

  const approveSuggestion = useMutation({
    mutationFn: (id: string) => mrpApi.approveSuggestion(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["mrp-suggestions"] }),
  });

  const rejectSuggestion = useMutation({
    mutationFn: (id: string) => mrpApi.rejectSuggestion(id, "Rejected from workbench"),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["mrp-suggestions"] }),
  });

  const criticalCount = exceptions.filter((e) => e.severity === "CRITICAL" || e.severity === "HIGH").length;
  const shortageCount = exceptions.filter((e) => e.exception_type === "SHORTAGE").length;
  const lateCount = exceptions.filter((e) => e.exception_type === "LATE_ORDER").length;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Planner Workbench</h1>
        <p className="text-sm text-gray-500 mt-1">
          {dashboard?.last_run
            ? `Run ${dashboard.last_run.run_no} · ${fmtDate(dashboard.last_run.run_date)} · ${dashboard.last_run.planning_horizon_days}d horizon${dashboard.last_run.frozen_horizon_days ? ` · ${dashboard.last_run.frozen_horizon_days}d frozen` : ""}`
            : "No MRP run completed yet"}
        </p>
      </div>

      {/* KPI strip */}
      <div className="grid grid-cols-5 gap-3">
        {[
          { label: "Open Suggestions",  value: dashboard?.open_suggestions   ?? 0, color: "text-indigo-700" },
          { label: "Pending Approval",  value: dashboard?.pending_approval    ?? 0, color: "text-amber-700" },
          { label: "Shortage Products", value: dashboard?.shortage_products   ?? 0, color: "text-red-700" },
          { label: "Exceptions",        value: criticalCount,                       color: criticalCount > 0 ? "text-red-600" : "text-gray-600" },
          { label: "Active Forecasts",  value: dashboard?.active_forecasts    ?? 0, color: "text-emerald-700" },
        ].map((k) => (
          <div key={k.label} className="bg-white rounded-lg border p-3 text-center">
            <p className="text-xs text-gray-500 mb-1">{k.label}</p>
            <p className={`text-2xl font-bold ${k.color}`}>{k.value}</p>
          </div>
        ))}
      </div>

      {/* Tabs */}
      <div className="flex gap-1 border-b">
        {([
          { key: "exceptions",    label: `Exceptions${exceptions.length ? ` (${exceptions.length})` : ""}` },
          { key: "supply_demand", label: "Supply vs Demand" },
          { key: "suggestions",   label: `Pending Suggestions${suggestions.length ? ` (${suggestions.length})` : ""}` },
        ] as const).map((t) => (
          <button
            key={t.key}
            className={`px-4 py-2 text-sm font-medium border-b-2 -mb-px ${tab === t.key ? "border-indigo-600 text-indigo-600" : "border-transparent text-gray-500 hover:text-gray-700"}`}
            onClick={() => setTab(t.key)}
          >
            {t.label}
          </button>
        ))}
      </div>

      {/* EXCEPTIONS tab */}
      {tab === "exceptions" && (
        <div className="bg-white rounded-lg border">
          <div className="px-5 py-3 border-b flex items-center justify-between">
            <div className="flex items-center gap-4">
              <h2 className="font-semibold text-gray-800">MRP Exceptions</h2>
              <div className="flex gap-3 text-xs text-gray-500">
                <span>⚠ {shortageCount} shortage</span>
                <span>🕐 {lateCount} late orders</span>
              </div>
            </div>
            <label className="flex items-center gap-2 text-sm text-gray-500 cursor-pointer">
              <input type="checkbox" checked={showAcknowledged} onChange={(e) => setShowAcknowledged(e.target.checked)} />
              Show acknowledged
            </label>
          </div>
          {excLoading ? (
            <p className="px-5 py-8 text-center text-gray-400">Loading…</p>
          ) : (
            <div className="divide-y">
              {exceptions.map((exc) => (
                <div key={exc.id} className={`px-5 py-3 flex items-start gap-4 ${exc.is_acknowledged ? "opacity-50" : ""}`}>
                  <span className="text-xl mt-0.5">{EXC_ICON[exc.exception_type] ?? "⚡"}</span>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      <Badge label={exc.severity} variant={SEV_COLOR[exc.severity] ?? "gray"} />
                      <span className="text-xs text-gray-500 font-medium">{exc.exception_type.replace("_", " ")}</span>
                      {exc.product_name && <span className="text-xs text-indigo-600">{exc.product_name}</span>}
                      {exc.material_name && <span className="text-xs text-indigo-600">{exc.material_name}</span>}
                    </div>
                    <p className="text-sm text-gray-800">{exc.message}</p>
                    {exc.action_required && (
                      <p className="text-xs text-amber-700 mt-1">→ {exc.action_required}</p>
                    )}
                    <div className="flex gap-3 mt-1 text-xs text-gray-400">
                      {exc.qty != null && <span>Qty: {fmtQty(exc.qty)}</span>}
                      {exc.due_date && <span>Due: {fmtDate(exc.due_date)}</span>}
                    </div>
                  </div>
                  {!exc.is_acknowledged && (
                    <button
                      className="text-xs text-gray-400 hover:text-gray-700 shrink-0"
                      onClick={() => ackException.mutate(exc.id)}
                    >
                      Acknowledge
                    </button>
                  )}
                </div>
              ))}
              {exceptions.length === 0 && (
                <p className="px-5 py-8 text-center text-emerald-600 font-medium">No exceptions — plan looks clean</p>
              )}
            </div>
          )}
        </div>
      )}

      {/* SUPPLY vs DEMAND tab */}
      {tab === "supply_demand" && (
        <div className="bg-white rounded-lg border overflow-x-auto">
          <div className="px-5 py-3 border-b font-semibold text-gray-800">Supply vs Demand — {results.length} products</div>
          {resLoading ? (
            <p className="px-5 py-8 text-center text-gray-400">Loading…</p>
          ) : (
            <table className="w-full text-sm min-w-[800px]">
              <thead>
                <tr className="border-b bg-gray-50 text-xs text-gray-500 uppercase">
                  <th className="px-4 py-2 text-left">Product</th>
                  <th className="px-4 py-2 text-right">SO Demand</th>
                  <th className="px-4 py-2 text-right">Forecast</th>
                  <th className="px-4 py-2 text-right">Safety Stock</th>
                  <th className="px-4 py-2 text-right">Gross Demand</th>
                  <th className="px-4 py-2 text-right">On Hand</th>
                  <th className="px-4 py-2 text-right">Incoming</th>
                  <th className="px-4 py-2 text-right">Net Req.</th>
                  <th className="px-4 py-2 text-center">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y">
                {results.map((r) => (
                  <tr key={r.id} className={`hover:bg-gray-50 ${r.shortage_flag ? "bg-red-50" : ""}`}>
                    <td className="px-4 py-2">
                      <span className="font-medium text-gray-800">{r.product_name ?? r.product_sku ?? "—"}</span>
                    </td>
                    <td className="px-4 py-2 text-right text-gray-600">{fmtQty(r.so_demand_qty)}</td>
                    <td className="px-4 py-2 text-right text-gray-500">{fmtQty(r.forecast_demand_qty)}</td>
                    <td className="px-4 py-2 text-right text-gray-500">{fmtQty(r.safety_stock_qty)}</td>
                    <td className="px-4 py-2 text-right font-medium text-gray-800">{fmtQty(r.gross_demand_qty)}</td>
                    <td className="px-4 py-2 text-right text-emerald-700">{fmtQty(r.stock_on_hand_qty)}</td>
                    <td className="px-4 py-2 text-right text-blue-600">{fmtQty(r.incoming_po_qty + r.incoming_prod_qty)}</td>
                    <td className={`px-4 py-2 text-right font-bold ${r.shortage_flag ? "text-red-700" : "text-emerald-700"}`}>
                      {fmtQty(r.net_requirement_qty)}
                    </td>
                    <td className="px-4 py-2 text-center">
                      <Badge label={r.shortage_flag ? "SHORTAGE" : "OK"} variant={r.shortage_flag ? "red" : "green"} />
                    </td>
                  </tr>
                ))}
                {results.length === 0 && (
                  <tr><td colSpan={9} className="px-5 py-8 text-center text-gray-400">No results</td></tr>
                )}
              </tbody>
            </table>
          )}
        </div>
      )}

      {/* SUGGESTIONS tab */}
      {tab === "suggestions" && (
        <div className="bg-white rounded-lg border">
          <div className="px-5 py-3 border-b font-semibold text-gray-800">
            Draft Suggestions — Quick Approve / Reject
          </div>
          {sugLoading ? (
            <p className="px-5 py-8 text-center text-gray-400">Loading…</p>
          ) : (
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b bg-gray-50 text-xs text-gray-500 uppercase">
                  <th className="px-4 py-2 text-left">Type</th>
                  <th className="px-4 py-2 text-left">Item</th>
                  <th className="px-4 py-2 text-right">Qty</th>
                  <th className="px-4 py-2 text-left">Required</th>
                  <th className="px-4 py-2 text-left">Order By</th>
                  <th className="px-4 py-2 text-right">MOQ</th>
                  <th className="px-4 py-2 text-right">Est. Cost</th>
                  <th className="px-4 py-2" />
                </tr>
              </thead>
              <tbody className="divide-y">
                {suggestions.map((s) => (
                  <tr key={s.id} className="hover:bg-gray-50">
                    <td className="px-4 py-2.5">
                      <span className={`text-xs px-2 py-0.5 rounded font-medium ${s.suggestion_type === "PRODUCTION" ? "bg-purple-100 text-purple-700" : "bg-blue-100 text-blue-700"}`}>
                        {s.suggestion_type}
                      </span>
                    </td>
                    <td className="px-4 py-2.5 text-gray-700">
                      {s.product_name ?? s.material_name ?? "—"}
                      {s.product_sku && <span className="text-xs text-gray-400 ml-1">({s.product_sku})</span>}
                    </td>
                    <td className="px-4 py-2.5 text-right font-medium">{fmtQty(s.suggested_qty)} {s.uom}</td>
                    <td className="px-4 py-2.5 text-gray-500 text-xs">{fmtDate(s.required_date)}</td>
                    <td className="px-4 py-2.5 text-xs">
                      {s.planned_start_date ? (
                        <span className={new Date(s.planned_start_date) < new Date() ? "text-red-600 font-medium" : "text-gray-500"}>
                          {fmtDate(s.planned_start_date)}
                          {new Date(s.planned_start_date) < new Date() ? " ⚠" : ""}
                        </span>
                      ) : "—"}
                    </td>
                    <td className="px-4 py-2.5 text-right text-gray-500">{s.moq != null ? fmtQty(s.moq) : "—"}</td>
                    <td className="px-4 py-2.5 text-right text-gray-600">
                      {s.estimated_cost != null ? `KES ${s.estimated_cost.toLocaleString(undefined, { maximumFractionDigits: 0 })}` : "—"}
                    </td>
                    <td className="px-4 py-2.5">
                      <div className="flex gap-2 justify-end">
                        <button
                          className="text-xs bg-green-100 text-green-700 px-2 py-1 rounded hover:bg-green-200"
                          onClick={() => approveSuggestion.mutate(s.id)}
                        >
                          Approve
                        </button>
                        <button
                          className="text-xs bg-red-100 text-red-700 px-2 py-1 rounded hover:bg-red-200"
                          onClick={() => rejectSuggestion.mutate(s.id)}
                        >
                          Reject
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
                {suggestions.length === 0 && (
                  <tr><td colSpan={8} className="px-5 py-8 text-center text-gray-400">No draft suggestions</td></tr>
                )}
              </tbody>
            </table>
          )}
        </div>
      )}
    </div>
  );
}
