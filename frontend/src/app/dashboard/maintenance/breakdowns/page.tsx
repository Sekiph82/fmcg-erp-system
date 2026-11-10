"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { maintenanceApi, BreakdownRecord, BreakdownStatus, BreakdownSeverity, DowntimeReasonCode } from "@/lib/maintenance";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { RequirePermission } from "@/components/PermissionGuard";

const severityBadge = (s: BreakdownSeverity) =>
  s === "CRITICAL" ? "red" : s === "HIGH" ? "red" : s === "MEDIUM" ? "yellow" : "gray";

const statusBadge = (s: BreakdownStatus) =>
  s === "RESOLVED" ? "green" : s === "IN_REPAIR" ? "blue" : "red";

export default function BreakdownsPage() {
  const qc = useQueryClient();
  const [showNew, setShowNew] = useState(false);
  const [resolving, setResolving] = useState<BreakdownRecord | null>(null);
  const [filterStatus, setFilterStatus] = useState<BreakdownStatus | "ALL">("ALL");

  const { data: breakdowns = [], isLoading } = useQuery({
    queryKey: ["maint-breakdowns"],
    queryFn: () => maintenanceApi.listBreakdowns(),
  });

  const { data: assets = [] } = useQuery({
    queryKey: ["maint-assets"],
    queryFn: () => maintenanceApi.listAssets(),
  });

  const { data: downtimeReasonCodes = [] } = useQuery<DowntimeReasonCode[]>({
    queryKey: ["downtime-reason-codes"],
    queryFn: () => maintenanceApi.listDowntimeReasonCodes(),
  });

  const { data: capacityImpact, isLoading: capacityImpactLoading, isError: capacityImpactError } = useQuery({
    queryKey: ["maint-downtime-capacity-impact"],
    queryFn: () => maintenanceApi.getDowntimeCapacityImpact(),
  });

  const { data: priorityEscalation, isLoading: priorityLoading, isError: priorityError } = useQuery({
    queryKey: ["maint-breakdown-priority-escalation"],
    queryFn: () => maintenanceApi.getBreakdownPriorityEscalation(),
  });
  const priorityByBreakdown = new Map((priorityEscalation?.assessments ?? []).map((assessment) => [assessment.breakdown_id, assessment]));

  const createBreakdown = useMutation({
    mutationFn: (data: object) => maintenanceApi.createBreakdown(data),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["maint-breakdowns"] }); qc.invalidateQueries({ queryKey: ["maint-downtime-capacity-impact"] }); qc.invalidateQueries({ queryKey: ["maint-breakdown-priority-escalation"] }); qc.invalidateQueries({ queryKey: ["maint-assets"] }); setShowNew(false); },
  });

  const resolveBreakdown = useMutation({
    mutationFn: ({ id, data }: { id: string; data: object }) => maintenanceApi.resolveBreakdown(id, data),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["maint-breakdowns"] }); qc.invalidateQueries({ queryKey: ["maint-downtime-capacity-impact"] }); qc.invalidateQueries({ queryKey: ["maint-breakdown-priority-escalation"] }); qc.invalidateQueries({ queryKey: ["maint-assets"] }); setResolving(null); },
  });

  const filtered = filterStatus === "ALL" ? breakdowns : breakdowns.filter((b) => b.status === filterStatus);

  const totalDowntime = filtered.reduce((s, b) => s + (b.downtime_minutes || 0), 0);

  return (
    <RequirePermission permission="maintenance.view">
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Breakdown Records</h1>
          <p className="text-sm text-gray-500 mt-1">Equipment failures, downtime logging and resolution</p>
        </div>
        <Button onClick={() => setShowNew(true)}>Log Breakdown</Button>
      </div>

      {/* Status filter */}
      <div className="flex items-center gap-3">
        <div className="flex gap-2">
          {(["ALL", "OPEN", "IN_REPAIR", "RESOLVED"] as const).map((s) => {
            const count = s === "ALL" ? breakdowns.length : breakdowns.filter((b) => b.status === s).length;
            return (
              <button
                key={s}
                onClick={() => setFilterStatus(s)}
                className={`px-3 py-1.5 rounded text-xs font-medium transition-colors ${
                  filterStatus === s ? "bg-indigo-600 text-white" : "bg-white border text-gray-600 hover:border-indigo-300"
                }`}
              >
                {s} ({count})
              </button>
            );
          })}
        </div>
        {filtered.length > 0 && (
          <span className="ml-4 text-sm text-gray-500">Total downtime: <span className="font-semibold text-gray-800">{totalDowntime.toLocaleString()} min ({(totalDowntime / 60).toFixed(1)} hrs)</span></span>
        )}
      </div>

      <section className="rounded-lg border bg-indigo-50 p-4 space-y-3">
        <div className="flex flex-wrap items-baseline justify-between gap-2">
          <div>
            <h2 className="font-semibold text-indigo-950">Scheduled Production Capacity at Risk</h2>
            {capacityImpact && <p className="text-xs text-indigo-800">UTC report window: {capacityImpact.date_from} – {capacityImpact.date_to}; snapshot {new Date(capacityImpact.as_of).toLocaleString()}</p>}
          </div>
          {capacityImpact && <p className="text-sm font-semibold text-indigo-950">{capacityImpact.total_schedule_minutes_at_risk.toLocaleString()} scheduled minutes</p>}
        </div>
        {capacityImpactLoading && <p className="text-sm text-indigo-800">Loading downtime impact…</p>}
        {capacityImpactError && <p className="text-sm text-amber-800">Capacity impact is unavailable for your current access.</p>}
        {capacityImpact?.data_notes.map((note) => <p key={note} className="text-xs text-indigo-800">{note}</p>)}
        {capacityImpact && capacityImpact.impacts.length > 0 && (
          <div className="overflow-x-auto rounded border bg-white">
            <table className="w-full text-xs">
              <thead><tr className="border-b bg-gray-50 text-left uppercase text-gray-500">
                <th className="px-3 py-2">Maintenance Record</th><th className="px-3 py-2">Asset / Work Center</th><th className="px-3 py-2">Interval</th><th className="px-3 py-2">Schedule Minutes</th><th className="px-3 py-2">Production Orders at Risk</th>
              </tr></thead>
              <tbody className="divide-y">
                {capacityImpact.impacts.map((impact) => (
                  <tr key={`${impact.source_type}-${impact.source_id}`}>
                    <td className="px-3 py-2">{impact.source_type === "BREAKDOWN" ? "Breakdown" : "PM"} {impact.source_number}<div className="text-gray-500">{impact.status}{impact.ongoing ? " · open" : ""}</div></td>
                    <td className="px-3 py-2">{impact.asset_no} — {impact.asset_name}<div className="text-gray-500">Work center: {impact.work_center_id || "not linked"}</div></td>
                    <td className="px-3 py-2">{new Date(impact.start_time).toLocaleString()} – {impact.end_time ? new Date(impact.end_time).toLocaleString() : `observed through ${impact.observed_through ? new Date(impact.observed_through).toLocaleString() : "snapshot"}`}</td>
                    <td className="px-3 py-2">{impact.unavailable_reason ? <span className="text-amber-700">Unknown: {impact.unavailable_reason}</span> : `${impact.schedule_minutes_at_risk.toLocaleString()} min`}</td>
                    <td className="px-3 py-2">{impact.affected_production_order_ids.length ? impact.affected_production_order_ids.join(", ") : impact.unavailable_reason ? "Not calculated" : "None in active schedule"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
        {capacityImpact && capacityImpact.impacts.length === 0 && <p className="text-sm text-indigo-800">No maintenance intervals intersect active scheduled production in this report window.</p>}
      </section>

      <section className="rounded-lg border bg-amber-50 p-4 space-y-2">
        <div className="flex flex-wrap items-baseline justify-between gap-2">
          <div>
            <h2 className="font-semibold text-amber-950">Breakdown Priority & Escalation Review</h2>
            <p className="text-xs text-amber-900">Virtual demo policy {priorityEscalation?.policy_version || "virtual-demo-v1"}: Critical/P1 now, High/P2 4h, Medium/P3 24h, Low/P4 72h.</p>
          </div>
          {priorityEscalation && <p className="text-xs text-amber-900">Snapshot {new Date(priorityEscalation.as_of).toLocaleString()}</p>}
        </div>
        <p className="text-xs text-amber-900">These are illustrative software defaults, not approved factory SLAs or staff assignments. The report does not send alerts or assign people.</p>
        {priorityLoading && <p className="text-sm text-amber-800">Calculating breakdown priority…</p>}
        {priorityError && <p className="text-sm text-amber-800">Priority review is unavailable for your current access.</p>}
        {priorityEscalation?.data_notes.map((note) => <p key={note} className="text-xs text-amber-800">{note}</p>)}
      </section>

      <div className="bg-white rounded-lg border overflow-x-auto">
        {isLoading ? (
          <p className="px-5 py-8 text-center text-gray-400">Loading…</p>
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b bg-gray-50 text-xs text-gray-500 uppercase">
                <th className="px-5 py-2 text-left">Breakdown No</th>
                <th className="px-5 py-2 text-left">Asset</th>
                <th className="px-5 py-2 text-left">Reason</th>
                <th className="px-5 py-2 text-left">Severity</th>
                <th className="px-5 py-2 text-left">Start</th>
                <th className="px-5 py-2 text-left">End</th>
                <th className="px-5 py-2 text-right">Downtime</th>
                <th className="px-5 py-2 text-left">Priority</th>
                <th className="px-5 py-2 text-left">Escalation</th>
                <th className="px-5 py-2 text-left">Status</th>
                <th className="px-5 py-2" />
              </tr>
            </thead>
            <tbody className="divide-y">
              {filtered.map((bd) => {
                const assessment = priorityByBreakdown.get(bd.id);
                return (
                <tr key={bd.id} className="hover:bg-gray-50">
                  <td className="px-5 py-3 font-mono text-xs font-semibold text-indigo-700">{bd.breakdown_no}</td>
                  <td className="px-5 py-3">
                    <p className="font-medium text-gray-900">{bd.asset_name || "—"}</p>
                    <p className="text-xs text-gray-400">{bd.asset_no}</p>
                  </td>
                  <td className="px-5 py-3 text-gray-700 max-w-xs">
                    <div className="truncate">{bd.reason}</div>
                    {bd.reason_code && <div className="text-xs text-gray-500">{downtimeReasonCodes.find((item) => item.code === bd.reason_code)?.label || bd.reason_code}</div>}
                  </td>
                  <td className="px-5 py-3"><Badge label={bd.severity} variant={severityBadge(bd.severity)} /></td>
                  <td className="px-5 py-3 text-gray-600 text-xs">{new Date(bd.start_time).toLocaleString()}</td>
                  <td className="px-5 py-3 text-gray-500 text-xs">{bd.end_time ? new Date(bd.end_time).toLocaleString() : "—"}</td>
                  <td className="px-5 py-3 text-right font-semibold">{bd.downtime_minutes != null ? `${bd.downtime_minutes} min` : "—"}</td>
                  <td className="px-5 py-3">{assessment?.priority || (bd.status === "RESOLVED" ? "Closed" : "—")}</td>
                  <td className={`px-5 py-3 text-xs ${assessment?.state === "ESCALATE_NOW" ? "font-semibold text-red-700" : assessment?.state === "DATA_INCOMPLETE" ? "text-amber-700" : "text-gray-600"}`}>
                    {assessment ? (
                      <span title={assessment.recommended_action}>
                        {assessment.state.replaceAll("_", " ")}{assessment.minutes_until_escalation != null ? ` · ${assessment.minutes_until_escalation} min left` : ""}
                      </span>
                    ) : bd.status === "RESOLVED" ? "Resolved" : "Unavailable"}
                  </td>
                  <td className="px-5 py-3"><Badge label={bd.status} variant={statusBadge(bd.status)} /></td>
                  <td className="px-5 py-3">
                    {bd.status !== "RESOLVED" && (
                      <button className="text-xs text-green-600 hover:underline" onClick={() => setResolving(bd)}>Resolve</button>
                    )}
                  </td>
                </tr>
                );
              })}
              {filtered.length === 0 && (
                <tr><td colSpan={11} className="px-5 py-8 text-center text-gray-400">No breakdowns</td></tr>
              )}
            </tbody>
          </table>
        )}
      </div>

      {showNew && (
        <NewBreakdownModal
          assets={assets}
          reasonCodes={downtimeReasonCodes}
          onClose={() => setShowNew(false)}
          onSubmit={(d) => createBreakdown.mutate(d)}
          loading={createBreakdown.isPending}
        />
      )}

      {resolving && (
        <ResolveModal
          bd={resolving}
          onClose={() => setResolving(null)}
          onSubmit={(d) => resolveBreakdown.mutate({ id: resolving.id, data: d })}
          loading={resolveBreakdown.isPending}
        />
      )}
    </div>
    </RequirePermission>
  );
}

function NewBreakdownModal({ assets, reasonCodes, onClose, onSubmit, loading }: { assets: { id: string; name: string; asset_no: string }[]; reasonCodes: DowntimeReasonCode[]; onClose: () => void; onSubmit: (d: object) => void; loading: boolean }) {
  const now = new Date().toISOString().slice(0, 16);
  const [form, setForm] = useState({ asset_id: "", start_time: now, reason: "", reason_code: "", severity: "MEDIUM", production_order_id: "" });
  const set = (k: string, v: string) => setForm((f) => ({ ...f, [k]: v }));
  const categories = reasonCodes.filter((reasonCode) => reasonCode.parent_code == null);

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
      <div className="bg-white rounded-xl shadow-xl w-full max-w-md p-6 space-y-4">
        <h2 className="font-semibold text-lg">Log Breakdown</h2>
        <div className="space-y-3">
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Asset</label>
            <select className="w-full border rounded px-3 py-2 text-sm" value={form.asset_id} onChange={(e) => set("asset_id", e.target.value)}>
              <option value="">Select asset…</option>
              {assets.map((a) => <option key={a.id} value={a.id}>{a.asset_no} — {a.name}</option>)}
            </select>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">Start Time</label>
              <input type="datetime-local" className="w-full border rounded px-3 py-2 text-sm" value={form.start_time} onChange={(e) => set("start_time", e.target.value)} />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">Severity</label>
              <select className="w-full border rounded px-3 py-2 text-sm" value={form.severity} onChange={(e) => set("severity", e.target.value)}>
                <option value="LOW">Low</option>
                <option value="MEDIUM">Medium</option>
                <option value="HIGH">High</option>
                <option value="CRITICAL">Critical</option>
              </select>
            </div>
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Reason / Description</label>
            <textarea className="w-full border rounded px-3 py-2 text-sm" rows={2} value={form.reason} onChange={(e) => set("reason", e.target.value)} />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Reason Code *</label>
            <select required className="w-full border rounded px-3 py-2 text-sm" value={form.reason_code} onChange={(e) => set("reason_code", e.target.value)}>
              <option value="">Select reason code…</option>
              {categories.map((category) => (
                <optgroup key={category.code} label={category.label}>
                  {reasonCodes.filter((reasonCode) => reasonCode.parent_code === category.code && reasonCode.is_selectable).map((reasonCode) => (
                    <option key={reasonCode.code} value={reasonCode.code}>{reasonCode.label}</option>
                  ))}
                </optgroup>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Production Order ID (optional)</label>
            <input className="w-full border rounded px-3 py-2 text-sm font-mono" placeholder="UUID" value={form.production_order_id} onChange={(e) => set("production_order_id", e.target.value)} />
          </div>
        </div>
        <div className="flex gap-2 justify-end">
          <Button variant="secondary" onClick={onClose}>Cancel</Button>
          <Button loading={loading} disabled={loading || !form.reason_code} onClick={() => onSubmit({
            ...form,
            start_time: new Date(form.start_time).toISOString(),
            reason_code: form.reason_code || undefined,
            production_order_id: form.production_order_id || undefined,
          })}>Log</Button>
        </div>
      </div>
    </div>
  );
}

function ResolveModal({ bd, onClose, onSubmit, loading }: { bd: BreakdownRecord; onClose: () => void; onSubmit: (d: object) => void; loading: boolean }) {
  const now = new Date().toISOString().slice(0, 16);
  const [form, setForm] = useState({ end_time: now, root_cause: "", corrective_action: "" });
  const set = (k: string, v: string) => setForm((f) => ({ ...f, [k]: v }));

  const endDt = new Date(form.end_time);
  const startDt = new Date(bd.start_time);
  const downtimeMin = endDt > startDt ? Math.round((endDt.getTime() - startDt.getTime()) / 60000) : 0;

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
      <div className="bg-white rounded-xl shadow-xl w-full max-w-md p-6 space-y-4">
        <div>
          <h2 className="font-semibold text-lg">Resolve Breakdown</h2>
          <p className="text-xs text-gray-500 mt-1">{bd.breakdown_no} — {bd.asset_name}</p>
        </div>
        <div className="space-y-3">
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">End Time</label>
            <input type="datetime-local" className="w-full border rounded px-3 py-2 text-sm" value={form.end_time} onChange={(e) => set("end_time", e.target.value)} />
            {downtimeMin > 0 && <p className="text-xs text-gray-500 mt-1">Downtime: {downtimeMin} min ({(downtimeMin / 60).toFixed(1)} hrs)</p>}
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Root Cause</label>
            <textarea className="w-full border rounded px-3 py-2 text-sm" rows={2} value={form.root_cause} onChange={(e) => set("root_cause", e.target.value)} />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Corrective Action Taken</label>
            <textarea className="w-full border rounded px-3 py-2 text-sm" rows={2} value={form.corrective_action} onChange={(e) => set("corrective_action", e.target.value)} />
          </div>
        </div>
        <div className="flex gap-2 justify-end">
          <Button variant="secondary" onClick={onClose}>Cancel</Button>
          <Button loading={loading} onClick={() => onSubmit({
            end_time: new Date(form.end_time).toISOString(),
            downtime_minutes: downtimeMin || undefined,
            root_cause: form.root_cause || undefined,
            corrective_action: form.corrective_action || undefined,
          })}>Resolve</Button>
        </div>
      </div>
    </div>
  );
}
