"use client";
import { useCallback, useEffect, useState } from "react";
import { shelfLifeApi, BulkHoldRecord } from "@/lib/shelfLife";

export default function BulkHoldMonitorPage() {
  const [holds, setHolds] = useState<BulkHoldRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [showCreate, setShowCreate] = useState(false);
  const [saving, setSaving] = useState(false);
  const [refreshing, setRefreshing] = useState(false);
  const [activeOnly, setActiveOnly] = useState(true);

  const [form, setForm] = useState({
    material_id: "", warehouse_id: "", lot_id: "",
    location_ref: "", max_hold_hours: "", notes: "",
  });

  const load = useCallback((ao: boolean) => {
    setLoading(true);
    shelfLifeApi.listBulkHolds(ao).then(setHolds).catch(console.error).finally(() => setLoading(false));
  }, []);

  useEffect(() => { load(activeOnly); }, [activeOnly, load]);

  const handleRefresh = async () => {
    setRefreshing(true);
    await shelfLifeApi.refreshBulkHolds();
    load(activeOnly);
    setRefreshing(false);
  };

  const handleCreate = async () => {
    if (!form.max_hold_hours) return;
    setSaving(true);
    try {
      await shelfLifeApi.createBulkHold({
        lot_id: form.lot_id || undefined,
        material_id: form.material_id || undefined,
        warehouse_id: form.warehouse_id || undefined,
        location_ref: form.location_ref || undefined,
        creation_time: new Date().toISOString(),
        max_hold_hours: form.max_hold_hours as any,
        notes: form.notes || undefined,
      } as any);
      setShowCreate(false);
      load(activeOnly);
    } finally { setSaving(false); }
  };

  const holdPct = (h: BulkHoldRecord) => parseFloat(h.pct_hold_used || "0");

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-gray-900">Bulk / Intermediate Hold-Age Monitor</h1>
          <p className="text-sm text-gray-500">Track max hold-age for premix, intermediate, bulk, and tank materials</p>
        </div>
        <div className="flex gap-2">
          <button onClick={handleRefresh} disabled={refreshing}
            className="px-4 py-2 text-sm border border-gray-200 rounded-lg hover:bg-gray-50 disabled:opacity-50">
            {refreshing ? "Refreshing…" : "Refresh All"}
          </button>
          <button onClick={() => setShowCreate(true)}
            className="px-4 py-2 text-sm bg-yellow-600 text-white rounded-lg hover:bg-yellow-700">
            + Register Hold
          </button>
        </div>
      </div>

      {/* Summary */}
      <div className="grid grid-cols-3 gap-4">
        {[
          { label: "Active Holds", value: holds.filter(h => !h.is_expired).length, color: "text-gray-800" },
          { label: "Near Limit (>80%)", value: holds.filter(h => h.is_near_limit && !h.is_expired).length, color: "text-amber-700" },
          { label: "Expired / Blocked", value: holds.filter(h => h.is_expired).length, color: "text-red-700" },
        ].map(s => (
          <div key={s.label} className="bg-white rounded-xl border border-gray-200 p-4 text-center">
            <p className={`text-2xl font-bold ${s.color}`}>{s.value}</p>
            <p className="text-xs text-gray-500 mt-0.5">{s.label}</p>
          </div>
        ))}
      </div>

      <div className="flex items-center gap-3">
        <label className="flex items-center gap-2 text-sm text-gray-600 cursor-pointer">
          <input type="checkbox" checked={activeOnly}
            onChange={e => setActiveOnly(e.target.checked)} />
          Active Only
        </label>
      </div>

      {/* Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
        {loading ? (
          <div className="col-span-3 text-center py-8 text-gray-400">Loading…</div>
        ) : holds.length === 0 ? (
          <div className="col-span-3 text-center py-8 text-gray-400">No bulk hold records</div>
        ) : holds.map(h => {
          const pct = holdPct(h);
          const borderCls = h.is_expired ? "border-red-300" : h.is_near_limit ? "border-amber-300" : "border-gray-200";
          const bgCls = h.is_expired ? "bg-red-50" : h.is_near_limit ? "bg-amber-50" : "bg-white";
          return (
            <div key={h.id} className={`rounded-xl border ${borderCls} ${bgCls} p-4 space-y-3`}>
              <div className="flex items-start justify-between">
                <div>
                  <p className="text-xs font-mono text-gray-500">{h.lot_id ? h.lot_id.slice(0,10) + "…" : "No Lot"}</p>
                  {h.location_ref && <p className="text-xs text-gray-400">{h.location_ref}</p>}
                </div>
                {h.is_expired ? (
                  <span className="px-2 py-0.5 bg-red-100 text-red-700 text-xs rounded font-semibold">EXPIRED</span>
                ) : h.is_near_limit ? (
                  <span className="px-2 py-0.5 bg-amber-100 text-amber-700 text-xs rounded">NEAR LIMIT</span>
                ) : (
                  <span className="px-2 py-0.5 bg-green-100 text-green-700 text-xs rounded">Active</span>
                )}
              </div>

              {/* Hold progress bar */}
              <div>
                <div className="flex justify-between text-xs mb-1">
                  <span className="text-gray-500">Hold Used</span>
                  <span className="font-semibold">{h.hours_used ? parseFloat(h.hours_used).toFixed(1) : 0}h / {parseFloat(h.max_hold_hours).toFixed(0)}h ({pct.toFixed(0)}%)</span>
                </div>
                <div className="w-full h-3 bg-gray-200 rounded-full overflow-hidden">
                  <div className={`h-full rounded-full transition-all ${pct >= 100 ? "bg-red-600" : pct >= 80 ? "bg-amber-500" : "bg-green-500"}`}
                    style={{ width: `${Math.min(100, pct)}%` }} />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-2 text-xs text-gray-500">
                <div>Created: <span className="text-gray-700">{new Date(h.creation_time).toLocaleString()}</span></div>
                <div>Expires: <span className={`font-medium ${h.is_expired ? "text-red-700" : "text-gray-700"}`}>{new Date(h.expiry_time).toLocaleString()}</span></div>
              </div>

              {h.notes && <p className="text-xs text-gray-400 italic">{h.notes}</p>}

              {h.is_expired && (
                <div className="flex gap-2">
                  <button className="flex-1 py-1 text-xs bg-red-600 text-white rounded hover:bg-red-700">Trigger QC Reassessment</button>
                </div>
              )}
            </div>
          );
        })}
      </div>

      {/* Create Modal */}
      {showCreate && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl shadow-xl w-full max-w-md p-6 space-y-4">
            <h3 className="font-semibold text-gray-800">Register Bulk Hold</h3>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="text-xs font-medium text-gray-600">Lot ID</label>
                <input className="mt-1 w-full border rounded-lg px-3 py-2 text-sm"
                  value={form.lot_id} onChange={e => setForm(f => ({ ...f, lot_id: e.target.value }))} />
              </div>
              <div>
                <label className="text-xs font-medium text-gray-600">Material ID</label>
                <input className="mt-1 w-full border rounded-lg px-3 py-2 text-sm"
                  value={form.material_id} onChange={e => setForm(f => ({ ...f, material_id: e.target.value }))} />
              </div>
              <div>
                <label className="text-xs font-medium text-gray-600">Warehouse ID</label>
                <input className="mt-1 w-full border rounded-lg px-3 py-2 text-sm"
                  value={form.warehouse_id} onChange={e => setForm(f => ({ ...f, warehouse_id: e.target.value }))} />
              </div>
              <div>
                <label className="text-xs font-medium text-gray-600">Location Ref</label>
                <input className="mt-1 w-full border rounded-lg px-3 py-2 text-sm" placeholder="Tank #, Room, etc."
                  value={form.location_ref} onChange={e => setForm(f => ({ ...f, location_ref: e.target.value }))} />
              </div>
              <div className="col-span-2">
                <label className="text-xs font-medium text-gray-600">Max Hold Hours *</label>
                <input type="number" className="mt-1 w-full border rounded-lg px-3 py-2 text-sm"
                  value={form.max_hold_hours} onChange={e => setForm(f => ({ ...f, max_hold_hours: e.target.value }))} />
              </div>
              <div className="col-span-2">
                <label className="text-xs font-medium text-gray-600">Notes</label>
                <input className="mt-1 w-full border rounded-lg px-3 py-2 text-sm"
                  value={form.notes} onChange={e => setForm(f => ({ ...f, notes: e.target.value }))} />
              </div>
            </div>
            <div className="flex gap-2 justify-end">
              <button onClick={() => setShowCreate(false)} className="px-4 py-2 text-sm border rounded-lg">Cancel</button>
              <button onClick={handleCreate} disabled={!form.max_hold_hours || saving}
                className="px-4 py-2 text-sm bg-yellow-600 text-white rounded-lg hover:bg-yellow-700 disabled:opacity-50">
                {saving ? "Registering…" : "Register Hold"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
