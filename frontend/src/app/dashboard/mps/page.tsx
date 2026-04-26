"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  mpsApi, MPSDashboard, MPSPlanSummary,
  STATUS_COLOR, FEASIBILITY_COLOR,
} from "@/lib/mps";

function KpiCard({ label, value, sub, color }: {
  label: string; value: string | number; sub?: string; color?: string;
}) {
  return (
    <div className="bg-white rounded-xl border border-gray-100 p-5 shadow-sm">
      <p className="text-xs font-medium text-gray-400 uppercase tracking-wide">{label}</p>
      <p className={`text-3xl font-bold mt-1 ${color || "text-gray-900"}`}>{value}</p>
      {sub && <p className="text-xs text-gray-400 mt-1">{sub}</p>}
    </div>
  );
}

function Badge({ label, color }: { label: string; color: string }) {
  return (
    <span className={`px-2 py-0.5 rounded text-xs font-medium ${color}`}>{label}</span>
  );
}

export default function MPSDashboardPage() {
  const qc = useQueryClient();
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [form, setForm] = useState({
    plan_name: "",
    start_date: "",
    end_date: "",
    planning_mode: "ASSISTED",
    capacity_mode: "FINITE",
    planning_horizon_days: 90,
    notes: "",
  });

  const { data: dash, isLoading } = useQuery<MPSDashboard>({
    queryKey: ["mps-dashboard"],
    queryFn: () => mpsApi.dashboard(),
  });

  const createPlan = useMutation({
    mutationFn: () => mpsApi.createPlan({
      ...form,
      planning_horizon_days: Number(form.planning_horizon_days),
    } as Parameters<typeof mpsApi.createPlan>[0]),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["mps-dashboard"] });
      setShowCreateModal(false);
      setForm({ plan_name: "", start_date: "", end_date: "", planning_mode: "ASSISTED", capacity_mode: "FINITE", planning_horizon_days: 90, notes: "" });
    },
  });

  if (isLoading) return <div className="p-8 text-gray-400">Loading MPS dashboard…</div>;
  if (!dash) return <div className="p-8 text-red-500">Failed to load MPS dashboard.</div>;

  const d = dash;

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold text-gray-900">Master Production Scheduling</h1>
          <p className="text-sm text-gray-400 mt-0.5">Execution brain between planning and factory reality</p>
        </div>
        <button
          onClick={() => setShowCreateModal(true)}
          className="px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700"
        >
          + New MPS Plan
        </button>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
        <KpiCard label="Active Plans" value={d.active_plans} color="text-blue-700" />
        <KpiCard label="Total Lines" value={d.total_lines} />
        <KpiCard label="Feasible" value={d.feasible_lines} color="text-green-600" sub="lines" />
        <KpiCard label="Overloaded" value={d.overloaded_lines} color={d.overloaded_lines > 0 ? "text-red-600" : "text-gray-400"} sub="capacity exceeded" />
        <KpiCard label="Pending AI Recs" value={d.pending_ai_recs} color="text-purple-600" />
        <KpiCard label="Awaiting Approval" value={d.pending_approvals} color={d.pending_approvals > 0 ? "text-orange-600" : "text-gray-400"} />
      </div>

      {/* Body */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">

        {/* Overload Alerts */}
        <div className="bg-white rounded-xl border border-gray-100 shadow-sm">
          <div className="flex items-center justify-between px-5 py-4 border-b border-gray-50">
            <h2 className="text-sm font-semibold text-gray-700">Capacity Overload Alerts</h2>
            {d.overload_alerts.length > 0 && (
              <span className="px-2 py-0.5 bg-red-100 text-red-700 text-xs rounded-full font-medium">
                {d.overload_alerts.length} alert{d.overload_alerts.length > 1 ? "s" : ""}
              </span>
            )}
          </div>
          {d.overload_alerts.length === 0 ? (
            <div className="p-8 text-center text-sm text-green-600">
              ✓ No capacity overloads detected
            </div>
          ) : (
            <div className="divide-y divide-gray-50">
              {d.overload_alerts.map((a) => (
                <div key={a.line_id} className="px-5 py-3 flex items-center justify-between">
                  <div>
                    <p className="text-sm font-medium text-gray-800">{a.line_no}</p>
                    <p className="text-xs text-gray-400">Period: {a.period_start}</p>
                  </div>
                  <span className="text-sm font-semibold text-red-600">
                    +{a.overload_hours.toFixed(1)} hrs
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Recent Plans */}
        <div className="bg-white rounded-xl border border-gray-100 shadow-sm">
          <div className="flex items-center justify-between px-5 py-4 border-b border-gray-50">
            <h2 className="text-sm font-semibold text-gray-700">Recent Plans</h2>
            <a href="/dashboard/mps/planning-board" className="text-xs text-blue-600 hover:underline">
              View all →
            </a>
          </div>
          {d.recent_plans.length === 0 ? (
            <div className="p-8 text-center text-sm text-gray-400">No plans yet</div>
          ) : (
            <div className="divide-y divide-gray-50">
              {d.recent_plans.map((p) => (
                <div key={p.id} className="px-5 py-3 flex items-center justify-between">
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="text-sm font-medium text-gray-800">{p.plan_no}</span>
                      <Badge label={p.status} color={STATUS_COLOR[p.status]} />
                    </div>
                    <p className="text-xs text-gray-400 mt-0.5">{p.plan_name}</p>
                    <p className="text-xs text-gray-300">{p.start_date} → {p.end_date}</p>
                  </div>
                  <div className="text-right">
                    <p className="text-xs text-gray-500">{p.total_lines} lines</p>
                    {p.overloaded_lines > 0 && (
                      <p className="text-xs text-red-500">{p.overloaded_lines} overloaded</p>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Quick Nav */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {[
          { label: "Planning Board", desc: "View & override lines", href: "/dashboard/mps/planning-board", color: "border-blue-200 hover:border-blue-400" },
          { label: "Capacity Heatmap", desc: "Work center load analysis", href: "/dashboard/mps/capacity", color: "border-orange-200 hover:border-orange-400" },
          { label: "Campaign View", desc: "SKU grouping & sequence", href: "/dashboard/mps/campaigns", color: "border-purple-200 hover:border-purple-400" },
          { label: "What-If Simulator", desc: "Impact analysis", href: "/dashboard/mps/whatif", color: "border-teal-200 hover:border-teal-400" },
        ].map((n) => (
          <a
            key={n.href}
            href={n.href}
            className={`bg-white rounded-xl border-2 ${n.color} p-4 transition-colors`}
          >
            <p className="text-sm font-semibold text-gray-800">{n.label}</p>
            <p className="text-xs text-gray-400 mt-0.5">{n.desc}</p>
          </a>
        ))}
      </div>

      {/* Create Plan Modal */}
      {showCreateModal && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
          <div className="bg-white rounded-2xl shadow-xl w-full max-w-lg p-6">
            <h2 className="text-lg font-semibold text-gray-900 mb-4">New MPS Plan</h2>
            <div className="space-y-3">
              <div>
                <label className="block text-xs font-medium text-gray-500 mb-1">Plan Name *</label>
                <input
                  className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm"
                  value={form.plan_name}
                  onChange={(e) => setForm({ ...form, plan_name: e.target.value })}
                  placeholder="e.g. Q3 2026 Production Plan"
                />
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-medium text-gray-500 mb-1">Start Date *</label>
                  <input
                    type="date"
                    className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm"
                    value={form.start_date}
                    onChange={(e) => setForm({ ...form, start_date: e.target.value })}
                  />
                </div>
                <div>
                  <label className="block text-xs font-medium text-gray-500 mb-1">End Date *</label>
                  <input
                    type="date"
                    className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm"
                    value={form.end_date}
                    onChange={(e) => setForm({ ...form, end_date: e.target.value })}
                  />
                </div>
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-medium text-gray-500 mb-1">Planning Mode</label>
                  <select
                    className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm"
                    value={form.planning_mode}
                    onChange={(e) => setForm({ ...form, planning_mode: e.target.value })}
                  >
                    <option value="MANUAL">Manual</option>
                    <option value="ASSISTED">Assisted</option>
                    <option value="AUTO">Auto</option>
                    <option value="AI">AI-Driven</option>
                  </select>
                </div>
                <div>
                  <label className="block text-xs font-medium text-gray-500 mb-1">Capacity Mode</label>
                  <select
                    className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm"
                    value={form.capacity_mode}
                    onChange={(e) => setForm({ ...form, capacity_mode: e.target.value })}
                  >
                    <option value="FINITE">Finite</option>
                    <option value="INFINITE">Infinite</option>
                  </select>
                </div>
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-500 mb-1">Horizon (days)</label>
                <input
                  type="number"
                  className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm"
                  value={form.planning_horizon_days}
                  onChange={(e) => setForm({ ...form, planning_horizon_days: Number(e.target.value) })}
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-500 mb-1">Notes</label>
                <textarea
                  className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm"
                  rows={2}
                  value={form.notes}
                  onChange={(e) => setForm({ ...form, notes: e.target.value })}
                />
              </div>
            </div>
            <div className="flex gap-3 mt-5">
              <button
                onClick={() => createPlan.mutate()}
                disabled={!form.plan_name || !form.start_date || !form.end_date || createPlan.isPending}
                className="flex-1 bg-blue-600 text-white py-2 rounded-lg text-sm font-medium hover:bg-blue-700 disabled:opacity-40"
              >
                {createPlan.isPending ? "Creating…" : "Create Plan"}
              </button>
              <button
                onClick={() => setShowCreateModal(false)}
                className="px-4 py-2 border border-gray-200 rounded-lg text-sm hover:bg-gray-50"
              >
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
