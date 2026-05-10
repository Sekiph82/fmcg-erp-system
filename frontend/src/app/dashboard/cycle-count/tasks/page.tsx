"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { listTasks, updateTask, CycleCountTask, TaskStatus, TASK_STATUS_BADGE, ABC_BADGE } from "@/lib/cycleCount";

const STATUSES: TaskStatus[] = ["pending", "in_progress", "completed", "approved", "rejected"];

export default function TasksPage() {
  const [tasks, setTasks] = useState<CycleCountTask[]>([]);
  const [loading, setLoading] = useState(true);
  const [statusFilter, setStatusFilter] = useState<TaskStatus | "all">("all");
  const [dateFilter, setDateFilter] = useState(new Date().toISOString().split("T")[0]);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      setTasks(await listTasks({
        status: statusFilter === "all" ? undefined : statusFilter,
        scheduled_date: dateFilter || undefined,
      }));
    } catch {}
    setLoading(false);
  }, [statusFilter, dateFilter]);

  useEffect(() => { load(); }, [load]);

  async function handleStatusChange(id: string, status: TaskStatus) {
    await updateTask(id, { status });
    await load();
  }

  const today = new Date().toISOString().split("T")[0];

  return (
    <div className="max-w-6xl mx-auto py-8 px-4 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Count Tasks</h1>
          <p className="text-sm text-gray-500 mt-1">{tasks.length} task(s)</p>
        </div>
        <div className="flex gap-2 items-center">
          <input type="date" className="border border-gray-300 rounded-lg px-3 py-2 text-sm" value={dateFilter} onChange={(e) => setDateFilter(e.target.value)} />
          {(["all", ...STATUSES] as const).map((s) => (
            <button key={s} onClick={() => setStatusFilter(s)} className={`text-sm px-2.5 py-1.5 rounded-lg capitalize ${statusFilter === s ? "bg-indigo-600 text-white" : "bg-gray-100 text-gray-700"}`}>
              {s.replace("_", " ")}
            </button>
          ))}
        </div>
      </div>

      {loading ? <div className="text-gray-500 py-8 text-center">Loading...</div> : (
        <div className="bg-white rounded-2xl border border-gray-200 overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 border-b border-gray-200">
              <tr>
                {["Task No.", "Date", "ABC", "Item", "Status", ""].map((h) => (
                  <th key={h} className="text-left px-4 py-3 font-medium text-gray-700">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {tasks.map((t) => {
                const overdue = t.scheduled_date < today && t.status === "pending";
                return (
                  <tr key={t.id} className={`hover:bg-gray-50 ${overdue ? "bg-red-50" : ""}`}>
                    <td className="px-4 py-3 font-mono text-xs text-indigo-700">{t.task_no}</td>
                    <td className={`px-4 py-3 ${overdue ? "text-red-600 font-medium" : ""}`}>{t.scheduled_date}{overdue ? " ⚠" : ""}</td>
                    <td className="px-4 py-3">
                      {t.abc_class && (
                        <span className={`text-xs px-2 py-0.5 rounded font-bold ${ABC_BADGE[t.abc_class]}`}>{t.abc_class}</span>
                      )}
                    </td>
                    <td className="px-4 py-3 text-gray-600 text-xs font-mono">
                      {t.product_id ? t.product_id.slice(0, 8) + "..." : t.material_id ? t.material_id.slice(0, 8) + "..." : "All items"}
                    </td>
                    <td className="px-4 py-3">
                      <span className={`text-xs px-2 py-0.5 rounded font-medium capitalize ${TASK_STATUS_BADGE[t.status]}`}>
                        {t.status.replace("_", " ")}
                      </span>
                    </td>
                    <td className="px-4 py-3 flex gap-2">
                      {t.status === "pending" && (
                        <Link href={`/dashboard/cycle-count/entries?task_id=${t.id}`} className="text-xs text-indigo-600 hover:underline">
                          Count
                        </Link>
                      )}
                      <select className="text-xs border border-gray-200 rounded px-2 py-0.5 capitalize" value={t.status} onChange={(e) => handleStatusChange(t.id, e.target.value as TaskStatus)}>
                        {STATUSES.map((s) => <option key={s} value={s}>{s.replace("_", " ")}</option>)}
                      </select>
                    </td>
                  </tr>
                );
              })}
              {tasks.length === 0 && <tr><td colSpan={6} className="px-4 py-8 text-center text-gray-400">No tasks found for selected filters</td></tr>}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
