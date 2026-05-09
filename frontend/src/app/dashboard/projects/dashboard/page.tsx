"use client";

import { useQuery } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { projectsApi, ProjectStatus, STATUS_COLOR, fmtDate } from "@/lib/projects";

function KpiCard({ label, value, accent }: { label: string; value: number; accent?: string }) {
  return (
    <div className={`bg-white rounded-xl border p-4 flex flex-col gap-1 ${accent ?? ""}`}>
      <span className="text-xs text-gray-500 font-medium">{label}</span>
      <span className="text-2xl font-bold text-gray-900">{value}</span>
    </div>
  );
}

function StatusBadge({ s }: { s: ProjectStatus }) {
  return <span className={`text-xs font-semibold px-2 py-0.5 rounded-full ${STATUS_COLOR[s]}`}>{s.replace("_", " ")}</span>;
}

export default function ProjectsDashboardPage() {
  const router = useRouter();

  const { data: dash } = useQuery({
    queryKey: ["projects", "dashboard"],
    queryFn: projectsApi.dashboard,
  });

  const { data: projects = [], isLoading } = useQuery({
    queryKey: ["projects"],
    queryFn: () => projectsApi.list(),
  });

  const active = projects.filter(p => p.status === "ACTIVE");

  return (
    <div className="p-6 space-y-6 max-w-7xl mx-auto">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Projects Dashboard</h1>
          <p className="text-sm text-gray-500">Portfolio overview and health metrics</p>
        </div>
        <button onClick={() => router.push("/dashboard/projects")}
          className="text-sm px-4 py-2 rounded-lg bg-blue-600 text-white hover:bg-blue-700 font-medium">
          All Projects
        </button>
      </div>

      {dash && (
        <div className="grid grid-cols-3 md:grid-cols-5 lg:grid-cols-9 gap-3">
          <KpiCard label="Total"     value={dash.total_projects} />
          <KpiCard label="Planning"  value={dash.planning_count} />
          <KpiCard label="Active"    value={dash.active_count} accent="border-blue-200" />
          <KpiCard label="On Hold"   value={dash.on_hold_count} />
          <KpiCard label="Completed" value={dash.completed_count} />
          <KpiCard label="Cancelled" value={dash.cancelled_count} />
          <KpiCard label="Tasks"     value={dash.total_tasks} />
          <KpiCard label="Overdue"   value={dash.overdue_tasks} accent={dash.overdue_tasks > 0 ? "border-red-300" : ""} />
          <KpiCard label="Blocked"   value={dash.blocked_tasks} accent={dash.blocked_tasks > 0 ? "border-orange-300" : ""} />
        </div>
      )}

      <div>
        <h2 className="text-lg font-semibold text-gray-900 mb-3">Active Projects</h2>
        {isLoading ? (
          <div className="text-center py-8 text-gray-400">Loading…</div>
        ) : active.length === 0 ? (
          <div className="bg-white rounded-xl border p-8 text-center text-gray-400">No active projects.</div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {active.map(p => {
              const pct = p.task_count > 0 ? Math.round((p.done_count / p.task_count) * 100) : 0;
              return (
                <div key={p.id} className="bg-white rounded-xl border p-4 space-y-3 hover:shadow-md transition-shadow cursor-pointer"
                  onClick={() => router.push(`/dashboard/projects/${p.id}`)}>
                  <div className="flex justify-between items-start">
                    <div>
                      <p className="font-semibold text-gray-900">{p.name}</p>
                      <p className="text-xs text-gray-400 font-mono">{p.project_no}</p>
                    </div>
                    <StatusBadge s={p.status} />
                  </div>
                  <div className="flex items-center gap-2">
                    <div className="flex-1 bg-gray-200 rounded-full h-1.5">
                      <div className="bg-blue-500 h-1.5 rounded-full" style={{ width: `${pct}%` }} />
                    </div>
                    <span className="text-xs text-gray-500 w-8">{pct}%</span>
                  </div>
                  <div className="flex justify-between text-xs text-gray-500">
                    <span>{p.done_count}/{p.task_count} tasks done</span>
                    {p.end_date && <span>Due {fmtDate(p.end_date)}</span>}
                  </div>
                  {p.owner_name && <div className="text-xs text-gray-500">Owner: {p.owner_name}</div>}
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
