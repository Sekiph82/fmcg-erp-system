"use client";

import { useEffect, useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { maintenanceApi, PMPlan, PMPlanSparePartRequirementsReport, PMWorkOrder, PMFrequency, PMStatus } from "@/lib/maintenance";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { PermissionGuard, RequirePermission } from "@/components/PermissionGuard";

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

  const { data: scheduleImpact, isLoading: scheduleImpactLoading, isError: scheduleImpactError } = useQuery({
    queryKey: ["maint-work-order-schedule-impact"],
    queryFn: () => maintenanceApi.getWorkOrderScheduleImpact(),
    enabled: tab === "workorders",
  });

  const { data: assets = [] } = useQuery({
    queryKey: ["maint-assets"],
    queryFn: () => maintenanceApi.listAssets(),
  });

  const planRequirementsQuery = useQuery({
    queryKey: ["maint-plan-spare-parts", selectedPlan?.id],
    queryFn: () => maintenanceApi.getPMPlanSpareParts(selectedPlan!.id),
    enabled: Boolean(selectedPlan),
  });

  const createPlan = useMutation({
    mutationFn: (data: object) => maintenanceApi.createPMPlan(data),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["maint-plans"] }); setShowNewPlan(false); },
  });

  const updatePlanSpareParts = useMutation({
    mutationFn: ({ planId, items }: { planId: string; items: { spare_part_id: string; quantity_required: number }[] }) =>
      maintenanceApi.updatePMPlanSpareParts(planId, items),
    onSuccess: (_, variables) => {
      qc.invalidateQueries({ queryKey: ["maint-plan-spare-parts", variables.planId] });
      qc.invalidateQueries({ queryKey: ["maint-plan-spare-parts"] });
      setSelectedPlan(null);
    },
  });

  const createWO = useMutation({
    mutationFn: (data: object) => maintenanceApi.createWorkOrder(data),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["maint-work-orders"] }); qc.invalidateQueries({ queryKey: ["maint-work-order-schedule-impact"] }); qc.invalidateQueries({ queryKey: ["maint-downtime-capacity-impact"] }); qc.invalidateQueries({ queryKey: ["maint-plan-spare-parts"] }); setShowNewWO(false); },
  });

  const completeWO = useMutation({
    mutationFn: ({ id, data }: { id: string; data: object }) => maintenanceApi.completeWorkOrder(id, data),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["maint-work-orders"] }); qc.invalidateQueries({ queryKey: ["maint-plans"] }); qc.invalidateQueries({ queryKey: ["maint-work-order-schedule-impact"] }); qc.invalidateQueries({ queryKey: ["maint-downtime-capacity-impact"] }); setShowComplete(null); },
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
                <th className="px-5 py-2 text-right">Spare parts</th>
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
                    <td className="px-5 py-3 text-right">
                      <PermissionGuard permission="maintenance.edit">
                        <Button variant="secondary" onClick={() => setSelectedPlan(p)}>Requirements</Button>
                      </PermissionGuard>
                    </td>
                  </tr>
                );
              })}
              {plans.length === 0 && (
                <tr><td colSpan={9} className="px-5 py-8 text-center text-gray-400">No PM plans</td></tr>
              )}
            </tbody>
          </table>
        </div>
      )}

      {/* Work Orders */}
      {tab === "workorders" && (
        <div className="space-y-3">
          <div className="rounded-lg border bg-indigo-50 px-4 py-3 text-sm text-indigo-900">
            PM windows are compared with production schedules on the asset&apos;s linked work center. Overlaps are advisory; this screen does not move or block production.
            {scheduleImpact && <p className="mt-1 text-xs text-indigo-700">Impact review period: {scheduleImpact.date_from} through {scheduleImpact.date_to}.</p>}
            {scheduleImpact?.data_notes.map((note) => <p key={note} className="mt-1 text-xs text-indigo-700">{note}</p>)}
            {scheduleImpactLoading && <p className="mt-1 text-xs">Loading schedule impact…</p>}
            {scheduleImpactError && <p className="mt-1 text-xs text-amber-800">Production schedule impact is unavailable for your current access.</p>}
          </div>
          <div className="bg-white rounded-lg border overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b bg-gray-50 text-xs text-gray-500 uppercase">
                <th className="px-5 py-2 text-left">WO No</th>
                <th className="px-5 py-2 text-left">Asset</th>
                <th className="px-5 py-2 text-left">Plan</th>
                <th className="px-5 py-2 text-left">Scheduled</th>
                <th className="px-5 py-2 text-left">PM Window / Production Impact</th>
                <th className="px-5 py-2 text-left">Technician</th>
                <th className="px-5 py-2 text-left">Status</th>
                <th className="px-5 py-2 text-right">Duration</th>
                <th className="px-5 py-2" />
              </tr>
            </thead>
            <tbody className="divide-y">
              {workOrders.map((wo) => {
                const impact = scheduleImpact?.windows.find((window) => window.pm_work_order_id === wo.id);
                return (
                <tr key={wo.id} className="hover:bg-gray-50">
                  <td className="px-5 py-3 font-mono text-xs font-semibold text-indigo-700">{wo.wo_no}</td>
                  <td className="px-5 py-3 font-medium">{wo.asset_name || "—"}</td>
                  <td className="px-5 py-3 text-gray-600">{wo.plan_name || "—"}</td>
                  <td className="px-5 py-3">{wo.scheduled_date}</td>
                  <td className="px-5 py-3 text-xs">
                    {wo.window_start && wo.window_end ? (
                      <>
                        <div>{new Date(wo.window_start).toLocaleString()} – {new Date(wo.window_end).toLocaleString()}</div>
                        {impact?.unavailable_reason ? <div className="mt-1 text-amber-700">{impact.unavailable_reason}</div> : null}
                        {impact && impact.conflicts.length > 0 ? (
                          <div className="mt-1 text-red-700">
                            {impact.conflicts.length} overlapping production schedule{impact.conflicts.length === 1 ? "" : "s"}
                            {impact.conflicts.map((conflict) => <div key={conflict.schedule_id}>{conflict.schedule_id}: {new Date(conflict.start_time).toLocaleString()} – {new Date(conflict.end_time).toLocaleString()}</div>)}
                          </div>
                        ) : impact && !impact.unavailable_reason ? <div className="mt-1 text-green-700">No scheduled overlap</div> : !impact && scheduleImpact ? <div className="mt-1 text-gray-500">Outside impact review period</div> : null}
                      </>
                    ) : <span className="text-gray-400">No explicit time window</span>}
                  </td>
                  <td className="px-5 py-3 text-gray-500">{wo.technician || "—"}</td>
                  <td className="px-5 py-3"><Badge label={wo.status} variant={statusBadge(wo.status)} /></td>
                  <td className="px-5 py-3 text-right">{wo.actual_duration_minutes ? `${wo.actual_duration_minutes} min` : "—"}</td>
                  <td className="px-5 py-3">
                    {wo.status === "PENDING" || wo.status === "IN_PROGRESS" ? (
                      <button className="text-xs text-green-600 hover:underline" onClick={() => setShowComplete(wo)}>Complete</button>
                    ) : null}
                  </td>
                </tr>
                );
              })}
              {workOrders.length === 0 && (
                <tr><td colSpan={9} className="px-5 py-8 text-center text-gray-400">No work orders</td></tr>
              )}
            </tbody>
          </table>
          </div>
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

      {selectedPlan && (
        <PlanSparePartsModal
          key={selectedPlan.id}
          plan={selectedPlan}
          report={planRequirementsQuery.data}
          loading={planRequirementsQuery.isLoading}
          error={planRequirementsQuery.isError}
          saving={updatePlanSpareParts.isPending}
          saveError={updatePlanSpareParts.isError}
          onClose={() => setSelectedPlan(null)}
          onSave={(items) => updatePlanSpareParts.mutate({ planId: selectedPlan.id, items })}
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

function PlanSparePartsModal({
  plan, report, loading, error, saving, saveError, onClose, onSave,
}: {
  plan: PMPlan;
  report?: PMPlanSparePartRequirementsReport;
  loading: boolean;
  error: boolean;
  saving: boolean;
  saveError: boolean;
  onClose: () => void;
  onSave: (items: { spare_part_id: string; quantity_required: number }[]) => void;
}) {
  const [items, setItems] = useState<{ spare_part_id: string; quantity_required: string }[]>([]);
  const { data: parts = [] } = useQuery({ queryKey: ["maint-spare-parts-active"], queryFn: () => maintenanceApi.listSpareParts() });

  useEffect(() => {
    if (report) {
      setItems(report.requirements.map((item) => ({
        spare_part_id: item.spare_part_id,
        quantity_required: String(item.quantity_required),
      })));
    }
  }, [report]);

  const hasInvalidItems = items.some((item) =>
    !item.spare_part_id || !Number.isFinite(Number(item.quantity_required)) || Number(item.quantity_required) <= 0
  );
  const hasDuplicates = new Set(items.map((item) => item.spare_part_id).filter(Boolean)).size !== items.filter((item) => item.spare_part_id).length;

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
      <div className="bg-white rounded-xl shadow-xl w-full max-w-3xl p-6 space-y-4 max-h-[90vh] overflow-y-auto">
        <div>
          <h2 className="font-semibold text-lg">Required spare parts</h2>
          <p className="text-xs text-gray-500 mt-1">{plan.asset_name} — {plan.name}</p>
        </div>
        <p className="text-sm text-gray-600">Only parts you add here become a scheduling prerequisite. Empty requirements mean no spare-part quantity is assumed.</p>
        {loading ? <p className="text-sm text-gray-500">Loading availability…</p> : null}
        {error ? <p className="text-sm text-red-700">Availability could not be loaded. Close and reopen this panel to retry.</p> : null}
        {!loading && !error ? (
          <div className="space-y-3">
            {items.map((item, index) => {
              const availability = report?.requirements.find((row) => row.spare_part_id === item.spare_part_id);
              return (
                <div key={`${item.spare_part_id}-${index}`} className="grid grid-cols-1 md:grid-cols-[2fr_1fr_2fr_auto] gap-2 items-end border rounded p-3">
                  <label className="text-xs text-gray-600">Part
                    <select className="mt-1 w-full border rounded px-2 py-2 text-sm" value={item.spare_part_id} onChange={(event) => setItems((current) => current.map((row, i) => i === index ? { ...row, spare_part_id: event.target.value } : row))}>
                      <option value="">Select spare part…</option>
                      {parts.map((part) => <option key={part.id} value={part.id}>{part.part_no} — {part.name}</option>)}
                    </select>
                  </label>
                  <label className="text-xs text-gray-600">Required quantity
                    <input className="mt-1 w-full border rounded px-2 py-2 text-sm" type="number" min="0.0001" step="0.0001" value={item.quantity_required} onChange={(event) => setItems((current) => current.map((row, i) => i === index ? { ...row, quantity_required: event.target.value } : row))} />
                  </label>
                  <div className="text-xs text-gray-600">
                    {availability ? (
                      <><div>Stock {availability.current_stock} · Reserved {availability.reserved_quantity} · Available {availability.available_quantity} {availability.unit}</div>
                        <div className={availability.is_available ? "text-green-700" : "text-amber-700"}>{availability.is_available ? "Available for the next schedule check" : "Currently short; scheduling will be blocked"}</div></>
                    ) : <span>Save to load stock and reservation totals.</span>}
                  </div>
                  <Button variant="secondary" onClick={() => setItems((current) => current.filter((_, i) => i !== index))}>Remove</Button>
                </div>
              );
            })}
            <Button variant="secondary" onClick={() => setItems((current) => [...current, { spare_part_id: "", quantity_required: "1" }])}>Add part</Button>
          </div>
        ) : null}
        {saveError ? <p className="text-sm text-red-700">The requirements were not saved. Check the selected active parts and retry.</p> : null}
        <div className="flex gap-2 justify-end">
          <Button variant="secondary" onClick={onClose}>Cancel</Button>
          <Button loading={saving} disabled={loading || error || hasInvalidItems || hasDuplicates} onClick={() => onSave(items.map((item) => ({ spare_part_id: item.spare_part_id, quantity_required: Number(item.quantity_required) })))}>Save requirements</Button>
        </div>
      </div>
    </div>
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
  const [form, setForm] = useState({ plan_id: "", scheduled_date: today, window_start: "", window_end: "", technician: "" });
  const requirementsQuery = useQuery({
    queryKey: ["maint-plan-spare-parts", form.plan_id],
    queryFn: () => maintenanceApi.getPMPlanSpareParts(form.plan_id),
    enabled: Boolean(form.plan_id),
    refetchOnMount: "always",
  });
  const set = (k: string, v: string) => setForm((f) => ({ ...f, [k]: v }));
  const shortages = (requirementsQuery.data?.requirements ?? []).filter((item) => !item.is_available);
  const windowIsValid = (!form.window_start && !form.window_end) || (
    !!form.window_start && !!form.window_end && new Date(form.window_end).getTime() > new Date(form.window_start).getTime()
  );

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
            <label className="block text-xs font-medium text-gray-600 mb-1">PM Window Start (optional)</label>
            <input type="datetime-local" className="w-full border rounded px-3 py-2 text-sm" value={form.window_start} onChange={(e) => set("window_start", e.target.value)} />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">PM Window End (optional)</label>
            <input type="datetime-local" className="w-full border rounded px-3 py-2 text-sm" value={form.window_end} onChange={(e) => set("window_end", e.target.value)} />
          </div>
          {(!form.window_start && !!form.window_end) || (!!form.window_start && !form.window_end) || !windowIsValid ? (
            <p className="col-span-2 text-xs text-red-600">Enter both window times and ensure the end is after the start.</p>
          ) : null}
          {form.plan_id && requirementsQuery.isFetching ? <p className="text-xs text-gray-500">Checking current spare-part availability…</p> : null}
          {form.plan_id && requirementsQuery.isError ? <p className="text-xs text-red-700">Availability could not be checked. Retry before scheduling.</p> : null}
          {form.plan_id && requirementsQuery.data?.requirements.length === 0 ? <p className="text-xs text-gray-500">No spare parts are configured as a prerequisite for this plan.</p> : null}
          {shortages.length > 0 ? (
            <div className="rounded border border-amber-300 bg-amber-50 p-3 text-xs text-amber-900">
              <p className="font-medium">Scheduling is blocked until required stock is available.</p>
              {shortages.map((item) => <p key={item.spare_part_id}>{item.part_no}: need {item.quantity_required} {item.unit}, available {item.available_quantity} {item.unit}</p>)}
            </div>
          ) : null}
          {requirementsQuery.data?.requirements.map((item) => item.is_available ? (
            <p key={item.spare_part_id} className="text-xs text-green-700">{item.part_no}: {item.quantity_required} {item.unit} required; {item.available_quantity} available.</p>
          ) : null)}
          <div className="col-span-2 text-xs text-gray-500">Times are saved as UTC instants after conversion from your browser&apos;s local time.</div>
          <div className="col-span-2">
            <label className="block text-xs font-medium text-gray-600 mb-1">Technician</label>
            <input className="w-full border rounded px-3 py-2 text-sm" value={form.technician} onChange={(e) => set("technician", e.target.value)} />
          </div>
        </div>
        <div className="flex gap-2 justify-end">
          <Button variant="secondary" onClick={onClose}>Cancel</Button>
          <Button loading={loading} disabled={!form.plan_id || !windowIsValid || requirementsQuery.isFetching || requirementsQuery.isError || shortages.length > 0} onClick={() => onSubmit({
            plan_id: form.plan_id,
            scheduled_date: form.scheduled_date,
            technician: form.technician || null,
            window_start: form.window_start ? new Date(form.window_start).toISOString() : null,
            window_end: form.window_end ? new Date(form.window_end).toISOString() : null,
          })}>Schedule</Button>
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
