"use client";
import { useEffect, useState } from "react";

interface FSA { id: string; supplier_name: string; supplier_id: string | null; approval_type: string; status: string; audit_score: number | null; last_audit_date: string | null; expiry_date: string | null; days_to_expiry: number | null; certificate_number: string | null; critical_findings: number; major_findings: number; minor_findings: number; notes: string | null; }

const STATUS_COLOR: Record<string, string> = {
  APPROVED: "bg-green-100 text-green-700", CONDITIONAL: "bg-amber-100 text-amber-600",
  PENDING: "bg-blue-100 text-blue-600", SUSPENDED: "bg-red-100 text-red-700",
  REJECTED: "bg-gray-100 text-gray-500",
};

const APPROVAL_TYPES = ["FSSC_22000", "HALAL", "HACCP", "BRC", "ISO_22000", "GMP", "ORGANIC", "KOSHER", "SQF"];
const STATUSES = ["APPROVED", "CONDITIONAL", "PENDING", "SUSPENDED", "REJECTED"];

interface FSAForm { supplier_name: string; approval_type: string; status: string; audit_score: string; auditor: string; last_audit_date: string; approval_date: string; expiry_date: string; certificate_number: string; critical_findings: string; major_findings: string; minor_findings: string; notes: string; }

const EMPTY: FSAForm = { supplier_name: "", approval_type: "FSSC_22000", status: "PENDING", audit_score: "", auditor: "", last_audit_date: "", approval_date: "", expiry_date: "", certificate_number: "", critical_findings: "0", major_findings: "0", minor_findings: "0", notes: "" };

function urgency(days: number | null): string {
  if (days === null) return "text-gray-400";
  if (days < 0) return "text-red-600 font-bold";
  if (days <= 30) return "text-red-500";
  if (days <= 90) return "text-amber-500";
  return "text-green-600";
}

export default function SupplierSafetyPage() {
  const [records, setRecords] = useState<FSA[]>([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState<FSAForm>(EMPTY);
  const [saving, setSaving] = useState(false);
  const [filterStatus, setFilterStatus] = useState("");
  const [expiringOnly, setExpiringOnly] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = () => {
    setLoading(true);
    const p = new URLSearchParams({ limit: "200" });
    if (filterStatus) p.set("status", filterStatus);
    if (expiringOnly) p.set("expiring_days", "90");
    fetch(`/api/v1/qms/supplier-food-safety?${p}`)
      .then(r => r.json()).then(setRecords).finally(() => setLoading(false));
  };
  useEffect(load, [filterStatus, expiringOnly]);

  const save = async () => {
    setSaving(true); setError(null);
    try {
      const r = await fetch("/api/v1/qms/supplier-food-safety", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          supplier_name: form.supplier_name, approval_type: form.approval_type, status: form.status,
          audit_score: form.audit_score ? Number(form.audit_score) : undefined,
          auditor: form.auditor || undefined,
          last_audit_date: form.last_audit_date || undefined,
          approval_date: form.approval_date || undefined,
          expiry_date: form.expiry_date || undefined,
          certificate_number: form.certificate_number || undefined,
          critical_findings: Number(form.critical_findings), major_findings: Number(form.major_findings),
          minor_findings: Number(form.minor_findings), notes: form.notes || undefined,
        }),
      });
      if (!r.ok) throw new Error(await r.text());
      setShowForm(false); setForm(EMPTY); load();
    } catch (e) { setError(String(e)); }
    setSaving(false);
  };

  const approved = records.filter(r => r.status === "APPROVED").length;
  const expiring = records.filter(r => r.days_to_expiry !== null && r.days_to_expiry <= 90 && r.days_to_expiry >= 0).length;
  const expired = records.filter(r => r.days_to_expiry !== null && r.days_to_expiry < 0).length;

  return (
    <div className="p-6 space-y-6 max-w-5xl mx-auto">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Supplier Food Safety Approvals</h1>
          <p className="text-sm text-gray-500 mt-0.5">Track FSSC, HALAL, HACCP, BRC, GMP approvals per supplier</p>
        </div>
        <button onClick={() => setShowForm(true)} className="bg-blue-600 hover:bg-blue-700 text-white text-sm font-medium px-4 py-2 rounded">+ Add Approval</button>
      </div>

      {error && <div className="bg-red-50 border border-red-200 rounded p-3 text-sm text-red-700">{error}</div>}

      <div className="grid grid-cols-3 gap-4">
        {[{ label: "Approved", value: approved, c: "text-green-600" }, { label: "Expiring (90d)", value: expiring, c: "text-amber-600" }, { label: "Expired", value: expired, c: "text-red-600" }].map(k => (
          <div key={k.label} className="bg-white border rounded-lg p-4 shadow-sm">
            <p className="text-xs text-gray-500">{k.label}</p>
            <p className={`text-2xl font-bold mt-1 ${k.c}`}>{k.value}</p>
          </div>
        ))}
      </div>

      <div className="flex flex-wrap gap-3 bg-white border rounded-lg p-3 shadow-sm items-end">
        <div>
          <label className="text-xs text-gray-500 block mb-1">Status</label>
          <select value={filterStatus} onChange={(e) => setFilterStatus(e.target.value)} className="border border-gray-300 rounded px-2 py-1 text-xs focus:outline-none">
            <option value="">All</option>
            {STATUSES.map(s => <option key={s} value={s}>{s}</option>)}
          </select>
        </div>
        <label className="flex items-center gap-1.5 text-sm cursor-pointer">
          <input type="checkbox" checked={expiringOnly} onChange={(e) => setExpiringOnly(e.target.checked)} className="h-3.5 w-3.5" />
          Expiring 90d
        </label>
        <button onClick={() => { setFilterStatus(""); setExpiringOnly(false); }} className="text-xs text-gray-500 underline">Clear</button>
      </div>

      {showForm && (
        <div className="bg-white border rounded-lg p-5 shadow-sm space-y-3 max-w-2xl">
          <h2 className="text-sm font-semibold text-gray-700">Add Supplier Food Safety Approval</h2>
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {([["Supplier Name *","supplier_name","e.g. Best Oils Ltd"],["Auditor","auditor","e.g. SGS Kenya"],["Certificate No","certificate_number","e.g. FSSC/2026/001"]] as const).map(([label,key,ph]) => (
              <div key={key}>
                <label className="text-xs text-gray-500 block mb-1">{label}</label>
                <input type="text" placeholder={ph} value={(form as unknown as Record<string,string>)[key]}
                  onChange={(e) => setForm((p) => ({ ...p, [key]: e.target.value }))}
                  className="w-full border border-gray-300 rounded px-3 py-1.5 text-sm focus:outline-none focus:ring-1 focus:ring-blue-500" />
              </div>
            ))}
            <div>
              <label className="text-xs text-gray-500 block mb-1">Approval Type *</label>
              <select value={form.approval_type} onChange={(e) => setForm((p) => ({ ...p, approval_type: e.target.value }))} className="w-full border border-gray-300 rounded px-3 py-1.5 text-sm focus:outline-none">
                {APPROVAL_TYPES.map(t => <option key={t} value={t}>{t.replace(/_/g, " ")}</option>)}
              </select>
            </div>
            <div>
              <label className="text-xs text-gray-500 block mb-1">Status</label>
              <select value={form.status} onChange={(e) => setForm((p) => ({ ...p, status: e.target.value }))} className="w-full border border-gray-300 rounded px-3 py-1.5 text-sm focus:outline-none">
                {STATUSES.map(s => <option key={s} value={s}>{s}</option>)}
              </select>
            </div>
            <div>
              <label className="text-xs text-gray-500 block mb-1">Audit Score (%)</label>
              <input type="number" value={form.audit_score} onChange={(e) => setForm((p) => ({ ...p, audit_score: e.target.value }))} placeholder="e.g. 87.5"
                className="w-full border border-gray-300 rounded px-3 py-1.5 text-sm focus:outline-none" />
            </div>
            {([["last_audit_date","Last Audit"],["approval_date","Approved On"],["expiry_date","Expiry Date"]] as const).map(([key,label]) => (
              <div key={key}>
                <label className="text-xs text-gray-500 block mb-1">{label}</label>
                <input type="date" value={(form as unknown as Record<string,string>)[key]}
                  onChange={(e) => setForm((p) => ({ ...p, [key]: e.target.value }))}
                  className="w-full border border-gray-300 rounded px-3 py-1.5 text-sm focus:outline-none" />
              </div>
            ))}
            {([["critical_findings","Critical"],["major_findings","Major"],["minor_findings","Minor"]] as const).map(([key,label]) => (
              <div key={key}>
                <label className="text-xs text-gray-500 block mb-1">{label} Findings</label>
                <input type="number" min={0} value={(form as unknown as Record<string,string>)[key]}
                  onChange={(e) => setForm((p) => ({ ...p, [key]: e.target.value }))}
                  className="w-full border border-gray-300 rounded px-3 py-1.5 text-sm focus:outline-none" />
              </div>
            ))}
          </div>
          <div className="flex gap-2">
            <button onClick={save} disabled={saving || !form.supplier_name} className="bg-blue-600 text-white text-sm px-4 py-2 rounded disabled:opacity-50">{saving ? "Saving…" : "Save"}</button>
            <button onClick={() => setShowForm(false)} className="border border-gray-300 text-sm px-4 py-2 rounded hover:bg-gray-50">Cancel</button>
          </div>
        </div>
      )}

      <div className="bg-white border rounded-lg shadow-sm overflow-hidden">
        <div className="px-4 py-3 border-b bg-gray-50"><h2 className="text-sm font-semibold text-gray-700">Supplier Food Safety Records ({records.length})</h2></div>
        {loading ? <div className="p-6 text-sm text-gray-400 text-center">Loading…</div> : records.length === 0 ? <div className="p-6 text-sm text-gray-400 text-center">No records.</div> : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-gray-50 text-xs text-gray-500">
                <tr>
                  <th className="text-left px-4 py-2">Supplier</th>
                  <th className="text-left px-4 py-2">Type</th>
                  <th className="text-left px-4 py-2">Status</th>
                  <th className="text-left px-4 py-2">Score</th>
                  <th className="text-left px-4 py-2">Expiry</th>
                  <th className="text-left px-4 py-2">Findings</th>
                </tr>
              </thead>
              <tbody className="divide-y">
                {records.map((r) => (
                  <tr key={r.id} className={(r.days_to_expiry !== null && r.days_to_expiry < 0) ? "bg-red-50" : (r.critical_findings > 0) ? "bg-orange-50" : ""}>
                    <td className="px-4 py-2.5 font-medium text-gray-900">{r.supplier_name}</td>
                    <td className="px-4 py-2.5 text-xs text-gray-600">{r.approval_type.replace(/_/g, " ")}</td>
                    <td className="px-4 py-2.5"><span className={`text-xs rounded-full px-2 py-0.5 ${STATUS_COLOR[r.status] ?? "bg-gray-100"}`}>{r.status}</span></td>
                    <td className="px-4 py-2.5 font-semibold text-gray-700">{r.audit_score !== null ? `${r.audit_score}%` : "—"}</td>
                    <td className={`px-4 py-2.5 text-xs ${urgency(r.days_to_expiry)}`}>
                      {r.expiry_date ? `${r.expiry_date} (${r.days_to_expiry !== null ? (r.days_to_expiry < 0 ? `Expired ${Math.abs(r.days_to_expiry)}d` : `${r.days_to_expiry}d`) : "—"})` : "—"}
                    </td>
                    <td className="px-4 py-2.5 text-xs">
                      {r.critical_findings > 0 && <span className="text-red-600 font-bold mr-1">C:{r.critical_findings}</span>}
                      {r.major_findings > 0 && <span className="text-orange-500 mr-1">M:{r.major_findings}</span>}
                      {r.minor_findings > 0 && <span className="text-gray-400">m:{r.minor_findings}</span>}
                      {r.critical_findings === 0 && r.major_findings === 0 && r.minor_findings === 0 && "—"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
