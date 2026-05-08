"use client";
import { useEffect, useState } from "react";
import { wmsApi, ReplenishmentTask, ReplenishmentStatus } from "@/lib/wms";

const STATUS_COLORS: Record<ReplenishmentStatus, string> = {
  PENDING: "bg-amber-100 text-amber-700",
  IN_PROGRESS: "bg-blue-100 text-blue-700",
  COMPLETED: "bg-green-100 text-green-700",
  CANCELLED: "bg-gray-100 text-gray-500",
};

const BLANK = {
  task_no: "", warehouse_id: "", location_id: "", product_id: "", material_id: "",
  current_qty: "", min_qty: "", requested_qty: "", unit: "PCS",
  assigned_to_id: "", notes: "",
};

export default function ReplenishmentPage() {
  const [tasks, setTasks] = useState<ReplenishmentTask[]>([]);
  const [loading, setLoading] = useState(true);
  const [filterStatus, setFilterStatus] = useState<ReplenishmentStatus | "">("");
  const [showCreate, setShowCreate] = useState(false);
  const [form, setForm] = useState({ ...BLANK });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  const load = async () => {
    setLoading(true);
    try {
      const data = await wmsApi.listReplenishmentTasks(filterStatus ? { status: filterStatus } : undefined);
      setTasks(data);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, [filterStatus]);

  const create = async () => {
    if (!form.task_no || !form.warehouse_id || !form.location_id || !form.requested_qty || !form.min_qty) {
      setError("Task No., Warehouse, Location, Min Qty, Requested Qty required"); return;
    }
    setSaving(true); setError("");
    try {
      await wmsApi.createReplenishmentTask({
        task_no: form.task_no,
        warehouse_id: form.warehouse_id,
        location_id: form.location_id,
        product_id: form.product_id || null,
        material_id: form.material_id || null,
        current_qty: parseFloat(form.current_qty) || 0,
        min_qty: parseFloat(form.min_qty),
        requested_qty: parseFloat(form.requested_qty),
        unit: form.unit,
        assigned_to_id: form.assigned_to_id || null,
        notes: form.notes || null,
      });
      setShowCreate(false);
      setForm({ ...BLANK });
      await load();
    } catch {
      setError("Failed to create task");
    } finally {
      setSaving(false);
    }
  };

  const advance = async (task: ReplenishmentTask) => {
    const next: Record<string, ReplenishmentStatus> = {
      PENDING: "IN_PROGRESS",
      IN_PROGRESS: "COMPLETED",
    };
    const nextStatus = next[task.status];
    if (!nextStatus) return;
    const updates: Record<string, unknown> = { status: nextStatus };
    if (nextStatus === "COMPLETED") updates.fulfilled_qty = task.requested_qty;
    await wmsApi.updateReplenishmentTask(task.id, updates);
    await load();
  };

  return (
    <div className="p-6 space-y-5">
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div>
          <h1 className="text-xl font-bold text-gray-900">Bin Replenishment</h1>
          <p className="text-xs text-gray-500 mt-0.5">
            Replenishment tasks triggered when bin stock falls below minimum level.
          </p>
        </div>
        <button onClick={() => { setShowCreate(true); setError(""); }}
          className="rounded bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700">
          + New Task
        </button>
      </div>

      <div className="bg-amber-50 border border-amber-100 rounded-lg px-4 py-3">
        <p className="text-xs text-amber-700 font-medium mb-1">Automatic Replenishment</p>
        <p className="text-xs text-amber-600">
          Set <code className="bg-amber-100 px-1 rounded">min_qty</code> and <code className="bg-amber-100 px-1 rounded">max_qty</code> on Storage Locations.
          When stock at a location drops below min_qty, a replenishment task is created automatically
          by the warehouse operations engine.
        </p>
      </div>

      <div className="flex gap-2 flex-wrap">
        {(["", "PENDING", "IN_PROGRESS", "COMPLETED", "CANCELLED"] as const).map(s => (
          <button key={s}
            onClick={() => setFilterStatus(s as ReplenishmentStatus | "")}
            className={`rounded-full px-3 py-1 text-xs font-medium border transition-colors ${
              filterStatus === s
                ? "bg-blue-600 text-white border-blue-600"
                : "bg-white text-gray-600 border-gray-300 hover:border-blue-400"
            }`}>
            {s || "All"}
          </button>
        ))}
        <span className="text-xs text-gray-500 self-center">{tasks.length} tasks</span>
      </div>

      {loading ? (
        <p className="text-sm text-gray-500">Loading…</p>
      ) : tasks.length === 0 ? (
        <div className="bg-white border rounded-lg p-10 text-center text-gray-400">
          <p className="text-2xl mb-2">🔄</p>
          <p className="text-sm">No replenishment tasks.</p>
        </div>
      ) : (
        <div className="bg-white border rounded-lg shadow-sm overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 border-b">
              <tr>
                {["Task No.", "Location", "Item", "Current", "Min", "Requested", "Fulfilled", "Status", "Actions"].map(h => (
                  <th key={h} className="px-4 py-2 text-left text-xs font-semibold text-gray-600">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y">
              {tasks.map(t => {
                const fillPct = t.requested_qty > 0 ? Math.min(Number(t.fulfilled_qty) / Number(t.requested_qty) * 100, 100) : 0;
                return (
                  <tr key={t.id} className={`hover:bg-gray-50 ${t.status === "CANCELLED" ? "opacity-60" : ""}`}>
                    <td className="px-4 py-3 font-mono text-xs text-gray-600">{t.task_no}</td>
                    <td className="px-4 py-3 text-xs">
                      <span className="bg-gray-100 rounded px-1.5 py-0.5">{t.location_code ?? "—"}</span>
                    </td>
                    <td className="px-4 py-3 text-xs text-gray-700">{t.product_name ?? t.product_id?.slice(0,8) ?? "Material"}</td>
                    <td className="px-4 py-3 text-xs font-semibold text-red-700">{Number(t.current_qty).toLocaleString()}</td>
                    <td className="px-4 py-3 text-xs text-amber-700">{Number(t.min_qty).toLocaleString()}</td>
                    <td className="px-4 py-3 text-xs font-semibold">{Number(t.requested_qty).toLocaleString()} {t.unit}</td>
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-2">
                        <div className="w-16 h-1.5 rounded-full bg-gray-200">
                          <div className="h-1.5 rounded-full bg-green-500" style={{ width: `${fillPct}%` }} />
                        </div>
                        <span className="text-xs text-gray-600">{Number(t.fulfilled_qty).toLocaleString()}</span>
                      </div>
                    </td>
                    <td className="px-4 py-3">
                      <span className={`text-xs rounded-full px-2 py-0.5 ${STATUS_COLORS[t.status]}`}>
                        {t.status.replace("_", " ")}
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      {(t.status === "PENDING" || t.status === "IN_PROGRESS") && (
                        <button onClick={() => advance(t)}
                          className="text-xs text-blue-600 hover:underline">
                          {t.status === "PENDING" ? "Start" : "Complete"}
                        </button>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}

      {showCreate && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-xl shadow-2xl w-full max-w-md max-h-[90vh] overflow-y-auto">
            <div className="px-6 py-4 border-b flex items-center justify-between">
              <h2 className="text-base font-semibold">New Replenishment Task</h2>
              <button onClick={() => setShowCreate(false)} className="text-gray-400 text-xl">×</button>
            </div>
            <div className="p-6 space-y-3">
              {error && <p className="text-xs text-red-500 bg-red-50 border border-red-200 rounded px-3 py-2">{error}</p>}
              <div className="grid grid-cols-2 gap-3">
                {[
                  { label: "Task No. *", key: "task_no", placeholder: "RPL-001", col: 2 },
                  { label: "Warehouse ID *", key: "warehouse_id", placeholder: "UUID", col: 2 },
                  { label: "Location ID *", key: "location_id", placeholder: "UUID", col: 2 },
                  { label: "Product ID (or Material)", key: "product_id", placeholder: "UUID", col: 1 },
                  { label: "Material ID (or Product)", key: "material_id", placeholder: "UUID", col: 1 },
                  { label: "Current Qty", key: "current_qty", type: "number", placeholder: "0", col: 1 },
                  { label: "Min Qty *", key: "min_qty", type: "number", placeholder: "0", col: 1 },
                  { label: "Requested Qty *", key: "requested_qty", type: "number", placeholder: "0", col: 1 },
                  { label: "Unit", key: "unit", placeholder: "PCS", col: 1 },
                  { label: "Notes", key: "notes", placeholder: "", col: 2 },
                ].map(f => (
                  <div key={f.key} className={f.col === 2 ? "col-span-2" : ""}>
                    <label className="block text-xs font-medium text-gray-600 mb-1">{f.label}</label>
                    <input type={f.type ?? "text"} placeholder={f.placeholder}
                      value={(form as Record<string, string>)[f.key]}
                      onChange={e => setForm(prev => ({ ...prev, [f.key]: e.target.value }))}
                      className="w-full border rounded px-3 py-2 text-sm focus:ring-1 focus:ring-blue-500 outline-none"
                    />
                  </div>
                ))}
              </div>
            </div>
            <div className="px-6 pb-5 flex gap-3">
              <button onClick={create} disabled={saving}
                className="flex-1 rounded bg-blue-600 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50">
                {saving ? "Creating…" : "Create Task"}
              </button>
              <button onClick={() => setShowCreate(false)}
                className="flex-1 rounded border py-2 text-sm text-gray-600 hover:bg-gray-50">
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
