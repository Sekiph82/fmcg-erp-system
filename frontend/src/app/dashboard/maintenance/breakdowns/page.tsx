"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { maintenanceApi, BreakdownRecord, BreakdownStatus, BreakdownSeverity } from "@/lib/maintenance";
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

  const createBreakdown = useMutation({
    mutationFn: (data: object) => maintenanceApi.createBreakdown(data),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["maint-breakdowns"] }); qc.invalidateQueries({ queryKey: ["maint-assets"] }); setShowNew(false); },
  });

  const resolveBreakdown = useMutation({
    mutationFn: ({ id, data }: { id: string; data: object }) => maintenanceApi.resolveBreakdown(id, data),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["maint-breakdowns"] }); qc.invalidateQueries({ queryKey: ["maint-assets"] }); setResolving(null); },
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
                <th className="px-5 py-2 text-left">Status</th>
                <th className="px-5 py-2" />
              </tr>
            </thead>
            <tbody className="divide-y">
              {filtered.map((bd) => (
                <tr key={bd.id} className="hover:bg-gray-50">
                  <td className="px-5 py-3 font-mono text-xs font-semibold text-indigo-700">{bd.breakdown_no}</td>
                  <td className="px-5 py-3">
                    <p className="font-medium text-gray-900">{bd.asset_name || "—"}</p>
                    <p className="text-xs text-gray-400">{bd.asset_no}</p>
                  </td>
                  <td className="px-5 py-3 text-gray-700 max-w-xs truncate">{bd.reason}</td>
                  <td className="px-5 py-3"><Badge label={bd.severity} variant={severityBadge(bd.severity)} /></td>
                  <td className="px-5 py-3 text-gray-600 text-xs">{new Date(bd.start_time).toLocaleString()}</td>
                  <td className="px-5 py-3 text-gray-500 text-xs">{bd.end_time ? new Date(bd.end_time).toLocaleString() : "—"}</td>
                  <td className="px-5 py-3 text-right font-semibold">{bd.downtime_minutes != null ? `${bd.downtime_minutes} min` : "—"}</td>
                  <td className="px-5 py-3"><Badge label={bd.status} variant={statusBadge(bd.status)} /></td>
                  <td className="px-5 py-3">
                    {bd.status !== "RESOLVED" && (
                      <button className="text-xs text-green-600 hover:underline" onClick={() => setResolving(bd)}>Resolve</button>
                    )}
                  </td>
                </tr>
              ))}
              {filtered.length === 0 && (
                <tr><td colSpan={9} className="px-5 py-8 text-center text-gray-400">No breakdowns</td></tr>
              )}
            </tbody>
          </table>
        )}
      </div>

      {showNew && (
        <NewBreakdownModal
          assets={assets}
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

function NewBreakdownModal({ assets, onClose, onSubmit, loading }: { assets: { id: string; name: string; asset_no: string }[]; onClose: () => void; onSubmit: (d: object) => void; loading: boolean }) {
  const now = new Date().toISOString().slice(0, 16);
  const [form, setForm] = useState({ asset_id: "", start_time: now, reason: "", severity: "MEDIUM", production_order_id: "" });
  const set = (k: string, v: string) => setForm((f) => ({ ...f, [k]: v }));

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
            <label className="block text-xs font-medium text-gray-600 mb-1">Production Order ID (optional)</label>
            <input className="w-full border rounded px-3 py-2 text-sm font-mono" placeholder="UUID" value={form.production_order_id} onChange={(e) => set("production_order_id", e.target.value)} />
          </div>
        </div>
        <div className="flex gap-2 justify-end">
          <Button variant="secondary" onClick={onClose}>Cancel</Button>
          <Button loading={loading} onClick={() => onSubmit({
            ...form,
            start_time: new Date(form.start_time).toISOString(),
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
