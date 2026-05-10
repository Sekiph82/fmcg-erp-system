"use client";
import { useCallback, useEffect, useState } from "react";
import { qmsApi, CoARecord } from "@/lib/qms";

const STATUS_COLORS: Record<string, string> = {
  DRAFT: "bg-gray-100 text-gray-600",
  ISSUED: "bg-green-100 text-green-700",
  SUPERSEDED: "bg-amber-100 text-amber-700",
};

const BLANK = {
  coa_no: "", lot_id: "", product_id: "", inspection_id: "",
  issue_date: new Date().toISOString().split("T")[0],
  valid_until: "", lot_number: "", batch_no: "",
  manufacture_date: "", expiry_date: "", overall_result: "PASS",
  customer_id: "", notes: "",
};

export default function CoAPage() {
  const [coas, setCoas] = useState<CoARecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [filterStatus, setFilterStatus] = useState("");
  const [showCreate, setShowCreate] = useState(false);
  const [form, setForm] = useState({ ...BLANK });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const data = await qmsApi.listCoA(filterStatus ? { status: filterStatus } : undefined);
      setCoas(data);
    } finally {
      setLoading(false);
    }
  }, [filterStatus]);

  useEffect(() => { load(); }, [load]);

  const create = async () => {
    if (!form.coa_no || !form.lot_id || !form.issue_date) {
      setError("CoA No., Lot ID, Issue Date required"); return;
    }
    setSaving(true); setError("");
    try {
      await qmsApi.createCoA({
        coa_no: form.coa_no,
        lot_id: form.lot_id,
        product_id: form.product_id || null,
        inspection_id: form.inspection_id || null,
        issue_date: form.issue_date,
        valid_until: form.valid_until || null,
        lot_number: form.lot_number || null,
        batch_no: form.batch_no || null,
        manufacture_date: form.manufacture_date || null,
        expiry_date: form.expiry_date || null,
        overall_result: form.overall_result,
        customer_id: form.customer_id || null,
        notes: form.notes || null,
      });
      setShowCreate(false);
      setForm({ ...BLANK });
      await load();
    } catch {
      setError("Failed to create CoA");
    } finally {
      setSaving(false);
    }
  };

  const issue = async (id: string) => {
    if (!confirm("Issue this CoA? It will be marked as ISSUED and cannot be edited.")) return;
    await qmsApi.issueCoA(id);
    await load();
  };

  return (
    <div className="p-6 space-y-5">
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div>
          <h1 className="text-xl font-bold text-gray-900">Certificate of Analysis</h1>
          <p className="text-xs text-gray-500 mt-0.5">
            Generate and manage CoAs from QC inspection results per lot/batch.
          </p>
        </div>
        <button onClick={() => { setShowCreate(true); setError(""); }}
          className="rounded bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700">
          + New CoA
        </button>
      </div>

      <div className="flex gap-2 flex-wrap">
        {["", "DRAFT", "ISSUED", "SUPERSEDED"].map(s => (
          <button key={s}
            onClick={() => setFilterStatus(s)}
            className={`rounded-full px-3 py-1 text-xs font-medium border transition-colors ${
              filterStatus === s
                ? "bg-blue-600 text-white border-blue-600"
                : "bg-white text-gray-600 border-gray-300 hover:border-blue-400"
            }`}>
            {s || "All"}
          </button>
        ))}
        <span className="text-xs text-gray-500 self-center">{coas.length} CoAs</span>
      </div>

      {loading ? (
        <p className="text-sm text-gray-500">Loading…</p>
      ) : coas.length === 0 ? (
        <div className="bg-white border rounded-lg p-10 text-center text-gray-400">
          <p className="text-2xl mb-2">📄</p>
          <p className="text-sm">No Certificates of Analysis yet.</p>
        </div>
      ) : (
        <div className="bg-white border rounded-lg shadow-sm overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 border-b">
              <tr>
                {["CoA No.", "Product", "Lot No.", "Batch", "Issue Date", "Expiry", "Result", "Status", "Actions"].map(h => (
                  <th key={h} className="px-4 py-2 text-left text-xs font-semibold text-gray-600">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y">
              {coas.map(c => (
                <tr key={c.id} className="hover:bg-gray-50">
                  <td className="px-4 py-3 font-mono text-xs text-gray-700 font-semibold">{c.coa_no}</td>
                  <td className="px-4 py-3 text-xs text-gray-700">{c.product_name ?? "—"}</td>
                  <td className="px-4 py-3 text-xs text-gray-600">{c.lot_number ?? c.lot_id.slice(0,8)}</td>
                  <td className="px-4 py-3 text-xs text-gray-600">{c.batch_no ?? "—"}</td>
                  <td className="px-4 py-3 text-xs text-gray-600">{c.issue_date}</td>
                  <td className="px-4 py-3 text-xs text-gray-600">{c.expiry_date ?? "—"}</td>
                  <td className="px-4 py-3">
                    <span className={`text-xs rounded-full px-2 py-0.5 ${c.overall_result === "PASS" ? "bg-green-100 text-green-700" : "bg-red-100 text-red-600"}`}>
                      {c.overall_result ?? "—"}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    <span className={`text-xs rounded-full px-2 py-0.5 ${STATUS_COLORS[c.status] ?? "bg-gray-100 text-gray-500"}`}>
                      {c.status}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    {c.status === "DRAFT" && (
                      <button onClick={() => issue(c.id)} className="text-xs text-blue-600 hover:underline">
                        Issue
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {showCreate && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-xl shadow-2xl w-full max-w-lg max-h-[90vh] overflow-y-auto">
            <div className="px-6 py-4 border-b flex items-center justify-between">
              <h2 className="text-base font-semibold">New Certificate of Analysis</h2>
              <button onClick={() => setShowCreate(false)} className="text-gray-400 text-xl">×</button>
            </div>
            <div className="p-6 space-y-3">
              {error && <p className="text-xs text-red-500 bg-red-50 border border-red-200 rounded px-3 py-2">{error}</p>}
              <div className="grid grid-cols-2 gap-3">
                {[
                  { label: "CoA No. *", key: "coa_no", placeholder: "COA-2026-001", col: 1 },
                  { label: "Lot ID (UUID) *", key: "lot_id", placeholder: "UUID", col: 1 },
                  { label: "Product ID (UUID)", key: "product_id", placeholder: "UUID", col: 1 },
                  { label: "Inspection ID (UUID)", key: "inspection_id", placeholder: "Link to QC inspection", col: 1 },
                  { label: "Lot Number", key: "lot_number", placeholder: "", col: 1 },
                  { label: "Batch No.", key: "batch_no", placeholder: "", col: 1 },
                  { label: "Issue Date *", key: "issue_date", type: "date", col: 1 },
                  { label: "Valid Until", key: "valid_until", type: "date", col: 1 },
                  { label: "Manufacture Date", key: "manufacture_date", type: "date", col: 1 },
                  { label: "Expiry Date", key: "expiry_date", type: "date", col: 1 },
                  { label: "Customer ID (UUID, optional)", key: "customer_id", placeholder: "", col: 2 },
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
                <div>
                  <label className="block text-xs font-medium text-gray-600 mb-1">Overall Result</label>
                  <select value={form.overall_result}
                    onChange={e => setForm(prev => ({ ...prev, overall_result: e.target.value }))}
                    className="w-full border rounded px-3 py-2 text-sm focus:ring-1 focus:ring-blue-500 outline-none">
                    <option value="PASS">PASS</option>
                    <option value="FAIL">FAIL</option>
                    <option value="CONDITIONAL">CONDITIONAL</option>
                  </select>
                </div>
              </div>
            </div>
            <div className="px-6 pb-5 flex gap-3">
              <button onClick={create} disabled={saving}
                className="flex-1 rounded bg-blue-600 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50">
                {saving ? "Creating…" : "Create CoA"}
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
