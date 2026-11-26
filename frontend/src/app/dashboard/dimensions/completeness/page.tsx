"use client";
import { useQuery } from "@tanstack/react-query";
import { dimApi } from "@/lib/dimensions";
import Link from "next/link";
import { tx } from "@/lib/i18n/core";

export default function CompletenessPage() {
  const { data: rows = [], isLoading } = useQuery({
    queryKey: ["dim-tagging-completeness"],
    queryFn: () => dimApi.getTaggingCompleteness(),
  });

  const { data: types = [] } = useQuery({
    queryKey: ["dim-types"],
    queryFn: () => dimApi.getTypes(),
  });

  const mandatory = types.filter((t) => t.is_mandatory);

  return (
    <div className="p-6 space-y-5">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">{tx("Tagging Completeness Report")}</h1>
          <p className="text-sm text-gray-500">{tx("Review dimension coverage across all transaction types.")}</p>
        </div>
        <Link href="/dashboard/dimensions/ai" className="glow-button text-sm">{tx("View AI Recs →")}</Link>
      </div>

      {mandatory.length > 0 && (
        <div className="liquid-glass p-4 space-y-2">
          <h2 className="text-sm font-semibold text-gray-700">{tx("Mandatory Dimensions")}</h2>
          <div className="flex flex-wrap gap-2">
            {mandatory.map((t) => (
              <span key={t.id} className="px-3 py-1 rounded-full text-xs font-medium bg-red-100 text-red-700">
                {t.type_name} {tx("(required)")}
              </span>
            ))}
          </div>
          <p className="text-xs text-gray-400">
            {tx("These dimensions must be tagged on every applicable transaction. Validation rules enforce this.")}
          </p>
        </div>
      )}

      <div className="glass-table overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-blue-900/30">
              <th className="text-left px-4 py-3 text-xs font-semibold text-gray-400 uppercase">{tx("Transaction Type")}</th>
              <th className="text-right px-4 py-3 text-xs font-semibold text-gray-400 uppercase">{tx("Tagged Count")}</th>
              <th className="text-right px-4 py-3 text-xs font-semibold text-gray-400 uppercase">{tx("Untagged")}</th>
              <th className="text-left px-4 py-3 text-xs font-semibold text-gray-400 uppercase">{tx("Completeness")}</th>
            </tr>
          </thead>
          <tbody>
            {isLoading ? (
              <tr><td colSpan={4} className="text-center py-10 text-gray-400">{tx("Loading…")}</td></tr>
            ) : rows.length === 0 ? (
              <tr>
                <td colSpan={4} className="text-center py-10 text-gray-400">
                  {tx("No tagged transactions found. Start tagging via the API or enable auto-derivation rules.")}
                </td>
              </tr>
            ) : rows.map((r: any, i: number) => {
              const pct = r.completeness_pct ?? 100;
              const color = pct >= 90 ? "bg-green-500" : pct >= 60 ? "bg-yellow-500" : "bg-red-500";
              return (
                <tr key={i} className="border-b border-blue-900/20 hover:bg-blue-950/20 transition-colors">
                  <td className="px-4 py-3 font-mono text-xs text-indigo-300">{r.transaction_type}</td>
                  <td className="px-4 py-3 text-right text-gray-300">{r.tagged_count}</td>
                  <td className="px-4 py-3 text-right text-red-400">{r.untagged_count}</td>
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-2">
                      <div className="flex-1 bg-gray-700 rounded-full h-2">
                        <div className={`${color} h-2 rounded-full`} style={{ width: `${pct}%` }} />
                      </div>
                      <span className="text-xs text-gray-300 w-10 text-right">{pct.toFixed(0)}%</span>
                    </div>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      <div className="grid grid-cols-2 gap-4">
        <div className="liquid-glass p-4 space-y-2">
          <h3 className="text-sm font-semibold text-gray-700">{tx("Quick Actions")}</h3>
          <div className="space-y-1">
            <Link href="/dashboard/dimensions/validation" className="block text-sm text-indigo-400 hover:text-indigo-300">{tx("→ Manage Validation Rules")}</Link>
            <Link href="/dashboard/dimensions/defaults" className="block text-sm text-indigo-400 hover:text-indigo-300">{tx("→ Set Up Auto-Derivation Rules")}</Link>
            <Link href="/dashboard/dimensions/reclassify" className="block text-sm text-indigo-400 hover:text-indigo-300">{tx("→ Reclassify Tagged Transactions")}</Link>
          </div>
        </div>
        <div className="liquid-glass p-4 space-y-2">
          <h3 className="text-sm font-semibold text-gray-700">{tx("All Dimension Types")}</h3>
          <div className="space-y-1">
            {types.map((t) => (
              <div key={t.id} className="flex items-center justify-between text-xs">
                <span className="text-gray-300">{t.type_name}</span>
                <span className="text-gray-400">{t.value_count} {tx("values")}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
