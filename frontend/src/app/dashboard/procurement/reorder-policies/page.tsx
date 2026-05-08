"use client";
import { useEffect, useState } from "react";
import { procurementApi, AutoReorderPolicy } from "@/lib/procurement";

const BLANK_FORM = {
  material_id: "", product_id: "", warehouse_id: "",
  reorder_point: "", reorder_quantity: "", max_stock_level: "",
  lead_time_days: "7", preferred_supplier_id: "",
  auto_create_pr: true, active_flag: true, notes: "",
};

export default function ReorderPoliciesPage() {
  const [policies, setPolicies] = useState<AutoReorderPolicy[]>([]);
  const [loading, setLoading] = useState(true);
  const [activeOnly, setActiveOnly] = useState(false);
  const [showModal, setShowModal] = useState(false);
  const [editId, setEditId] = useState<string | null>(null);
  const [form, setForm] = useState({ ...BLANK_FORM });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  const load = async () => {
    setLoading(true);
    try {
      const data = await procurementApi.listReorderPolicies({ active_only: activeOnly });
      setPolicies(data);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, [activeOnly]);

  const openCreate = () => { setForm({ ...BLANK_FORM }); setEditId(null); setError(""); setShowModal(true); };

  const openEdit = (p: AutoReorderPolicy) => {
    setForm({
      material_id: p.material_id ?? "",
      product_id: p.product_id ?? "",
      warehouse_id: p.warehouse_id ?? "",
      reorder_point: String(p.reorder_point),
      reorder_quantity: String(p.reorder_quantity),
      max_stock_level: p.max_stock_level != null ? String(p.max_stock_level) : "",
      lead_time_days: String(p.lead_time_days),
      preferred_supplier_id: p.preferred_supplier_id ?? "",
      auto_create_pr: p.auto_create_pr,
      active_flag: p.active_flag,
      notes: p.notes ?? "",
    });
    setEditId(p.id);
    setError("");
    setShowModal(true);
  };

  const save = async () => {
    if (!form.reorder_point || !form.reorder_quantity) {
      setError("Reorder point and quantity required"); return;
    }
    if (!form.material_id && !form.product_id) {
      setError("Set either Material ID or Product ID"); return;
    }
    setSaving(true); setError("");
    try {
      const payload = {
        material_id: form.material_id || null,
        product_id: form.product_id || null,
        warehouse_id: form.warehouse_id || null,
        reorder_point: parseFloat(form.reorder_point),
        reorder_quantity: parseFloat(form.reorder_quantity),
        max_stock_level: form.max_stock_level ? parseFloat(form.max_stock_level) : null,
        lead_time_days: parseInt(form.lead_time_days),
        preferred_supplier_id: form.preferred_supplier_id || null,
        auto_create_pr: form.auto_create_pr,
        active_flag: form.active_flag,
        notes: form.notes || null,
      };
      if (editId) {
        await procurementApi.updateReorderPolicy(editId, payload);
      } else {
        await procurementApi.createReorderPolicy(payload);
      }
      setShowModal(false);
      await load();
    } catch {
      setError("Failed to save policy");
    } finally {
      setSaving(false);
    }
  };

  const remove = async (p: AutoReorderPolicy) => {
    if (!confirm("Delete this reorder policy?")) return;
    await procurementApi.deleteReorderPolicy(p.id);
    await load();
  };

  const toggle = async (p: AutoReorderPolicy) => {
    await procurementApi.updateReorderPolicy(p.id, { active_flag: !p.active_flag });
    await load();
  };

  return (
    <div className="p-6 space-y-5">
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div>
          <h1 className="text-xl font-bold text-gray-900">Auto Reorder Policies</h1>
          <p className="text-xs text-gray-500 mt-0.5">
            Define reorder points and quantities per material/product. When stock falls below reorder point,
            a Purchase Requisition is auto-created.
          </p>
        </div>
        <button onClick={openCreate}
          className="rounded bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700">
          + New Policy
        </button>
      </div>

      <div className="bg-blue-50 border border-blue-100 rounded-lg px-4 py-3">
        <p className="text-xs text-blue-700 font-medium mb-1">How Auto Reorder Works</p>
        <p className="text-xs text-blue-600">
          The MRP engine checks stock levels against reorder points daily. When a material/product
          falls below its reorder point, the system auto-creates a Purchase Requisition for the
          configured reorder quantity from the preferred supplier.
          "Auto Create PR" must be enabled for automatic triggering.
        </p>
      </div>

      <div className="flex gap-3 items-center">
        <label className="flex items-center gap-2 text-sm text-gray-700 cursor-pointer">
          <input type="checkbox" checked={activeOnly}
            onChange={e => setActiveOnly(e.target.checked)}
            className="h-4 w-4 rounded border-gray-300 text-blue-600"
          />
          Active only
        </label>
        <span className="text-xs text-gray-500">{policies.length} policies</span>
      </div>

      {loading ? (
        <p className="text-sm text-gray-500">Loading…</p>
      ) : policies.length === 0 ? (
        <div className="bg-white border rounded-lg p-10 text-center text-gray-400">
          <p className="text-2xl mb-2">🔄</p>
          <p className="text-sm">No reorder policies defined.</p>
          <button onClick={openCreate} className="mt-3 text-xs text-blue-600 hover:underline">Create first policy →</button>
        </div>
      ) : (
        <div className="bg-white border rounded-lg shadow-sm overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 border-b">
              <tr>
                {["Item", "Warehouse", "Reorder Point", "Reorder Qty", "Max Stock", "Lead Time", "Supplier", "Auto PR", "Status", "Actions"].map(h => (
                  <th key={h} className="px-4 py-2 text-left text-xs font-semibold text-gray-600">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y">
              {policies.map(p => (
                <tr key={p.id} className={`hover:bg-gray-50 ${!p.active_flag ? "opacity-60" : ""}`}>
                  <td className="px-4 py-3 text-xs text-gray-700">
                    {p.material_id ? (
                      <span className="bg-blue-50 text-blue-600 rounded px-1.5 py-0.5">Material</span>
                    ) : (
                      <span className="bg-green-50 text-green-600 rounded px-1.5 py-0.5">Product</span>
                    )}
                    <span className="font-mono ml-1 text-gray-500">
                      {(p.material_id ?? p.product_id ?? "").slice(0, 8)}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-xs text-gray-500 font-mono">
                    {p.warehouse_id ? p.warehouse_id.slice(0, 8) : "Any"}
                  </td>
                  <td className="px-4 py-3 text-xs font-semibold text-amber-700">
                    {Number(p.reorder_point).toLocaleString()}
                  </td>
                  <td className="px-4 py-3 text-xs font-semibold text-blue-700">
                    {Number(p.reorder_quantity).toLocaleString()}
                  </td>
                  <td className="px-4 py-3 text-xs text-gray-600">
                    {p.max_stock_level != null ? Number(p.max_stock_level).toLocaleString() : "—"}
                  </td>
                  <td className="px-4 py-3 text-xs text-gray-600">{p.lead_time_days}d</td>
                  <td className="px-4 py-3 text-xs text-gray-600">
                    {p.preferred_supplier_name ?? (p.preferred_supplier_id ? p.preferred_supplier_id.slice(0,8) : "Any")}
                  </td>
                  <td className="px-4 py-3">
                    <span className={`text-xs rounded-full px-2 py-0.5 ${p.auto_create_pr ? "bg-green-100 text-green-700" : "bg-gray-100 text-gray-500"}`}>
                      {p.auto_create_pr ? "Yes" : "No"}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    <span className={`text-xs rounded-full px-2 py-0.5 ${p.active_flag ? "bg-green-100 text-green-700" : "bg-gray-100 text-gray-500"}`}>
                      {p.active_flag ? "active" : "disabled"}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex gap-2">
                      <button onClick={() => openEdit(p)} className="text-xs text-blue-600 hover:underline">Edit</button>
                      <button onClick={() => toggle(p)} className="text-xs text-yellow-600 hover:underline">
                        {p.active_flag ? "Disable" : "Enable"}
                      </button>
                      <button onClick={() => remove(p)} className="text-xs text-red-500 hover:underline">Delete</button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {showModal && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-xl shadow-2xl w-full max-w-lg max-h-[90vh] overflow-y-auto">
            <div className="px-6 py-4 border-b flex items-center justify-between">
              <h2 className="text-base font-semibold">{editId ? "Edit Policy" : "New Reorder Policy"}</h2>
              <button onClick={() => setShowModal(false)} className="text-gray-400 hover:text-gray-600 text-xl">×</button>
            </div>
            <div className="p-6 space-y-4">
              {error && <p className="text-xs text-red-500 bg-red-50 border border-red-200 rounded px-3 py-2">{error}</p>}

              <div className="bg-gray-50 border rounded p-3">
                <p className="text-xs font-semibold text-gray-600 mb-2">Item (set one)</p>
                <div className="grid grid-cols-2 gap-3">
                  {[
                    { label: "Material ID (UUID)", key: "material_id" },
                    { label: "Product ID (UUID)", key: "product_id" },
                  ].map(f => (
                    <div key={f.key}>
                      <label className="block text-xs text-gray-500 mb-1">{f.label}</label>
                      <input type="text" value={(form as unknown as Record<string, string>)[f.key]}
                        onChange={e => setForm(prev => ({ ...prev, [f.key]: e.target.value }))}
                        className="w-full border rounded px-3 py-2 text-sm focus:ring-1 focus:ring-blue-500 outline-none bg-white font-mono text-xs"
                        placeholder="Leave blank if using other"
                      />
                    </div>
                  ))}
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4">
                {[
                  { label: "Reorder Point *", key: "reorder_point", type: "number", placeholder: "100" },
                  { label: "Reorder Quantity *", key: "reorder_quantity", type: "number", placeholder: "500" },
                  { label: "Max Stock Level", key: "max_stock_level", type: "number", placeholder: "" },
                  { label: "Lead Time (days)", key: "lead_time_days", type: "number", placeholder: "7" },
                  { label: "Warehouse ID (optional)", key: "warehouse_id", placeholder: "UUID" },
                  { label: "Preferred Supplier ID (optional)", key: "preferred_supplier_id", placeholder: "UUID" },
                ].map(f => (
                  <div key={f.key}>
                    <label className="block text-xs font-medium text-gray-600 mb-1">{f.label}</label>
                    <input type={f.type ?? "text"} placeholder={f.placeholder}
                      value={(form as unknown as Record<string, string>)[f.key]}
                      onChange={e => setForm(prev => ({ ...prev, [f.key]: e.target.value }))}
                      className="w-full border rounded px-3 py-2 text-sm focus:ring-1 focus:ring-blue-500 outline-none"
                    />
                  </div>
                ))}
              </div>

              <div className="flex gap-6">
                <label className="flex items-center gap-2 text-sm text-gray-700 cursor-pointer">
                  <input type="checkbox" checked={form.auto_create_pr}
                    onChange={e => setForm(prev => ({ ...prev, auto_create_pr: e.target.checked }))}
                    className="h-4 w-4 rounded border-gray-300 text-blue-600"
                  />
                  Auto Create PR
                </label>
                <label className="flex items-center gap-2 text-sm text-gray-700 cursor-pointer">
                  <input type="checkbox" checked={form.active_flag}
                    onChange={e => setForm(prev => ({ ...prev, active_flag: e.target.checked }))}
                    className="h-4 w-4 rounded border-gray-300 text-blue-600"
                  />
                  Active
                </label>
              </div>

              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1">Notes</label>
                <textarea value={form.notes}
                  onChange={e => setForm(prev => ({ ...prev, notes: e.target.value }))}
                  rows={2} placeholder="Internal notes…"
                  className="w-full border rounded px-3 py-2 text-sm focus:ring-1 focus:ring-blue-500 outline-none resize-none"
                />
              </div>
            </div>
            <div className="px-6 pb-5 flex gap-3">
              <button onClick={save} disabled={saving}
                className="flex-1 rounded bg-blue-600 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50">
                {saving ? "Saving…" : editId ? "Update" : "Create Policy"}
              </button>
              <button onClick={() => setShowModal(false)}
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
