"use client";
import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { portalApi, PortalAccount, ACCOUNT_TYPE_LABELS, ACCOUNT_STATUS_COLORS } from "@/lib/portal";

export default function PortalAccountsPage() {
  const [accounts, setAccounts] = useState<PortalAccount[]>([]);
  const [loading, setLoading] = useState(true);
  const [statusFilter, setStatusFilter] = useState("");
  const [typeFilter, setTypeFilter] = useState("");

  const load = useCallback(() => {
    setLoading(true);
    portalApi.getAccounts({ status: statusFilter || undefined })
      .then(d => setAccounts(d as PortalAccount[]))
      .catch(console.error)
      .finally(() => setLoading(false));
  }, [statusFilter]);

  useEffect(() => { load(); }, [load]);

  const filtered = typeFilter ? accounts.filter(a => a.account_type === typeFilter) : accounts;

  return (
    <div className="p-6 space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-bold text-gray-900">All Portal Accounts</h1>
        <Link href="/dashboard/portal" className="text-sm text-gray-500 hover:underline">← Portal Admin</Link>
      </div>

      <div className="flex flex-wrap gap-3 items-center">
        <select value={statusFilter} onChange={e => setStatusFilter(e.target.value)}
          className="text-sm border rounded-lg px-2 py-1.5">
          <option value="">All Statuses</option>
          <option value="PENDING">Pending</option>
          <option value="ACTIVE">Active</option>
          <option value="SUSPENDED">Suspended</option>
          <option value="CLOSED">Closed</option>
        </select>
        <select value={typeFilter} onChange={e => setTypeFilter(e.target.value)}
          className="text-sm border rounded-lg px-2 py-1.5">
          <option value="">All Types</option>
          {Object.entries(ACCOUNT_TYPE_LABELS).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
        </select>
        <span className="text-sm text-gray-500">{filtered.length} accounts</span>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {loading && <div className="col-span-3 text-gray-400 py-6 text-center">Loading…</div>}
        {!loading && filtered.length === 0 && (
          <div className="col-span-3 text-gray-400 py-6 text-center">No accounts found</div>
        )}
        {filtered.map(acc => (
          <div key={acc.id} className="bg-white rounded-xl border shadow-sm p-4 hover:shadow-md transition-shadow">
            <div className="flex items-start justify-between mb-2">
              <div>
                <div className="font-semibold text-gray-800">{acc.primary_contact_name || acc.account_code}</div>
                <div className="font-mono text-xs text-gray-400">{acc.account_code}</div>
              </div>
              <span className="px-2 py-0.5 rounded-full text-xs font-medium"
                style={{ background: ACCOUNT_STATUS_COLORS[acc.portal_status] + "22", color: ACCOUNT_STATUS_COLORS[acc.portal_status] }}>
                {acc.portal_status}
              </span>
            </div>
            <div className="text-xs text-gray-500 space-y-1">
              <div>{ACCOUNT_TYPE_LABELS[acc.account_type]}</div>
              {acc.primary_contact_email && <div>{acc.primary_contact_email}</div>}
              <div>Order Mode: {acc.order_mode}</div>
            </div>
            <div className="mt-3 flex gap-2">
              <Link href={`/dashboard/portal/accounts/${acc.id}`}
                className="flex-1 text-center text-xs text-blue-600 border border-blue-200 py-1.5 rounded-lg hover:bg-blue-50">
                Manage
              </Link>
              <Link href={`/dashboard/portal/accounts/${acc.id}/view`}
                className="flex-1 text-center text-xs text-gray-600 border py-1.5 rounded-lg hover:bg-gray-50">
                Portal View
              </Link>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
