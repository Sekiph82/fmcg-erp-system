"use client";
import { useEffect, useState } from "react";
import { qmsApi, LotQualityStatus, RELEASE_BG, ReleaseStatus } from "@/lib/qms";

export default function QuarantinePage() {
  const [statuses, setStatuses] = useState<LotQualityStatus[]>([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState<ReleaseStatus | "">("");
  const [releaseModal, setReleaseModal] = useState<{ lot_id: string; type: "release" | "hold" } | null>(null);
  const [releaseNotes, setReleaseNotes] = useState("");
  const [holdReason, setHoldReason] = useState("");
  const [quarantine, setQuarantine] = useState(false);

  const load = () => {
    setLoading(true);
    const params: Record<string, unknown> = {};
    if (filter === "ON_HOLD") params.hold_flag = true;
    else if (filter === "QUARANTINED") params.quarantine_flag = true;
    else if (filter) params.release_status = filter;
    qmsApi.listLotStatuses(params).then(setStatuses).finally(() => setLoading(false));
  };

  useEffect(load, [filter]);

  const handleRelease = async () => {
    if (!releaseModal) return;
    if (releaseModal.type === "release") {
      await qmsApi.releaseLot(releaseModal.lot_id, releaseNotes);
    } else {
      await qmsApi.holdLot({ lot_id: releaseModal.lot_id, hold_reason: holdReason, quarantine });
    }
    setReleaseModal(null);
    setReleaseNotes("");
    setHoldReason("");
    setQuarantine(false);
    load();
  };

  const summary = {
    total: statuses.length,
    hold: statuses.filter(s => s.hold_flag).length,
    quarantined: statuses.filter(s => s.quarantine_flag).length,
    released: statuses.filter(s => s.release_status === "RELEASED").length,
    unreleased: statuses.filter(s => s.release_status === "UNRELEASED").length,
    fefo_eligible: statuses.filter(s => s.fefo_eligible).length,
  };

  return (
    <div className="p-6 space-y-5">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Quarantine / Hold Management</h1>
          <p className="text-sm text-gray-500 mt-0.5">
            Lot release control · FEFO eligibility · Shipment gates
          </p>
        </div>
      </div>

      {/* Summary */}
      <div className="grid grid-cols-3 md:grid-cols-6 gap-4">
        {[
          { label: "Total Tracked", value: summary.total },
          { label: "On Hold", value: summary.hold, color: summary.hold > 0 ? "text-orange-700" : "text-gray-800" },
          { label: "Quarantined", value: summary.quarantined, color: summary.quarantined > 0 ? "text-red-700" : "text-gray-800" },
          { label: "Released", value: summary.released, color: "text-green-700" },
          { label: "Unreleased", value: summary.unreleased, color: summary.unreleased > 0 ? "text-amber-700" : "text-gray-800" },
          { label: "FEFO Eligible", value: summary.fefo_eligible, color: "text-teal-700" },
        ].map(k => (
          <div key={k.label} className="bg-white rounded-xl border border-gray-200 p-4">
            <p className="text-xs text-gray-500 uppercase tracking-wide">{k.label}</p>
            <p className={`text-2xl font-bold mt-1 ${k.color || "text-gray-800"}`}>{k.value}</p>
          </div>
        ))}
      </div>

      <div className="flex gap-3">
        <select className="border rounded-lg px-3 py-2 text-sm text-gray-700 bg-white"
          value={filter} onChange={e => setFilter(e.target.value as ReleaseStatus | "")}>
          <option value="">All Lots</option>
          <option value="UNRELEASED">Unreleased</option>
          <option value="ON_HOLD">On Hold</option>
          <option value="QUARANTINED">Quarantined</option>
          <option value="RELEASED">Released</option>
          <option value="REJECTED">Rejected</option>
          <option value="REWORK">Rework</option>
        </select>
      </div>

      <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
        {loading ? (
          <p className="px-5 py-8 text-gray-400 text-sm">Loading…</p>
        ) : statuses.length === 0 ? (
          <p className="px-5 py-8 text-gray-400 text-sm">No lot quality records found</p>
        ) : (
          <table className="w-full text-sm">
            <thead className="bg-gray-50 text-xs uppercase text-gray-500">
              <tr>
                {["Lot ID", "QC Status", "Release Status", "Flags", "FEFO Eligible", "Shipment OK", "Hold Reason", "Released At", "Actions"].map(h => (
                  <th key={h} className="px-4 py-3 text-left font-medium">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {statuses.map(s => (
                <tr key={s.id} className={`hover:bg-gray-50 ${s.quarantine_flag ? "bg-red-50" : s.hold_flag ? "bg-orange-50" : ""}`}>
                  <td className="px-4 py-3 font-mono text-xs text-gray-700">{s.lot_id.slice(0, 8)}…</td>
                  <td className="px-4 py-3">
                    <span className={`px-2 py-0.5 rounded text-xs ${
                      s.qc_status === "PASSED" ? "bg-green-100 text-green-800" :
                      s.qc_status === "FAILED" ? "bg-red-100 text-red-800" :
                      "bg-gray-100 text-gray-600"
                    }`}>{s.qc_status}</span>
                  </td>
                  <td className="px-4 py-3">
                    <span className={`px-2 py-0.5 rounded text-xs ${RELEASE_BG[s.release_status]}`}>
                      {s.release_status}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex gap-1">
                      {s.hold_flag && <span className="text-xs bg-orange-100 text-orange-700 px-1.5 rounded">HOLD</span>}
                      {s.quarantine_flag && <span className="text-xs bg-red-100 text-red-700 px-1.5 rounded">QUARANTINE</span>}
                      {!s.allergen_cleared && <span className="text-xs bg-purple-100 text-purple-700 px-1.5 rounded">ALLERGEN</span>}
                    </div>
                  </td>
                  <td className="px-4 py-3">{s.fefo_eligible ? "✓" : "✗"}</td>
                  <td className="px-4 py-3">{s.shipment_eligible ? "✓" : "✗"}</td>
                  <td className="px-4 py-3 text-gray-500 text-xs max-w-xs truncate">{s.hold_reason || "—"}</td>
                  <td className="px-4 py-3 text-gray-400 text-xs">
                    {s.released_at ? new Date(s.released_at).toLocaleDateString() : "—"}
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex gap-2">
                      {(s.hold_flag || s.quarantine_flag || s.release_status !== "RELEASED") && (
                        <button
                          onClick={() => setReleaseModal({ lot_id: s.lot_id, type: "release" })}
                          className="text-xs text-green-700 hover:underline">Release</button>
                      )}
                      {!s.hold_flag && (
                        <button
                          onClick={() => setReleaseModal({ lot_id: s.lot_id, type: "hold" })}
                          className="text-xs text-orange-700 hover:underline">Hold</button>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {releaseModal && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl border border-gray-200 p-6 w-full max-w-md space-y-4">
            <h3 className="font-semibold text-gray-800">
              {releaseModal.type === "release" ? "Release Lot from Hold/Quarantine" : "Place Lot on Hold"}
            </h3>
            {releaseModal.type === "release" ? (
              <div>
                <label className="text-xs text-gray-500 block mb-1">Release Notes</label>
                <textarea className="border rounded-lg px-3 py-2 text-sm w-full" rows={3}
                  value={releaseNotes} onChange={e => setReleaseNotes(e.target.value)}
                  placeholder="Reason for release, approving authority…" />
              </div>
            ) : (
              <>
                <div>
                  <label className="text-xs text-gray-500 block mb-1">Hold Reason *</label>
                  <textarea className="border rounded-lg px-3 py-2 text-sm w-full" rows={2}
                    value={holdReason} onChange={e => setHoldReason(e.target.value)} />
                </div>
                <label className="flex items-center gap-2 text-sm">
                  <input type="checkbox" checked={quarantine}
                    onChange={e => setQuarantine(e.target.checked)} />
                  Quarantine (physical isolation required)
                </label>
              </>
            )}
            <p className="text-xs text-red-600">
              {releaseModal.type === "release"
                ? "⚠ Only authorized QA personnel may release quarantined lots."
                : "⚠ This will block FEFO picking and shipment for this lot."}
            </p>
            <div className="flex gap-3">
              <button onClick={handleRelease}
                className={`px-4 py-2 text-white text-sm rounded-lg ${releaseModal.type === "release" ? "bg-green-600 hover:bg-green-700" : "bg-orange-600 hover:bg-orange-700"}`}>
                Confirm
              </button>
              <button onClick={() => setReleaseModal(null)}
                className="px-4 py-2 bg-gray-100 text-gray-700 text-sm rounded-lg hover:bg-gray-200">
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
