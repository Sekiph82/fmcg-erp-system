"use client";
import { useEffect, useState } from "react";
import { procurementApi, RFQRead, RFQDetail, RFQStatus } from "@/lib/procurement";

const STATUS_COLORS: Record<RFQStatus, string> = {
  DRAFT: "bg-gray-100 text-gray-600",
  SENT: "bg-blue-100 text-blue-700",
  RESPONSES_RECEIVED: "bg-amber-100 text-amber-700",
  AWARDED: "bg-green-100 text-green-700",
  CANCELLED: "bg-red-100 text-red-500",
};

export default function RFQPage() {
  const [rfqs, setRFQs] = useState<RFQRead[]>([]);
  const [loading, setLoading] = useState(true);
  const [filterStatus, setFilterStatus] = useState<RFQStatus | "">("");
  const [showCreate, setShowCreate] = useState(false);
  const [selected, setSelected] = useState<RFQDetail | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [form, setForm] = useState({
    rfq_no: "", title: "", quantity: "", unit: "KG",
    description: "", required_by: "", response_deadline: "", notes: "",
  });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  // Response form
  const [showResponse, setShowResponse] = useState(false);
  const [respForm, setRespForm] = useState({
    supplier_id: "", quoted_unit_price: "", quoted_currency: "KES",
    lead_time_days: "", valid_until: "", payment_terms: "", notes: "",
  });

  const load = async () => {
    setLoading(true);
    try {
      const data = await procurementApi.listRFQs(filterStatus ? { status: filterStatus as RFQStatus } : undefined);
      setRFQs(data);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, [filterStatus]);

  const openDetail = async (id: string) => {
    setDetailLoading(true);
    setSelected(null);
    try {
      const detail = await procurementApi.getRFQ(id);
      setSelected(detail);
    } finally {
      setDetailLoading(false);
    }
  };

  const create = async () => {
    if (!form.rfq_no.trim() || !form.title.trim() || !form.quantity) {
      setError("RFQ No., Title, and Quantity required"); return;
    }
    setSaving(true); setError("");
    try {
      await procurementApi.createRFQ({
        ...form,
        quantity: parseFloat(form.quantity),
      });
      setShowCreate(false);
      setForm({ rfq_no: "", title: "", quantity: "", unit: "KG", description: "", required_by: "", response_deadline: "", notes: "" });
      await load();
    } catch {
      setError("Failed to create RFQ");
    } finally {
      setSaving(false);
    }
  };

  const sendRFQ = async (id: string) => {
    await procurementApi.updateRFQ(id, { status: "SENT" });
    await load();
    if (selected?.id === id) {
      const updated = await procurementApi.getRFQ(id);
      setSelected(updated);
    }
  };

  const awardRFQ = async (id: string, supplierId: string) => {
    await procurementApi.updateRFQ(id, { status: "AWARDED", awarded_supplier_id: supplierId });
    await load();
    const updated = await procurementApi.getRFQ(id);
    setSelected(updated);
  };

  const submitResponse = async () => {
    if (!selected || !respForm.supplier_id) { setError("Supplier ID required"); return; }
    setSaving(true); setError("");
    try {
      await procurementApi.addRFQResponse(selected.id, {
        supplier_id: respForm.supplier_id,
        quoted_unit_price: respForm.quoted_unit_price ? parseFloat(respForm.quoted_unit_price) : null,
        quoted_currency: respForm.quoted_currency,
        lead_time_days: respForm.lead_time_days ? parseInt(respForm.lead_time_days) : null,
        valid_until: respForm.valid_until || null,
        payment_terms: respForm.payment_terms || null,
        notes: respForm.notes || null,
      });
      setShowResponse(false);
      const updated = await procurementApi.getRFQ(selected.id);
      setSelected(updated);
      await load();
    } catch {
      setError("Failed to submit response");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="p-6 space-y-5">
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div>
          <h1 className="text-xl font-bold text-gray-900">Request for Quotation (RFQ)</h1>
          <p className="text-xs text-gray-500 mt-0.5">Issue RFQs to suppliers, collect quotes, compare, and award.</p>
        </div>
        <button onClick={() => { setShowCreate(true); setError(""); }}
          className="rounded bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700">
          + New RFQ
        </button>
      </div>

      <div className="flex gap-3 flex-wrap items-center">
        <select className="border rounded px-2 py-1.5 text-sm" value={filterStatus}
          onChange={e => setFilterStatus(e.target.value as RFQStatus | "")}>
          <option value="">All Status</option>
          {(["DRAFT","SENT","RESPONSES_RECEIVED","AWARDED","CANCELLED"] as RFQStatus[]).map(s => (
            <option key={s} value={s}>{s.replace("_", " ")}</option>
          ))}
        </select>
        <span className="text-xs text-gray-500 self-center">{rfqs.length} RFQs</span>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
        {/* RFQ List */}
        <div className="lg:col-span-2">
          {loading ? (
            <p className="text-sm text-gray-500">Loading…</p>
          ) : rfqs.length === 0 ? (
            <div className="bg-white border rounded-lg p-10 text-center text-gray-400">
              <p className="text-2xl mb-2">📋</p>
              <p className="text-sm">No RFQs found.</p>
            </div>
          ) : (
            <div className="bg-white border rounded-lg shadow-sm overflow-x-auto">
              <table className="w-full text-sm">
                <thead className="bg-gray-50 border-b">
                  <tr>
                    {["RFQ No.", "Title", "Qty", "Deadline", "Responses", "Status", ""].map(h => (
                      <th key={h} className="px-4 py-2 text-left text-xs font-semibold text-gray-600">{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody className="divide-y">
                  {rfqs.map(r => (
                    <tr key={r.id} className="hover:bg-gray-50">
                      <td className="px-4 py-3 font-mono text-xs text-gray-600">{r.rfq_no}</td>
                      <td className="px-4 py-3 font-medium text-gray-800">
                        <button onClick={() => openDetail(r.id)} className="hover:text-blue-600 text-left">
                          {r.title}
                        </button>
                      </td>
                      <td className="px-4 py-3 text-xs text-gray-600">{r.quantity} {r.unit}</td>
                      <td className="px-4 py-3 text-xs text-gray-600">{r.response_deadline ?? "—"}</td>
                      <td className="px-4 py-3 text-xs font-semibold text-blue-600">{r.response_count}</td>
                      <td className="px-4 py-3">
                        <span className={`text-xs rounded-full px-2 py-0.5 ${STATUS_COLORS[r.status]}`}>
                          {r.status.replace("_", " ")}
                        </span>
                      </td>
                      <td className="px-4 py-3">
                        {r.status === "DRAFT" && (
                          <button onClick={() => sendRFQ(r.id)} className="text-xs text-blue-600 hover:underline">
                            Send
                          </button>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>

        {/* Detail Panel */}
        <div className="bg-white border rounded-lg p-5">
          {detailLoading ? (
            <p className="text-sm text-gray-500">Loading…</p>
          ) : selected ? (
            <div className="space-y-4">
              <div>
                <div className="flex items-center justify-between mb-1">
                  <h3 className="text-sm font-semibold text-gray-800">{selected.rfq_no}</h3>
                  <span className={`text-xs rounded-full px-2 py-0.5 ${STATUS_COLORS[selected.status]}`}>
                    {selected.status.replace("_", " ")}
                  </span>
                </div>
                <p className="text-xs text-gray-600">{selected.title}</p>
                <p className="text-xs text-gray-500 mt-1">{selected.quantity} {selected.unit}</p>
                {selected.description && <p className="text-xs text-gray-500 mt-1">{selected.description}</p>}
              </div>

              <div className="border-t pt-3">
                <div className="flex items-center justify-between mb-2">
                  <p className="text-xs font-semibold text-gray-600">Supplier Responses ({selected.responses.length})</p>
                  {selected.status !== "AWARDED" && selected.status !== "CANCELLED" && (
                    <button onClick={() => { setShowResponse(true); setError(""); }}
                      className="text-xs text-blue-600 hover:underline">
                      + Add Response
                    </button>
                  )}
                </div>
                {selected.responses.length === 0 ? (
                  <p className="text-xs text-gray-400">No responses yet.</p>
                ) : (
                  <div className="space-y-2">
                    {selected.responses.map(resp => (
                      <div key={resp.id} className="border rounded p-3 bg-gray-50">
                        <div className="flex items-center justify-between">
                          <p className="text-xs font-medium text-gray-700">{resp.supplier_name ?? resp.supplier_id.slice(0,8)}</p>
                          <span className="text-xs text-gray-500">{resp.status}</span>
                        </div>
                        {resp.quoted_unit_price != null && (
                          <p className="text-xs text-gray-600 mt-1">
                            {resp.quoted_currency} {Number(resp.quoted_unit_price).toLocaleString()} /unit
                            {resp.lead_time_days != null && ` · ${resp.lead_time_days}d lead`}
                          </p>
                        )}
                        {selected.status === "RESPONSES_RECEIVED" && (
                          <button
                            onClick={() => awardRFQ(selected.id, resp.supplier_id)}
                            className="mt-2 text-xs bg-green-600 text-white rounded px-2 py-0.5 hover:bg-green-700"
                          >
                            Award
                          </button>
                        )}
                      </div>
                    ))}
                  </div>
                )}
              </div>

              {selected.awarded_supplier_name && (
                <div className="bg-green-50 border border-green-200 rounded p-3">
                  <p className="text-xs font-semibold text-green-700">Awarded to: {selected.awarded_supplier_name}</p>
                </div>
              )}
            </div>
          ) : (
            <div className="text-center py-8 text-gray-400">
              <p className="text-2xl mb-2">📋</p>
              <p className="text-sm">Click an RFQ to view details.</p>
            </div>
          )}
        </div>
      </div>

      {/* Create Modal */}
      {showCreate && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-xl shadow-2xl w-full max-w-md max-h-[90vh] overflow-y-auto">
            <div className="px-6 py-4 border-b flex items-center justify-between">
              <h2 className="text-base font-semibold">New RFQ</h2>
              <button onClick={() => setShowCreate(false)} className="text-gray-400 hover:text-gray-600 text-xl">×</button>
            </div>
            <div className="p-6 space-y-4">
              {error && <p className="text-xs text-red-500 bg-red-50 border border-red-200 rounded px-3 py-2">{error}</p>}
              {[
                { label: "RFQ No. *", key: "rfq_no", placeholder: "RFQ-2026-001" },
                { label: "Title *", key: "title", placeholder: "Raw material procurement Q3" },
                { label: "Description", key: "description", placeholder: "Details…" },
                { label: "Quantity *", key: "quantity", placeholder: "100", type: "number" },
              ].map(f => (
                <div key={f.key}>
                  <label className="block text-xs font-medium text-gray-600 mb-1">{f.label}</label>
                  <input type={f.type ?? "text"} placeholder={f.placeholder}
                    value={(form as Record<string, string>)[f.key]}
                    onChange={e => setForm(prev => ({ ...prev, [f.key]: e.target.value }))}
                    className="w-full border rounded px-3 py-2 text-sm focus:ring-1 focus:ring-blue-500 outline-none"
                  />
                </div>
              ))}
              <div className="grid grid-cols-2 gap-3">
                {[
                  { label: "Unit", key: "unit" },
                  { label: "Required By", key: "required_by", type: "date" },
                  { label: "Response Deadline", key: "response_deadline", type: "date" },
                ].map(f => (
                  <div key={f.key}>
                    <label className="block text-xs font-medium text-gray-600 mb-1">{f.label}</label>
                    <input type={f.type ?? "text"}
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
                {saving ? "Creating…" : "Create RFQ"}
              </button>
              <button onClick={() => setShowCreate(false)}
                className="flex-1 rounded border py-2 text-sm text-gray-600 hover:bg-gray-50">
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Add Response Modal */}
      {showResponse && selected && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-xl shadow-2xl w-full max-w-md">
            <div className="px-6 py-4 border-b flex items-center justify-between">
              <h2 className="text-base font-semibold">Add Supplier Response</h2>
              <button onClick={() => setShowResponse(false)} className="text-gray-400 hover:text-gray-600 text-xl">×</button>
            </div>
            <div className="p-6 space-y-3">
              {error && <p className="text-xs text-red-500 bg-red-50 border border-red-200 rounded px-3 py-2">{error}</p>}
              {[
                { label: "Supplier ID *", key: "supplier_id", placeholder: "UUID of supplier" },
                { label: "Quoted Unit Price", key: "quoted_unit_price", type: "number", placeholder: "0.00" },
                { label: "Currency", key: "quoted_currency", placeholder: "KES" },
                { label: "Lead Time (days)", key: "lead_time_days", type: "number", placeholder: "7" },
                { label: "Valid Until", key: "valid_until", type: "date" },
                { label: "Payment Terms", key: "payment_terms", placeholder: "e.g. Net 30" },
                { label: "Notes", key: "notes", placeholder: "" },
              ].map(f => (
                <div key={f.key}>
                  <label className="block text-xs font-medium text-gray-600 mb-1">{f.label}</label>
                  <input type={f.type ?? "text"} placeholder={f.placeholder}
                    value={(respForm as Record<string, string>)[f.key]}
                    onChange={e => setRespForm(prev => ({ ...prev, [f.key]: e.target.value }))}
                    className="w-full border rounded px-3 py-2 text-sm focus:ring-1 focus:ring-blue-500 outline-none"
                  />
                </div>
              ))}
            </div>
            <div className="px-6 pb-5 flex gap-3">
              <button onClick={submitResponse} disabled={saving}
                className="flex-1 rounded bg-blue-600 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50">
                {saving ? "Saving…" : "Submit Response"}
              </button>
              <button onClick={() => setShowResponse(false)}
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
