"use client";

import { useState, useEffect, useCallback } from "react";
import { putawayApi, PutawayTask, PutawayTaskStatus } from "@/lib/putaway";
import { wmsApi } from "@/lib/wms";
import Link from "next/link";

const STATUS_COLORS: Record<PutawayTaskStatus, string> = {
  PENDING: "bg-yellow-100 text-yellow-800",
  IN_PROGRESS: "bg-blue-100 text-blue-800",
  COMPLETED: "bg-green-100 text-green-800",
  CANCELLED: "bg-gray-100 text-gray-700",
};

export default function PutawayPage() {
  const [tasks, setTasks] = useState<PutawayTask[]>([]);
  const [warehouses, setWarehouses] = useState<any[]>([]);
  const [filterWarehouse, setFilterWarehouse] = useState("");
  const [filterStatus, setFilterStatus] = useState<PutawayTaskStatus | "">("");
  const [loading, setLoading] = useState(false);
  const [aiInsights, setAiInsights] = useState<string[]>([]);
  const [aiLoading, setAiLoading] = useState(false);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [createForm, setCreateForm] = useState({
    warehouse_id: "",
    quantity: "",
    receipt_ref: "",
    lot_number: "",
    notes: "",
  });
  const [createLoading, setCreateLoading] = useState(false);
  const [createError, setCreateError] = useState("");

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const data = await putawayApi.listTasks({
        warehouse_id: filterWarehouse || undefined,
        status: filterStatus || undefined,
      });
      setTasks(data);
    } finally {
      setLoading(false);
    }
  }, [filterWarehouse, filterStatus]);

  useEffect(() => {
    load();
  }, [load]);

  useEffect(() => {
    wmsApi.listZones().then((zones) => {
      const whMap: Record<string, { id: string; name: string }> = {};
      zones.forEach((z) => {
        if (z.warehouse_id) whMap[z.warehouse_id] = { id: z.warehouse_id, name: z.warehouse_name || z.warehouse_id };
      });
      setWarehouses(Object.values(whMap));
    });
  }, []);

  const loadEfficiency = async () => {
    if (!filterWarehouse) return;
    setAiLoading(true);
    try {
      const res = await putawayApi.efficiencyAnalyzer(filterWarehouse);
      setAiInsights(res.ai_insights || []);
    } finally {
      setAiLoading(false);
    }
  };

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    setCreateLoading(true);
    setCreateError("");
    try {
      await putawayApi.createTask({
        warehouse_id: createForm.warehouse_id,
        quantity: parseFloat(createForm.quantity),
        receipt_ref: createForm.receipt_ref || undefined,
        lot_number: createForm.lot_number || undefined,
        notes: createForm.notes || undefined,
      });
      setShowCreateModal(false);
      setCreateForm({ warehouse_id: "", quantity: "", receipt_ref: "", lot_number: "", notes: "" });
      load();
    } catch (err: any) {
      setCreateError(err?.response?.data?.detail || "Failed to create task");
    } finally {
      setCreateLoading(false);
    }
  };

  const pending = tasks.filter((t) => t.status === "PENDING").length;
  const inProgress = tasks.filter((t) => t.status === "IN_PROGRESS").length;
  const completed = tasks.filter((t) => t.status === "COMPLETED").length;

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Putaway Tasks</h1>
          <p className="text-sm text-gray-500 mt-1">Manage warehouse putaway operations</p>
        </div>
        <div className="flex gap-2">
          <Link
            href="/dashboard/putaway/rules"
            className="px-4 py-2 text-sm border border-gray-300 rounded-lg hover:bg-gray-50"
          >
            Putaway Rules
          </Link>
          <button
            onClick={() => setShowCreateModal(true)}
            className="px-4 py-2 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700"
          >
            + New Task
          </button>
        </div>
      </div>

      {/* KPI Row */}
      <div className="grid grid-cols-3 gap-4">
        {[
          { label: "Pending", value: pending, color: "text-yellow-600" },
          { label: "In Progress", value: inProgress, color: "text-blue-600" },
          { label: "Completed", value: completed, color: "text-green-600" },
        ].map((s) => (
          <div key={s.label} className="bg-white rounded-lg border p-4">
            <p className="text-xs text-gray-500">{s.label}</p>
            <p className={`text-3xl font-bold mt-1 ${s.color}`}>{s.value}</p>
          </div>
        ))}
      </div>

      {/* Filters */}
      <div className="flex gap-3 flex-wrap">
        <select
          value={filterWarehouse}
          onChange={(e) => setFilterWarehouse(e.target.value)}
          className="border rounded-lg px-3 py-2 text-sm"
        >
          <option value="">All Warehouses</option>
          {warehouses.map((w) => (
            <option key={w.id} value={w.id}>{w.name}</option>
          ))}
        </select>
        <select
          value={filterStatus}
          onChange={(e) => setFilterStatus(e.target.value as PutawayTaskStatus | "")}
          className="border rounded-lg px-3 py-2 text-sm"
        >
          <option value="">All Statuses</option>
          {(["PENDING", "IN_PROGRESS", "COMPLETED", "CANCELLED"] as PutawayTaskStatus[]).map((s) => (
            <option key={s} value={s}>{s}</option>
          ))}
        </select>
        {filterWarehouse && (
          <button
            onClick={loadEfficiency}
            disabled={aiLoading}
            className="px-3 py-2 text-sm bg-purple-600 text-white rounded-lg hover:bg-purple-700 disabled:opacity-50"
          >
            {aiLoading ? "Analyzing…" : "AI Efficiency Insights"}
          </button>
        )}
      </div>

      {/* AI Insights */}
      {aiInsights.length > 0 && (
        <div className="bg-purple-50 border border-purple-200 rounded-lg p-4">
          <h3 className="text-sm font-semibold text-purple-800 mb-2">AI Efficiency Analysis</h3>
          <ul className="space-y-1">
            {aiInsights.map((i, idx) => (
              <li key={idx} className="text-sm text-purple-700">• {i}</li>
            ))}
          </ul>
        </div>
      )}

      {/* Task Table */}
      <div className="bg-white rounded-lg border overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-gray-50 text-gray-600 uppercase text-xs">
            <tr>
              <th className="px-4 py-3 text-left">Task No</th>
              <th className="px-4 py-3 text-left">Item</th>
              <th className="px-4 py-3 text-left">Qty</th>
              <th className="px-4 py-3 text-left">Suggested Location</th>
              <th className="px-4 py-3 text-left">Warehouse</th>
              <th className="px-4 py-3 text-left">Receipt Ref</th>
              <th className="px-4 py-3 text-left">Status</th>
              <th className="px-4 py-3 text-left">Action</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {loading ? (
              <tr>
                <td colSpan={8} className="px-4 py-8 text-center text-gray-400">Loading…</td>
              </tr>
            ) : tasks.length === 0 ? (
              <tr>
                <td colSpan={8} className="px-4 py-8 text-center text-gray-400">No putaway tasks found</td>
              </tr>
            ) : (
              tasks.map((task) => (
                <tr key={task.id} className="hover:bg-gray-50">
                  <td className="px-4 py-3 font-mono text-xs font-semibold">{task.task_no}</td>
                  <td className="px-4 py-3">
                    {task.product_name || task.material_name || "—"}
                    {task.lot_number && <span className="ml-1 text-xs text-gray-400">({task.lot_number})</span>}
                  </td>
                  <td className="px-4 py-3">{task.quantity}</td>
                  <td className="px-4 py-3 font-mono text-xs">
                    {task.suggested_location_code || <span className="text-gray-400">—</span>}
                  </td>
                  <td className="px-4 py-3 text-gray-600">{task.warehouse_name || "—"}</td>
                  <td className="px-4 py-3 text-gray-600 text-xs">{task.receipt_ref || "—"}</td>
                  <td className="px-4 py-3">
                    <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${STATUS_COLORS[task.status]}`}>
                      {task.status}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    {task.status === "PENDING" && (
                      <Link
                        href={`/dashboard/putaway/execute/${task.id}`}
                        className="text-blue-600 hover:underline text-xs"
                      >
                        Execute
                      </Link>
                    )}
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {/* Create Modal */}
      {showCreateModal && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl shadow-xl w-full max-w-md p-6">
            <h2 className="text-lg font-semibold mb-4">New Putaway Task</h2>
            <form onSubmit={handleCreate} className="space-y-4">
              <div>
                <label className="block text-sm font-medium mb-1">Warehouse *</label>
                <select
                  required
                  value={createForm.warehouse_id}
                  onChange={(e) => setCreateForm({ ...createForm, warehouse_id: e.target.value })}
                  className="w-full border rounded-lg px-3 py-2 text-sm"
                >
                  <option value="">Select warehouse…</option>
                  {warehouses.map((w) => (
                    <option key={w.id} value={w.id}>{w.name}</option>
                  ))}
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium mb-1">Quantity *</label>
                <input
                  required
                  type="number"
                  step="0.001"
                  value={createForm.quantity}
                  onChange={(e) => setCreateForm({ ...createForm, quantity: e.target.value })}
                  className="w-full border rounded-lg px-3 py-2 text-sm"
                />
              </div>
              <div>
                <label className="block text-sm font-medium mb-1">Receipt Reference</label>
                <input
                  value={createForm.receipt_ref}
                  onChange={(e) => setCreateForm({ ...createForm, receipt_ref: e.target.value })}
                  className="w-full border rounded-lg px-3 py-2 text-sm"
                  placeholder="e.g. GRN-001"
                />
              </div>
              <div>
                <label className="block text-sm font-medium mb-1">Lot Number</label>
                <input
                  value={createForm.lot_number}
                  onChange={(e) => setCreateForm({ ...createForm, lot_number: e.target.value })}
                  className="w-full border rounded-lg px-3 py-2 text-sm"
                />
              </div>
              <div>
                <label className="block text-sm font-medium mb-1">Notes</label>
                <textarea
                  value={createForm.notes}
                  onChange={(e) => setCreateForm({ ...createForm, notes: e.target.value })}
                  className="w-full border rounded-lg px-3 py-2 text-sm"
                  rows={2}
                />
              </div>
              {createError && <p className="text-red-600 text-sm">{createError}</p>}
              <div className="flex justify-end gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => setShowCreateModal(false)}
                  className="px-4 py-2 text-sm border rounded-lg hover:bg-gray-50"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={createLoading}
                  className="px-4 py-2 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
                >
                  {createLoading ? "Creating…" : "Create Task"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
