"use client";
import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { faApi, fmtCurrency, DEPR_METHOD_LABEL } from "@/lib/fixed_assets";
import { tx } from "@/lib/i18n/core";

export default function FADepreciationPage() {
  const [assetId, setAssetId] = useState("");

  const { data: assets = [] } = useQuery({
    queryKey: ["fa-assets-active"],
    queryFn: () => faApi.listAssets({ status: "ACTIVE" }),
  });

  const { data: schedule = [], isLoading } = useQuery({
    queryKey: ["fa-schedule", assetId],
    queryFn: () => faApi.getSchedule(assetId),
    enabled: !!assetId,
  });

  const selected = assets.find((a) => a.id === assetId);

  const posted  = schedule.filter((l) => l.schedule_status === "POSTED");
  const planned = schedule.filter((l) => l.schedule_status === "PLANNED");
  const totalPosted  = posted.reduce((s, l) => s + l.depreciation_amount, 0);
  const totalPlanned = planned.reduce((s, l) => s + l.depreciation_amount, 0);

  return (
    <div className="p-6 space-y-5">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">{tx("Depreciation Schedules")}</h1>
          <p className="text-sm text-gray-500">{tx("View period-by-period depreciation lines for any active asset.")}</p>
        </div>
        <Link href="/dashboard/fixed-assets/posting" className="glow-button text-sm">
          {tx("Posting Run →")}
        </Link>
      </div>

      <div className="liquid-glass p-4 flex items-end gap-4">
        <div className="flex flex-col gap-1 flex-1 max-w-sm">
          <label className="text-xs text-gray-500">{tx("Select Asset")}</label>
          <select value={assetId} onChange={(e) => setAssetId(e.target.value)}
            className="rounded-lg border border-gray-300 px-3 py-2 text-sm">
            <option value="">{tx("— Choose an asset —")}</option>
            {assets.map((a) => (
              <option key={a.id} value={a.id}>{a.asset_code} — {a.asset_name}</option>
            ))}
          </select>
        </div>
        {selected && (
          <Link href={`/dashboard/fixed-assets/assets/${selected.id}`}
            className="glow-button-secondary text-sm self-end">
            {tx("View Asset Detail")}
          </Link>
        )}
      </div>

      {selected && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {[
            { label: tx("Original Cost"),   value: fmtCurrency(selected.original_cost),          color: "text-blue-600" },
            { label: tx("Accumulated Depr"),value: fmtCurrency(selected.accumulated_depreciation),color: "text-orange-600" },
            { label: tx("Net Book Value"),  value: fmtCurrency(selected.net_book_value),          color: "text-green-600" },
            { label: tx("Method"),          value: DEPR_METHOD_LABEL[selected.depreciation_method] ?? selected.depreciation_method, color: "text-indigo-600" },
          ].map((k) => (
            <div key={k.label} className="glow-card p-4 text-center">
              <p className="text-xs text-gray-500">{k.label}</p>
              <p className={`text-lg font-bold mt-1 ${k.color}`}>{k.value}</p>
            </div>
          ))}
        </div>
      )}

      {assetId && (
        <>
          {!isLoading && schedule.length > 0 && (
            <div className="grid grid-cols-2 gap-4">
              <div className="liquid-glass p-3 text-center">
                <p className="text-xs text-gray-500">{tx("Posted (")}{posted.length} {tx("periods)")}</p>
                <p className="text-base font-bold text-green-600">{fmtCurrency(totalPosted)}</p>
              </div>
              <div className="liquid-glass p-3 text-center">
                <p className="text-xs text-gray-500">{tx("Planned (")}{planned.length} {tx("periods)")}</p>
                <p className="text-base font-bold text-yellow-600">{fmtCurrency(totalPlanned)}</p>
              </div>
            </div>
          )}

          <div className="glass-table overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-blue-900/30">
                  <th className="text-left px-4 py-3 text-xs font-semibold text-gray-400 uppercase">{tx("Period Start")}</th>
                  <th className="text-left px-4 py-3 text-xs font-semibold text-gray-400 uppercase">{tx("Period End")}</th>
                  <th className="text-right px-4 py-3 text-xs font-semibold text-gray-400 uppercase">{tx("Opening NBV")}</th>
                  <th className="text-right px-4 py-3 text-xs font-semibold text-gray-400 uppercase">{tx("Depreciation")}</th>
                  <th className="text-right px-4 py-3 text-xs font-semibold text-gray-400 uppercase">{tx("Closing NBV")}</th>
                  <th className="text-center px-4 py-3 text-xs font-semibold text-gray-400 uppercase">{tx("Status")}</th>
                </tr>
              </thead>
              <tbody>
                {isLoading ? (
                  <tr><td colSpan={6} className="text-center py-10 text-gray-400">{tx("Loading…")}</td></tr>
                ) : schedule.length === 0 ? (
                  <tr>
                    <td colSpan={6} className="text-center py-10 text-gray-400">
                      {tx("No schedule lines found.")}{" "}
                      <Link href="/dashboard/fixed-assets/posting" className="text-indigo-400 underline">
                        {tx("Run Generate Schedules")}
                      </Link>
                    </td>
                  </tr>
                ) : schedule.map((line) => (
                  <tr key={line.id} className="border-b border-blue-900/20 hover:bg-blue-950/20 transition-colors">
                    <td className="px-4 py-3 text-gray-300">{line.period_start}</td>
                    <td className="px-4 py-3 text-gray-300">{line.period_end}</td>
                    <td className="px-4 py-3 text-right text-gray-300">{fmtCurrency(line.opening_nbv)}</td>
                    <td className="px-4 py-3 text-right font-medium text-orange-400">{fmtCurrency(line.depreciation_amount)}</td>
                    <td className="px-4 py-3 text-right text-gray-300">{fmtCurrency(line.closing_nbv)}</td>
                    <td className="px-4 py-3 text-center">
                      <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${
                        line.schedule_status === "POSTED"
                          ? "bg-green-100 text-green-700"
                          : "bg-yellow-100 text-yellow-700"
                      }`}>
                        {line.schedule_status}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}

      {!assetId && (
        <div className="liquid-glass p-12 text-center text-gray-400">
          {tx("Select an asset above to view its depreciation schedule.")}
        </div>
      )}
    </div>
  );
}
