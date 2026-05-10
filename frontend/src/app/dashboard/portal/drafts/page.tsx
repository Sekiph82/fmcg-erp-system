"use client";
import { useCallback, useEffect, useState } from "react";
import { portalApi, PortalDraftOrder, fmtCurrency, DRAFT_STATUS_COLORS } from "@/lib/portal";

export default function DraftsQueuePage() {
  const [accounts, setAccounts] = useState<{ id: string; account_code: string }[]>([]);
  const [allDrafts, setAllDrafts] = useState<(PortalDraftOrder & { account_code: string })[]>([]);
  const [loading, setLoading] = useState(true);
  const [statusFilter, setStatusFilter] = useState("SUBMITTED");

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const accs = await portalApi.getAccounts({ status: "ACTIVE" });
      const accountList = accs as { id: string; account_code: string }[];
      setAccounts(accountList);
      const draftsAll: (PortalDraftOrder & { account_code: string })[] = [];
      for (const acc of accountList.slice(0, 20)) {
        const drafts = await portalApi.getDraftOrders(acc.id, { status: statusFilter || undefined });
        for (const d of (drafts as PortalDraftOrder[])) {
          draftsAll.push({ ...d, account_code: acc.account_code });
        }
      }
      draftsAll.sort((a, b) => new Date(b.created_at || 0).getTime() - new Date(a.created_at || 0).getTime());
      setAllDrafts(draftsAll);
    } catch (e) { console.error(e); }
    setLoading(false);
  }, [statusFilter]);

  useEffect(() => { load(); }, [load]);

  const handleApprove = async (draftId: string) => {
    try {
      await portalApi.reviewDraftOrder(draftId, { status: "APPROVED", reviewed_by: "admin" });
      load();
    } catch (e) { console.error(e); }
  };

  const handleReject = async (draftId: string) => {
    try {
      await portalApi.reviewDraftOrder(draftId, { status: "REJECTED", reviewed_by: "admin", review_notes: "Rejected" });
      load();
    } catch (e) { console.error(e); }
  };

  return (
    <div className="p-6 space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-bold text-gray-900">Draft Order Review Queue</h1>
        <div className="flex items-center gap-2">
          <select value={statusFilter} onChange={e => setStatusFilter(e.target.value)}
            className="text-sm border rounded-lg px-2 py-1.5">
            <option value="">All</option>
            <option value="SUBMITTED">Submitted (Pending Review)</option>
            <option value="APPROVED">Approved</option>
            <option value="REJECTED">Rejected</option>
            <option value="DRAFT">Draft</option>
          </select>
        </div>
      </div>

      <div className="bg-white rounded-xl border shadow-sm overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b bg-gray-50 text-xs text-gray-600">
              <th className="px-3 py-2 text-left">Draft No</th>
              <th className="px-3 py-2 text-left">Account</th>
              <th className="px-3 py-2 text-left">Submitted By</th>
              <th className="px-3 py-2 text-right">Total</th>
              <th className="px-3 py-2 text-left">Delivery Date</th>
              <th className="px-3 py-2 text-left">Status</th>
              <th className="px-3 py-2 text-left">Submitted</th>
              <th className="px-3 py-2 text-left">Actions</th>
            </tr>
          </thead>
          <tbody>
            {loading && <tr><td colSpan={8} className="px-3 py-6 text-center text-gray-400">Loading…</td></tr>}
            {!loading && allDrafts.length === 0 && <tr><td colSpan={8} className="px-3 py-6 text-center text-gray-400">No draft orders</td></tr>}
            {allDrafts.map(draft => (
              <tr key={draft.id} className="border-b hover:bg-gray-50">
                <td className="px-3 py-2 font-mono text-xs text-blue-600">{draft.draft_no}</td>
                <td className="px-3 py-2 text-xs font-medium text-gray-700">{draft.account_code}</td>
                <td className="px-3 py-2 text-xs text-gray-500">{draft.submitted_by || "—"}</td>
                <td className="px-3 py-2 text-xs text-right font-medium text-gray-800">{fmtCurrency(draft.total_amount, draft.currency)}</td>
                <td className="px-3 py-2 text-xs text-gray-500">{draft.requested_delivery_date || "—"}</td>
                <td className="px-3 py-2">
                  <span className="px-2 py-0.5 rounded-full text-xs font-medium"
                    style={{ background: DRAFT_STATUS_COLORS[draft.status] + "22", color: DRAFT_STATUS_COLORS[draft.status] }}>
                    {draft.status}
                  </span>
                </td>
                <td className="px-3 py-2 text-xs text-gray-400">
                  {draft.created_at ? new Date(draft.created_at).toLocaleDateString() : "—"}
                </td>
                <td className="px-3 py-2 flex gap-2">
                  {draft.status === "SUBMITTED" && (
                    <>
                      <button onClick={() => handleApprove(draft.id)}
                        className="text-xs bg-green-100 text-green-700 px-2 py-0.5 rounded hover:bg-green-200">
                        Approve
                      </button>
                      <button onClick={() => handleReject(draft.id)}
                        className="text-xs bg-red-100 text-red-700 px-2 py-0.5 rounded hover:bg-red-200">
                        Reject
                      </button>
                    </>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
