"use client";

import { useState, useMemo } from "react";
import { useParams } from "next/navigation";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  projectsApi, ProjectStatus, ProjectTaskStatus, GanttTask, GanttResponse,
  TASK_BAR_COLOR, TASK_STATUS_COLOR, STATUS_COLOR, fmtDate,
} from "@/lib/projects";
import { Button } from "@/components/ui/Button";

// ── Gantt chart ───────────────────────────────────────────────────────────────

function GanttChart({ gantt }: { gantt: GanttResponse }) {
  const tasks = gantt.tasks.filter(t => t.start_date && t.due_date);

  if (tasks.length === 0) {
    return <div className="p-6 text-center text-gray-400 text-sm">Add tasks with start and due dates to see the Gantt chart.</div>;
  }

  // Compute date range
  const allDates = tasks.flatMap(t => [new Date(t.start_date!), new Date(t.due_date!)]);
  const projectStart = gantt.start_date ? new Date(gantt.start_date) : new Date(Math.min(...allDates.map(d => d.getTime())));
  const projectEnd   = gantt.end_date   ? new Date(gantt.end_date)   : new Date(Math.max(...allDates.map(d => d.getTime())));
  const totalDays = Math.max(1, Math.ceil((projectEnd.getTime() - projectStart.getTime()) / 86400000) + 1);
  const CHART_WIDTH = 600;

  const dayPx = CHART_WIDTH / totalDays;

  function dayOffset(d: string) {
    return Math.max(0, Math.ceil((new Date(d).getTime() - projectStart.getTime()) / 86400000));
  }

  function barWidth(start: string, end: string) {
    const w = Math.max(4, Math.ceil((new Date(end).getTime() - new Date(start).getTime()) / 86400000) * dayPx);
    return w;
  }

  // Generate month labels
  const months: { label: string; leftPx: number }[] = [];
  let cur = new Date(projectStart);
  cur.setDate(1);
  while (cur <= projectEnd) {
    const off = Math.max(0, Math.ceil((cur.getTime() - projectStart.getTime()) / 86400000));
    months.push({ label: cur.toLocaleDateString("en-KE", { month: "short", year: "2-digit" }), leftPx: off * dayPx });
    cur.setMonth(cur.getMonth() + 1);
  }

  const ROW_H = 32;
  const LABEL_W = 200;

  return (
    <div className="overflow-x-auto">
      <div style={{ minWidth: LABEL_W + CHART_WIDTH + 20 }}>
        {/* Header */}
        <div className="flex border-b bg-gray-50">
          <div style={{ width: LABEL_W }} className="px-3 py-2 text-xs font-semibold text-gray-500 shrink-0">TASK</div>
          <div style={{ width: CHART_WIDTH }} className="relative h-8 overflow-hidden">
            {months.map((m, i) => (
              <div key={i} className="absolute text-xs text-gray-400 top-2" style={{ left: m.leftPx + 2 }}>{m.label}</div>
            ))}
            {/* Today line position */}
            {(() => {
              const todayOff = dayOffset(new Date().toISOString().slice(0, 10));
              return todayOff >= 0 && todayOff <= totalDays ? (
                <div className="absolute top-0 bottom-0 w-px bg-red-400 opacity-60" style={{ left: todayOff * dayPx }} />
              ) : null;
            })()}
          </div>
        </div>

        {/* Milestones */}
        {gantt.milestones.map(m => (
          <div key={m.id} className="flex border-b bg-purple-50 items-center" style={{ height: ROW_H }}>
            <div style={{ width: LABEL_W }} className="px-3 flex items-center gap-1.5">
              <span className="text-purple-500">◆</span>
              <span className="text-xs font-medium text-purple-700 truncate">{m.name}</span>
              {m.is_complete && <span className="text-xs text-green-500">✓</span>}
            </div>
            <div style={{ width: CHART_WIDTH }} className="relative h-full">
              {m.due_date && (() => {
                const x = dayOffset(m.due_date) * dayPx;
                return (
                  <div className="absolute top-1/2 -translate-y-1/2" style={{ left: x }}>
                    <div className="w-3 h-3 bg-purple-500 rotate-45 -translate-x-1.5" title={m.name} />
                  </div>
                );
              })()}
            </div>
          </div>
        ))}

        {/* Tasks */}
        {tasks.map(t => {
          const left = dayOffset(t.start_date!) * dayPx;
          const width = barWidth(t.start_date!, t.due_date!);
          const barColor = TASK_BAR_COLOR[t.status];
          const isCritical = t.is_critical_path;

          return (
            <div key={t.id} className="flex border-b hover:bg-gray-50 items-center" style={{ height: ROW_H }}>
              <div style={{ width: LABEL_W }} className="px-3 flex items-center gap-1">
                {t.parent_task_id && <span className="w-2 shrink-0" />}
                {isCritical && <span className="text-red-400 text-xs shrink-0" title="Critical path">★</span>}
                <span className="text-xs text-gray-700 truncate">{t.title}</span>
              </div>
              <div style={{ width: CHART_WIDTH }} className="relative h-full">
                <div
                  className={`absolute top-1/2 -translate-y-1/2 rounded ${barColor} ${isCritical ? "ring-1 ring-red-400" : ""}`}
                  style={{ left, width: Math.min(width, CHART_WIDTH - left) }}
                  title={`${t.title}: ${fmtDate(t.start_date)} → ${fmtDate(t.due_date)}`}
                >
                  <div className="h-5 flex items-center px-1.5">
                    {width > 60 && (
                      <span className="text-white text-xs truncate">{t.pct_complete}%</span>
                    )}
                  </div>
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

// ── Task form ─────────────────────────────────────────────────────────────────

function AddTaskModal({ projectId, onClose }: { projectId: string; onClose: () => void }) {
  const qc = useQueryClient();
  const [form, setForm] = useState<{
    title: string;
    description: string;
    priority: "LOW" | "MEDIUM" | "HIGH";
    start_date: string;
    due_date: string;
    estimated_hours: string;
    is_critical_path: boolean;
  }>({
    title: "",
    description: "",
    priority: "MEDIUM",
    start_date: "",
    due_date: "",
    estimated_hours: "",
    is_critical_path: false,
  });

  const mut = useMutation({
    mutationFn: () => projectsApi.addTask(projectId, {
      project_id: projectId,
      title: form.title,
      description: form.description || undefined,
      priority: form.priority,
      start_date: form.start_date || undefined,
      due_date: form.due_date || undefined,
      estimated_hours: form.estimated_hours ? parseFloat(form.estimated_hours) : undefined,
      is_critical_path: form.is_critical_path,
    } as any),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["project", projectId] }); onClose(); },
  });

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-md p-6 space-y-3">
        <div className="flex justify-between items-center">
          <h2 className="text-lg font-bold">Add Task</h2>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600">✕</button>
        </div>

        <div>
          <label className="text-sm font-medium text-gray-700">Title *</label>
          <input className="w-full border rounded px-3 py-2 text-sm mt-1" value={form.title}
            onChange={e => setForm({ ...form, title: e.target.value })} />
        </div>
        <div>
          <label className="text-sm font-medium text-gray-700">Description</label>
          <textarea className="w-full border rounded px-3 py-2 text-sm mt-1" rows={2}
            value={form.description} onChange={e => setForm({ ...form, description: e.target.value })} />
        </div>
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="text-sm font-medium text-gray-700">Priority</label>
            <select className="w-full border rounded px-3 py-2 text-sm mt-1" value={form.priority}
              onChange={e => setForm({ ...form, priority: e.target.value as "LOW" | "MEDIUM" | "HIGH" })}>
              <option>LOW</option><option>MEDIUM</option><option>HIGH</option>
            </select>
          </div>
          <div>
            <label className="text-sm font-medium text-gray-700">Est. Hours</label>
            <input type="number" min={0} className="w-full border rounded px-3 py-2 text-sm mt-1" value={form.estimated_hours}
              onChange={e => setForm({ ...form, estimated_hours: e.target.value })} />
          </div>
          <div>
            <label className="text-sm font-medium text-gray-700">Start Date</label>
            <input type="date" className="w-full border rounded px-3 py-2 text-sm mt-1" value={form.start_date}
              onChange={e => setForm({ ...form, start_date: e.target.value })} />
          </div>
          <div>
            <label className="text-sm font-medium text-gray-700">Due Date</label>
            <input type="date" className="w-full border rounded px-3 py-2 text-sm mt-1" value={form.due_date}
              onChange={e => setForm({ ...form, due_date: e.target.value })} />
          </div>
        </div>
        <label className="flex items-center gap-2 text-sm text-gray-600">
          <input type="checkbox" checked={form.is_critical_path}
            onChange={e => setForm({ ...form, is_critical_path: e.target.checked })} />
          Mark as Critical Path
        </label>

        <div className="flex gap-2 justify-end pt-2">
          <Button variant="secondary" onClick={onClose}>Cancel</Button>
          <Button onClick={() => mut.mutate()} disabled={!form.title || mut.isPending}>
            {mut.isPending ? "Adding…" : "Add Task"}
          </Button>
        </div>
        {mut.isError && <p className="text-xs text-red-600">{(mut.error as Error).message}</p>}
      </div>
    </div>
  );
}

// ── Main project detail page ──────────────────────────────────────────────────

export default function ProjectDetailPage() {
  const params = useParams();
  const projectId = params?.id as string;
  const qc = useQueryClient();
  const [tab, setTab] = useState<"overview" | "tasks" | "gantt">("overview");
  const [showAddTask, setShowAddTask] = useState(false);

  const { data: project, isLoading } = useQuery({
    queryKey: ["project", projectId],
    queryFn: () => projectsApi.get(projectId),
    enabled: !!projectId,
  });

  const { data: gantt } = useQuery({
    queryKey: ["project", projectId, "gantt"],
    queryFn: () => projectsApi.gantt(projectId),
    enabled: !!projectId && tab === "gantt",
  });

  const completeTask = useMutation({
    mutationFn: (tid: string) => projectsApi.completeTask(tid),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["project", projectId] }),
  });

  const updateStatus = useMutation({
    mutationFn: (status: ProjectStatus) => projectsApi.update(projectId, { status }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["project", projectId] }),
  });

  if (isLoading || !project) {
    return <div className="p-8 text-center text-gray-400">Loading project…</div>;
  }

  const doneCount = project.tasks.filter(t => t.status === "DONE").length;
  const totalCount = project.tasks.length;
  const pct = totalCount > 0 ? Math.round((doneCount / totalCount) * 100) : 0;

  const statuses: ProjectStatus[] = ["PLANNING", "ACTIVE", "ON_HOLD", "COMPLETED", "CANCELLED"];

  return (
    <div className="p-6 space-y-6 max-w-7xl mx-auto">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <div className="text-xs text-gray-400 font-mono">{project.project_no}</div>
          <h1 className="text-2xl font-bold text-gray-900 mt-0.5">{project.name}</h1>
          {project.description && <p className="text-sm text-gray-500 mt-1">{project.description}</p>}
        </div>
        <div className="flex items-center gap-2">
          <select className="border rounded px-3 py-2 text-sm"
            value={project.status}
            onChange={e => updateStatus.mutate(e.target.value as ProjectStatus)}>
            {statuses.map(s => <option key={s} value={s}>{s.replace("_", " ")}</option>)}
          </select>
        </div>
      </div>

      {/* Progress + meta */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="bg-white rounded-xl border p-4 col-span-2">
          <div className="flex justify-between text-sm text-gray-600 mb-2">
            <span>Overall Progress</span>
            <span>{doneCount}/{totalCount} tasks done</span>
          </div>
          <div className="bg-gray-200 rounded-full h-3">
            <div className="bg-blue-500 h-3 rounded-full transition-all" style={{ width: `${pct}%` }} />
          </div>
          <div className="text-xs text-gray-400 mt-1 text-right">{pct}%</div>
        </div>
        <div className="bg-white rounded-xl border p-4">
          <div className="text-xs text-gray-500">Timeline</div>
          <div className="text-sm font-medium mt-1">{fmtDate(project.start_date)}</div>
          <div className="text-xs text-gray-400">→ {fmtDate(project.end_date)}</div>
        </div>
        <div className="bg-white rounded-xl border p-4">
          <div className="text-xs text-gray-500">Budget</div>
          <div className="text-sm font-medium mt-1">
            {project.budget != null ? `KES ${project.budget.toLocaleString()}` : "—"}
          </div>
          <div className="text-xs text-gray-400">{project.milestone_count} milestones</div>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 border-b">
        {(["overview", "tasks", "gantt"] as const).map(t => (
          <button key={t} onClick={() => setTab(t)}
            className={`px-4 py-2 text-sm font-medium border-b-2 -mb-px capitalize ${tab === t ? "border-blue-600 text-blue-600" : "border-transparent text-gray-500 hover:text-gray-700"}`}>
            {t === "gantt" ? "Gantt Chart" : t.charAt(0).toUpperCase() + t.slice(1)}
          </button>
        ))}
      </div>

      {/* Overview tab */}
      {tab === "overview" && (
        <div className="space-y-4">
          <h3 className="font-semibold text-gray-800">Milestones ({project.milestones.length})</h3>
          {project.milestones.length === 0 ? (
            <p className="text-sm text-gray-400">No milestones defined.</p>
          ) : (
            <div className="space-y-2">
              {project.milestones.map(m => (
                <div key={m.id} className={`bg-white border rounded-lg p-3 flex items-center gap-3 ${m.is_complete ? "opacity-60" : ""}`}>
                  <span className={`text-lg ${m.is_complete ? "text-green-500" : "text-gray-300"}`}>
                    {m.is_complete ? "✓" : "◇"}
                  </span>
                  <div className="flex-1">
                    <div className="font-medium text-sm text-gray-900">{m.name}</div>
                    <div className="text-xs text-gray-400">Due: {fmtDate(m.due_date)}</div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Tasks tab */}
      {tab === "tasks" && (
        <div className="space-y-3">
          <div className="flex justify-between items-center">
            <h3 className="font-semibold text-gray-800">Tasks ({project.tasks.length})</h3>
            <Button onClick={() => setShowAddTask(true)}>+ Add Task</Button>
          </div>
          {project.tasks.length === 0 ? (
            <p className="text-sm text-gray-400">No tasks yet.</p>
          ) : (
            <div className="bg-white rounded-xl border overflow-hidden">
              <table className="w-full text-sm">
                <thead className="bg-gray-50 border-b">
                  <tr>
                    {["Task", "Status", "Priority", "Assigned", "Due", "Est. Hours", "Action"].map(h => (
                      <th key={h} className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase">{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody className="divide-y">
                  {project.tasks.map(t => (
                    <tr key={t.id} className="hover:bg-gray-50">
                      <td className="px-4 py-3">
                        <div className="flex items-center gap-1">
                          {t.is_critical_path && <span className="text-red-400 text-xs">★</span>}
                          <span className="font-medium text-gray-900">{t.title}</span>
                        </div>
                        {t.description && <div className="text-xs text-gray-400 truncate max-w-[200px]">{t.description}</div>}
                      </td>
                      <td className="px-4 py-3">
                        <span className={`text-xs font-semibold px-2 py-0.5 rounded-full ${TASK_STATUS_COLOR[t.status]}`}>
                          {t.status.replace("_", " ")}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-xs text-gray-600">{t.priority}</td>
                      <td className="px-4 py-3 text-xs text-gray-500">{t.assigned_to_name ?? "—"}</td>
                      <td className="px-4 py-3 text-xs text-gray-500">{fmtDate(t.due_date)}</td>
                      <td className="px-4 py-3 text-xs text-gray-500">{t.estimated_hours ?? "—"}h</td>
                      <td className="px-4 py-3">
                        {t.status !== "DONE" && (
                          <button disabled={completeTask.isPending}
                            onClick={() => completeTask.mutate(t.id)}
                            className="text-xs px-2 py-1 rounded bg-green-50 text-green-700 hover:bg-green-100">
                            Done
                          </button>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {/* Gantt tab */}
      {tab === "gantt" && (
        <div className="bg-white rounded-xl border overflow-hidden">
          <div className="px-4 py-3 border-b bg-gray-50 flex justify-between items-center">
            <h3 className="font-semibold text-gray-800">Gantt Chart</h3>
            <div className="flex gap-3 text-xs text-gray-500">
              {(["TODO", "IN_PROGRESS", "BLOCKED", "DONE"] as const).map(s => (
                <div key={s} className="flex items-center gap-1">
                  <div className={`w-3 h-3 rounded ${TASK_BAR_COLOR[s]}`} />
                  {s.replace("_", " ")}
                </div>
              ))}
              <div className="flex items-center gap-1">
                <span className="text-red-400">★</span> Critical
              </div>
            </div>
          </div>
          {gantt ? (
            <GanttChart gantt={gantt} />
          ) : (
            <div className="p-6 text-center text-gray-400">Loading Gantt data…</div>
          )}
        </div>
      )}

      {showAddTask && <AddTaskModal projectId={projectId} onClose={() => setShowAddTask(false)} />}
    </div>
  );
}
