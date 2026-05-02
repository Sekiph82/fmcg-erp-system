"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import { spApi, SPAccount, SPAccountStatus, SP_STATUS_COLORS } from "@/lib/supplier_portal";

export default function SupplierPortalAccountsPage() {
  const [accounts, setAccounts] = useState<SPAccount[]>([]);
  const [loading, setLoading] = useState(true);
  const [statusFilter, setStatusFilter] = useState("");
  const [search, setSearch] = useState("");

  useEffect(() => {
    setLoading(true);
    spApi.listAccounts(statusFilter || undefined)
      .then(setAccounts)
      .finally(() => setLoading(false));
  }, [statusFilter]);

  const filtered = accounts.filter((a) =>
    !search ||
    a.primary_contact_name?.toLowerCase().includes(search.toLowerCase()) ||
    a.primary_contact_email?.toLowerCase().includes(search.toLowerCase())
  );

  return (
    <div className="p-6 space-y-5 text-slate-200">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-white">Supplier Portal Accounts</h1>
          <p className="text-slate-500 text-sm mt-0.5">{filtered.length} accounts</p>
        </div>
        <Link
          href="/dashboard/supplier-portal"
          className="px-4 py-2 rounded-lg border border-white/[0.08] text-slate-400 text-sm hover:border-white/20"
        >
          ← Portal Admin
        </Link>
      </div>

      {/* Filters */}
      <div className="flex gap-3 flex-wrap">
        <input
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Search by name or email..."
          className="bg-white/[0.04] border border-white/[0.08] rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-indigo-500 w-64"
        />
        {(["", "PENDING", "ACTIVE", "SUSPENDED", "CLOSED"] as (SPAccountStatus | "")[]).map((s) => (
          <button
            key={s}
            onClick={() => setStatusFilter(s)}
            className={`px-3 py-1.5 rounded-lg text-xs font-medium border transition-colors ${
              statusFilter === s
                ? "bg-indigo-600 border-indigo-500 text-white"
                : "border-white/[0.08] text-slate-400 hover:border-white/20"
            }`}
          >
            {s || "All"}
          </button>
        ))}
      </div>

      {/* Accounts table */}
      <div className="rounded-xl border border-white/[0.07] overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-white/[0.03] text-slate-500 text-xs uppercase tracking-wider">
            <tr>
              <th className="px-4 py-3 text-left">Contact</th>
              <th className="px-4 py-3 text-left">Email</th>
              <th className="px-4 py-3 text-left">Phone</th>
              <th className="px-4 py-3 text-left">Status</th>
              <th className="px-4 py-3 text-left">Created</th>
              <th className="px-4 py-3 text-left">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-white/[0.04]">
            {loading && (
              <tr><td colSpan={6} className="text-center py-8 text-slate-600">Loading...</td></tr>
            )}
            {!loading && filtered.length === 0 && (
              <tr><td colSpan={6} className="text-center py-8 text-slate-600">No accounts found</td></tr>
            )}
            {filtered.map((a) => (
              <tr key={a.id} className="hover:bg-white/[0.02] transition-colors">
                <td className="px-4 py-3 text-white font-medium">
                  {a.primary_contact_name ?? <span className="text-slate-600">—</span>}
                </td>
                <td className="px-4 py-3 text-slate-400 text-xs">{a.primary_contact_email ?? "—"}</td>
                <td className="px-4 py-3 text-slate-400 text-xs">{a.primary_contact_phone ?? "—"}</td>
                <td className="px-4 py-3">
                  <span className={`text-[10px] px-2 py-0.5 rounded-full font-medium ${SP_STATUS_COLORS[a.portal_status]}`}>
                    {a.portal_status}
                  </span>
                </td>
                <td className="px-4 py-3 text-slate-500 text-xs">
                  {a.created_at ? new Date(a.created_at).toLocaleDateString() : "—"}
                </td>
                <td className="px-4 py-3">
                  <Link
                    href={`/dashboard/supplier-portal/accounts/${a.id}`}
                    className="text-xs text-indigo-400 hover:text-indigo-300"
                  >
                    View →
                  </Link>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
