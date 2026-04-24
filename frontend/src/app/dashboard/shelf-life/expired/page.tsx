"use client";
import { useEffect, useState } from "react";
import { shelfLifeApi, LotShelfLifeProfile, fmtDays } from "@/lib/shelfLife";

export default function ExpiredStockPage() {
  const [lots, setLots] = useState<LotShelfLifeProfile[]>([]);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);

  useEffect(() => {
    shelfLifeApi.getExpired().then(setLots).catch(console.error).finally(() => setLoading(false));
  }, []);

  const handleGenerateDispositions = async () => {
    setGenerating(true);
    try {
      const r = await shelfLifeApi.generateDispositions();
      alert(`Generated ${r.created} disposition suggestions.`);
    } finally { setGenerating(false); }
  };

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-gray-900">Expired Stock Board</h1>
          <p className="text-sm text-gray-500 text-red-600">{lots.length} expired lots in active stock — immediate action required</p>
        </div>
        <button onClick={handleGenerateDispositions} disabled={generating}
          className="px-4 py-2 text-sm bg-red-600 text-white rounded-lg hover:bg-red-700 disabled:opacity-50">
          {generating ? "Generating…" : "Generate Disposition Suggestions"}
        </button>
      </div>

      {lots.length > 0 && (
        <div className="bg-red-50 border border-red-200 rounded-xl p-4 flex items-start gap-3">
          <svg className="h-5 w-5 text-red-600 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
          </svg>
          <div>
            <p className="text-sm font-semibold text-red-800">Expired stock detected in active inventory</p>
            <p className="text-xs text-red-600 mt-0.5">
              These lots must not be issued to production, shipped to customers, or transferred to active locations.
              Move to quarantine/scrap or initiate formal disposition immediately.
            </p>
          </div>
        </div>
      )}

      <div className="bg-white rounded-xl border border-red-200 overflow-x-auto">
        <table className="w-full text-sm">
          <thead className="bg-red-50 text-xs uppercase text-red-700">
            <tr>
              {["Lot ID","Expiry Date","Days Expired","% Life Used","Age Since Prod","Blocked Issue","Blocked Ship","Hold Reason","Last Recalc"].map(h => (
                <th key={h} className="px-4 py-3 text-left font-medium">{h}</th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-red-100">
            {loading ? (
              <tr><td colSpan={9} className="px-4 py-8 text-center text-red-300">Loading…</td></tr>
            ) : lots.length === 0 ? (
              <tr><td colSpan={9} className="px-4 py-8 text-center text-gray-400">No expired lots found — good!</td></tr>
            ) : lots.map(l => (
              <tr key={l.id} className="bg-red-50 hover:bg-red-100">
                <td className="px-4 py-3 font-mono text-xs text-red-700">{l.lot_id.slice(0,12)}…</td>
                <td className="px-4 py-3 font-medium text-red-700">{l.expiry_date || "—"}</td>
                <td className="px-4 py-3 font-bold text-red-800">
                  {l.remaining_shelf_life_days !== null ? `${Math.abs(l.remaining_shelf_life_days)}d ago` : "—"}
                </td>
                <td className="px-4 py-3">
                  {l.pct_remaining && parseFloat(l.pct_remaining) > 100 ? (
                    <span className="text-xs font-semibold text-red-700">{parseFloat(l.pct_remaining).toFixed(1)}% (over)</span>
                  ) : l.pct_remaining ? `${parseFloat(l.pct_remaining).toFixed(1)}%` : "—"}
                </td>
                <td className="px-4 py-3">{l.age_since_production_days !== null ? `${l.age_since_production_days}d` : "—"}</td>
                <td className="px-4 py-3">{l.blocked_for_issue_flag ? <span className="text-red-600 font-medium">Yes</span> : <span className="text-orange-600 font-bold">NO — RISK!</span>}</td>
                <td className="px-4 py-3">{l.blocked_for_shipment_flag ? <span className="text-red-600 font-medium">Yes</span> : <span className="text-orange-600 font-bold">NO — RISK!</span>}</td>
                <td className="px-4 py-3 text-xs text-gray-500">{l.hold_reason || "—"}</td>
                <td className="px-4 py-3 text-xs text-gray-400">
                  {l.last_recalc_at ? new Date(l.last_recalc_at).toLocaleDateString() : "Never"}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
