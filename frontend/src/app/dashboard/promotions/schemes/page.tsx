"use client";
import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { promoApi, PromoScheme, SchemeStatus, SchemeType, SCHEME_TYPE_LABEL, STATUS_BADGE, fmtCurrency } from "@/lib/promotions";

export default function SchemesListPage() {
  const qc = useQueryClient();
  const [statusFilter, setStatusFilter] = useState<SchemeStatus | "">("");

  const { data: schemes = [], isLoading } = useQuery({
    queryKey: ["promo-schemes", statusFilter],
    queryFn: () => promoApi.getSchemes(statusFilter || undefined),
  });

  const activate = useMutation({
    mutationFn: (id: string) => promoApi.activateScheme(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["promo-schemes"] }),
  });

  const setStatus = useMutation({
    mutationFn: ({ id, status }: { id: string; status: SchemeStatus }) =>
      promoApi.updateSchemeStatus(id, status),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["promo-schemes"] }),
  });

  const today = new Date().toISOString().slice(0, 10);

  return (
    <div className="p-6 space-y-5">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Promotional Scheme Master</h1>
          <p className="text-sm text-gray-500">All trade and sales promotions configured in the system.</p>
        </div>
        <Link href="/dashboard/promotions/schemes/new" className="glow-button">+ New Scheme</Link>
      </div>

      <div className="liquid-glass p-3 flex items-center gap-3">
        <label className="text-xs text-gray-500">Status:</label>
        <select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value as SchemeStatus | "")}
          className="rounded-lg border border-gray-300 px-3 py-2 text-sm">
          <option value="">All Statuses</option>
          {(["DRAFT","APPROVED","ACTIVE","EXPIRED","SUSPENDED","ARCHIVED"] as SchemeStatus[]).map(s => (
            <option key={s} value={s}>{s}</option>
          ))}
        </select>
        <span className="text-xs text-gray-400">{schemes.length} schemes</span>
      </div>

      <div className="glass-table overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-blue-900/30">
              <th className="text-left px-4 py-3 text-xs font-semibold text-gray-400 uppercase">Code</th>
              <th className="text-left px-4 py-3 text-xs font-semibold text-gray-400 uppercase">Name</th>
              <th className="text-left px-4 py-3 text-xs font-semibold text-gray-400 uppercase">Type</th>
              <th className="text-left px-4 py-3 text-xs font-semibold text-gray-400 uppercase">Validity</th>
              <th className="text-center px-4 py-3 text-xs font-semibold text-gray-400 uppercase">Priority</th>
              <th className="text-center px-4 py-3 text-xs font-semibold text-gray-400 uppercase">Stack</th>
              <th className="text-right px-4 py-3 text-xs font-semibold text-gray-400 uppercase">Total Cost</th>
              <th className="text-center px-4 py-3 text-xs font-semibold text-gray-400 uppercase">Status</th>
              <th className="text-center px-4 py-3 text-xs font-semibold text-gray-400 uppercase">Actions</th>
            </tr>
          </thead>
          <tbody>
            {isLoading ? (
              <tr><td colSpan={9} className="text-center py-10 text-gray-400">Loading…</td></tr>
            ) : schemes.length === 0 ? (
              <tr><td colSpan={9} className="text-center py-10 text-gray-400">No schemes found.</td></tr>
            ) : schemes.map((s) => {
              const expiringSoon = s.status === "ACTIVE" && s.valid_to <= new Date(Date.now() + 7 * 86400000).toISOString().slice(0, 10);
              return (
                <tr key={s.id} className="border-b border-blue-900/20 hover:bg-blue-950/20 transition-colors">
                  <td className="px-4 py-3 font-mono text-xs text-indigo-300">{s.scheme_code}</td>
                  <td className="px-4 py-3">
                    <Link href={`/dashboard/promotions/schemes/${s.id}`} className="font-medium text-gray-200 hover:text-indigo-300">
                      {s.scheme_name}
                    </Link>
                  </td>
                  <td className="px-4 py-3 text-xs text-gray-400">{SCHEME_TYPE_LABEL[s.scheme_type]}</td>
                  <td className="px-4 py-3 text-xs text-gray-400">
                    {s.valid_from} → {s.valid_to}
                    {expiringSoon && <span className="ml-1 px-1 py-0.5 rounded bg-yellow-100 text-yellow-700 text-xs">Expiring</span>}
                  </td>
                  <td className="px-4 py-3 text-center text-gray-300">{s.priority_rank}</td>
                  <td className="px-4 py-3 text-center text-xs">
                    {s.stackable ? <span className="text-green-400">✓ Stack</span> : s.exclusive ? <span className="text-red-400">Exclusive</span> : "—"}
                  </td>
                  <td className="px-4 py-3 text-right text-gray-300">{fmtCurrency(s.total_cost)}</td>
                  <td className="px-4 py-3 text-center">
                    <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${STATUS_BADGE[s.status]}`}>
                      {s.status}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-center">
                    <div className="flex gap-1 justify-center">
                      {s.status === "DRAFT" && (
                        <button onClick={() => activate.mutate(s.id)}
                          className="glow-button text-xs !py-0.5 !px-2">Activate</button>
                      )}
                      {s.status === "ACTIVE" && (
                        <button onClick={() => setStatus.mutate({ id: s.id, status: "SUSPENDED" })}
                          className="glow-button-secondary text-xs !py-0.5 !px-2">Suspend</button>
                      )}
                      {s.status === "SUSPENDED" && (
                        <button onClick={() => setStatus.mutate({ id: s.id, status: "ACTIVE" })}
                          className="glow-button text-xs !py-0.5 !px-2">Resume</button>
                      )}
                      <Link href={`/dashboard/promotions/schemes/${s.id}`}
                        className="glow-button-secondary text-xs !py-0.5 !px-2">View</Link>
                    </div>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
