"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  planningApi, PlanningDashboard, ScenarioSummary,
  SCENARIO_STATUS_COLOR, BN_SEVERITY_COLOR, AGENT_COLOR, AGENT_LABEL,
  PLANNING_CREATE_PERMISSIONS,
} from "@/lib/planning";
import { useAuth } from "@/context/AuthContext";

export default function PlanningDashboardPage() {
  const qc = useQueryClient();
  const { hasAnyPermission } = useAuth();
  const [showCreate, setShowCreate] = useState(false);
  const [form, setForm] = useState({ scenario_name: "", mode: "FINITE" as "FINITE" | "INFINITE", description: "" });
  const canCreateScenario = hasAnyPermission(PLANNING_CREATE_PERMISSIONS);

  const { data, isLoading } = useQuery<PlanningDashboard>({
    queryKey: ["planning-dashboard"],
    queryFn: () => planningApi.dashboard(),
  });

  const createScenario = useMutation({
    mutationFn: () => planningApi.createScenario({ scenario_name: form.scenario_name, mode: form.mode, description: form.description || undefined } as any),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["planning-dashboard"] });
      setShowCreate(false);
      setForm({ scenario_name: "", mode: "FINITE", description: "" });
    },
  });

  if (isLoading) return <div className="p-6 text-gray-400">Loading…</div>;

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Advanced Production Planning</h1>
          <p className="text-sm text-gray-500 mt-0.5">Finite capacity scheduling · Bottleneck detection · AI optimization</p>
        </div>
        {canCreateScenario && (
          <button
            onClick={() => setShowCreate(true)}
            className="px-4 py-2 bg-indigo-600 text-white text-sm font-medium rounded-lg hover:bg-indigo-700"
          >
            + New Scenario
          </button>
        )}
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
        {[
          { label: "Active Scenarios", value: data?.active_scenarios ?? 0, color: "text-green-600" },
          { label: "Total Operations", value: data?.total_ops_today ?? 0, color: "text-gray-900" },
          { label: "Scheduled", value: `${data?.scheduled_pct?.toFixed(1) ?? 0}%`, color: "text-blue-600" },
          { label: "Avg Utilization", value: `${data?.avg_utilization_pct?.toFixed(1) ?? 0}%`, color: data?.avg_utilization_pct && data.avg_utilization_pct >= 85 ? "text-red-600" : "text-gray-900" },
          { label: "Critical Bottlenecks", value: data?.critical_bottlenecks ?? 0, color: data?.critical_bottlenecks ? "text-red-600" : "text-green-600" },
          { label: "Pending AI Recs", value: data?.pending_ai_recs ?? 0, color: "text-purple-600" },
        ].map((kpi) => (
          <div key={kpi.label} className="bg-white rounded-xl border border-gray-100 shadow-sm p-4">
            <p className="text-xs text-gray-400 font-medium">{kpi.label}</p>
            <p className={`text-2xl font-bold mt-1 ${kpi.color}`}>{kpi.value}</p>
          </div>
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Scenarios */}
        <div className="lg:col-span-2 bg-white rounded-xl border border-gray-100 shadow-sm overflow-hidden">
          <div className="px-5 py-4 border-b border-gray-50 flex items-center justify-between">
            <h2 className="text-sm font-semibold text-gray-700">Planning Scenarios</h2>
            <a href="/dashboard/planning/schedule" className="text-xs text-blue-600 hover:underline">View all →</a>
          </div>
          {!data?.scenarios?.length ? (
            <div className="p-8 text-center text-sm text-gray-400">No scenarios yet. Create one to start scheduling.</div>
          ) : (
            <div className="divide-y divide-gray-50">
              {data.scenarios.map((s) => (
                <div key={s.id} className="px-5 py-3 flex items-center justify-between hover:bg-gray-50">
                  <div>
                    <div className="flex items-center gap-2">
                      <a href={`/dashboard/planning/schedule?scenario=${s.id}`} className="text-sm font-medium text-gray-800 hover:text-indigo-600">
                        {s.scenario_name}
                      </a>
                      <span className={`text-xs px-1.5 py-0.5 rounded ${SCENARIO_STATUS_COLOR[s.status]}`}>
                        {s.status}
                      </span>
                    </div>
                    <p className="text-xs text-gray-400 mt-0.5">
                      {s.scenario_no} · {s.mode} · {s.horizon_start ? `${s.horizon_start} → ${s.horizon_end}` : "No horizon set"}
                    </p>
                  </div>
                  <div className="flex items-center gap-6 text-xs text-gray-500">
                    <span>{s.scheduled_ops}/{s.total_ops} ops</span>
                    <span className={s.bottleneck_count > 0 ? "text-red-500 font-medium" : "text-green-500"}>
                      {s.bottleneck_count} bottleneck(s)
                    </span>
                    {s.calculated_at && (
                      <span className="text-gray-300">
                        {new Date(s.calculated_at).toLocaleDateString()}
                      </span>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Right panel */}
        <div className="space-y-4">
          {/* Critical Bottlenecks */}
          <div className="bg-white rounded-xl border border-gray-100 shadow-sm overflow-hidden">
            <div className="px-4 py-3 border-b border-gray-50">
              <h2 className="text-sm font-semibold text-gray-700">Top Bottlenecks</h2>
            </div>
            {!data?.top_bottlenecks?.length ? (
              <div className="p-4 text-xs text-gray-400">No bottlenecks detected</div>
            ) : (
              <div className="divide-y divide-gray-50">
                {data.top_bottlenecks.map((bn) => (
                  <div key={bn.id} className="px-4 py-2">
                    <div className="flex items-center justify-between">
                      <p className="text-xs font-medium text-gray-700 truncate">{bn.work_center_name || "Unknown WC"}</p>
                      <span className={`text-xs px-1.5 py-0.5 rounded ${BN_SEVERITY_COLOR[bn.severity]}`}>
                        {bn.severity}
                      </span>
                    </div>
                    <p className="text-xs text-gray-400 mt-0.5">
                      {Number(bn.peak_utilization_pct).toFixed(0)}% peak · {bn.overloaded_days}d overloaded
                    </p>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Pending AI Recs */}
          <div className="bg-white rounded-xl border border-gray-100 shadow-sm overflow-hidden">
            <div className="px-4 py-3 border-b border-gray-50">
              <h2 className="text-sm font-semibold text-gray-700">AI Recommendations</h2>
            </div>
            {!data?.recent_ai_recs?.length ? (
              <div className="p-4 text-xs text-gray-400">No pending recommendations</div>
            ) : (
              <div className="divide-y divide-gray-50">
                {data.recent_ai_recs.map((rec) => (
                  <div key={rec.id} className="px-4 py-2">
                    <span className={`text-xs px-1.5 py-0.5 rounded ${AGENT_COLOR[rec.agent_type]}`}>
                      {AGENT_LABEL[rec.agent_type]}
                    </span>
                    <p className="text-xs font-medium text-gray-700 mt-1 line-clamp-2">{rec.title}</p>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Quick nav */}
          <div className="bg-white rounded-xl border border-gray-100 shadow-sm p-4">
            <h2 className="text-xs font-semibold text-gray-500 mb-3">Quick Actions</h2>
            <div className="space-y-2">
              {[
                { label: "Schedule Board",     href: "/dashboard/planning/schedule",     color: "bg-indigo-50 text-indigo-700" },
                { label: "Capacity Board",     href: "/dashboard/planning/capacity",     color: "bg-orange-50 text-orange-700" },
                { label: "Bottleneck Explorer",href: "/dashboard/planning/bottlenecks",  color: "bg-red-50 text-red-700" },
                { label: "Simulation Sandbox", href: "/dashboard/planning/simulation",   color: "bg-teal-50 text-teal-700" },
                { label: "Changeover Matrix",  href: "/dashboard/planning/changeover",   color: "bg-purple-50 text-purple-700" },
              ].map((link) => (
                <a key={link.href} href={link.href}
                  className={`block text-xs font-medium px-3 py-2 rounded-lg ${link.color} hover:opacity-80`}
                >
                  {link.label}
                </a>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* Create Scenario Modal */}
      {showCreate && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
          <div className="bg-white rounded-2xl shadow-xl w-full max-w-md p-6">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-semibold">New Planning Scenario</h2>
              <button onClick={() => setShowCreate(false)} className="text-gray-400 hover:text-gray-600 text-xl">×</button>
            </div>
            <div className="space-y-3">
              <input
                className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm"
                placeholder="Scenario name *"
                value={form.scenario_name}
                onChange={(e) => setForm({ ...form, scenario_name: e.target.value })}
              />
              <select
                className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm"
                value={form.mode}
                onChange={(e) => setForm({ ...form, mode: e.target.value as "FINITE" | "INFINITE" })}
              >
                <option value="FINITE">Finite Capacity</option>
                <option value="INFINITE">Infinite Capacity</option>
              </select>
              <textarea
                className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm"
                rows={2}
                placeholder="Description (optional)"
                value={form.description}
                onChange={(e) => setForm({ ...form, description: e.target.value })}
              />
            </div>
            <div className="flex gap-3 mt-4">
              <button
                onClick={() => createScenario.mutate()}
                disabled={!form.scenario_name || createScenario.isPending}
                className="flex-1 bg-indigo-600 text-white py-2 rounded-lg text-sm font-medium hover:bg-indigo-700 disabled:opacity-40"
              >
                {createScenario.isPending ? "Creating…" : "Create Scenario"}
              </button>
              <button onClick={() => setShowCreate(false)} className="px-4 py-2 border rounded-lg text-sm text-gray-600 hover:bg-gray-50">
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
