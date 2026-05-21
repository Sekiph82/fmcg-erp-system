"use client";
import { useEffect, useState } from "react";
import {
  shelfLifeApi, DispositionSuggestion, DispositionStatus,
  DISPOSITION_ACTION_LABEL,
} from "@/lib/shelfLife";

const STATUS_BG: Record<DispositionStatus, string> = {
  suggested: "bg-amber-100 text-amber-700",
  approved:  "bg-blue-100 text-blue-700",
  executed:  "bg-green-100 text-green-700",
  cancelled: "bg-gray-100 text-gray-500",
};

export default function DispositionPage() {
  const [suggestions, setSuggestions] = useState<DispositionSuggestion[]>([]);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [filterStatus, setFilterStatus] = useState<DispositionStatus | "">("");
  const [approving, setApproving] = useState<string | null>(null);
  const [approveNote, setApproveNote] = useState("");
  const [selectedId, setSelectedId] = useState<string | null>(null);

  const load = (status?: DispositionStatus) => {
    setLoading(true);
    shelfLifeApi.listDispositions(status || undefined)
      .then(setSuggestions).catch(console.error).finally(() => setLoading(false));
  };

  useEffect(() => { load(); }, []);

  const handleGenerate = async () => {
    setGenerating(true);
    try {
      const r = await shelfLifeApi.generateDispositions();
      alert(`Generated ${r.created} new disposition suggestions.`);
      load();
    } finally { setGenerating(false); }
  };

  const handleApprove = async () => {
    if (!selectedId) return;
    setApproving(selectedId);
    try {
      await shelfLifeApi.approveDisposition(selectedId, {
        approved_by_id: "00000000-0000-0000-0000-000000000001",
        execution_notes: approveNote || undefined,
      });
      setSelectedId(null);
      setApproveNote("");
      load();
    } finally { setApproving(null); }
  };

  const selected = suggestions.find(s => s.id === selectedId);

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-gray-900">Disposition Suggestion Console</h1>
          <p className="text-sm text-gray-500">System-generated lot disposition recommendations for expired, near-expiry, and at-risk stock</p>
        </div>
        <button onClick={handleGenerate} disabled={generating}
          className="px-4 py-2 text-sm bg-orange-600 text-white rounded-lg hover:bg-orange-700 disabled:opacity-50">
          {generating ? "Generating…" : "Generate Suggestions"}
        </button>
      </div>

      {/* Filter */}
      <div className="flex gap-2">
        {(["", "suggested","approved","executed","cancelled"] as const).map(s => (
          <button key={s} onClick={() => { setFilterStatus(s as any); load(s ? s as DispositionStatus : undefined); }}
            className={`px-3 py-1.5 rounded-lg text-sm border ${filterStatus === s ? "bg-orange-600 text-white border-orange-600" : "border-gray-200 text-gray-600 hover:bg-gray-50"}`}>
            {s || "All"}
          </button>
        ))}
      </div>

      <div className="bg-white rounded-xl border border-gray-200 overflow-x-auto">
        <table className="w-full text-sm">
          <thead className="bg-gray-50 text-xs uppercase text-gray-500">
            <tr>
              {["Lot ID","Action","Status","Urgency","Days Until Expiry","Fin. Exposure","Reason","Action"].map(h => (
                <th key={h} className="px-4 py-3 text-left font-medium">{h}</th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {loading ? (
              <tr><td colSpan={8} className="px-4 py-8 text-center text-gray-400">Loading…</td></tr>
            ) : suggestions.length === 0 ? (
              <tr><td colSpan={8} className="px-4 py-8 text-center text-gray-400">No disposition suggestions</td></tr>
            ) : suggestions.map(s => (
              <tr key={s.id} className="hover:bg-gray-50">
                <td className="px-4 py-3 font-mono text-xs">{s.lot_id.slice(0,10)}…</td>
                <td className="px-4 py-3 font-medium">
                  <span className={`px-2 py-0.5 rounded text-xs ${s.action === "scrap" ? "bg-red-100 text-red-700" : s.action === "use_urgently" ? "bg-amber-100 text-amber-700" : "bg-blue-100 text-blue-700"}`}>
                    {DISPOSITION_ACTION_LABEL[s.action]}
                  </span>
                </td>
                <td className="px-4 py-3">
                  <span className={`px-2 py-0.5 rounded text-xs ${STATUS_BG[s.status]}`}>{s.status}</span>
                </td>
                <td className="px-4 py-3">
                  <div className="flex items-center gap-1">
                    <div className="w-16 h-2 bg-gray-200 rounded-full overflow-hidden">
                      <div className="h-full bg-orange-500 rounded-full"
                        style={{ width: `${Math.min(100, s.urgency_score || 0)}%` }} />
                    </div>
                    <span className="text-xs">{s.urgency_score}</span>
                  </div>
                </td>
                <td className="px-4 py-3">
                  {s.days_until_expiry !== null ? (
                    <span className={s.days_until_expiry < 0 ? "text-red-700 font-bold" : s.days_until_expiry <= 14 ? "text-amber-700 font-semibold" : "text-gray-700"}>
                      {s.days_until_expiry < 0 ? `${Math.abs(s.days_until_expiry)}d expired` : `${s.days_until_expiry}d`}
                    </span>
                  ) : "—"}
                </td>
                <td className="px-4 py-3 text-gray-600">
                  {s.financial_exposure ? `KES ${parseFloat(s.financial_exposure).toLocaleString()}` : "—"}
                </td>
                <td className="px-4 py-3 text-xs text-gray-500 max-w-xs truncate">{s.reason}</td>
                <td className="px-4 py-3">
                  {s.status === "suggested" && (
                    <button onClick={() => setSelectedId(s.id)}
                      className="px-3 py-1 text-xs bg-blue-600 text-white rounded hover:bg-blue-700">
                      Approve
                    </button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Approve Modal */}
      {selectedId && selected && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl shadow-xl w-full max-w-md p-6 space-y-4">
            <h3 className="font-semibold text-gray-800">Approve Disposition</h3>
            <div className="bg-amber-50 border border-amber-200 rounded-lg p-3">
              <p className="text-sm font-medium text-amber-800">{DISPOSITION_ACTION_LABEL[selected.action]}</p>
              <p className="text-xs text-amber-600 mt-1">{selected.reason}</p>
            </div>
            <div>
              <label className="text-xs font-medium text-gray-600">Execution Notes</label>
              <textarea rows={3} className="mt-1 w-full border rounded-lg px-3 py-2 text-sm"
                value={approveNote} onChange={e => setApproveNote(e.target.value)}
                placeholder="Notes on how this disposition will be executed…" />
            </div>
            <div className="flex gap-2 justify-end">
              <button onClick={() => { setSelectedId(null); setApproveNote(""); }}
                className="px-4 py-2 text-sm border rounded-lg">Cancel</button>
              <button onClick={handleApprove} disabled={!!approving}
                className="px-4 py-2 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50">
                {approving ? "Approving…" : "Approve Disposition"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
