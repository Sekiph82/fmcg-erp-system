"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { moApi, MODashboard, MOAIRec, DowntimeIntel, MACHINE_STATUS_COLORS, AI_AGENT_LABELS, SEVERITY_COLORS, DOWNTIME_CLASS_LABELS } from "@/lib/machineOperator";

function KPI({ label, value, sub, color }: { label: string; value: string | number; sub?: string; color?: string }) {
  return (
    <div className="bg-white rounded-lg border p-4">
      <p className="text-xs text-gray-500 uppercase tracking-wide">{label}</p>
      <p className={`text-2xl font-bold mt-1 ${color || "text-gray-900"}`}>{value}</p>
      {sub && <p className="text-xs text-gray-400 mt-0.5">{sub}</p>}
    </div>
  );
}

function OEEGauge({ oee }: { oee: number }) {
  const pct = oee * 100;
  const color = pct >= 85 ? "text-green-600" : pct >= 65 ? "text-yellow-600" : "text-red-600";
  const ring = pct >= 85 ? "stroke-green-500" : pct >= 65 ? "stroke-yellow-500" : "stroke-red-500";
  const r = 36;
  const circ = 2 * Math.PI * r;
  const dash = circ * (pct / 100);
  return (
    <div className="flex flex-col items-center">
      <svg width="96" height="96" viewBox="0 0 96 96">
        <circle cx="48" cy="48" r={r} fill="none" stroke="#e5e7eb" strokeWidth="8" />
        <circle cx="48" cy="48" r={r} fill="none" strokeWidth="8" className={ring}
          strokeDasharray={`${dash} ${circ}`} strokeLinecap="round"
          transform="rotate(-90 48 48)" />
        <text x="48" y="53" textAnchor="middle" className={`text-sm font-bold ${color}`} fontSize="14" fill="currentColor">{pct.toFixed(1)}%</text>
      </svg>
      <p className="text-xs text-gray-500 mt-1">OEE Today</p>
    </div>
  );
}

export default function MachineOpsDashboard() {
  const qc = useQueryClient();
  const { data, isLoading } = useQuery<MODashboard>({
    queryKey: ["mo-dashboard"],
    queryFn: () => moApi.getDashboard().then((r) => r.data),
    refetchInterval: 30000,
  });

  const runAI = useMutation({
    mutationFn: () => moApi.runAI(),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["mo-dashboard"] }),
  });

  const actionRec = useMutation({
    mutationFn: ({ id, status }: { id: string; status: "ACCEPTED" | "REJECTED" }) => moApi.actionAIRec(id, status),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["mo-dashboard"] }),
  });

  if (isLoading) return <div className="p-8 text-gray-500">Loading Machine & Operator Intelligence…</div>;
  if (!data) return <div className="p-8 text-red-500">Failed to load Machine & Operator dashboard. Ensure the backend is running.</div>;
  const d = data;
  const oeeValue = d.avg_oee_today ? Number(d.avg_oee_today) : null;

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Machine + Operator Intelligence</h1>
          <p className="text-sm text-gray-500 mt-0.5">Runtime · Labor · OEE · Cost · Anomaly Detection</p>
        </div>
        <button
          onClick={() => runAI.mutate()}
          disabled={runAI.isPending}
          className="bg-indigo-600 text-white px-4 py-2 rounded-lg text-sm hover:bg-indigo-700 disabled:opacity-50"
        >
          {runAI.isPending ? "Running AI…" : "Run AI Analysis"}
        </button>
      </div>

      {/* KPIs */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <KPI label="Total Machines" value={d.total_machines} />
        <KPI label="Active" value={d.machines_active} color="text-green-700" />
        <KPI label="In Maintenance" value={d.machines_maintenance} color={d.machines_maintenance > 0 ? "text-orange-600" : "text-gray-700"} />
        <KPI label="Operators" value={d.total_operators} color="text-blue-700" />
        <KPI label="Teams" value={d.total_teams} color="text-purple-700" />
        <KPI label="Expiring Certs" value={d.expiring_certs} color={d.expiring_certs > 0 ? "text-red-600" : "text-gray-700"} sub="within 30 days" />
        <KPI label="Downtime Today" value={`${Number(d.total_downtime_today_min).toFixed(0)} min`} color={Number(d.total_downtime_today_min) > 60 ? "text-red-600" : "text-gray-700"} />
        <KPI label="Pending AI Recs" value={d.pending_ai_recs} color={d.pending_ai_recs > 0 ? "text-orange-600" : "text-gray-700"} />
      </div>

      {/* OEE + Quick Actions */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {oeeValue !== null && (
          <div className="bg-white rounded-lg border p-5 flex items-center justify-center">
            <OEEGauge oee={oeeValue} />
          </div>
        )}
        <div className={`${oeeValue !== null ? "lg:col-span-2" : "lg:col-span-3"} grid grid-cols-2 md:grid-cols-3 gap-3`}>
          {[
            { label: "Machine Master", href: "/dashboard/machine-ops/machines", color: "bg-blue-50 text-blue-700 border-blue-200" },
            { label: "Operators", href: "/dashboard/machine-ops/operators", color: "bg-green-50 text-green-700 border-green-200" },
            { label: "Teams", href: "/dashboard/machine-ops/teams", color: "bg-purple-50 text-purple-700 border-purple-200" },
            { label: "Runtime Logs", href: "/dashboard/machine-ops/runtime", color: "bg-cyan-50 text-cyan-700 border-cyan-200" },
            { label: "Performance", href: "/dashboard/machine-ops/performance", color: "bg-emerald-50 text-emerald-700 border-emerald-200" },
            { label: "Downtime Board", href: "/dashboard/machine-ops/downtime", color: "bg-red-50 text-red-700 border-red-200" },
            { label: "Cost Contribution", href: "/dashboard/machine-ops/costing", color: "bg-orange-50 text-orange-700 border-orange-200" },
            { label: "Cert Monitor", href: "/dashboard/machine-ops/certs", color: "bg-yellow-50 text-yellow-700 border-yellow-200" },
            { label: "Assignment Board", href: "/dashboard/machine-ops/assignment", color: "bg-teal-50 text-teal-700 border-teal-200" },
          ].map((q) => (
            <a key={q.href} href={q.href} className={`border rounded-lg p-3 text-sm font-medium text-center hover:opacity-80 ${q.color}`}>
              {q.label}
            </a>
          ))}
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Recent Downtime */}
        <div className="bg-white rounded-lg border">
          <div className="px-4 py-3 border-b flex items-center justify-between">
            <h2 className="font-semibold text-gray-900">Recent Downtime Events</h2>
            <a href="/dashboard/machine-ops/downtime" className="text-xs text-indigo-600 hover:underline">View all</a>
          </div>
          <div className="divide-y">
            {d.recent_downtime.length === 0 && <p className="p-4 text-sm text-gray-400">No downtime events today.</p>}
            {d.recent_downtime.map((dt: DowntimeIntel) => (
              <div key={dt.id} className="px-4 py-2.5">
                <div className="flex items-center justify-between">
                  <p className="text-sm font-medium text-gray-900">
                    {DOWNTIME_CLASS_LABELS[dt.downtime_class] || dt.downtime_class}
                    {dt.repeat_occurrence && <span className="ml-2 text-xs bg-red-100 text-red-700 px-1.5 py-0.5 rounded-full">Repeat</span>}
                  </p>
                  <span className="text-xs text-gray-500">{dt.duration_minutes ? `${Number(dt.duration_minutes).toFixed(0)} min` : "–"}</span>
                </div>
                <p className="text-xs text-gray-400">{dt.machine_name || dt.machine_id?.slice(0, 8)} · {new Date(dt.start_time).toLocaleString()}</p>
                {dt.cost_impact && <p className="text-xs text-red-500">KES {Number(dt.cost_impact).toLocaleString()}</p>}
              </div>
            ))}
          </div>
        </div>

        {/* AI Recommendations */}
        <div className="bg-white rounded-lg border">
          <div className="px-4 py-3 border-b">
            <h2 className="font-semibold text-gray-900">AI Recommendations</h2>
          </div>
          <div className="divide-y">
            {d.ai_recommendations.length === 0 && <p className="p-4 text-sm text-gray-400">No pending AI recommendations.</p>}
            {d.ai_recommendations.map((r: MOAIRec) => (
              <div key={r.id} className="p-3">
                <div className="flex items-start justify-between gap-2">
                  <div className="flex-1">
                    <div className="flex items-center gap-2 mb-0.5">
                      <span className="text-xs bg-indigo-50 text-indigo-700 px-2 py-0.5 rounded-full">{AI_AGENT_LABELS[r.agent_type]}</span>
                      <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${SEVERITY_COLORS[r.severity] || "bg-gray-100 text-gray-600"}`}>{r.severity}</span>
                    </div>
                    <p className="text-sm font-medium text-gray-900">{r.title}</p>
                    <p className="text-xs text-gray-500 mt-0.5 line-clamp-2">{r.description}</p>
                  </div>
                  {r.status === "PENDING" && (
                    <div className="flex gap-1 shrink-0 mt-1">
                      <button onClick={() => actionRec.mutate({ id: r.id, status: "ACCEPTED" })} className="text-xs bg-green-100 text-green-700 px-2 py-1 rounded hover:bg-green-200">Accept</button>
                      <button onClick={() => actionRec.mutate({ id: r.id, status: "REJECTED" })} className="text-xs bg-red-100 text-red-700 px-2 py-1 rounded hover:bg-red-200">Reject</button>
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
