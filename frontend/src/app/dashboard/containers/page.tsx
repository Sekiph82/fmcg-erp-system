"use client";
import { useEffect, useState } from "react";
import Link from "next/link";

interface ContainerStats {
  total_issuances: number;
  containers_outstanding: number;
  overdue_issuances: number;
  written_off_issuances: number;
  deposit_at_risk_kes: number;
}

interface ContainerType {
  id: string;
  code: string;
  name: string;
  deposit_amount: number;
  currency: string;
  material: string | null;
  capacity_liters: number | null;
  active_flag: boolean;
}

interface NewTypeForm {
  code: string;
  name: string;
  deposit_amount: string;
  material: string;
  capacity_liters: string;
}

interface IssueForm {
  customer_id: string;
  customer_name: string;
  container_type_id: string;
  qty_issued: string;
  delivery_ref: string;
  return_due_days: string;
  notes: string;
}

const EMPTY_ISSUE: IssueForm = {
  customer_id: "", customer_name: "", container_type_id: "",
  qty_issued: "1", delivery_ref: "", return_due_days: "14", notes: "",
};

export default function ContainerManagementPage() {
  const [stats, setStats] = useState<ContainerStats | null>(null);
  const [types, setTypes] = useState<ContainerType[]>([]);
  const [loading, setLoading] = useState(true);
  const [showTypeForm, setShowTypeForm] = useState(false);
  const [showIssueForm, setShowIssueForm] = useState(false);
  const [typeForm, setTypeForm] = useState<NewTypeForm>({ code: "", name: "", deposit_amount: "0", material: "", capacity_liters: "" });
  const [issueForm, setIssueForm] = useState<IssueForm>(EMPTY_ISSUE);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [issueResult, setIssueResult] = useState<Record<string, unknown> | null>(null);

  const load = () => {
    setLoading(true);
    Promise.all([
      fetch("/api/v1/containers/stats").then((r) => r.json()),
      fetch("/api/v1/containers/types").then((r) => r.json()),
    ]).then(([s, t]) => { setStats(s); setTypes(t); }).finally(() => setLoading(false));
  };

  useEffect(load, []);

  const saveType = async () => {
    setSaving(true);
    setError(null);
    try {
      const r = await fetch("/api/v1/containers/types", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          code: typeForm.code,
          name: typeForm.name,
          deposit_amount: Number(typeForm.deposit_amount),
          material: typeForm.material || undefined,
          capacity_liters: typeForm.capacity_liters ? Number(typeForm.capacity_liters) : undefined,
        }),
      });
      if (!r.ok) throw new Error(await r.text());
      setShowTypeForm(false);
      setTypeForm({ code: "", name: "", deposit_amount: "0", material: "", capacity_liters: "" });
      load();
    } catch (e) { setError(String(e)); }
    setSaving(false);
  };

  const issue = async () => {
    setSaving(true);
    setError(null);
    try {
      const r = await fetch("/api/v1/containers/issue", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          customer_id: issueForm.customer_id,
          customer_name: issueForm.customer_name || undefined,
          container_type_id: issueForm.container_type_id,
          qty_issued: Number(issueForm.qty_issued),
          delivery_ref: issueForm.delivery_ref || undefined,
          return_due_days: Number(issueForm.return_due_days),
          notes: issueForm.notes || undefined,
        }),
      });
      if (!r.ok) throw new Error(await r.text());
      const res = await r.json();
      setIssueResult(res);
      setIssueForm(EMPTY_ISSUE);
      setShowIssueForm(false);
      load();
    } catch (e) { setError(String(e)); }
    setSaving(false);
  };

  const links = [
    { href: "/dashboard/containers/outstanding", label: "Outstanding Containers", desc: "All unresolved issuances incl. overdue" },
    { href: "/dashboard/containers", label: "Container Types", desc: "Manage returnable container catalog" },
  ];

  return (
    <div className="p-6 space-y-6 max-w-5xl mx-auto">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Returnable Container Management</h1>
          <p className="text-sm text-gray-500 mt-0.5">Track crates, drums, pallets, and bottles issued to customers</p>
        </div>
        <div className="flex gap-2">
          <button onClick={() => { setShowTypeForm(true); setShowIssueForm(false); }}
            className="border border-gray-300 rounded px-3 py-1.5 text-sm text-gray-600 hover:bg-gray-50">
            + Type
          </button>
          <button onClick={() => { setShowIssueForm(true); setShowTypeForm(false); }}
            className="bg-blue-600 hover:bg-blue-700 text-white text-sm font-medium px-4 py-1.5 rounded">
            Issue Containers
          </button>
        </div>
      </div>

      {error && <div className="bg-red-50 border border-red-200 rounded p-3 text-sm text-red-700">{error}</div>}
      {issueResult && (
        <div className="bg-green-50 border border-green-200 rounded-lg p-4 text-sm text-green-700">
          <p className="font-semibold">Containers issued — Ref: {issueResult.issuance_ref as string}</p>
          <p>Qty: {issueResult.qty_issued as number} · Deposit: KES {(issueResult.deposit_charged as number)?.toLocaleString()} · Due: {issueResult.return_due_date as string}</p>
          <button onClick={() => setIssueResult(null)} className="text-xs underline mt-1">Dismiss</button>
        </div>
      )}

      {/* KPI strip */}
      {!loading && stats && (
        <div className="grid grid-cols-2 gap-4 sm:grid-cols-5">
          {[
            { label: "Total Issuances", value: stats.total_issuances, color: "text-gray-800" },
            { label: "Containers Out", value: stats.containers_outstanding, color: "text-blue-600" },
            { label: "Overdue", value: stats.overdue_issuances, color: "text-red-600" },
            { label: "Written Off", value: stats.written_off_issuances, color: "text-orange-500" },
            { label: "Deposit at Risk (KES)", value: `${Math.round(stats.deposit_at_risk_kes).toLocaleString()}`, color: "text-amber-600" },
          ].map((k) => (
            <div key={k.label} className="bg-white border rounded-lg p-3 shadow-sm">
              <p className="text-xs text-gray-500">{k.label}</p>
              <p className={`text-xl font-bold mt-1 ${k.color}`}>{k.value}</p>
            </div>
          ))}
        </div>
      )}

      {/* Quick nav */}
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
        {links.map((l) => (
          <Link key={l.href} href={l.href}
            className="flex flex-col rounded border border-blue-200 bg-blue-50 px-4 py-3 hover:bg-blue-100">
            <span className="text-sm font-semibold text-blue-700">{l.label}</span>
            <span className="text-xs text-blue-500 mt-0.5">{l.desc}</span>
          </Link>
        ))}
      </div>

      {/* Add type form */}
      {showTypeForm && (
        <div className="bg-white border rounded-lg p-4 shadow-sm space-y-3">
          <h2 className="text-sm font-semibold text-gray-700">New Container Type</h2>
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {[
              { label: "Code *", key: "code", placeholder: "e.g. CRATE-20L" },
              { label: "Name *", key: "name", placeholder: "e.g. 20L Plastic Crate" },
              { label: "Deposit Amount (KES) *", key: "deposit_amount", placeholder: "e.g. 150" },
              { label: "Material", key: "material", placeholder: "plastic | glass | metal" },
              { label: "Capacity (Litres)", key: "capacity_liters", placeholder: "e.g. 20" },
            ].map(({ label, key, placeholder }) => (
              <div key={key}>
                <label className="text-xs text-gray-500 block mb-1">{label}</label>
                <input type="text" placeholder={placeholder}
                  value={(typeForm as unknown as Record<string, string>)[key]}
                  onChange={(e) => setTypeForm((p) => ({ ...p, [key]: e.target.value }))}
                  className="w-full border border-gray-300 rounded px-3 py-1.5 text-sm focus:outline-none focus:ring-1 focus:ring-blue-500" />
              </div>
            ))}
          </div>
          <div className="flex gap-2">
            <button onClick={saveType} disabled={saving || !typeForm.code || !typeForm.name}
              className="bg-blue-600 text-white text-sm px-4 py-2 rounded disabled:opacity-50">{saving ? "Saving…" : "Create Type"}</button>
            <button onClick={() => setShowTypeForm(false)} className="border border-gray-300 text-sm px-4 py-2 rounded hover:bg-gray-50">Cancel</button>
          </div>
        </div>
      )}

      {/* Issue form */}
      {showIssueForm && (
        <div className="bg-white border rounded-lg p-4 shadow-sm space-y-3">
          <h2 className="text-sm font-semibold text-gray-700">Issue Containers</h2>
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
            <div>
              <label className="text-xs text-gray-500 block mb-1">Customer ID *</label>
              <input type="text" value={issueForm.customer_id} placeholder="UUID"
                onChange={(e) => setIssueForm((p) => ({ ...p, customer_id: e.target.value }))}
                className="w-full border border-gray-300 rounded px-3 py-1.5 text-sm focus:outline-none focus:ring-1 focus:ring-blue-500" />
            </div>
            <div>
              <label className="text-xs text-gray-500 block mb-1">Customer Name</label>
              <input type="text" value={issueForm.customer_name} placeholder="e.g. Nairobi Distributors"
                onChange={(e) => setIssueForm((p) => ({ ...p, customer_name: e.target.value }))}
                className="w-full border border-gray-300 rounded px-3 py-1.5 text-sm focus:outline-none focus:ring-1 focus:ring-blue-500" />
            </div>
            <div>
              <label className="text-xs text-gray-500 block mb-1">Container Type *</label>
              <select value={issueForm.container_type_id}
                onChange={(e) => setIssueForm((p) => ({ ...p, container_type_id: e.target.value }))}
                className="w-full border border-gray-300 rounded px-3 py-1.5 text-sm focus:outline-none focus:ring-1 focus:ring-blue-500">
                <option value="">— Select type —</option>
                {types.map((t) => <option key={t.id} value={t.id}>{t.name} (KES {t.deposit_amount}/unit)</option>)}
              </select>
            </div>
            <div>
              <label className="text-xs text-gray-500 block mb-1">Qty Issued *</label>
              <input type="number" min={1} value={issueForm.qty_issued}
                onChange={(e) => setIssueForm((p) => ({ ...p, qty_issued: e.target.value }))}
                className="w-full border border-gray-300 rounded px-3 py-1.5 text-sm focus:outline-none focus:ring-1 focus:ring-blue-500" />
            </div>
            <div>
              <label className="text-xs text-gray-500 block mb-1">Delivery Ref</label>
              <input type="text" value={issueForm.delivery_ref} placeholder="e.g. DEL-001"
                onChange={(e) => setIssueForm((p) => ({ ...p, delivery_ref: e.target.value }))}
                className="w-full border border-gray-300 rounded px-3 py-1.5 text-sm focus:outline-none focus:ring-1 focus:ring-blue-500" />
            </div>
            <div>
              <label className="text-xs text-gray-500 block mb-1">Return Due (Days)</label>
              <input type="number" min={1} value={issueForm.return_due_days}
                onChange={(e) => setIssueForm((p) => ({ ...p, return_due_days: e.target.value }))}
                className="w-full border border-gray-300 rounded px-3 py-1.5 text-sm focus:outline-none focus:ring-1 focus:ring-blue-500" />
            </div>
          </div>
          <div className="flex gap-2">
            <button onClick={issue} disabled={saving || !issueForm.customer_id || !issueForm.container_type_id || !issueForm.qty_issued}
              className="bg-blue-600 text-white text-sm px-4 py-2 rounded disabled:opacity-50">{saving ? "Issuing…" : "Issue Containers"}</button>
            <button onClick={() => setShowIssueForm(false)} className="border border-gray-300 text-sm px-4 py-2 rounded hover:bg-gray-50">Cancel</button>
          </div>
        </div>
      )}

      {/* Container types list */}
      <div className="bg-white border rounded-lg shadow-sm overflow-hidden">
        <div className="px-4 py-3 border-b bg-gray-50">
          <h2 className="text-sm font-semibold text-gray-700">Container Types <span className="font-normal text-gray-400">({types.length})</span></h2>
        </div>
        {loading ? <div className="p-6 text-sm text-gray-400 text-center">Loading…</div> : types.length === 0 ? (
          <div className="p-6 text-sm text-gray-400 text-center">No container types yet. Add one above.</div>
        ) : (
          <table className="w-full text-sm">
            <thead className="bg-gray-50 text-xs text-gray-500">
              <tr>
                <th className="text-left px-4 py-2">Code</th>
                <th className="text-left px-4 py-2">Name</th>
                <th className="text-left px-4 py-2">Deposit</th>
                <th className="text-left px-4 py-2">Material</th>
                <th className="text-left px-4 py-2">Capacity</th>
              </tr>
            </thead>
            <tbody className="divide-y">
              {types.map((t) => (
                <tr key={t.id}>
                  <td className="px-4 py-2.5 font-mono text-xs text-gray-600">{t.code}</td>
                  <td className="px-4 py-2.5 font-medium text-gray-900">{t.name}</td>
                  <td className="px-4 py-2.5 text-gray-700">{t.currency} {t.deposit_amount.toLocaleString()}</td>
                  <td className="px-4 py-2.5 text-gray-500 capitalize">{t.material ?? "—"}</td>
                  <td className="px-4 py-2.5 text-gray-500">{t.capacity_liters ? `${t.capacity_liters}L` : "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
