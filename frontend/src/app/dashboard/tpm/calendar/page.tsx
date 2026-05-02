"use client";
import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { tpmApi, TPMPromotion, PROMOTION_TYPE_LABEL, PROMOTION_STATUS_BADGE } from "@/lib/tpm";
import Link from "next/link";

const MONTHS = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"];
const TYPE_COLORS: Record<string, string> = {
  DISCOUNT:    "bg-blue-500/30 border-blue-500/50",
  FREE_GOODS:  "bg-purple-500/30 border-purple-500/50",
  DISPLAY:     "bg-green-500/30 border-green-500/50",
  REBATE:      "bg-orange-500/30 border-orange-500/50",
  LISTING_FEE: "bg-yellow-500/30 border-yellow-500/50",
  BILL_BACK:   "bg-red-500/30 border-red-500/50",
  VISIBILITY:  "bg-teal-500/30 border-teal-500/50",
  EVENT:       "bg-indigo-500/30 border-indigo-500/50",
  BUNDLE:      "bg-pink-500/30 border-pink-500/50",
  OFF_INVOICE: "bg-gray-500/30 border-gray-500/50",
  CUSTOM:      "bg-gray-400/30 border-gray-400/50",
};

function monthOverlaps(promo: TPMPromotion, year: number, month: number): boolean {
  const start = new Date(`${year}-${String(month+1).padStart(2,"0")}-01`);
  const end   = new Date(start.getFullYear(), start.getMonth() + 1, 0);
  const pStart = new Date(promo.valid_from);
  const pEnd   = new Date(promo.valid_to);
  return pStart <= end && pEnd >= start;
}

export default function TPMCalendarPage() {
  const currentYear = new Date().getFullYear();
  const [year, setYear] = useState(currentYear);
  const [typeFilter, setTypeFilter] = useState("");
  const [channelFilter, setChannelFilter] = useState("");

  const { data: promotions = [], isLoading } = useQuery({
    queryKey: ["tpm-promotions-all"],
    queryFn: () => tpmApi.getPromotions(),
  });

  const filtered = promotions.filter((p: TPMPromotion) => {
    const yearMatch = new Date(p.valid_from).getFullYear() === year || new Date(p.valid_to).getFullYear() === year;
    const typeMatch = !typeFilter || p.promotion_type === typeFilter;
    const channelMatch = !channelFilter || p.channel_id === channelFilter;
    return yearMatch && typeMatch && channelMatch;
  });

  const channels = Array.from(new Set(promotions.map((p: TPMPromotion) => p.channel_id).filter(Boolean)));

  return (
    <div className="p-6 space-y-5">
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Promotion Calendar</h1>
          <p className="text-sm text-gray-500">View overlaps, gaps, and concentration by month.</p>
        </div>
        <div className="flex gap-2 items-center flex-wrap">
          <button onClick={() => setYear(y => y - 1)} className="glow-button-secondary text-xs !py-1">← {year - 1}</button>
          <span className="text-sm font-bold text-gray-200 px-2">{year}</span>
          <button onClick={() => setYear(y => y + 1)} className="glow-button-secondary text-xs !py-1">{year + 1} →</button>
          <select value={typeFilter} onChange={(e) => setTypeFilter(e.target.value)}
            className="rounded-lg border border-gray-300 px-3 py-1.5 text-sm">
            <option value="">All Types</option>
            {Object.keys(PROMOTION_TYPE_LABEL).map((t) => (
              <option key={t} value={t}>{PROMOTION_TYPE_LABEL[t as import("@/lib/tpm").TPMPromotionType]}</option>
            ))}
          </select>
          {channels.length > 0 && (
            <select value={channelFilter} onChange={(e) => setChannelFilter(e.target.value)}
              className="rounded-lg border border-gray-300 px-3 py-1.5 text-sm">
              <option value="">All Channels</option>
              {channels.map((c) => <option key={c} value={c!}>{c}</option>)}
            </select>
          )}
        </div>
      </div>

      {isLoading ? (
        <div className="text-gray-400 text-center py-10">Loading…</div>
      ) : (
        <div className="glass-table overflow-x-auto">
          <table className="w-full text-sm min-w-[900px]">
            <thead>
              <tr className="border-b border-blue-900/30">
                <th className="text-left px-4 py-3 text-xs font-semibold text-gray-400 uppercase w-48">Promotion</th>
                {MONTHS.map((m) => (
                  <th key={m} className="text-center px-1 py-3 text-xs font-semibold text-gray-400 uppercase w-16">{m}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {filtered.length === 0 ? (
                <tr><td colSpan={13} className="text-center py-10 text-gray-400">No promotions for {year}.</td></tr>
              ) : filtered.map((p: TPMPromotion) => (
                <tr key={p.id} className="border-b border-blue-900/20 hover:bg-blue-950/10">
                  <td className="px-4 py-2">
                    <Link href={`/dashboard/tpm/promotions/${p.id}`} className="font-medium text-gray-200 hover:text-indigo-300 text-xs block">
                      {p.promotion_name}
                    </Link>
                    <span className={`px-1.5 py-0.5 rounded text-xs font-medium ${PROMOTION_STATUS_BADGE[p.status]}`}>{p.status}</span>
                  </td>
                  {MONTHS.map((_, mi) => {
                    const active = monthOverlaps(p, year, mi);
                    const color = TYPE_COLORS[p.promotion_type] ?? "bg-gray-500/20 border-gray-500/30";
                    return (
                      <td key={mi} className="px-1 py-2 text-center">
                        {active && (
                          <div className={`h-4 rounded border ${color} mx-auto`} title={PROMOTION_TYPE_LABEL[p.promotion_type]} />
                        )}
                      </td>
                    );
                  })}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Legend */}
      <div className="flex flex-wrap gap-3 text-xs">
        {Object.entries(PROMOTION_TYPE_LABEL).map(([type, label]) => (
          <div key={type} className="flex items-center gap-1">
            <div className={`w-4 h-3 rounded border ${TYPE_COLORS[type] ?? "bg-gray-500/20"}`} />
            <span className="text-gray-400">{label}</span>
          </div>
        ))}
      </div>

      {/* Overlap warnings */}
      {(() => {
        const warnings: string[] = [];
        for (let i = 0; i < filtered.length; i++) {
          for (let j = i + 1; j < filtered.length; j++) {
            const a = filtered[i], b = filtered[j];
            const overlap = new Date(a.valid_from) <= new Date(b.valid_to) && new Date(b.valid_from) <= new Date(a.valid_to);
            const sameChannel = a.channel_id && b.channel_id && a.channel_id === b.channel_id;
            const sameBrand   = a.brand_id   && b.brand_id   && a.brand_id   === b.brand_id;
            if (overlap && (sameChannel || sameBrand)) {
              warnings.push(`"${a.promotion_name}" and "${b.promotion_name}" overlap${sameChannel ? ` on channel ${a.channel_id}` : ` on brand ${a.brand_id}`}`);
            }
          }
        }
        return warnings.length > 0 ? (
          <div className="liquid-glass p-4 space-y-2 border border-yellow-900/40">
            <p className="text-sm font-semibold text-yellow-400">⚠ Overlap Warnings ({warnings.length})</p>
            {warnings.map((w, i) => <p key={i} className="text-xs text-yellow-300">{w}</p>)}
          </div>
        ) : null;
      })()}
    </div>
  );
}
