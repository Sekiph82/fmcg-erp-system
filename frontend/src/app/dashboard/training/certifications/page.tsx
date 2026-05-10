"use client";
import { useCallback, useEffect, useState } from "react";
import {
  trainingApi, CertificationRecord, CertificationStatus, TrainingProgram,
  CERT_STATUS_COLOR,
} from "@/lib/training";

const STATUSES: CertificationStatus[] = ["valid","expiring","expired","revoked"];

export default function CertificationsPage() {
  const [certs, setCerts] = useState<CertificationRecord[]>([]);
  const [programs, setPrograms] = useState<TrainingProgram[]>([]);
  const [loading, setLoading] = useState(true);
  const [statusFilter, setStatusFilter] = useState("");
  const [empFilter, setEmpFilter] = useState("");
  const [showForm, setShowForm] = useState(false);
  const [editing, setEditing] = useState<CertificationRecord | null>(null);
  const [form, setForm] = useState({
    employee_id: "", employee_name: "", training_id: "",
    certificate_name: "", certificate_no: "", issuer: "",
    issue_date: "", expiry_date: "", notes: "",
  });
  const [editForm, setEditForm] = useState({ certificate_no: "", expiry_date: "", notes: "", status: "" as CertificationStatus | "" });

  const load = useCallback(() =>
    Promise.all([
      trainingApi.listCertifications({ status: statusFilter || undefined, employee_id: empFilter || undefined }),
      trainingApi.listPrograms(),
    ]).then(([c, p]) => { setCerts(c); setPrograms(p); }).finally(() => setLoading(false)), [statusFilter, empFilter]);
  useEffect(() => { load(); }, [load]);

  const submit = async () => {
    await trainingApi.createCertification({
      ...form,
      training_id: form.training_id || undefined,
      certificate_no: form.certificate_no || undefined,
      issuer: form.issuer || undefined,
      expiry_date: form.expiry_date || undefined,
      notes: form.notes || undefined,
    });
    setShowForm(false);
    load();
  };

  const saveEdit = async () => {
    if (!editing) return;
    await trainingApi.updateCertification(editing.certification_id, {
      certificate_no: editForm.certificate_no || undefined,
      expiry_date: editForm.expiry_date || undefined,
      notes: editForm.notes || undefined,
      status: editForm.status || undefined,
    });
    setEditing(null);
    load();
  };

  const refresh = async () => {
    const result = await trainingApi.refreshCertStatuses();
    alert(`Updated ${result.updated} certification statuses.`);
    load();
  };

  const expiringAlert = certs.filter(c => c.status === "expiring").length;
  const expiredAlert = certs.filter(c => c.status === "expired").length;

  return (
    <div className="p-6 space-y-4">
      <div className="flex items-center justify-between flex-wrap gap-2">
        <h1 className="text-xl font-bold text-gray-900">Certification Tracker</h1>
        <div className="flex gap-2">
          <button onClick={refresh} className="rounded border border-gray-300 px-3 py-1.5 text-sm text-gray-600 hover:bg-gray-50">
            Refresh Statuses
          </button>
          <button onClick={() => setShowForm(true)} className="rounded bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700">
            + Add Certification
          </button>
        </div>
      </div>

      {(expiringAlert > 0 || expiredAlert > 0) && (
        <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-3 text-sm text-yellow-800">
          {expiredAlert > 0 && <span className="font-semibold text-red-700">{expiredAlert} expired. </span>}
          {expiringAlert > 0 && <span className="font-semibold text-yellow-700">{expiringAlert} expiring within 30 days. </span>}
          Action required to maintain compliance.
        </div>
      )}

      <div className="flex gap-3 flex-wrap">
        <select className="border rounded px-2 py-1 text-sm" value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)}>
          <option value="">All Statuses</option>
          {STATUSES.map(s => <option key={s} value={s}>{s}</option>)}
        </select>
        <input className="border rounded px-2 py-1 text-sm w-40" placeholder="Employee ID…"
          value={empFilter} onChange={(e) => setEmpFilter(e.target.value)} />
      </div>

      {showForm && (
        <div className="bg-white border rounded-lg p-4 shadow-sm space-y-3">
          <h2 className="font-semibold text-gray-800">Add Certification</h2>
          <div className="grid grid-cols-2 gap-3">
            {(["employee_id","employee_name","certificate_name","certificate_no","issuer"] as const).map((f) => (
              <div key={f}>
                <label className="text-xs text-gray-500 capitalize">{f.replace(/_/g," ")}</label>
                <input className="w-full border rounded px-2 py-1 text-sm mt-1" value={form[f]}
                  onChange={(e) => setForm({ ...form, [f]: e.target.value })} />
              </div>
            ))}
            <div>
              <label className="text-xs text-gray-500">Linked Training Program</label>
              <select className="w-full border rounded px-2 py-1 text-sm mt-1" value={form.training_id}
                onChange={(e) => setForm({ ...form, training_id: e.target.value })}>
                <option value="">None</option>
                {programs.map(p => <option key={p.training_id} value={p.training_id}>{p.training_name}</option>)}
              </select>
            </div>
            <div>
              <label className="text-xs text-gray-500">Issue Date *</label>
              <input type="date" className="w-full border rounded px-2 py-1 text-sm mt-1"
                value={form.issue_date} onChange={(e) => setForm({ ...form, issue_date: e.target.value })} />
            </div>
            <div>
              <label className="text-xs text-gray-500">Expiry Date</label>
              <input type="date" className="w-full border rounded px-2 py-1 text-sm mt-1"
                value={form.expiry_date} onChange={(e) => setForm({ ...form, expiry_date: e.target.value })} />
            </div>
          </div>
          <div className="flex gap-2">
            <button onClick={submit} className="rounded bg-blue-600 px-4 py-1.5 text-sm text-white hover:bg-blue-700">Save</button>
            <button onClick={() => setShowForm(false)} className="rounded border px-4 py-1.5 text-sm text-gray-600 hover:bg-gray-50">Cancel</button>
          </div>
        </div>
      )}

      {loading ? (
        <p className="text-gray-500 text-sm">Loading…</p>
      ) : (
        <div className="bg-white border rounded-lg shadow-sm overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 border-b">
              <tr>
                {["Employee","Certificate","Cert No","Issuer","Issue Date","Expiry","Days Left","Status","Actions"].map(h=>(
                  <th key={h} className="px-3 py-2 text-left text-xs font-semibold text-gray-600">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y">
              {certs.map(c => (
                <tr key={c.certification_id} className="hover:bg-gray-50">
                  <td className="px-3 py-2 font-medium text-gray-800">{c.employee_name ?? c.employee_id}</td>
                  <td className="px-3 py-2 text-gray-700">{c.certificate_name}</td>
                  <td className="px-3 py-2 text-gray-500 font-mono text-xs">{c.certificate_no ?? "—"}</td>
                  <td className="px-3 py-2 text-gray-500">{c.issuer ?? "—"}</td>
                  <td className="px-3 py-2 text-gray-600">{c.issue_date}</td>
                  <td className="px-3 py-2 text-gray-600">{c.expiry_date ?? "No expiry"}</td>
                  <td className={`px-3 py-2 font-semibold ${c.days_to_expiry != null && c.days_to_expiry <= 0 ? "text-red-600" : c.days_to_expiry != null && c.days_to_expiry <= 30 ? "text-yellow-600" : "text-gray-600"}`}>
                    {c.days_to_expiry != null ? (c.days_to_expiry <= 0 ? "EXPIRED" : `${c.days_to_expiry}d`) : "—"}
                  </td>
                  <td className="px-3 py-2">
                    <span className={`inline-flex rounded-full px-2 py-0.5 text-xs font-medium ${CERT_STATUS_COLOR[c.status]}`}>
                      {c.status}
                    </span>
                  </td>
                  <td className="px-3 py-2">
                    <button
                      onClick={() => { setEditing(c); setEditForm({ certificate_no: c.certificate_no ?? "", expiry_date: c.expiry_date ?? "", notes: c.notes ?? "", status: c.status }); }}
                      className="text-xs text-blue-600 hover:underline"
                    >
                      Edit
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          {certs.length === 0 && <p className="text-center text-gray-400 py-8 text-sm">No certifications found.</p>}
        </div>
      )}

      {editing && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-lg shadow-xl w-full max-w-sm p-6 space-y-3">
            <div className="flex justify-between">
              <h2 className="font-bold text-gray-900">Update Certification</h2>
              <button onClick={() => setEditing(null)} className="text-gray-400 hover:text-gray-700">✕</button>
            </div>
            <p className="text-sm text-gray-600">{editing.certificate_name} — {editing.employee_name ?? editing.employee_id}</p>
            <div>
              <label className="text-xs text-gray-500">Certificate No</label>
              <input className="w-full border rounded px-2 py-1 text-sm mt-1" value={editForm.certificate_no}
                onChange={(e) => setEditForm({ ...editForm, certificate_no: e.target.value })} />
            </div>
            <div>
              <label className="text-xs text-gray-500">New Expiry Date</label>
              <input type="date" className="w-full border rounded px-2 py-1 text-sm mt-1" value={editForm.expiry_date}
                onChange={(e) => setEditForm({ ...editForm, expiry_date: e.target.value })} />
            </div>
            <div>
              <label className="text-xs text-gray-500">Status Override</label>
              <select className="w-full border rounded px-2 py-1 text-sm mt-1" value={editForm.status}
                onChange={(e) => setEditForm({ ...editForm, status: e.target.value as CertificationStatus })}>
                {STATUSES.map(s => <option key={s} value={s}>{s}</option>)}
              </select>
            </div>
            <div>
              <label className="text-xs text-gray-500">Notes</label>
              <textarea className="w-full border rounded px-2 py-1 text-sm mt-1" rows={2}
                value={editForm.notes} onChange={(e) => setEditForm({ ...editForm, notes: e.target.value })} />
            </div>
            <div className="flex gap-2">
              <button onClick={saveEdit} className="rounded bg-blue-600 px-4 py-1.5 text-sm text-white hover:bg-blue-700">Save</button>
              <button onClick={() => setEditing(null)} className="rounded border px-4 py-1.5 text-sm text-gray-600 hover:bg-gray-50">Cancel</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
