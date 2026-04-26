"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import { portalApi, PortalAccount, ACCOUNT_TYPE_LABELS, ACCOUNT_STATUS_COLORS } from "@/lib/portal";

export default function PortalAdminPage() {
  const [accounts, setAccounts] = useState<PortalAccount[]>([]);
  const [loading, setLoading] = useState(true);
  const [statusFilter, setStatusFilter] = useState("");
  const [showCreate, setShowCreate] = useState(false);
  const [form, setForm] = useState({
    account_type: "CUSTOMER",
    linked_customer_id: "",
    linked_distributor_id: "",
    primary_contact_name: "",
    primary_contact_email: "",
    primary_contact_phone: "",
    can_view_prices: true,
    can_view_promotions: false,
    can_initiate_payment: false,
    order_mode: "DRAFT_REQUEST",
  });
  const [saving, setSaving] = useState(false);
  const [report, setReport] = useState<Record<string, unknown> | null>(null);

  const load = () => {
    setLoading(true);
    Promise.all([
      portalApi.getAccounts({ status: statusFilter || undefined }),
      portalApi.getAdoptionReport(),
    ]).then(([accs, rep]) => {
      setAccounts(accs as PortalAccount[]);
      setReport(rep as Record<string, unknown>);
    }).catch(console.error).finally(() => setLoading(false));
  };

  useEffect(() => { load(); }, [statusFilter]);

  const handleCreate = async () => {
    setSaving(true);
    try {
      await portalApi.createAccount(form as Partial<PortalAccount>);
      setShowCreate(false);
      load();
    } catch (e) { console.error(e); }
    setSaving(false);
  };

  const handleActivate = async (id: string) => {
    try { await portalApi.activateAccount(id); load(); } catch (e) { console.error(e); }
  };

  const handleSuspend = async (id: string) => {
    try { await portalApi.suspendAccount(id); load(); } catch (e) { console.error(e); }
  };

  const adoptionKpis = report ? [
    { label: "Total Accounts", value: report.total_accounts as number },
    { label: "Active Accounts", value: report.active_accounts as number },
    { label: "Activation Rate", value: `${report.activation_rate_pct}%` },
    { label: "Total Portal Users", value: report.total_users as number },
    { label: "Active Users", value: report.active_users as number },
    { label: "Logins (30d)", value: report.logins_last_30_days as number },
    { label: "Orders Submitted (30d)", value: report.orders_submitted_last_30_days as number },
    { label: "Claims (30d)", value: report.claims_submitted_last_30_days as number },
  ] : [];

  const quickLinks = [
    { href: "/dashboard/portal/accounts", label: "All Accounts" },
    { href: "/dashboard/portal/drafts", label: "Draft Orders Queue" },
    { href: "/dashboard/portal/claims", label: "Claims Review" },
    { href: "/dashboard/portal/users", label: "Portal Users" },
    { href: "/dashboard/portal/activity", label: "Activity Log" },
    { href: "/dashboard/portal/ai", label: "AI Agents" },
    { href: "/dashboard/portal/reports", label: "Reports" },
  ];

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Customer / Distributor Portal</h1>
          <p className="text-gray-500 text-sm mt-0.5">B2B self-service portal management</p>
        </div>
        <button onClick={() => setShowCreate(true)}
          className="px-3 py-1.5 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700">
          + New Portal Account
        </button>
      </div>

      {/* Adoption KPIs */}
      {report && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          {adoptionKpis.map(k => (
            <div key={k.label} className="bg-white rounded-xl border shadow-sm p-3">
              <div className="text-xs text-gray-500">{k.label}</div>
              <div className="text-xl font-bold text-gray-800 mt-0.5">{k.value}</div>
            </div>
          ))}
        </div>
      )}

      {/* Quick Links */}
      <div className="bg-white rounded-xl border shadow-sm p-4">
        <h2 className="font-semibold text-gray-800 mb-3">Quick Links</h2>
        <div className="flex flex-wrap gap-2">
          {quickLinks.map(l => (
            <Link key={l.href} href={l.href}
              className="px-3 py-1.5 text-sm border border-gray-200 rounded-lg hover:bg-gray-50 text-gray-700">
              {l.label}
            </Link>
          ))}
        </div>
      </div>

      {/* Accounts Table */}
      <div>
        <div className="flex items-center justify-between mb-3">
          <h2 className="font-semibold text-gray-800">Portal Accounts</h2>
          <select value={statusFilter} onChange={e => setStatusFilter(e.target.value)}
            className="text-sm border rounded-lg px-2 py-1.5">
            <option value="">All Statuses</option>
            <option value="PENDING">Pending</option>
            <option value="ACTIVE">Active</option>
            <option value="SUSPENDED">Suspended</option>
            <option value="CLOSED">Closed</option>
          </select>
        </div>
        <div className="bg-white rounded-xl border shadow-sm overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b bg-gray-50 text-xs text-gray-600">
                <th className="px-3 py-2 text-left">Code</th>
                <th className="px-3 py-2 text-left">Type</th>
                <th className="px-3 py-2 text-left">Contact</th>
                <th className="px-3 py-2 text-left">Linked ID</th>
                <th className="px-3 py-2 text-left">Status</th>
                <th className="px-3 py-2 text-left">Order Mode</th>
                <th className="px-3 py-2 text-left">Actions</th>
              </tr>
            </thead>
            <tbody>
              {loading && <tr><td colSpan={7} className="px-3 py-6 text-center text-gray-400">Loading…</td></tr>}
              {!loading && accounts.length === 0 && <tr><td colSpan={7} className="px-3 py-6 text-center text-gray-400">No portal accounts</td></tr>}
              {accounts.map(acc => (
                <tr key={acc.id} className="border-b hover:bg-gray-50">
                  <td className="px-3 py-2 font-mono text-xs text-gray-600">{acc.account_code}</td>
                  <td className="px-3 py-2 text-xs text-gray-600">{ACCOUNT_TYPE_LABELS[acc.account_type]}</td>
                  <td className="px-3 py-2">
                    <div className="text-gray-800 text-xs">{acc.primary_contact_name || "—"}</div>
                    <div className="text-gray-400 text-xs">{acc.primary_contact_email}</div>
                  </td>
                  <td className="px-3 py-2 text-xs text-gray-500">
                    {acc.linked_customer_id || acc.linked_distributor_id || "—"}
                  </td>
                  <td className="px-3 py-2">
                    <span className="px-2 py-0.5 rounded-full text-xs font-medium"
                      style={{ background: ACCOUNT_STATUS_COLORS[acc.portal_status] + "22", color: ACCOUNT_STATUS_COLORS[acc.portal_status] }}>
                      {acc.portal_status}
                    </span>
                  </td>
                  <td className="px-3 py-2 text-xs text-gray-500">{acc.order_mode}</td>
                  <td className="px-3 py-2 flex items-center gap-2">
                    <Link href={`/dashboard/portal/accounts/${acc.id}`}
                      className="text-xs text-blue-600 hover:underline">Manage</Link>
                    {acc.portal_status === "PENDING" && (
                      <button onClick={() => handleActivate(acc.id)}
                        className="text-xs text-green-600 hover:underline">Activate</button>
                    )}
                    {acc.portal_status === "ACTIVE" && (
                      <button onClick={() => handleSuspend(acc.id)}
                        className="text-xs text-red-600 hover:underline">Suspend</button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Create Modal */}
      {showCreate && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl shadow-xl p-6 w-full max-w-md space-y-3 max-h-screen overflow-y-auto">
            <h2 className="font-semibold text-lg">New Portal Account</h2>
            <select value={form.account_type} onChange={e => setForm(f => ({ ...f, account_type: e.target.value }))}
              className="w-full border rounded-lg px-3 py-2 text-sm">
              {Object.entries(ACCOUNT_TYPE_LABELS).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
            </select>
            <input placeholder="Linked Customer ID" value={form.linked_customer_id}
              onChange={e => setForm(f => ({ ...f, linked_customer_id: e.target.value }))}
              className="w-full border rounded-lg px-3 py-2 text-sm" />
            <input placeholder="Linked Distributor ID" value={form.linked_distributor_id}
              onChange={e => setForm(f => ({ ...f, linked_distributor_id: e.target.value }))}
              className="w-full border rounded-lg px-3 py-2 text-sm" />
            <input placeholder="Primary Contact Name" value={form.primary_contact_name}
              onChange={e => setForm(f => ({ ...f, primary_contact_name: e.target.value }))}
              className="w-full border rounded-lg px-3 py-2 text-sm" />
            <input placeholder="Primary Contact Email" value={form.primary_contact_email}
              onChange={e => setForm(f => ({ ...f, primary_contact_email: e.target.value }))}
              className="w-full border rounded-lg px-3 py-2 text-sm" />
            <select value={form.order_mode} onChange={e => setForm(f => ({ ...f, order_mode: e.target.value }))}
              className="w-full border rounded-lg px-3 py-2 text-sm">
              <option value="DRAFT_REQUEST">Draft Request (requires approval)</option>
              <option value="DIRECT_SUBMIT">Direct Submit</option>
              <option value="REORDER_ONLY">Reorder Only</option>
            </select>
            <div className="flex flex-col gap-2 text-sm">
              <label className="flex items-center gap-2"><input type="checkbox" checked={form.can_view_prices} onChange={e => setForm(f => ({ ...f, can_view_prices: e.target.checked }))} /> Can View Prices</label>
              <label className="flex items-center gap-2"><input type="checkbox" checked={form.can_view_promotions} onChange={e => setForm(f => ({ ...f, can_view_promotions: e.target.checked }))} /> Can View Promotions</label>
              <label className="flex items-center gap-2"><input type="checkbox" checked={form.can_initiate_payment} onChange={e => setForm(f => ({ ...f, can_initiate_payment: e.target.checked }))} /> Can Initiate Payment</label>
            </div>
            <div className="flex gap-2 pt-1">
              <button onClick={handleCreate} disabled={saving}
                className="flex-1 bg-blue-600 text-white py-2 rounded-lg text-sm disabled:opacity-50">
                {saving ? "Creating…" : "Create"}
              </button>
              <button onClick={() => setShowCreate(false)} className="flex-1 border rounded-lg py-2 text-sm">Cancel</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
