"use client";
import { useState, useEffect } from "react";
import { useParams } from "next/navigation";
import { spApi, SPAccount, SPDashboard, SP_STATUS_COLORS } from "@/lib/supplier_portal";

export default function SPAccountDetail() {
  const { id } = useParams<{ id: string }>();
  const [account, setAccount] = useState<SPAccount | null>(null);
  const [dashboard, setDashboard] = useState<SPDashboard | null>(null);
  const [editing, setEditing] = useState(false);
  const [form, setForm] = useState<Partial<SPAccount>>({});
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    spApi.getAccount(id).then((a) => { setAccount(a); setForm(a); });
    spApi.getDashboard(id).then(setDashboard);
  }, [id]);

  const save = async () => {
    if (!account) return;
    setSaving(true);
    const updated = await spApi.updateAccount(id, form);
    setAccount(updated);
    setEditing(false);
    setSaving(false);
  };

  if (!account) return <div className="p-6 text-gray-400">Loading...</div>;

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center gap-4">
        <a href="/dashboard/supplier-portal" className="text-blue-600 hover:underline text-sm">← Supplier Portal</a>
        <h1 className="text-2xl font-bold text-gray-900">Supplier Account</h1>
        <span className={`px-2 py-0.5 rounded-full text-xs font-semibold ${SP_STATUS_COLORS[account.portal_status]}`}>{account.portal_status}</span>
      </div>

      {/* Dashboard KPIs */}
      {dashboard && (
        <div className="grid grid-cols-5 gap-4">
          {[
            { label: "Open POs", value: dashboard.open_pos },
            { label: "Pending ACK", value: dashboard.pending_acknowledgment },
            { label: "Invoices (30d)", value: dashboard.uploaded_invoices_30d },
            { label: "Docs Uploaded (30d)", value: dashboard.uploaded_docs_30d },
            { label: "Expiring Certs", value: dashboard.expiring_certs, warn: dashboard.expiring_certs > 0 },
          ].map((k) => (
            <div key={k.label} className={`bg-white rounded-xl border p-4 ${k.warn ? "border-red-300" : "border-gray-200"}`}>
              <div className={`text-2xl font-bold ${k.warn ? "text-red-600" : "text-gray-900"}`}>{k.value}</div>
              <div className="text-xs text-gray-500 mt-1">{k.label}</div>
            </div>
          ))}
        </div>
      )}

      {/* Account Details */}
      <div className="grid grid-cols-2 gap-6">
        <div className="bg-white rounded-xl border border-gray-200 p-5">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-base font-semibold text-gray-900">Account Details</h2>
            {!editing && (
              <button onClick={() => setEditing(true)} className="text-xs text-blue-600 hover:underline">Edit</button>
            )}
          </div>
          {editing ? (
            <div className="space-y-3">
              {[
                { key: "primary_contact_name", label: "Contact Name" },
                { key: "primary_contact_email", label: "Contact Email" },
                { key: "primary_contact_phone", label: "Contact Phone" },
                { key: "default_currency", label: "Currency" },
                { key: "timezone", label: "Timezone" },
              ].map(({ key, label }) => (
                <div key={key}>
                  <label className="text-xs text-gray-600">{label}</label>
                  <input value={(form as any)[key] || ""}
                    onChange={(e) => setForm({ ...form, [key]: e.target.value })}
                    className="mt-1 w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" />
                </div>
              ))}
              <div className="flex gap-2 pt-1">
                <label className="flex items-center gap-2 text-sm">
                  <input type="checkbox" checked={!!form.can_view_payment}
                    onChange={(e) => setForm({ ...form, can_view_payment: e.target.checked })} />
                  Can View Payment
                </label>
                <label className="flex items-center gap-2 text-sm ml-4">
                  <input type="checkbox" checked={!!form.can_view_prices}
                    onChange={(e) => setForm({ ...form, can_view_prices: e.target.checked })} />
                  Can View Prices
                </label>
              </div>
              <div className="flex gap-2 pt-2">
                <button onClick={() => setEditing(false)} className="px-3 py-1.5 border border-gray-300 rounded-lg text-xs">Cancel</button>
                <button onClick={save} disabled={saving} className="px-3 py-1.5 bg-blue-600 text-white rounded-lg text-xs">Save</button>
              </div>
            </div>
          ) : (
            <div className="space-y-2 text-sm">
              {[
                ["Supplier ID", account.supplier_id],
                ["Contact Name", account.primary_contact_name],
                ["Email", account.primary_contact_email],
                ["Phone", account.primary_contact_phone],
                ["Currency", account.default_currency],
                ["Language", account.preferred_language],
                ["Timezone", account.timezone],
                ["Can View Prices", account.can_view_prices ? "Yes" : "No"],
                ["Can View Payment", account.can_view_payment ? "Yes" : "No"],
              ].map(([k, v]) => (
                <div key={String(k)} className="flex justify-between">
                  <span className="text-gray-500">{k}</span>
                  <span className="font-medium text-gray-900">{v || "—"}</span>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Quick Links */}
        <div className="bg-white rounded-xl border border-gray-200 p-5">
          <h2 className="text-base font-semibold text-gray-900 mb-4">Quick Access</h2>
          <div className="grid grid-cols-2 gap-3">
            {[
              { label: "Purchase Orders", href: `/dashboard/supplier-portal/accounts/${id}/purchase-orders`, icon: "📋" },
              { label: "ETA Management", href: `/dashboard/supplier-portal/eta?account=${id}`, icon: "📅" },
              { label: "Documents", href: `/dashboard/supplier-portal/documents?account=${id}`, icon: "📁" },
              { label: "Invoices", href: `/dashboard/supplier-portal/invoices?account=${id}`, icon: "🧾" },
              { label: "Payment Status", href: `/dashboard/supplier-portal/payment?account=${id}`, icon: "💳" },
              { label: "Users", href: `/dashboard/supplier-portal/users?account=${id}`, icon: "👥" },
              { label: "Activity Log", href: `/dashboard/supplier-portal/activity?account=${id}`, icon: "📝" },
            ].map((l) => (
              <a key={l.label} href={l.href}
                className="flex items-center gap-2 p-3 border border-gray-200 rounded-lg hover:border-blue-400 hover:bg-blue-50 text-sm font-medium text-gray-700">
                <span>{l.icon}</span>{l.label}
              </a>
            ))}
          </div>
        </div>
      </div>

      {/* AI Alerts */}
      {dashboard && dashboard.ai_alerts.length > 0 && (
        <div className="bg-white rounded-xl border border-gray-200 p-5">
          <h2 className="text-base font-semibold text-gray-900 mb-3">AI Alerts</h2>
          <div className="space-y-2">
            {dashboard.ai_alerts.map((a) => (
              <div key={a.id} className={`p-3 rounded-lg border text-sm ${a.severity === "CRITICAL" ? "border-red-200 bg-red-50" : a.severity === "WARNING" ? "border-yellow-200 bg-yellow-50" : "border-blue-200 bg-blue-50"}`}>
                <div className="font-medium">{a.title}</div>
                <div className="text-gray-600 text-xs mt-0.5">{a.body}</div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Recent Activity */}
      {dashboard && (
        <div className="bg-white rounded-xl border border-gray-200 p-5">
          <h2 className="text-base font-semibold text-gray-900 mb-3">Recent Activity</h2>
          <table className="w-full text-sm">
            <thead>
              <tr className="text-xs text-gray-500 border-b">
                <th className="pb-2 text-left">Type</th>
                <th className="pb-2 text-left">Reference</th>
                <th className="pb-2 text-left">When</th>
              </tr>
            </thead>
            <tbody>
              {dashboard.recent_activity.map((a) => (
                <tr key={a.id} className="border-b border-gray-50">
                  <td className="py-2 font-medium">{a.activity_type}</td>
                  <td className="py-2 text-gray-500">{a.reference_type} {a.reference_id?.slice(0, 8)}</td>
                  <td className="py-2 text-gray-500">{new Date(a.activity_datetime).toLocaleString()}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
