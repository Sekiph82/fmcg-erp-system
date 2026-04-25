"use client";
import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { faApi, FAAssetStatus, STATUS_BADGE, DEPR_METHOD_LABEL, fmtCurrency } from "@/lib/fixed_assets";

export default function FAAssetListPage() {
  const [search, setSearch]       = useState("");
  const [status, setStatus]       = useState<FAAssetStatus | "">("");
  const [costCenter, setCostCenter] = useState("");

  const { data = [], isLoading } = useQuery({
    queryKey: ["fa-assets", search, status, costCenter],
    queryFn: () => faApi.listAssets({
      search: search || undefined,
      status: (status as FAAssetStatus) || undefined,
      cost_center: costCenter || undefined,
    }),
  });

  return (
    <div className="p-6 space-y-5">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-900">Asset Register</h1>
        <Link href="/dashboard/fixed-assets/assets/new" className="glow-button">+ New Asset</Link>
      </div>

      {/* Filters */}
      <div className="glass-panel p-4 flex flex-wrap gap-3">
        <input
          type="text"
          placeholder="Search assets…"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="rounded-lg border border-gray-300 px-3 py-2 text-sm flex-1 min-w-[180px]"
        />
        <select
          value={status}
          onChange={(e) => setStatus(e.target.value as FAAssetStatus | "")}
          className="rounded-lg border border-gray-300 px-3 py-2 text-sm"
        >
          <option value="">All Statuses</option>
          {(["DRAFT","ACTIVE","SUSPENDED","IMPAIRED","DISPOSED","RETIRED","ARCHIVED"] as FAAssetStatus[]).map(s => (
            <option key={s} value={s}>{s}</option>
          ))}
        </select>
        <input
          type="text"
          placeholder="Cost Center"
          value={costCenter}
          onChange={(e) => setCostCenter(e.target.value)}
          className="rounded-lg border border-gray-300 px-3 py-2 text-sm w-36"
        />
      </div>

      {/* Table */}
      <div className="glass-table overflow-x-auto">
        <table className="min-w-full text-sm">
          <thead>
            <tr>
              {["Code","Name","Category","Method","Cost (KES)","Acc. Depr.","NBV","Status",""].map(h => (
                <th key={h} className="px-4 py-3 text-left">{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {isLoading ? (
              <tr><td colSpan={9} className="px-4 py-10 text-center text-gray-400">Loading…</td></tr>
            ) : data.length === 0 ? (
              <tr><td colSpan={9} className="px-4 py-10 text-center text-gray-400">No assets found.</td></tr>
            ) : data.map((a) => (
              <tr key={a.id}>
                <td className="px-4 py-3 font-mono text-xs font-medium">{a.asset_code}</td>
                <td className="px-4 py-3 font-medium max-w-[180px] truncate">{a.asset_name}</td>
                <td className="px-4 py-3 text-xs text-gray-500">{a.category_name ?? "—"}</td>
                <td className="px-4 py-3 text-xs">{DEPR_METHOD_LABEL[a.depreciation_method]}</td>
                <td className="px-4 py-3 text-right">{a.local_currency_cost.toLocaleString(undefined,{maximumFractionDigits:0})}</td>
                <td className="px-4 py-3 text-right text-orange-600">{a.accumulated_depreciation.toLocaleString(undefined,{maximumFractionDigits:0})}</td>
                <td className="px-4 py-3 text-right font-semibold text-green-600">{a.net_book_value.toLocaleString(undefined,{maximumFractionDigits:0})}</td>
                <td className="px-4 py-3">
                  <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${STATUS_BADGE[a.status]}`}>
                    {a.status}
                  </span>
                </td>
                <td className="px-4 py-3">
                  <Link href={`/dashboard/fixed-assets/assets/${a.id}`} className="text-blue-600 hover:underline text-xs">
                    Open
                  </Link>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <p className="text-xs text-gray-400">{data.length} assets</p>
    </div>
  );
}
