"use client";
import { useEffect, useState } from "react";
import { shelfLifeApi, LotShelfLifeProfile, SL_STATUS_BG, fmtDays } from "@/lib/shelfLife";

export default function NearExpiryPage() {
  const [lots, setLots] = useState<LotShelfLifeProfile[]>([]);
  const [loading, setLoading] = useState(true);
  const [days, setDays] = useState(30);
  const [generating, setGenerating] = useState(false);

  const load = (d: number) => {
    setLoading(true);
    shelfLifeApi.getNearExpiry(d).then(setLots).catch(console.error).finally(() => setLoading(false));
  };

  useEffect(() => { load(days); }, []);

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-gray-900">Near-Expiry Stock Board</h1>
          <p className="text-sm text-gray-500">{lots.length} lots expiring within threshold</p>
        </div>
        <div className="flex gap-2 items-center">
          <label className="text-sm text-gray-600">Within</label>
          <select className="border rounded-lg px-3 py-2 text-sm"
            value={days} onChange={e => { setDays(Number(e.target.value)); load(Number(e.target.value)); }}>
            {[7, 14, 30, 60, 90].map(d => <option key={d} value={d}>{d} days</option>)}
          </select>
          <button onClick={() => { setGenerating(true); shelfLifeApi.generateAlerts().finally(() => { setGenerating(false); load(days); }) }}
            className="px-4 py-2 text-sm bg-amber-600 text-white rounded-lg hover:bg-amber-700 disabled:opacity-50"
            disabled={generating}>
            {generating ? "Generating…" : "Generate Alerts"}
          </button>
        </div>
      </div>

      {/* Urgency bands */}
      <div className="grid grid-cols-3 gap-4">
        {[
          { label: "Critical (≤7d)", filter: (l: LotShelfLifeProfile) => (l.remaining_shelf_life_days ?? 0) <= 7, bg: "bg-red-50 border-red-200 text-red-800" },
          { label: "Warning (8–14d)", filter: (l: LotShelfLifeProfile) => { const d = l.remaining_shelf_life_days ?? 0; return d > 7 && d <= 14; }, bg: "bg-amber-50 border-amber-200 text-amber-800" },
          { label: "Monitor (15–30d)", filter: (l: LotShelfLifeProfile) => { const d = l.remaining_shelf_life_days ?? 0; return d > 14 && d <= 30; }, bg: "bg-yellow-50 border-yellow-200 text-yellow-800" },
        ].map(band => {
          const filtered = lots.filter(band.filter);
          return (
            <div key={band.label} className={`rounded-xl border p-4 ${band.bg}`}>
              <p className="text-lg font-bold">{filtered.length}</p>
              <p className="text-sm font-medium">{band.label}</p>
              <div className="mt-2 space-y-1">
                {filtered.slice(0, 5).map(l => (
                  <div key={l.id} className="flex justify-between text-xs">
                    <span className="font-mono">{l.lot_id.slice(0,10)}…</span>
                    <span className="font-semibold">{fmtDays(l.remaining_shelf_life_days)}</span>
                  </div>
                ))}
                {filtered.length > 5 && <p className="text-xs opacity-70">+{filtered.length - 5} more</p>}
              </div>
            </div>
          );
        })}
      </div>

      <div className="bg-white rounded-xl border border-gray-200 overflow-x-auto">
        <table className="w-full text-sm">
          <thead className="bg-gray-50 text-xs uppercase text-gray-500">
            <tr>
              {["Lot ID","Expiry Date","Remaining","% Shelf Life","Status","Manuf. Date","Blocked Issue","Blocked Ship"].map(h => (
                <th key={h} className="px-4 py-3 text-left font-medium">{h}</th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {loading ? (
              <tr><td colSpan={8} className="px-4 py-8 text-center text-gray-400">Loading…</td></tr>
            ) : lots.length === 0 ? (
              <tr><td colSpan={8} className="px-4 py-8 text-center text-gray-400">No near-expiry lots within {days} days</td></tr>
            ) : lots.map(l => (
              <tr key={l.id} className={`hover:bg-gray-50 ${(l.remaining_shelf_life_days ?? 99) <= 7 ? "bg-red-50" : (l.remaining_shelf_life_days ?? 99) <= 14 ? "bg-amber-50" : ""}`}>
                <td className="px-4 py-3 font-mono text-xs">{l.lot_id.slice(0,12)}…</td>
                <td className="px-4 py-3 font-medium">{l.expiry_date || "—"}</td>
                <td className="px-4 py-3 font-bold text-amber-700">{fmtDays(l.remaining_shelf_life_days)}</td>
                <td className="px-4 py-3">
                  {l.pct_remaining ? (
                    <div className="flex items-center gap-2">
                      <div className="w-16 h-2 bg-gray-200 rounded-full overflow-hidden">
                        <div className="h-full bg-amber-500 rounded-full"
                          style={{ width: `${Math.max(0, parseFloat(l.pct_remaining))}%` }} />
                      </div>
                      <span className="text-xs">{parseFloat(l.pct_remaining).toFixed(1)}%</span>
                    </div>
                  ) : "—"}
                </td>
                <td className="px-4 py-3"><span className={`px-2 py-0.5 rounded text-xs ${SL_STATUS_BG[l.shelf_life_status]}`}>{l.shelf_life_status}</span></td>
                <td className="px-4 py-3">{l.manufacturing_date || "—"}</td>
                <td className="px-4 py-3">{l.blocked_for_issue_flag ? <span className="text-red-600 font-medium">Yes</span> : "No"}</td>
                <td className="px-4 py-3">{l.blocked_for_shipment_flag ? <span className="text-red-600 font-medium">Yes</span> : "No"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
