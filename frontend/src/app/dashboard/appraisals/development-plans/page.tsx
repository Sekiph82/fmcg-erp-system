"use client";
import { useCallback, useEffect, useState } from "react";
import { appraisalsApi, DevelopmentPlan, DevelopmentPlanStatus, PLAN_STATUS_COLOR } from "@/lib/appraisals";

const STATUSES: DevelopmentPlanStatus[] = ["open","in_progress","completed","cancelled"];

export default function DevelopmentPlansPage() {
  const [plans, setPlans] = useState<DevelopmentPlan[]>([]);
  const [loading, setLoading] = useState(true);
  const [statusFilter, setStatusFilter] = useState("");
  const [selected, setSelected] = useState<DevelopmentPlan | null>(null);
  const [updateStatus, setUpdateStatus] = useState<DevelopmentPlanStatus>("open");
  const [notes, setNotes] = useState("");

  const load = useCallback(() =>
    appraisalsApi.listDevelopmentPlans({ status: statusFilter || undefined })
      .then(setPlans).finally(() => setLoading(false)), [statusFilter]);
  useEffect(() => { load(); }, [load]);

  const save = async () => {
    if (!selected) return;
    await appraisalsApi.updateDevelopmentPlan(selected.development_plan_id, {
      status: updateStatus,
      notes: notes || undefined,
    });
    setSelected(null);
    load();
  };

  const overdue = (plan: DevelopmentPlan) =>
    plan.due_date && new Date(plan.due_date) < new Date() && plan.status !== "completed";

  return (
    <div className="p-6 space-y-4">
      <h1 className="text-xl font-bold text-gray-900">Development Plans</h1>

      <select
        className="border rounded px-2 py-1 text-sm"
        value={statusFilter}
        onChange={(e) => setStatusFilter(e.target.value)}
      >
        <option value="">All Statuses</option>
        {STATUSES.map((s) => <option key={s} value={s}>{s.replace(/_/g," ")}</option>)}
      </select>

      {loading ? (
        <p className="text-gray-500 text-sm">Loading…</p>
      ) : (
        <div className="grid gap-3">
          {plans.map((p) => (
            <div
              key={p.development_plan_id}
              className={`bg-white border rounded-lg p-4 shadow-sm cursor-pointer hover:bg-gray-50 ${overdue(p) ? "border-red-300" : ""}`}
              onClick={() => { setSelected(p); setUpdateStatus(p.status); setNotes(p.notes ?? ""); }}
            >
              <div className="flex justify-between items-start">
                <div className="flex-1">
                  <p className="font-semibold text-gray-800">{p.goal_title}</p>
                  <p className="text-sm text-gray-500 mt-0.5">Employee: {p.employee_id}</p>
                  {p.action_plan && <p className="text-sm text-gray-600 mt-1 line-clamp-2">{p.action_plan}</p>}
                  <div className="flex gap-3 mt-2 text-xs text-gray-400">
                    {p.due_date && <span className={overdue(p) ? "text-red-500 font-semibold" : ""}>Due: {p.due_date}</span>}
                    {p.owner_name && <span>Owner: {p.owner_name}</span>}
                  </div>
                </div>
                <span className={`inline-flex rounded-full px-2 py-0.5 text-xs font-medium ml-3 ${PLAN_STATUS_COLOR[p.status]}`}>
                  {p.status.replace(/_/g," ")}
                </span>
              </div>
              {overdue(p) && (
                <p className="text-xs text-red-500 mt-1 font-semibold">⚠ Overdue</p>
              )}
            </div>
          ))}
          {plans.length === 0 && <p className="text-gray-400 text-sm text-center py-8">No development plans found.</p>}
        </div>
      )}

      {selected && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-lg shadow-xl w-full max-w-md p-6 space-y-4">
            <div className="flex justify-between">
              <h2 className="text-lg font-bold text-gray-900">Update Plan</h2>
              <button onClick={() => setSelected(null)} className="text-gray-400 hover:text-gray-700 text-xl">✕</button>
            </div>
            <div>
              <p className="font-semibold text-gray-800">{selected.goal_title}</p>
              {selected.action_plan && <p className="text-sm text-gray-600 mt-1">{selected.action_plan}</p>}
            </div>
            <div>
              <label className="text-xs text-gray-500">Status</label>
              <select className="w-full border rounded px-2 py-1 text-sm mt-1"
                value={updateStatus} onChange={(e) => setUpdateStatus(e.target.value as DevelopmentPlanStatus)}>
                {STATUSES.map(s => <option key={s} value={s}>{s.replace(/_/g," ")}</option>)}
              </select>
            </div>
            <div>
              <label className="text-xs text-gray-500">Notes</label>
              <textarea className="w-full border rounded px-2 py-1 text-sm mt-1" rows={3}
                value={notes} onChange={(e) => setNotes(e.target.value)} />
            </div>
            <div className="flex gap-2">
              <button onClick={save} className="rounded bg-blue-600 px-4 py-1.5 text-sm text-white hover:bg-blue-700">Save</button>
              <button onClick={() => setSelected(null)} className="rounded border px-4 py-1.5 text-sm text-gray-600 hover:bg-gray-50">Cancel</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
