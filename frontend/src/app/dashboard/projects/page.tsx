"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import {
  projectsApi, Project, ProjectStatus, STATUS_COLOR, fmtDate,
} from "@/lib/projects";
import { Button } from "@/components/ui/Button";

function KpiCard({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="bg-white rounded-xl border p-4 flex flex-col gap-1">
      <span className="text-xs text-gray-500 font-medium">{label}</span>
      <span className="text-2xl font-bold text-gray-900">{value}</span>
    </div>
  );
}

function StatusBadge({ s }: { s: ProjectStatus }) {
  return <span className={`text-xs font-semibold px-2 py-0.5 rounded-full ${STATUS_COLOR[s]}`}>{s.replace("_", " ")}</span>;
}

function ProgressBar({ done, total }: { done: number; total: number }) {
  const pct = total > 0 ? Math.round((done / total) * 100) : 0;
  return (
    <div className="flex items-center gap-2">
      <div className="flex-1 bg-gray-200 rounded-full h-1.5">
        <div className="bg-blue-500 h-1.5 rounded-full" style={{ width: `${pct}%` }} />
      </div>
      <span className="text-xs text-gray-500 w-8">{pct}%</span>
    </div>
  );
}

function CreateModal({ onClose }: { onClose: () => void }) {
  const qc = useQueryClient();
  const [form, setForm] = useState({ name: "", description: "", start_date: "", end_date: "", budget: "" });
  const mut = useMutation({
    mutationFn: () => projectsApi.create({
      name: form.name,
      description: form.description || undefined,
      start_date: form.start_date || undefined,
      end_date: form.end_date || undefined,
      budget: form.budget ? parseFloat(form.budget) : undefined,
    }),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["projects"] }); onClose(); },
  });

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-md p-6 space-y-4">
        <div className="flex justify-between items-center">
          <h2 className="text-lg font-bold">New Project</h2>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600">✕</button>
        </div>

        <div className="space-y-3">
          <div>
            <label className="text-sm font-medium text-gray-700">Project Name *</label>
            <input className="w-full border rounded px-3 py-2 text-sm mt-1" value={form.name}
              onChange={e => setForm({ ...form, name: e.target.value })} placeholder="e.g. Q3 NPD Launch" />
          </div>
          <div>
            <label className="text-sm font-medium text-gray-700">Description</label>
            <textarea className="w-full border rounded px-3 py-2 text-sm mt-1" rows={2}
              value={form.description} onChange={e => setForm({ ...form, description: e.target.value })} />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="text-sm font-medium text-gray-700">Start Date</label>
              <input type="date" className="w-full border rounded px-3 py-2 text-sm mt-1" value={form.start_date}
                onChange={e => setForm({ ...form, start_date: e.target.value })} />
            </div>
            <div>
              <label className="text-sm font-medium text-gray-700">End Date</label>
              <input type="date" className="w-full border rounded px-3 py-2 text-sm mt-1" value={form.end_date}
                onChange={e => setForm({ ...form, end_date: e.target.value })} />
            </div>
          </div>
          <div>
            <label className="text-sm font-medium text-gray-700">Budget (KES)</label>
            <input type="number" min={0} className="w-full border rounded px-3 py-2 text-sm mt-1" value={form.budget}
              onChange={e => setForm({ ...form, budget: e.target.value })} />
          </div>
        </div>

        <div className="flex gap-2 justify-end pt-2">
          <Button variant="secondary" onClick={onClose}>Cancel</Button>
          <Button onClick={() => mut.mutate()} disabled={!form.name || mut.isPending}>
            {mut.isPending ? "Creating…" : "Create Project"}
          </Button>
        </div>
        {mut.isError && <p className="text-xs text-red-600">{(mut.error as Error).message}</p>}
      </div>
    </div>
  );
}

export default function ProjectsPage() {
  const router = useRouter();
  const [statusFilter, setStatusFilter] = useState<ProjectStatus | "">("");
  const [showCreate, setShowCreate] = useState(false);

  const { data: dash } = useQuery({ queryKey: ["projects", "dashboard"], queryFn: projectsApi.dashboard });
  const { data: projects = [], isLoading } = useQuery({
    queryKey: ["projects", "list", statusFilter],
    queryFn: () => projectsApi.list(statusFilter || undefined),
  });

  const statuses: ProjectStatus[] = ["PLANNING", "ACTIVE", "ON_HOLD", "COMPLETED", "CANCELLED"];

  return (
    <div className="p-6 space-y-6 max-w-7xl mx-auto">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Project Management</h1>
          <p className="text-sm text-gray-500">Track projects, milestones, tasks, and Gantt timelines</p>
        </div>
        <Button onClick={() => setShowCreate(true)}>+ New Project</Button>
      </div>

      {dash && (
        <div className="grid grid-cols-2 md:grid-cols-5 lg:grid-cols-9 gap-3">
          <KpiCard label="Total" value={dash.total_projects} />
          <KpiCard label="Planning" value={dash.planning_count} />
          <KpiCard label="Active" value={dash.active_count} />
          <KpiCard label="On Hold" value={dash.on_hold_count} />
          <KpiCard label="Completed" value={dash.completed_count} />
          <KpiCard label="Cancelled" value={dash.cancelled_count} />
          <KpiCard label="Total Tasks" value={dash.total_tasks} />
          <KpiCard label="Overdue" value={dash.overdue_tasks} />
          <KpiCard label="Blocked" value={dash.blocked_tasks} />
        </div>
      )}

      <div className="flex gap-2 flex-wrap">
        <button onClick={() => setStatusFilter("")}
          className={`text-xs px-3 py-1.5 rounded-full border font-medium ${statusFilter === "" ? "bg-gray-900 text-white" : "bg-white text-gray-600 border-gray-200"}`}>
          All
        </button>
        {statuses.map(s => (
          <button key={s} onClick={() => setStatusFilter(s)}
            className={`text-xs px-3 py-1.5 rounded-full border font-medium ${statusFilter === s ? "bg-gray-900 text-white" : "bg-white text-gray-600 border-gray-200"}`}>
            {s.replace("_", " ")}
          </button>
        ))}
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {isLoading ? (
          <div className="col-span-3 p-8 text-center text-gray-400">Loading projects…</div>
        ) : projects.length === 0 ? (
          <div className="col-span-3 p-8 text-center text-gray-400">No projects yet. Create your first project.</div>
        ) : projects.map(p => (
          <div key={p.id} className="bg-white rounded-xl border shadow-sm p-4 space-y-3 hover:shadow-md transition-shadow cursor-pointer"
            onClick={() => router.push(`/dashboard/projects/${p.id}`)}>
            <div className="flex justify-between items-start">
              <div>
                <div className="font-mono text-xs text-gray-400">{p.project_no}</div>
                <div className="font-semibold text-gray-900 mt-0.5">{p.name}</div>
              </div>
              <StatusBadge s={p.status} />
            </div>

            {p.description && (
              <p className="text-sm text-gray-500 line-clamp-2">{p.description}</p>
            )}

            <ProgressBar done={p.done_count} total={p.task_count} />

            <div className="flex justify-between text-xs text-gray-500">
              <span>{p.task_count} tasks ({p.done_count} done)</span>
              <span>{p.milestone_count} milestones</span>
            </div>

            <div className="flex justify-between text-xs text-gray-400 border-t pt-2">
              <span>{fmtDate(p.start_date)} → {fmtDate(p.end_date)}</span>
              {p.owner_name && <span>{p.owner_name}</span>}
            </div>
          </div>
        ))}
      </div>

      {showCreate && <CreateModal onClose={() => setShowCreate(false)} />}
    </div>
  );
}
