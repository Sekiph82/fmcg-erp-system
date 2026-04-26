"use client";
import { useState, useEffect } from "react";
import { spApi, SPAccount, SPAccountStatus, SP_STATUS_COLORS } from "@/lib/supplier_portal";

export default function SupplierPortalAdmin() {
  const [accounts, setAccounts] = useState<SPAccount[]>([]);
  const [loading, setLoading] = useState(true);
  const [statusFilter, setStatusFilter] = useState("");
  const [creating, setCreating] = useState(false);
  const [form, setForm] = useState({ supplier_id: "", primary_contact_name: "", primary_contact_email: "", primary_contact_phone: "", notes: "" });

  const load = () => {
    setLoading(true);
    spApi.listAccounts(statusFilter || undefined).then(setAccounts).finally(() => setLoading(false));
  };

  useEffect(() => { load(); }, [statusFilter]);

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    await spApi.createAccount(form);
    setCreating(false);
    setForm({ supplier_id: "", primary_contact_name: "", primary_contact_email: "", primary_contact_phone: "", notes: "" });
    load();
  };

  const badge = (s: SPAccountStatus) => (
    <span className={`px-2 py-0.5 rounded-full text-xs font-semibold ${SP_STATUS_COLORS[s]}`}>{s}</span>
  );

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Supplier Portal</h1>
          <p className="text-sm text-gray-500 mt-1">External supplier collaboration hub — POs, invoices, documents</p>
        </div>
        <button onClick={() => setCreating(true)} className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700">
          + Onboard Supplier
        </button>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-4 gap-4">
        {(["PENDING", "ACTIVE", "SUSPENDED", "CLOSED"] as SPAccountStatus[]).map((s) => (
          <div key={s} className="bg-white rounded-xl border border-gray-200 p-4">
            <div className="text-2xl font-bold text-gray-900">{accounts.filter((a) => a.portal_status === s).length}</div>
            <div className="text-xs text-gray-500 mt-1">{s}</div>
          </div>
        ))}
      </div>

      {/* Filter */}
      <div className="flex gap-3 flex-wrap">
        {["", "PENDING", "ACTIVE", "SUSPENDED", "CLOSED"].map((s) => (
          <button key={s} onClick={() => setStatusFilter(s)}
            className={`px-3 py-1.5 rounded-lg text-xs font-medium border ${statusFilter === s ? "bg-blue-600 text-white border-blue-600" : "bg-white text-gray-600 border-gray-300 hover:border-blue-400"}`}>
            {s || "All"}
          </button>
        ))}
      </div>

      {/* Table */}
      <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-gray-50 border-b border-gray-200">
            <tr>
              {["Supplier ID", "Contact Name", "Email", "Phone", "Status", "Currency", "Can View Payment", "Actions"].map((h) => (
                <th key={h} className="px-4 py-3 text-left text-xs font-semibold text-gray-600 uppercase tracking-wide">{h}</th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {loading ? (
              <tr><td colSpan={8} className="px-4 py-8 text-center text-gray-400">Loading...</td></tr>
            ) : accounts.length === 0 ? (
              <tr><td colSpan={8} className="px-4 py-8 text-center text-gray-400">No supplier portal accounts found.</td></tr>
            ) : accounts.map((a) => (
              <tr key={a.id} className="hover:bg-gray-50">
                <td className="px-4 py-3 font-mono text-xs text-gray-500">{a.supplier_id.slice(0, 8)}…</td>
                <td className="px-4 py-3 font-medium text-gray-900">{a.primary_contact_name || "—"}</td>
                <td className="px-4 py-3 text-gray-600">{a.primary_contact_email || "—"}</td>
                <td className="px-4 py-3 text-gray-600">{a.primary_contact_phone || "—"}</td>
                <td className="px-4 py-3">{badge(a.portal_status)}</td>
                <td className="px-4 py-3 text-gray-600">{a.default_currency}</td>
                <td className="px-4 py-3">
                  <span className={`px-2 py-0.5 rounded-full text-xs ${a.can_view_payment ? "bg-green-100 text-green-700" : "bg-gray-100 text-gray-500"}`}>
                    {a.can_view_payment ? "Yes" : "No"}
                  </span>
                </td>
                <td className="px-4 py-3">
                  <a href={`/dashboard/supplier-portal/accounts/${a.id}`} className="text-blue-600 hover:underline text-xs mr-2">View</a>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Create Modal */}
      {creating && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl shadow-2xl p-6 w-full max-w-lg">
            <h2 className="text-lg font-bold text-gray-900 mb-4">Onboard Supplier to Portal</h2>
            <form onSubmit={handleCreate} className="space-y-4">
              <div>
                <label className="text-xs font-medium text-gray-700">Supplier ID</label>
                <input required value={form.supplier_id} onChange={(e) => setForm({ ...form, supplier_id: e.target.value })}
                  className="mt-1 w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500" placeholder="UUID of supplier" />
              </div>
              <div>
                <label className="text-xs font-medium text-gray-700">Primary Contact Name</label>
                <input value={form.primary_contact_name} onChange={(e) => setForm({ ...form, primary_contact_name: e.target.value })}
                  className="mt-1 w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" />
              </div>
              <div>
                <label className="text-xs font-medium text-gray-700">Primary Contact Email</label>
                <input type="email" value={form.primary_contact_email} onChange={(e) => setForm({ ...form, primary_contact_email: e.target.value })}
                  className="mt-1 w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" />
              </div>
              <div>
                <label className="text-xs font-medium text-gray-700">Primary Contact Phone</label>
                <input value={form.primary_contact_phone} onChange={(e) => setForm({ ...form, primary_contact_phone: e.target.value })}
                  className="mt-1 w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" />
              </div>
              <div>
                <label className="text-xs font-medium text-gray-700">Notes</label>
                <textarea value={form.notes} onChange={(e) => setForm({ ...form, notes: e.target.value })}
                  rows={2} className="mt-1 w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" />
              </div>
              <div className="flex justify-end gap-3 pt-2">
                <button type="button" onClick={() => setCreating(false)} className="px-4 py-2 border border-gray-300 rounded-lg text-sm">Cancel</button>
                <button type="submit" className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700">Create</button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
