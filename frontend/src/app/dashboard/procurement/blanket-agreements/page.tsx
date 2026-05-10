"use client";
import { useCallback, useEffect, useState } from "react";
import { procurementApi, BlanketAgreement, BPAStatus } from "@/lib/procurement";

const STATUS_COLORS: Record<BPAStatus, string> = {
  ACTIVE: "bg-green-100 text-green-700",
  EXPIRED: "bg-gray-100 text-gray-500",
  CANCELLED: "bg-red-100 text-red-500",
};

const BLANK_FORM = {
  bpa_no: "", supplier_id: "", description: "",
  agreed_unit_price: "", currency: "KES", agreed_quantity: "",
  unit: "KG", valid_from: "", valid_to: "", payment_terms: "", notes: "",
};

export default function BlanketAgreementsPage() {
  const [bpas, setBPAs] = useState<BlanketAgreement[]>([]);
  const [loading, setLoading] = useState(true);
  const [filterStatus, setFilterStatus] = useState<BPAStatus | "">("");
  const [showModal, setShowModal] = useState(false);
  const [editId, setEditId] = useState<string | null>(null);
  const [form, setForm] = useState({ ...BLANK_FORM });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const data = await procurementApi.listBPAs(filterStatus ? { status: filterStatus as BPAStatus } : undefined);
      setBPAs(data);
    } finally {
      setLoading(false);
    }
  }, [filterStatus]);

  useEffect(() => { load(); }, [load]);

  const openCreate = () => { setForm({ ...BLANK_FORM }); setEditId(null); setError(""); setShowModal(true); };

  const openEdit = (b: BlanketAgreement) => {
    setForm({
      bpa_no: b.bpa_no,
      supplier_id: b.supplier_id,
      description: b.description ?? "",
      agreed_unit_price: String(b.agreed_unit_price),
      currency: b.currency,
      agreed_quantity: b.agreed_quantity != null ? String(b.agreed_quantity) : "",
      unit: b.unit,
      valid_from: b.valid_from,
      valid_to: b.valid_to,
      payment_terms: b.payment_terms ?? "",
      notes: b.notes ?? "",
    });
    setEditId(b.id);
    setError("");
    setShowModal(true);
  };

  const save = async () => {
    if (!form.bpa_no || !form.supplier_id || !form.agreed_unit_price || !form.valid_from || !form.valid_to) {
      setError("BPA No., Supplier ID, Price, and validity dates required"); return;
    }
    setSaving(true); setError("");
    try {
      const payload = {
        bpa_no: form.bpa_no,
        supplier_id: form.supplier_id,
        description: form.description || null,
        agreed_unit_price: parseFloat(form.agreed_unit_price),
        currency: form.currency,
        agreed_quantity: form.agreed_quantity ? parseFloat(form.agreed_quantity) : null,
        unit: form.unit,
        valid_from: form.valid_from,
        valid_to: form.valid_to,
        payment_terms: form.payment_terms || null,
        notes: form.notes || null,
      };
      if (editId) {
        await procurementApi.updateBPA(editId, payload);
      } else {
        await procurementApi.createBPA(payload);
      }
      setShowModal(false);
      await load();
    } catch {
      setError("Failed to save agreement");
    } finally {
      setSaving(false);
    }
  };

  const cancel = async (b: BlanketAgreement) => {
    if (!confirm(`Cancel agreement ${b.bpa_no}?`)) return;
    await procurementApi.updateBPA(b.id, { status: "CANCELLED" });
    await load();
  };

  const today = new Date().toISOString().split("T")[0];
  const active = bpas.filter(b => b.status === "ACTIVE" && !b.is_expired).length;
  const expired = bpas.filter(b => b.is_expired || b.status === "EXPIRED").length;
  const totalValue = bpas.filter(b => b.status === "ACTIVE").reduce((acc, b) => {
    const qty = b.agreed_quantity ?? 0;
    return acc + (Number(b.agreed_unit_price) * Number(qty));
  }, 0);

  return (
    <div className="p-6 space-y-5">
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div>
          <h1 className="text-xl font-bold text-gray-900">Blanket Purchase Agreements</h1>
          <p className="text-xs text-gray-500 mt-0.5">Long-term price agreements with suppliers for materials and products.</p>
        </div>
        <button onClick={openCreate}
          className="rounded bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700">
          + New Agreement
        </button>
      </div>

      <div className="grid grid-cols-3 gap-4">
        {[
          { label: "Active Agreements", value: active, color: "text-green-600" },
          { label: "Expired / Cancelled", value: expired, color: "text-gray-500" },
          { label: "Total Contracted Value", value: `KES ${totalValue.toLocaleString(undefined, { maximumFractionDigits: 0 })}`, color: "text-blue-600" },
        ].map(s => (
          <div key={s.label} className="bg-white border rounded-lg p-4 shadow-sm">
            <p className="text-xs text-gray-500">{s.label}</p>
            <p className={`text-xl font-bold mt-1 ${s.color}`}>{s.value}</p>
          </div>
        ))}
      </div>

      <div className="flex gap-3 flex-wrap items-center">
        <select className="border rounded px-2 py-1.5 text-sm" value={filterStatus}
          onChange={e => setFilterStatus(e.target.value as BPAStatus | "")}>
          <option value="">All Status</option>
          <option value="ACTIVE">Active</option>
          <option value="EXPIRED">Expired</option>
          <option value="CANCELLED">Cancelled</option>
        </select>
        <span className="text-xs text-gray-500">{bpas.length} agreements</span>
      </div>

      {loading ? (
        <p className="text-sm text-gray-500">Loading…</p>
      ) : bpas.length === 0 ? (
        <div className="bg-white border rounded-lg p-10 text-center text-gray-400">
          <p className="text-2xl mb-2">🤝</p>
          <p className="text-sm">No blanket agreements found.</p>
        </div>
      ) : (
        <div className="bg-white border rounded-lg shadow-sm overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 border-b">
              <tr>
                {["BPA No.", "Supplier", "Description", "Price", "Qty", "Consumed", "Valid To", "Status", "Actions"].map(h => (
                  <th key={h} className="px-4 py-2 text-left text-xs font-semibold text-gray-600">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y">
              {bpas.map(b => {
                const expiringSoon = b.status === "ACTIVE" && !b.is_expired && b.valid_to <= new Date(Date.now() + 30 * 86400000).toISOString().split("T")[0];
                return (
                  <tr key={b.id} className={`hover:bg-gray-50 ${b.is_expired ? "opacity-60" : ""}`}>
                    <td className="px-4 py-3 font-mono text-xs text-gray-600">{b.bpa_no}</td>
                    <td className="px-4 py-3 text-gray-800 font-medium text-xs">{b.supplier_name ?? b.supplier_id.slice(0,8)}</td>
                    <td className="px-4 py-3 text-gray-600 text-xs max-w-xs truncate">{b.description ?? "—"}</td>
                    <td className="px-4 py-3 text-xs font-semibold">
                      {b.currency} {Number(b.agreed_unit_price).toLocaleString()} /{b.unit}
                    </td>
                    <td className="px-4 py-3 text-xs text-gray-600">
                      {b.agreed_quantity != null ? `${Number(b.agreed_quantity).toLocaleString()} ${b.unit}` : "Open"}
                    </td>
                    <td className="px-4 py-3 text-xs text-gray-600">
                      {Number(b.consumed_quantity).toLocaleString()}
                      {b.remaining_quantity != null && (
                        <span className="text-gray-400"> ({Number(b.remaining_quantity).toLocaleString()} left)</span>
                      )}
                    </td>
                    <td className="px-4 py-3 text-xs">
                      <span className={expiringSoon ? "text-amber-600 font-semibold" : "text-gray-600"}>
                        {b.valid_to}
                        {expiringSoon && " ⚠️"}
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      <span className={`text-xs rounded-full px-2 py-0.5 ${STATUS_COLORS[b.status]}`}>
                        {b.is_expired && b.status === "ACTIVE" ? "EXPIRED" : b.status}
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex gap-2">
                        {b.status === "ACTIVE" && !b.is_expired && (
                          <>
                            <button onClick={() => openEdit(b)} className="text-xs text-blue-600 hover:underline">Edit</button>
                            <button onClick={() => cancel(b)} className="text-xs text-red-500 hover:underline">Cancel</button>
                          </>
                        )}
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}

      {showModal && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-xl shadow-2xl w-full max-w-lg max-h-[90vh] overflow-y-auto">
            <div className="px-6 py-4 border-b flex items-center justify-between">
              <h2 className="text-base font-semibold">{editId ? "Edit Agreement" : "New Blanket Agreement"}</h2>
              <button onClick={() => setShowModal(false)} className="text-gray-400 hover:text-gray-600 text-xl">×</button>
            </div>
            <div className="p-6 space-y-4">
              {error && <p className="text-xs text-red-500 bg-red-50 border border-red-200 rounded px-3 py-2">{error}</p>}
              <div className="grid grid-cols-2 gap-4">
                {[
                  { label: "BPA No. *", key: "bpa_no", placeholder: "BPA-2026-001", col: 1 },
                  { label: "Supplier ID *", key: "supplier_id", placeholder: "UUID", col: 1 },
                  { label: "Description", key: "description", placeholder: "e.g. Palm Oil FY2026", col: 2 },
                  { label: "Agreed Unit Price *", key: "agreed_unit_price", type: "number", placeholder: "0.00", col: 1 },
                  { label: "Currency", key: "currency", placeholder: "KES", col: 1 },
                  { label: "Agreed Quantity (blank = open)", key: "agreed_quantity", type: "number", placeholder: "", col: 1 },
                  { label: "Unit", key: "unit", placeholder: "KG", col: 1 },
                  { label: "Valid From *", key: "valid_from", type: "date", col: 1 },
                  { label: "Valid To *", key: "valid_to", type: "date", col: 1 },
                  { label: "Payment Terms", key: "payment_terms", placeholder: "Net 30", col: 2 },
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
              <button onClick={save} disabled={saving}
                className="flex-1 rounded bg-blue-600 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50">
                {saving ? "Saving…" : editId ? "Update" : "Create"}
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
