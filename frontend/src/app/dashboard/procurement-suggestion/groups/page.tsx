"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useSearchParams } from "next/navigation";
import { psApi, PSGroupOut, urgencyBadge, fmt } from "@/lib/procurement_suggestion";

export default function GroupsPage() {
  const params = useSearchParams();
  const runId  = params.get("run_id") ?? "";
  const qc     = useQueryClient();

  const [expanded, setExpanded] = useState<string | null>(null);
  const [converting, setConverting] = useState<PSGroupOut | null>(null);
  const [reqDate, setReqDate] = useState(() => new Date().toISOString().split("T")[0]);
  const [prNotes, setPrNotes] = useState("");

  const { data: groups, isLoading } = useQuery({
    queryKey: ["ps-groups", runId],
    queryFn: () => psApi.listGroups(runId),
    enabled: !!runId,
  });

  const convertPR = useMutation({
    mutationFn: (g: PSGroupOut) =>
      psApi.convertGroupToPR({ group_id: g.id, required_date: reqDate, notes: prNotes }),
    onSuccess: (res) => {
      qc.invalidateQueries({ queryKey: ["ps-groups"] });
      setConverting(null);
      alert(`Purchase Requisition created: ${res.pr_no}`);
    },
  });

  if (!runId) return (
    <div className="p-8 text-gray-400">
      No run selected. <a href="/dashboard/procurement-suggestion" className="text-blue-600 underline">Go to dashboard</a>
    </div>
  );

  return (
    <div className="p-6 space-y-4">
      {/* Convert-to-PR modal */}
      {converting && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl p-6 w-96 space-y-4 shadow-xl">
            <h2 className="font-semibold text-gray-900">Convert to Purchase Requisition</h2>
            <p className="text-sm text-gray-500">
              Supplier: <strong>{converting.supplier_name}</strong> · {converting.line_count} items ·{" "}
              {converting.currency} {fmt(converting.total_estimated_cost ?? 0, 0)}
            </p>
            <div>
              <label className="text-sm text-gray-600">Required Date</label>
              <input
                type="date"
                value={reqDate}
                onChange={(e) => setReqDate(e.target.value)}
                className="mt-1 w-full border rounded px-3 py-1.5 text-sm"
              />
            </div>
            <div>
              <label className="text-sm text-gray-600">Notes (optional)</label>
              <textarea
                value={prNotes}
                onChange={(e) => setPrNotes(e.target.value)}
                rows={2}
                className="mt-1 w-full border rounded px-3 py-1.5 text-sm resize-none"
              />
            </div>
            <div className="flex gap-2 pt-2">
              <button
                onClick={() => convertPR.mutate(converting)}
                disabled={convertPR.isPending}
                className="flex-1 py-2 bg-blue-600 text-white rounded text-sm hover:bg-blue-700 disabled:opacity-50"
              >
                {convertPR.isPending ? "Creating PR…" : "Create Purchase Requisition"}
              </button>
              <button onClick={() => setConverting(null)} className="flex-1 py-2 border rounded text-sm hover:bg-gray-50">
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}

      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold text-gray-900">Grouped Orders</h1>
          <p className="text-sm text-gray-500 font-mono">Run: {runId}</p>
        </div>
        <a href={`/dashboard/procurement-suggestion/suggestions?run_id=${runId}`} className="text-sm text-blue-600 hover:underline">
          ← Suggestion List
        </a>
      </div>

      {isLoading && <div className="text-gray-400">Loading groups…</div>}

      <div className="space-y-3">
        {(groups ?? []).map((g) => (
          <div key={g.id} className="bg-white border border-gray-200 rounded-lg overflow-hidden">
            {/* Group header */}
            <div
              className="flex items-center justify-between px-5 py-4 cursor-pointer hover:bg-gray-50"
              onClick={() => setExpanded(expanded === g.id ? null : g.id)}
            >
              <div className="flex items-center gap-4">
                <div>
                  <p className="font-semibold text-gray-800">{g.supplier_name}</p>
                  <p className="text-xs text-gray-400 font-mono">{g.group_no}</p>
                </div>
                <span className={`px-2 py-0.5 rounded-full text-xs border ${
                  g.status === "CONVERTED" ? "bg-purple-100 text-purple-700 border-purple-300" :
                  g.status === "SENT" ? "bg-blue-100 text-blue-700 border-blue-300" :
                  "bg-gray-100 text-gray-600 border-gray-300"
                }`}>{g.status}</span>
              </div>
              <div className="flex items-center gap-6 text-sm">
                <div className="text-right">
                  <p className="text-gray-500 text-xs">Items</p>
                  <p className="font-semibold">{g.line_count}</p>
                </div>
                <div className="text-right">
                  <p className="text-gray-500 text-xs">Est. Cost</p>
                  <p className="font-semibold">{g.currency} {fmt(g.total_estimated_cost ?? 0, 0)}</p>
                </div>
                <div className="text-right">
                  <p className="text-gray-500 text-xs">Target Delivery</p>
                  <p className="font-semibold">{g.target_delivery_date ?? "—"}</p>
                </div>
                {g.status !== "CONVERTED" && (
                  <button
                    onClick={(e) => { e.stopPropagation(); setConverting(g); }}
                    className="px-3 py-1.5 text-sm bg-blue-600 text-white rounded hover:bg-blue-700"
                  >
                    Create PR
                  </button>
                )}
                {g.status === "CONVERTED" && (
                  <span className="text-xs text-purple-600">PR Created ✓</span>
                )}
                <span className="text-gray-400">{expanded === g.id ? "▲" : "▼"}</span>
              </div>
            </div>

            {/* Lines detail */}
            {expanded === g.id && (
              <div className="border-t border-gray-100 overflow-x-auto">
                <table className="w-full text-xs">
                  <thead className="bg-gray-50 text-gray-500 uppercase">
                    <tr>
                      <th className="text-left px-4 py-2">Material</th>
                      <th className="text-right px-4 py-2">Order Qty</th>
                      <th className="text-left px-4 py-2">UOM</th>
                      <th className="text-right px-4 py-2">Unit Price</th>
                      <th className="text-right px-4 py-2">Total Cost</th>
                      <th className="text-left px-4 py-2">Order Date</th>
                      <th className="text-left px-4 py-2">Urgency</th>
                    </tr>
                  </thead>
                  <tbody>
                    {g.lines.map((l) => (
                      <tr key={l.id} className="border-t border-gray-100">
                        <td className="px-4 py-2">
                          <p className="font-medium">{l.material_name}</p>
                          <p className="text-gray-400 font-mono">{l.material_code}</p>
                        </td>
                        <td className="px-4 py-2 text-right font-semibold">{fmt(l.adjusted_order_qty)}</td>
                        <td className="px-4 py-2">{l.uom}</td>
                        <td className="px-4 py-2 text-right">{l.supplier_price ? `${l.currency} ${fmt(l.supplier_price)}` : "—"}</td>
                        <td className="px-4 py-2 text-right">{l.estimated_total_cost ? `${l.currency} ${fmt(l.estimated_total_cost, 0)}` : "—"}</td>
                        <td className="px-4 py-2">{l.suggested_order_date ?? "—"}</td>
                        <td className="px-4 py-2">
                          <span className={`px-1.5 py-0.5 rounded text-xs border ${urgencyBadge(l.urgency_level)}`}>
                            {l.urgency_level}
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        ))}

        {!isLoading && !groups?.length && (
          <div className="text-center py-12 text-gray-400">
            No grouped orders found for this run.
          </div>
        )}
      </div>
    </div>
  );
}
