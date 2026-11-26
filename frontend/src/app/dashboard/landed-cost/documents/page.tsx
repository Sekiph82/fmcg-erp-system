"use client";
import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { lcApi, LC_STATUS_COLOR, LCStatus, LandedCostSummary, fmtCurrency } from "@/lib/landed_cost";
import { tx, lx } from "@/lib/i18n/core";

const STATUSES: { value: LCStatus | ""; label: string }[] = lx(() => [
  { value: "", label: tx("All") },
  { value: "DRAFT", label: tx("Draft") },
  { value: "VALIDATED", label: tx("Validated") },
  { value: "POSTED", label: tx("Posted") },
  { value: "CANCELLED", label: tx("Cancelled") },
]);

export default function LandedCostDocuments() {
  const [statusFilter, setStatusFilter] = useState<LCStatus | "">("");
  const [search, setSearch] = useState("");

  const { data = [], isLoading } = useQuery<LandedCostSummary[]>({
    queryKey: ["lc-docs", statusFilter],
    queryFn: () => lcApi.list(statusFilter ? { status: statusFilter } : undefined),
  });

  const filtered = data.filter((d) => {
    if (!search) return true;
    const q = search.toLowerCase();
    return (
      d.lc_no.toLowerCase().includes(q) ||
      (d.vendor_name ?? "").toLowerCase().includes(q) ||
      (d.bill_no ?? "").toLowerCase().includes(q)
    );
  });

  return (
    <div className="p-6 space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-900">{tx("Landed Cost Documents")}</h1>
        <Link
          href="/dashboard/landed-cost/new"
          className="px-4 py-2 bg-blue-600 text-white text-sm rounded-lg hover:bg-blue-700"
        >
          {tx("+ New Document")}
        </Link>
      </div>

      {/* Filters */}
      <div className="flex flex-wrap gap-3">
        <input
          className="border rounded-lg px-3 py-1.5 text-sm w-56"
          placeholder={tx("Search LC no, vendor, bill…")}
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
        <div className="flex gap-1">
          {STATUSES.map((s) => (
            <button
              key={s.value}
              onClick={() => setStatusFilter(s.value)}
              className={`px-3 py-1.5 text-xs rounded-lg border ${
                statusFilter === s.value
                  ? "bg-blue-600 text-white border-blue-600"
                  : "bg-white text-gray-600 hover:bg-gray-50"
              }`}
            >
              {s.label}
            </button>
          ))}
        </div>
      </div>

      {/* Table */}
      <div className="bg-white border rounded-xl overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-gray-50 text-xs text-gray-500 uppercase">
            <tr>
              {[tx("LC No"), tx("Bill No"), tx("Vendor"), tx("Bill Date"), tx("Currency"), tx("Total (Base)"), tx("Method"), tx("Status"), ""].map((h) => (
                <th key={h} className="px-4 py-2 text-left font-medium">{h}</th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {isLoading ? (
              <tr><td colSpan={9} className="px-4 py-6 text-center text-gray-400">{tx("Loading…")}</td></tr>
            ) : filtered.length === 0 ? (
              <tr><td colSpan={9} className="px-4 py-6 text-center text-gray-400">{tx("No documents found.")}</td></tr>
            ) : (
              filtered.map((doc) => (
                <tr key={doc.id} className="hover:bg-gray-50">
                  <td className="px-4 py-2 font-mono text-xs font-medium">{doc.lc_no}</td>
                  <td className="px-4 py-2 text-gray-600">{doc.bill_no ?? "—"}</td>
                  <td className="px-4 py-2">{doc.vendor_name ?? "—"}</td>
                  <td className="px-4 py-2 text-gray-600">{doc.bill_date ?? "—"}</td>
                  <td className="px-4 py-2">{doc.currency_code}</td>
                  <td className="px-4 py-2 font-medium">{fmtCurrency(doc.total_lc_amount_base)}</td>
                  <td className="px-4 py-2 text-gray-600 text-xs">{doc.allocation_method.replace(/_/g, " ")}</td>
                  <td className="px-4 py-2">
                    <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${LC_STATUS_COLOR[doc.status]}`}>
                      {doc.status}
                    </span>
                  </td>
                  <td className="px-4 py-2">
                    <Link href={`/dashboard/landed-cost/${doc.id}`} className="text-blue-600 hover:underline text-xs">
                      {tx("View")}
                    </Link>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
