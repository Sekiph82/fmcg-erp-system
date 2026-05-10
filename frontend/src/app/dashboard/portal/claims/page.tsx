"use client";
import { useCallback, useEffect, useState } from "react";
import { portalApi, PortalClaim, CLAIM_TYPE_LABELS, CLAIM_STATUS_COLORS } from "@/lib/portal";

export default function PortalClaimsReviewPage() {
  const [allClaims, setAllClaims] = useState<(PortalClaim & { account_code: string })[]>([]);
  const [loading, setLoading] = useState(true);
  const [statusFilter, setStatusFilter] = useState("SUBMITTED");
  const [selected, setSelected] = useState<PortalClaim & { account_code: string } | null>(null);
  const [resolution, setResolution] = useState("");
  const [resolving, setResolving] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const accs = await portalApi.getAccounts({ status: "ACTIVE" });
      const claimsAll: (PortalClaim & { account_code: string })[] = [];
      for (const acc of (accs as { id: string; account_code: string }[]).slice(0, 20)) {
        const claims = await portalApi.getClaims(acc.id, { status: statusFilter || undefined });
        for (const c of (claims as PortalClaim[])) {
          claimsAll.push({ ...c, account_code: acc.account_code });
        }
      }
      claimsAll.sort((a, b) => new Date(b.created_at || 0).getTime() - new Date(a.created_at || 0).getTime());
      setAllClaims(claimsAll);
    } catch (e) { console.error(e); }
    setLoading(false);
  }, [statusFilter]);

  useEffect(() => { load(); }, [load]);

  const handleResolve = async (status: string) => {
    if (!selected) return;
    setResolving(true);
    try {
      await portalApi.reviewClaim(selected.id, { status, resolution_notes: resolution, resolved_by: "admin" });
      setSelected(null);
      setResolution("");
      load();
    } catch (e) { console.error(e); }
    setResolving(false);
  };

  return (
    <div className="p-6 space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-bold text-gray-900">Portal Claims Review</h1>
        <select value={statusFilter} onChange={e => setStatusFilter(e.target.value)}
          className="text-sm border rounded-lg px-2 py-1.5">
          <option value="">All</option>
          <option value="SUBMITTED">Submitted</option>
          <option value="UNDER_REVIEW">Under Review</option>
          <option value="RESOLVED">Resolved</option>
          <option value="REJECTED">Rejected</option>
          <option value="CLOSED">Closed</option>
        </select>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Claims List */}
        <div className="space-y-2">
          {loading && <div className="text-gray-400 text-sm py-4">Loading…</div>}
          {!loading && allClaims.length === 0 && <div className="text-gray-400 text-sm py-4">No claims</div>}
          {allClaims.map(claim => (
            <div key={claim.id}
              onClick={() => setSelected(claim)}
              className={`bg-white rounded-xl border shadow-sm p-4 cursor-pointer hover:border-blue-400 transition-colors ${selected?.id === claim.id ? "border-blue-500 ring-1 ring-blue-200" : ""}`}>
              <div className="flex items-start justify-between">
                <div>
                  <div className="font-medium text-gray-800 text-sm">{CLAIM_TYPE_LABELS[claim.claim_type]}</div>
                  <div className="text-xs text-gray-400 mt-0.5">{claim.claim_no} · {claim.account_code}</div>
                  <p className="text-xs text-gray-600 mt-1 line-clamp-2">{claim.reason}</p>
                </div>
                <span className="px-2 py-0.5 rounded-full text-xs font-medium flex-shrink-0"
                  style={{ background: CLAIM_STATUS_COLORS[claim.status] + "22", color: CLAIM_STATUS_COLORS[claim.status] }}>
                  {claim.status}
                </span>
              </div>
            </div>
          ))}
        </div>

        {/* Review Panel */}
        <div>
          {selected ? (
            <div className="bg-white rounded-xl border shadow-sm p-4 space-y-3 sticky top-4">
              <h2 className="font-semibold text-gray-800">{CLAIM_TYPE_LABELS[selected.claim_type]}</h2>
              <div className="grid grid-cols-2 gap-2 text-sm">
                <div className="text-gray-500">Claim No</div><div className="font-mono">{selected.claim_no}</div>
                <div className="text-gray-500">Account</div><div>{selected.account_code}</div>
                <div className="text-gray-500">Order Ref</div><div className="font-mono text-xs">{selected.linked_order_id || "—"}</div>
                <div className="text-gray-500">Invoice Ref</div><div className="font-mono text-xs">{selected.linked_invoice_id || "—"}</div>
                <div className="text-gray-500">Qty Involved</div><div>{selected.quantity_involved ?? "—"}</div>
                <div className="text-gray-500">Submitted</div><div className="text-xs">{selected.created_at ? new Date(selected.created_at).toLocaleDateString() : "—"}</div>
              </div>
              <div>
                <div className="text-xs text-gray-500 mb-1">Reason</div>
                <p className="text-sm text-gray-700 bg-gray-50 rounded-lg p-2">{selected.reason}</p>
              </div>
              {selected.description && (
                <div>
                  <div className="text-xs text-gray-500 mb-1">Description</div>
                  <p className="text-xs text-gray-600">{selected.description}</p>
                </div>
              )}
              <textarea placeholder="Resolution notes…" value={resolution}
                onChange={e => setResolution(e.target.value)}
                className="w-full border rounded-lg px-3 py-2 text-sm" rows={2} />
              <div className="flex gap-2">
                <button onClick={() => handleResolve("RESOLVED")} disabled={resolving}
                  className="flex-1 bg-green-600 text-white py-2 rounded-lg text-sm disabled:opacity-50">
                  Resolve
                </button>
                <button onClick={() => handleResolve("REJECTED")} disabled={resolving}
                  className="flex-1 bg-red-600 text-white py-2 rounded-lg text-sm disabled:opacity-50">
                  Reject
                </button>
                <button onClick={() => handleResolve("UNDER_REVIEW")} disabled={resolving}
                  className="flex-1 border py-2 rounded-lg text-sm">
                  Under Review
                </button>
              </div>
            </div>
          ) : (
            <div className="bg-gray-50 rounded-xl border-2 border-dashed p-8 text-center text-gray-400 text-sm">
              Select a claim from the left to review it
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
