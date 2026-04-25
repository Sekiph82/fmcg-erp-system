"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { psApi, runStatusBadge, fmt, urgencyBadge } from "@/lib/procurement_suggestion";

function Kpi({ label, value, sub, warn }: { label: string; value: string | number; sub?: string; warn?: boolean }) {
  return (
    <div className={`bg-white border rounded-lg p-4 ${warn ? "border-red-200" : "border-gray-200"}`}>
      <p className="text-xs text-gray-500 uppercase tracking-wide">{label}</p>
      <p className={`text-2xl font-bold mt-1 ${warn ? "text-red-600" : "text-gray-900"}`}>{value}</p>
      {sub && <p className="text-xs text-gray-400 mt-1">{sub}</p>}
    </div>
  );
}

export default function ProcurementSuggestionDashboard() {
  const qc = useQueryClient();
  const [showRun, setShowRun] = useState(false);
  const [horizonDays, setHorizonDays] = useState(90);

  const { data, isLoading, isError } = useQuery({
    queryKey: ["ps-dashboard"],
    queryFn: psApi.getDashboard,
  });

  const { data: runs } = useQuery({
    queryKey: ["ps-runs"],
    queryFn: () => psApi.listRuns(0, 10),
  });

  const createRun = useMutation({
    mutationFn: () => psApi.createRun({
      planning_horizon_days: horizonDays,
      include_safety_stock: true,
      include_reorder_point: true,
    }),
    onSuccess: async (run) => {
      await executeRun.mutateAsync(run.id);
    },
  });

  const executeRun = useMutation({
    mutationFn: (id: string) => psApi.executeRun(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["ps-dashboard"] });
      qc.invalidateQueries({ queryKey: ["ps-runs"] });
      setShowRun(false);
      alert("Procurement Suggestion Engine completed.");
    },
  });

  if (isLoading) return <div className="p-8 text-gray-400">Loading…</div>;
  if (isError || !data) return <div className="p-8 text-red-500">Failed to load dashboard.</div>;

  const running = createRun.isPending || executeRun.isPending;

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold text-gray-900">Procurement Suggestion Engine</h1>
          <p className="text-sm text-gray-500">Smart purchasing · Supplier selection · MRP integration · AI optimization</p>
        </div>
        <button
          onClick={() => setShowRun(true)}
          disabled={running}
          className="px-4 py-2 bg-blue-600 text-white text-sm rounded hover:bg-blue-700 disabled:opacity-50"
        >
          {running ? "Running Engine…" : "Run Procurement Engine"}
        </button>
      </div>

      {/* Run modal */}
      {showRun && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl p-6 w-96 space-y-4 shadow-xl">
            <h2 className="text-lg font-semibold">New Procurement Suggestion Run</h2>
            <div>
              <label className="text-sm text-gray-600">Planning Horizon (days)</label>
              <input
                type="number"
                value={horizonDays}
                onChange={(e) => setHorizonDays(Number(e.target.value))}
                className="mt-1 w-full border rounded px-3 py-1.5 text-sm"
              />
            </div>
            <div className="flex gap-2 pt-2">
              <button
                onClick={() => createRun.mutate()}
                disabled={running}
                className="flex-1 py-2 bg-blue-600 text-white rounded text-sm hover:bg-blue-700 disabled:opacity-50"
              >
                {running ? "Running…" : "Start Engine"}
              </button>
              <button onClick={() => setShowRun(false)} className="flex-1 py-2 border rounded text-sm hover:bg-gray-50">
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}

      {/* KPIs */}
      <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-7 gap-3">
        <Kpi label="Total Runs" value={data.total_runs} />
        <Kpi label="Open Suggestions" value={data.open_suggestions} />
        <Kpi label="Critical" value={data.critical_suggestions} warn={data.critical_suggestions > 0} />
        <Kpi label="High Priority" value={data.high_suggestions} warn={data.high_suggestions > 0} />
        <Kpi label="Risk Flagged" value={data.risk_flagged} warn={data.risk_flagged > 0} />
        <Kpi label="Est. Total Cost" value={`KES ${fmt(data.total_estimated_cost, 0)}`} />
        <Kpi label="Converted to PR" value={data.converted_count} />
      </div>

      {/* Secondary KPIs */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <Kpi label="Approved" value={data.approved_count} />
        <Kpi label="Active Suppliers" value={data.supplier_count} />
        <Kpi label="Supplier-Item Prices" value={data.supplier_items_count} sub="Mapped in system" />
        <Kpi label="AI Recommendations" value={data.ai_recs_count} />
      </div>

      {/* Latest runs */}
      <div className="bg-white border border-gray-200 rounded-lg">
        <div className="px-4 py-3 border-b border-gray-100">
          <h2 className="text-sm font-semibold text-gray-700">Recent Runs</h2>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 text-xs text-gray-500 uppercase">
              <tr>
                <th className="text-left px-4 py-2">Run No</th>
                <th className="text-left px-4 py-2">Date</th>
                <th className="text-left px-4 py-2">Status</th>
                <th className="text-right px-4 py-2">Suggestions</th>
                <th className="text-right px-4 py-2">Est. Cost</th>
                <th className="text-left px-4 py-2">Actions</th>
              </tr>
            </thead>
            <tbody>
              {(runs ?? []).map((r) => (
                <tr key={r.id} className="border-t border-gray-100 hover:bg-gray-50">
                  <td className="px-4 py-2 font-mono font-medium text-blue-700">{r.run_no}</td>
                  <td className="px-4 py-2 text-gray-600">{r.suggestion_date}</td>
                  <td className="px-4 py-2">
                    <span className={`px-2 py-0.5 rounded-full text-xs border ${runStatusBadge(r.status)}`}>
                      {r.status}
                    </span>
                  </td>
                  <td className="px-4 py-2 text-right">{r.suggestion_count ?? "—"}</td>
                  <td className="px-4 py-2 text-right">{r.total_estimated_cost ? `KES ${fmt(r.total_estimated_cost, 0)}` : "—"}</td>
                  <td className="px-4 py-2">
                    <a href={`/dashboard/procurement-suggestion/suggestions?run_id=${r.id}`} className="text-blue-600 hover:underline text-xs">
                      View Suggestions →
                    </a>
                  </td>
                </tr>
              ))}
              {!runs?.length && (
                <tr><td colSpan={6} className="px-4 py-6 text-center text-gray-400">No runs yet — click "Run Procurement Engine" to start.</td></tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Quick links */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        {[
          { label: "Suggestion List",      href: "/dashboard/procurement-suggestion/suggestions",      desc: "Review & approve all suggestions" },
          { label: "Grouped Orders",       href: "/dashboard/procurement-suggestion/groups",           desc: "Consolidated supplier orders" },
          { label: "Supplier Prices",      href: "/dashboard/procurement-suggestion/supplier-prices",  desc: "Manage supplier-item price mappings" },
          { label: "AI Recommendations",   href: "/dashboard/procurement-suggestion/ai",               desc: "Supplier optimizer · Risk predictor · Cost optimizer" },
        ].map((link) => (
          <a key={link.href} href={link.href} className="block bg-white border border-gray-200 rounded-lg p-4 hover:border-blue-300 transition-colors">
            <p className="font-medium text-gray-800 text-sm">{link.label}</p>
            <p className="text-xs text-gray-500 mt-1">{link.desc}</p>
          </a>
        ))}
      </div>
    </div>
  );
}
