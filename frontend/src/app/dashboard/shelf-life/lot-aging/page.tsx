"use client";
import { useEffect, useState } from "react";
import {
  shelfLifeApi, LotShelfLifeProfile, ShelfLifeStatus,
  SL_STATUS_BG, SL_STATUS_LABEL, fmtDays, expiryBgColor,
} from "@/lib/shelfLife";

const STATUSES: ShelfLifeStatus[] = [
  "active","near_expiry","expired","blocked","qc_hold","quarantine",
  "pending_retest","retested_released","customer_restricted","not_applicable",
];

const AGE_BUCKETS = [
  { label: "Expiring in ≤7d",  min: -Infinity, max: 7 },
  { label: "8–30d",            min: 8,  max: 30 },
  { label: "31–90d",           min: 31, max: 90 },
  { label: "91–180d",          min: 91, max: 180 },
  { label: "> 180d",           min: 181, max: Infinity },
  { label: "Expired",          min: -Infinity, max: -1 },
];

function bucket(days: number | null): string {
  if (days === null) return "Unknown";
  if (days < 0) return "Expired";
  if (days <= 7) return "Expiring in ≤7d";
  if (days <= 30) return "8–30d";
  if (days <= 90) return "31–90d";
  if (days <= 180) return "91–180d";
  return "> 180d";
}

export default function LotAgingPage() {
  const [lots, setLots] = useState<LotShelfLifeProfile[]>([]);
  const [loading, setLoading] = useState(true);
  const [filterStatus, setFilterStatus] = useState<ShelfLifeStatus | "">("");
  const [sortBy, setSortBy] = useState<"remaining" | "expiry">("remaining");
  const [recalculating, setRecalculating] = useState(false);

  const load = (status?: ShelfLifeStatus) => {
    setLoading(true);
    shelfLifeApi.listLots(status || undefined, 500)
      .then(setLots)
      .catch(console.error)
      .finally(() => setLoading(false));
  };

  useEffect(() => { load(); }, []);

  const handleStatusFilter = (s: string) => {
    setFilterStatus(s as ShelfLifeStatus | "");
    load(s as ShelfLifeStatus || undefined);
  };

  const handleBatchRecalc = async () => {
    setRecalculating(true);
    try {
      const r = await shelfLifeApi.batchRecalculate();
      alert(`Recalculated ${r.updated} lot statuses.`);
      load();
    } finally { setRecalculating(false); }
  };

  const sorted = [...lots].sort((a, b) => {
    if (sortBy === "remaining") {
      const aD = a.remaining_shelf_life_days ?? 99999;
      const bD = b.remaining_shelf_life_days ?? 99999;
      return aD - bD;
    }
    return (a.expiry_date || "").localeCompare(b.expiry_date || "");
  });

  // Summary by bucket
  const summary: Record<string, number> = {};
  lots.forEach(l => {
    const b = bucket(l.remaining_shelf_life_days);
    summary[b] = (summary[b] || 0) + 1;
  });

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-gray-900">Lot Aging Explorer</h1>
          <p className="text-sm text-gray-500">{lots.length} lots tracked — filter by status or age bucket</p>
        </div>
        <button onClick={handleBatchRecalc} disabled={recalculating}
          className="px-4 py-2 text-sm bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 disabled:opacity-50">
          {recalculating ? "Recalculating…" : "Batch Recalculate All"}
        </button>
      </div>

      {/* Age Bucket Summary */}
      <div className="grid grid-cols-3 md:grid-cols-6 gap-3">
        {Object.entries(summary).map(([bkt, count]) => (
          <div key={bkt} className={`rounded-xl border p-3 text-center ${bkt === "Expired" ? "border-red-200 bg-red-50" : bkt.includes("≤7d") ? "border-amber-200 bg-amber-50" : "border-gray-200 bg-white"}`}>
            <p className="text-lg font-bold text-gray-800">{count}</p>
            <p className="text-xs text-gray-500 mt-0.5">{bkt}</p>
          </div>
        ))}
      </div>

      {/* Filters */}
      <div className="flex flex-wrap gap-3 items-center">
        <select className="border rounded-lg px-3 py-2 text-sm"
          value={filterStatus} onChange={e => handleStatusFilter(e.target.value)}>
          <option value="">All Statuses</option>
          {STATUSES.map(s => <option key={s} value={s}>{SL_STATUS_LABEL[s]}</option>)}
        </select>
        <select className="border rounded-lg px-3 py-2 text-sm"
          value={sortBy} onChange={e => setSortBy(e.target.value as any)}>
          <option value="remaining">Sort: Remaining Days (asc)</option>
          <option value="expiry">Sort: Expiry Date</option>
        </select>
      </div>

      {/* Table */}
      <div className="bg-white rounded-xl border border-gray-200 overflow-x-auto">
        <table className="w-full text-sm">
          <thead className="bg-gray-50 text-xs uppercase text-gray-500">
            <tr>
              {["Lot ID", "Expiry Date", "Remaining", "% Remaining", "Status", "Age Since Prod", "Blocked Issue", "Blocked Ship", "Hold Reason"].map(h => (
                <th key={h} className="px-4 py-3 text-left font-medium">{h}</th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {loading ? (
              <tr><td colSpan={9} className="px-4 py-8 text-center text-gray-400">Loading…</td></tr>
            ) : sorted.length === 0 ? (
              <tr><td colSpan={9} className="px-4 py-8 text-center text-gray-400">No lots found</td></tr>
            ) : sorted.map((l) => (
              <tr key={l.id} className={`hover:bg-gray-50 ${expiryBgColor(l.remaining_shelf_life_days)}`}>
                <td className="px-4 py-3 font-mono text-xs text-gray-700">{l.lot_id.slice(0, 12)}…</td>
                <td className="px-4 py-3">{l.expiry_date || "—"}</td>
                <td className="px-4 py-3 font-semibold">{fmtDays(l.remaining_shelf_life_days)}</td>
                <td className="px-4 py-3">{l.pct_remaining ? `${parseFloat(l.pct_remaining).toFixed(1)}%` : "—"}</td>
                <td className="px-4 py-3">
                  <span className={`px-2 py-0.5 rounded text-xs ${SL_STATUS_BG[l.shelf_life_status]}`}>
                    {SL_STATUS_LABEL[l.shelf_life_status]}
                  </span>
                </td>
                <td className="px-4 py-3">{l.age_since_production_days !== null ? `${l.age_since_production_days}d` : "—"}</td>
                <td className="px-4 py-3">{l.blocked_for_issue_flag ? <span className="text-red-600 font-medium">Yes</span> : "No"}</td>
                <td className="px-4 py-3">{l.blocked_for_shipment_flag ? <span className="text-red-600 font-medium">Yes</span> : "No"}</td>
                <td className="px-4 py-3 text-gray-500 text-xs">{l.hold_reason || "—"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
