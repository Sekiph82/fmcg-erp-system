"use client";
import { useEffect, useState } from "react";
import { wmsApi, PickingTask, PickingTaskStatus } from "@/lib/wms";

const STATUS_COLORS: Record<PickingTaskStatus, string> = {
  PENDING: "bg-gray-100 text-gray-600",
  IN_PROGRESS: "bg-blue-100 text-blue-700",
  PICKED: "bg-green-100 text-green-700",
  PACKED: "bg-purple-100 text-purple-700",
  CANCELLED: "bg-red-100 text-red-500",
};

const BLANK = {
  task_no: "", warehouse_id: "", product_id: "", lot_id: "",
  from_location_id: "", requested_qty: "", unit: "PCS",
  assigned_to_id: "", fefo_enforced: true, notes: "",
};

export default function PickingTasksPage() {
  const [tasks, setTasks] = useState<PickingTask[]>([]);
  const [loading, setLoading] = useState(true);
  const [filterStatus, setFilterStatus] = useState<PickingTaskStatus | "">("");
  const [showCreate, setShowCreate] = useState(false);
  const [form, setForm] = useState({ ...BLANK });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  const load = async () => {
    setLoading(true);
    try {
      const data = await wmsApi.listPickingTasks(filterStatus ? { status: filterStatus } : undefined);
      setTasks(data);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, [filterStatus]);

  const create = async () => {
    if (!form.task_no || !form.warehouse_id || !form.product_id || !form.requested_qty) {
      setError("Task No., Warehouse ID, Product ID, Qty required"); return;
    }
    setSaving(true); setError("");
    try {
      await wmsApi.createPickingTask({
        task_no: form.task_no,
        warehouse_id: form.warehouse_id,
        product_id: form.product_id,
        lot_id: form.lot_id || null,
        from_location_id: form.from_location_id || null,
        requested_qty: parseFloat(form.requested_qty),
        unit: form.unit,
        assigned_to_id: form.assigned_to_id || null,
        fefo_enforced: form.fefo_enforced,
        notes: form.notes || null,
      });
      setShowCreate(false);
      setForm({ ...BLANK });
      await load();
    } catch {
      setError("Failed to create picking task");
    } finally {
      setSaving(false);
    }
  };

  const advance = async (task: PickingTask) => {
    const nextStatus: Record<string, PickingTaskStatus> = {
      PENDING: "IN_PROGRESS",
      IN_PROGRESS: "PICKED",
      PICKED: "PACKED",
    };
    const next = nextStatus[task.status];
    if (!next) return;
    const updates: Record<string, unknown> = { status: next };
    if (next === "PICKED") updates.picked_qty = task.requested_qty;
    await wmsApi.updatePickingTask(task.id, updates);
    await load();
  };

  const cancel = async (task: PickingTask) => {
    if (!confirm("Cancel this picking task?")) return;
    await wmsApi.updatePickingTask(task.id, { status: "CANCELLED" });
    await load();
  };

  const pending = tasks.filter(t => t.status === "PENDING").length;
  const inProgress = tasks.filter(t => t.status === "IN_PROGRESS").length;
  const picked = tasks.filter(t => t.status === "PICKED").length;

  return (
    <div className="p-4 md:p-6 space-y-4">
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div>
          <h1 className="text-xl font-bold text-gray-900">Picking Operations</h1>
          <p className="text-xs text-gray-500 mt-0.5">Warehouse pick tasks with FEFO enforcement.</p>
        </div>
        <button onClick={() => { setShowCreate(true); setError(""); }}
          className="rounded bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700">
          + New Task
        </button>
      </div>

      {/* KPIs */}
      <div className="grid grid-cols-3 gap-3">
        {[
          { label: "Pending", value: pending, color: "text-gray-700" },
          { label: "In Progress", value: inProgress, color: "text-blue-700" },
          { label: "Picked", value: picked, color: "text-green-700" },
        ].map(s => (
          <div key={s.label} className="bg-white border rounded-lg p-3 text-center shadow-sm">
            <p className="text-xs text-gray-500">{s.label}</p>
            <p className={`text-2xl font-bold ${s.color}`}>{s.value}</p>
          </div>
        ))}
      </div>

      <div className="flex gap-2 flex-wrap">
        {(["", "PENDING", "IN_PROGRESS", "PICKED", "PACKED", "CANCELLED"] as const).map(s => (
          <button
            key={s}
            onClick={() => setFilterStatus(s as PickingTaskStatus | "")}
            className={`rounded-full px-3 py-1 text-xs font-medium border transition-colors ${
              filterStatus === s
                ? "bg-blue-600 text-white border-blue-600"
                : "bg-white text-gray-600 border-gray-300 hover:border-blue-400"
            }`}
          >
            {s || "All"}
          </button>
        ))}
      </div>

      {loading ? (
        <p className="text-sm text-gray-500">Loading…</p>
      ) : tasks.length === 0 ? (
        <div className="bg-white border rounded-lg p-10 text-center text-gray-400">
          <p className="text-2xl mb-2">📦</p>
          <p className="text-sm">No picking tasks found.</p>
        </div>
      ) : (
        <div className="space-y-3">
          {tasks.map(task => (
            <div key={task.id} className={`bg-white border rounded-xl p-4 shadow-sm ${task.status === "CANCELLED" ? "opacity-60" : ""}`}>
              <div className="flex items-start justify-between gap-2">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className="font-mono text-xs text-gray-500">{task.task_no}</span>
                    <span className={`text-xs rounded-full px-2 py-0.5 ${STATUS_COLORS[task.status]}`}>
                      {task.status.replace("_", " ")}
                    </span>
                    {task.fefo_enforced && (
                      <span className="text-xs bg-amber-50 text-amber-600 rounded px-1.5 py-0.5">FEFO</span>
                    )}
                  </div>
                  <p className="text-sm font-semibold text-gray-800 mt-1">
                    {task.product_name ?? task.product_id.slice(0, 8)}
                  </p>
                  <div className="flex gap-3 text-xs text-gray-500 mt-0.5 flex-wrap">
                    <span>Qty: <strong className="text-gray-700">{task.requested_qty} {task.unit}</strong></span>
                    {task.picked_qty != null && (
                      <span>Picked: <strong className="text-green-700">{task.picked_qty}</strong></span>
                    )}
                    {task.from_location_code && <span>From: {task.from_location_code}</span>}
                    {task.lot_number && <span>Lot: {task.lot_number}</span>}
                    {task.assignee_name && <span>Assignee: {task.assignee_name}</span>}
                  </div>
                  {task.started_at && (
                    <p className="text-xs text-gray-400 mt-0.5">
                      Started: {new Date(task.started_at).toLocaleTimeString()}
                    </p>
                  )}
                </div>
                <div className="flex gap-2 flex-shrink-0">
                  {task.status !== "CANCELLED" && task.status !== "PACKED" && (
                    <button
                      onClick={() => advance(task)}
                      className="rounded-lg bg-blue-600 text-white text-xs px-3 py-2 hover:bg-blue-700"
                    >
                      {task.status === "PENDING" ? "Start" :
                       task.status === "IN_PROGRESS" ? "Mark Picked" :
                       task.status === "PICKED" ? "Mark Packed" : "→"}
                    </button>
                  )}
                  {(task.status === "PENDING" || task.status === "IN_PROGRESS") && (
                    <button
                      onClick={() => cancel(task)}
                      className="rounded-lg border border-red-200 text-red-500 text-xs px-3 py-2 hover:bg-red-50"
                    >
                      Cancel
                    </button>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {showCreate && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-xl shadow-2xl w-full max-w-md max-h-[90vh] overflow-y-auto">
            <div className="px-6 py-4 border-b flex items-center justify-between">
              <h2 className="text-base font-semibold">New Picking Task</h2>
              <button onClick={() => setShowCreate(false)} className="text-gray-400 hover:text-gray-600 text-xl">×</button>
            </div>
            <div className="p-6 space-y-3">
              {error && <p className="text-xs text-red-500 bg-red-50 border border-red-200 rounded px-3 py-2">{error}</p>}
              {[
                { label: "Task No. *", key: "task_no", placeholder: "PICK-001" },
                { label: "Warehouse ID *", key: "warehouse_id", placeholder: "UUID" },
                { label: "Product ID *", key: "product_id", placeholder: "UUID" },
                { label: "Requested Qty *", key: "requested_qty", type: "number", placeholder: "0" },
                { label: "Unit", key: "unit", placeholder: "PCS" },
                { label: "Lot ID (optional)", key: "lot_id", placeholder: "UUID" },
                { label: "From Location ID (optional)", key: "from_location_id", placeholder: "UUID" },
                { label: "Assign To User ID (optional)", key: "assigned_to_id", placeholder: "UUID" },
                { label: "Notes", key: "notes", placeholder: "" },
              ].map(f => (
                <div key={f.key}>
                  <label className="block text-xs font-medium text-gray-600 mb-1">{f.label}</label>
                  <input type={f.type ?? "text"} placeholder={f.placeholder}
                    value={(form as unknown as Record<string, string>)[f.key] ?? ""}
                    onChange={e => setForm(prev => ({ ...prev, [f.key]: e.target.value }))}
                    className="w-full border rounded px-3 py-2 text-sm focus:ring-1 focus:ring-blue-500 outline-none"
                  />
                </div>
              ))}
              <label className="flex items-center gap-2 text-sm text-gray-700 cursor-pointer">
                <input type="checkbox" checked={form.fefo_enforced}
                  onChange={e => setForm(prev => ({ ...prev, fefo_enforced: e.target.checked }))}
                  className="h-4 w-4 rounded border-gray-300 text-blue-600"
                />
                Enforce FEFO (pick earliest expiry first)
              </label>
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
