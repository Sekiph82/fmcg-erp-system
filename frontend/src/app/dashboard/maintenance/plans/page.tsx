"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { maintenanceApi, PMPlan, PMWorkOrder, PMFrequency, PMStatus } from "@/lib/maintenance";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { RequirePermission } from "@/components/PermissionGuard";

const statusBadge = (s: PMStatus) =>
  s === "COMPLETED" ? "green" : s === "OVERDUE" ? "red" : s === "IN_PROGRESS" ? "blue" : s === "SKIPPED" ? "gray" : "yellow";

export default function PMPlansPage() {
  const qc = useQueryClient();
  const [showNewPlan, setShowNewPlan] = useState(false);
  const [showNewWO, setShowNewWO] = useState(false);
  const [showComplete, setShowComplete] = useState<PMWorkOrder | null>(null);
  const [selectedPlan, setSelectedPlan] = useState<PMPlan | null>(null);
  const [tab, setTab] = useState<"plans" | "workorders">("plans");

  const { data: plans = [] } = useQuery({
    queryKey: ["maint-plans"],
    queryFn: () => maintenanceApi.listPMPlans(),
  });

  const { data: workOrders = [] } = useQuery({
    queryKey: ["maint-work-orders"],
    queryFn: () => maintenanceApi.listWorkOrders(),
  });

  const { data: assets = [] } = useQuery({
    queryKey: ["maint-assets"],
    queryFn: () => maintenanceApi.listAssets(),
  });

  const createPlan = useMutation({
    mutationFn: (data: object) => maintenanceApi.createPMPlan(data),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["maint-plans"] }); setShowNewPlan(false); },
  });

  const createWO = useMutation({
    mutationFn: (data: object) => maintenanceApi.createWorkOrder(data),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["maint-work-orders"] }); setShowNewWO(false); },
  });

  const completeWO = useMutation({
    mutationFn: ({ id, data }: { id: string; data: object }) => maintenanceApi.completeWorkOrder(id, data),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["maint-work-orders"] }); qc.invalidateQueries({ queryKey: ["maint-plans"] }); setShowComplete(null); },
  });

  const today = new Date().toISOString().slice(0, 10);

  return (
    <RequirePermission permission="maintenance.view">
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">PM Plans & Work Orders</h1>
          <p className="text-sm text-gray-500 mt-1">Preventive maintenance schedules and execution</p>
        </div>
        <div className="flex gap-2">
          {tab === "plans" && <Button onClick={() => setShowNewPlan(true)}>New PM Plan</Button>}
          {tab === "workorders" && <Button onClick={() => setShowNewWO(true)}>Schedule Work Order</Button>}
        </div>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 border-b">
        {(["plans", "workorders"] as const).map((t) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={`px-4 py-2 text-sm font-medium capitalize transition-colors border-b-2 -mb-px ${
              tab === t ? "border-indigo-600 text-indigo-700" : "border-transparent text-gray-500 hover:text-gray-700"
            }`}
          >
            {t === "plans" ? `PM Plans (${plans.length})` : `Work Orders (${workOrders.length})`}
          </button>
        ))}
      </div>

      {/* PM Plans */}
      {tab === "plans" && (
        <div className="bg-white rounded-lg border">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b bg-gray-50 text-xs text-gray-500 uppercase">
                <th className="px-5 py-2 text-left">Asset</th>
                <th className="px-5 py-2 text-left">Plan Name</th>
                <th className="px-5 py-2 text-left">Frequency</th>
                <th className="px-5 py-2 text-left">Assigned To</th>
                <th className="px-5 py-2 text-left">Last Done</th>
                <th className="px-5 py-2 text-left">Next Due</th>
                <th className="px-5 py-2 text-left">Est. Duration</th>
                <th className="px-5 py-2 text-left">Active</th>
              </tr>
            </thead>
            <tbody className="divide-y">
              {plans.map((p) => {
                const isOverdue = p.next_due_date && p.next_due_date < today;
                return (
                  <tr key={p.id} className="hover:bg-gray-50">
                    <td className="px-5 py-3">
                      <p className="font-medium text-gray-900">{p.asset_name || "—"}</p>
                      <p className="text-xs text-gray-400">{p.asset_no}</p>
                    </td>
                    <td className="px-5 py-3 text-gray-700">{p.name}</td>
                    <td className="px-5 py-3"><Badge label={p.frequency} variant="blue" /></td>
                    <td className="px-5 py-3 text-gray-500">{p.assigned_to || "—"}</td>
                    <td className="px-5 py-3 text-gray-500">{p.last_completed_date || "—"}</td>
                    <td className={`px-5 py-3 font-medium ${isOverdue ? "text-red-600" : "text-gray-700"}`}>
                      {p.next_due_date || "—"}
                      {isOverdue && <span className="ml-1 text-xs text-red-500">overdue</span>}
                    </td>
                    <td className="px-5 py-3 text-gray-500">{p.estimated_duration_minutes ? `${p.estimated_duration_minutes} min` : "—"}</td>
                    <td className="px-5 py-3"><Badge label={p.is_active ? "Yes" : "No"} variant={p.is_active ? "green" : "gray"} /></td>
                  </tr>
                );
              })}
              {plans.length === 0 && (
                <tr><td colSpan={8} className="px-5 py-8 text-center text-gray-400">No PM plans</td></tr>
              )}
            </tbody>
          </table>
        </div>
      )}

      {/* Work Orders */}
      {tab === "workorders" && (
        <div className="bg-white rounded-lg border">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b bg-gray-50 text-xs text-gray-500 uppercase">
                <th className="px-5 py-2 text-left">WO No</th>
                <th className="px-5 py-2 text-left">Asset</th>
                <th className="px-5 py-2 text-left">Plan</th>
                <th className="px-5 py-2 text-left">Scheduled</th>
                <th className="px-5 py-2 text-left">Technician</th>
                <th className="px-5 py-2 text-left">Status</th>
                <th className="px-5 py-2 text-right">Duration</th>
                <th className="px-5 py-2" />
              </tr>
            </thead>
            <tbody className="divide-y">
              {workOrders.map((wo) => (
                <tr key={wo.id} className="hover:bg-gray-50">
                  <td className="px-5 py-3 font-mono text-xs font-semibold text-indigo-700">{wo.wo_no}</td>
                  <td className="px-5 py-3 font-medium">{wo.asset_name || "—"}</td>
                  <td className="px-5 py-3 text-gray-600">{wo.plan_name || "—"}</td>
                  <td className="px-5 py-3">{wo.scheduled_date}</td>
                  <td className="px-5 py-3 text-gray-500">{wo.technician || "—"}</td>
                  <td className="px-5 py-3"><Badge label={wo.status} variant={statusBadge(wo.status)} /></td>
                  <td className="px-5 py-3 text-right">{wo.actual_duration_minutes ? `${wo.actual_duration_minutes} min` : "—"}</td>
                  <td className="px-5 py-3">
                    {wo.status === "PENDING" || wo.status === "IN_PROGRESS" ? (
                      <button className="text-xs text-green-600 hover:underline" onClick={() => setShowComplete(wo)}>Complete</button>
                    ) : null}
                  </td>
                </tr>
              ))}
              {workOrders.length === 0 && (
                <tr><td colSpan={8} className="px-5 py-8 text-center text-gray-400">No work orders</td></tr>
              )}
            </tbody>
          </table>
        </div>
      )}

      {/* New PM Plan modal */}
      {showNewPlan && (
        <NewPMPlanModal
          assets={assets}
          onClose={() => setShowNewPlan(false)}
          onSubmit={(d) => createPlan.mutate(d)}
          loading={createPlan.isPending}
        />
      )}

      {/* New WO modal */}
      {showNewWO && (
        <NewWOModal
          plans={plans}
          onClose={() => setShowNewWO(false)}
          onSubmit={(d) => createWO.mutate(d)}
          loading={createWO.isPending}
        />
      )}

      {/* Complete WO modal */}
      {showComplete && (
        <CompleteWOModal
          wo={showComplete}
          onClose={() => setShowComplete(null)}
          onSubmit={(d) => completeWO.mutate({ id: showComplete.id, data: d })}
          loading={completeWO.isPending}
        />
      )}
    </div>
    </RequirePermission>
  );
}

function NewPMPlanModal({ assets, onClose, onSubmit, loading }: { assets: { id: string; name: string; asset_no: string }[]; onClose: () => void; onSubmit: (d: object) => void; loading: boolean }) {
  const today = new Date().toISOString().slice(0, 10);
  const [form, setForm] = useState({ asset_id: "", name: "", frequency: "MONTHLY", interval_days: "", estimated_duration_minutes: "", assigned_to: "", next_due_date: today, checklist: "" });
  const set = (k: string, v: string) => setForm((f) => ({ ...f, [k]: v }));

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
      <div className="bg-white rounded-xl shadow-xl w-full max-w-lg p-6 space-y-4">
        <h2 className="font-semibold text-lg">New PM Plan</h2>
        <div className="grid grid-cols-2 gap-3">
          <div className="col-span-2">
            <label className="block text-xs font-medium text-gray-600 mb-1">Asset</label>
            <select className="w-full border rounded px-3 py-2 text-sm" value={form.asset_id} onChange={(e) => set("asset_id", e.target.value)}>
              <option value="">Select asset…</option>
              {assets.map((a) => <option key={a.id} value={a.id}>{a.asset_no} — {a.name}</option>)}
            </select>
          </div>
          <div className="col-span-2">
            <label className="block text-xs font-medium text-gray-600 mb-1">Plan Name</label>
            <input className="w-full border rounded px-3 py-2 text-sm" value={form.name} onChange={(e) => set("name", e.target.value)} />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Frequency</label>
            <select className="w-full border rounded px-3 py-2 text-sm" value={form.frequency} onChange={(e) => set("frequency", e.target.value)}>
              {["DAILY","WEEKLY","MONTHLY","QUARTERLY","BIANNUAL","ANNUAL"].map((f) => <option key={f} value={f}>{f}</option>)}
            </select>
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Custom Interval (days)</label>
            <input className="w-full border rounded px-3 py-2 text-sm" type="number" placeholder="Override frequency" value={form.interval_days} onChange={(e) => set("interval_days", e.target.value)} />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Est. Duration (min)</label>
            <input className="w-full border rounded px-3 py-2 text-sm" type="number" value={form.estimated_duration_minutes} onChange={(e) => set("estimated_duration_minutes", e.target.value)} />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Assigned To</label>
            <input className="w-full border rounded px-3 py-2 text-sm" value={form.assigned_to} onChange={(e) => set("assigned_to", e.target.value)} />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Next Due Date</label>
            <input type="date" className="w-full border rounded px-3 py-2 text-sm" value={form.next_due_date} onChange={(e) => set("next_due_date", e.target.value)} />
          </div>
        </div>
        <div>
          <label className="block text-xs font-medium text-gray-600 mb-1">Checklist (one item per line)</label>
          <textarea className="w-full border rounded px-3 py-2 text-sm" rows={4} value={form.checklist} onChange={(e) => set("checklist", e.target.value)} placeholder="Check oil level&#10;Inspect belts&#10;Lubricate bearings…" />
        </div>
        <div className="flex gap-2 justify-end">
          <Button variant="secondary" onClick={onClose}>Cancel</Button>
          <Button loading={loading} onClick={() => onSubmit({
            ...form,
            interval_days: form.interval_days ? parseInt(form.interval_days) : null,
            estimated_duration_minutes: form.estimated_duration_minutes ? parseInt(form.estimated_duration_minutes) : null,
          })}>Create</Button>
        </div>
      </div>
    </div>
  );
}

function NewWOModal({ plans, onClose, onSubmit, loading }: { plans: PMPlan[]; onClose: () => void; onSubmit: (d: object) => void; loading: boolean }) {
  const today = new Date().toISOString().slice(0, 10);
  const [form, setForm] = useState({ plan_id: "", scheduled_date: today, technician: "" });
  const set = (k: string, v: string) => setForm((f) => ({ ...f, [k]: v }));

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
      <div className="bg-white rounded-xl shadow-xl w-full max-w-md p-6 space-y-4">
        <h2 className="font-semibold text-lg">Schedule Work Order</h2>
        <div className="space-y-3">
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">PM Plan</label>
            <select className="w-full border rounded px-3 py-2 text-sm" value={form.plan_id} onChange={(e) => set("plan_id", e.target.value)}>
              <option value="">Select plan…</option>
              {plans.map((p) => <option key={p.id} value={p.id}>{p.asset_name} — {p.name}</option>)}
            </select>
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Scheduled Date</label>
            <input type="date" className="w-full border rounded px-3 py-2 text-sm" value={form.scheduled_date} onChange={(e) => set("scheduled_date", e.target.value)} />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Technician</label>
            <input className="w-full border rounded px-3 py-2 text-sm" value={form.technician} onChange={(e) => set("technician", e.target.value)} />
          </div>
        </div>
        <div className="flex gap-2 justify-end">
          <Button variant="secondary" onClick={onClose}>Cancel</Button>
          <Button loading={loading} onClick={() => onSubmit(form)}>Schedule</Button>
        </div>
      </div>
    </div>
  );
}

function CompleteWOModal({ wo, onClose, onSubmit, loading }: { wo: PMWorkOrder; onClose: () => void; onSubmit: (d: object) => void; loading: boolean }) {
  const [form, setForm] = useState({ actual_duration_minutes: "", checklist_notes: "", technician: wo.technician ?? "" });
  const set = (k: string, v: string) => setForm((f) => ({ ...f, [k]: v }));

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
      <div className="bg-white rounded-xl shadow-xl w-full max-w-md p-6 space-y-4">
        <div>
          <h2 className="font-semibold text-lg">Complete Work Order</h2>
          <p className="text-xs text-gray-500 mt-1">{wo.wo_no} — {wo.asset_name}</p>
        </div>
        <div className="space-y-3">
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">Actual Duration (min)</label>
              <input className="w-full border rounded px-3 py-2 text-sm" type="number" value={form.actual_duration_minutes} onChange={(e) => set("actual_duration_minutes", e.target.value)} />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">Technician</label>
              <input className="w-full border rounded px-3 py-2 text-sm" value={form.technician} onChange={(e) => set("technician", e.target.value)} />
            </div>
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Completion Notes</label>
            <textarea className="w-full border rounded px-3 py-2 text-sm" rows={3} value={form.checklist_notes} onChange={(e) => set("checklist_notes", e.target.value)} placeholder="Notes on each checklist item…" />
          </div>
        </div>
        <div className="flex gap-2 justify-end">
          <Button variant="secondary" onClick={onClose}>Cancel</Button>
          <Button loading={loading} onClick={() => onSubmit({
            status: "COMPLETED",
            completed_at: new Date().toISOString(),
            actual_duration_minutes: form.actual_duration_minutes ? parseInt(form.actual_duration_minutes) : undefined,
            checklist_notes: form.checklist_notes || undefined,
            technician: form.technician || undefined,
          })}>Mark Complete</Button>
        </div>
      </div>
    </div>
  );
}
