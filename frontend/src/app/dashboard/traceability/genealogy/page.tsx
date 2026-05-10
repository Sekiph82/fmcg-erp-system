"use client";
import { useSearchParams } from "next/navigation";
import { useCallback, useState, useEffect, Suspense } from "react";
import { traceApi, GenealogyTree, GenealogyEdge, STAGE_COLOR } from "@/lib/traceability";

function GenealogyContent() {
  const params = useSearchParams();
  const initialLotId = params.get("lot_id") || "";
  const [lotId, setLotId] = useState(initialLotId);
  const [direction, setDirection] = useState<"both" | "forward" | "backward">("both");
  const [maxDepth, setMaxDepth] = useState(6);
  const [tree, setTree] = useState<GenealogyTree | null>(null);
  const [loading, setLoading] = useState(false);
  const [view, setView] = useState<"graph" | "list">("list");

  const handleLoad = useCallback(async (traceId: string) => {
    if (!traceId) return;
    setLoading(true);
    setTree(null);
    try {
      const r = await traceApi.getGenealogyTree(traceId, direction, maxDepth);
      setTree(r);
    } catch (e: any) { alert(e.message); }
    finally { setLoading(false); }
  }, [direction, maxDepth]);

  useEffect(() => { if (initialLotId) handleLoad(initialLotId); }, [initialLotId, handleLoad]);

  return (
    <div className="p-6 space-y-6">
      <div>
        <h1 className="text-xl font-bold text-gray-900">Genealogy Graph / Tree</h1>
        <p className="text-sm text-gray-500">Full lot genealogy — parent/child relationships across all production stages</p>
      </div>

      <div className="bg-white rounded-xl border border-gray-200 p-5 flex flex-wrap gap-3">
        <div className="flex-1 min-w-48">
          <label className="text-xs font-medium text-gray-600">Lot ID</label>
          <input className="mt-1 w-full border rounded-lg px-3 py-2 text-sm"
            placeholder="UUID" value={lotId}
            onChange={e => setLotId(e.target.value)} />
        </div>
        <div className="w-36">
          <label className="text-xs font-medium text-gray-600">Direction</label>
          <select className="mt-1 w-full border rounded-lg px-3 py-2 text-sm"
            value={direction} onChange={e => setDirection(e.target.value as any)}>
            <option value="both">Both</option>
            <option value="forward">Forward Only</option>
            <option value="backward">Backward Only</option>
          </select>
        </div>
        <div className="w-28">
          <label className="text-xs font-medium text-gray-600">Max Depth</label>
          <select className="mt-1 w-full border rounded-lg px-3 py-2 text-sm"
            value={maxDepth} onChange={e => setMaxDepth(Number(e.target.value))}>
            {[3,5,6,8,10].map(d => <option key={d} value={d}>{d}</option>)}
          </select>
        </div>
        <div className="flex items-end">
          <button onClick={() => handleLoad(lotId)} disabled={!lotId || loading}
            className="px-5 py-2 bg-purple-600 text-white text-sm rounded-lg hover:bg-purple-700 disabled:opacity-50">
            {loading ? "Loading…" : "Build Genealogy"}
          </button>
        </div>
      </div>

      {tree && (
        <div className="space-y-4">
          {/* Summary */}
          <div className="flex flex-wrap gap-4">
            <div className="bg-white rounded-xl border border-gray-200 px-5 py-3 flex gap-6">
              <div className="text-center">
                <p className="text-2xl font-bold text-purple-700">{tree.lot_count}</p>
                <p className="text-xs text-gray-500">Lots in Tree</p>
              </div>
              <div className="text-center">
                <p className="text-2xl font-bold text-gray-800">{tree.edges.length}</p>
                <p className="text-xs text-gray-500">Links</p>
              </div>
              <div className="text-center">
                <p className="text-2xl font-bold text-gray-800">{tree.depth}</p>
                <p className="text-xs text-gray-500">Max Depth</p>
              </div>
            </div>

            {/* Stage summary */}
            {Object.keys(tree.stage_summary).length > 0 && (
              <div className="bg-white rounded-xl border border-gray-200 px-5 py-3 flex flex-wrap gap-2">
                {Object.entries(tree.stage_summary).map(([stage, count]) => (
                  <div key={stage} className={`px-3 py-1.5 rounded-lg border text-xs font-medium ${(STAGE_COLOR as any)[stage] || "border-gray-200 bg-gray-50"}`}>
                    {stage}: {count}
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* View toggle */}
          <div className="flex gap-1 bg-gray-100 p-1 rounded-lg w-fit">
            {(["list","graph"] as const).map(v => (
              <button key={v} onClick={() => setView(v)}
                className={`px-4 py-1.5 rounded text-sm font-medium ${view === v ? "bg-white shadow text-gray-800" : "text-gray-500"}`}>
                {v === "list" ? "Table View" : "Graph View"}
              </button>
            ))}
          </div>

          {view === "list" && (
            <div className="bg-white rounded-xl border border-gray-200 overflow-x-auto">
              <table className="w-full text-sm">
                <thead className="bg-gray-50 text-xs uppercase text-gray-500">
                  <tr>
                    {["Lot Number","Stage","Parent","Relationship","Quantity"].map(h => (
                      <th key={h} className="px-4 py-3 text-left font-medium">{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100">
                  {tree.edges.map((e: GenealogyEdge, i) => {
                    const srcNode = tree.nodes.find(n => n.lot_id === e.source);
                    const tgtNode = tree.nodes.find(n => n.lot_id === e.target);
                    return (
                      <tr key={i} className="hover:bg-gray-50">
                        <td className="px-4 py-3 font-mono text-xs">
                          {tgtNode?.lot_number || e.target.slice(0,10)}
                        </td>
                        <td className="px-4 py-3">
                          {tgtNode?.stage ? (
                            <span className={`px-2 py-0.5 rounded text-xs border ${(STAGE_COLOR as any)[tgtNode.stage] || "border-gray-200 bg-gray-50"}`}>
                              {tgtNode.stage}
                            </span>
                          ) : "—"}
                        </td>
                        <td className="px-4 py-3 font-mono text-xs text-gray-500">
                          {srcNode?.lot_number || e.source.slice(0,10)}
                        </td>
                        <td className="px-4 py-3">
                          <span className="text-xs bg-purple-100 text-purple-700 px-2 py-0.5 rounded">
                            {e.rel_type.replace(/_/g," ")}
                          </span>
                        </td>
                        <td className="px-4 py-3 text-gray-600">{e.qty.toLocaleString()}</td>
                      </tr>
                    );
                  })}
                  {tree.edges.length === 0 && (
                    <tr><td colSpan={5} className="px-4 py-8 text-center text-gray-400">
                      No genealogy links found for this lot
                    </td></tr>
                  )}
                </tbody>
              </table>
            </div>
          )}

          {view === "graph" && (
            <div className="bg-gray-50 rounded-xl border border-gray-200 p-6 min-h-64">
              <p className="text-xs text-gray-500 mb-4 text-center">Genealogy graph — {tree.nodes.length} nodes, {tree.edges.length} edges</p>
              <div className="flex flex-wrap justify-center gap-3">
                {tree.nodes.map(n => (
                  <div key={String(n.lot_id)}
                    className={`rounded-xl border-2 p-3 text-center min-w-24 ${n.stage ? (STAGE_COLOR as any)[n.stage] || "border-gray-300 bg-white" : "border-gray-300 bg-white"} ${String(n.lot_id) === String(tree.root_lot_id) ? "ring-2 ring-purple-500" : ""}`}>
                    <p className="text-xs font-bold text-gray-800">{n.lot_number}</p>
                    {n.stage && <p className="text-xs text-gray-500 mt-0.5">{n.stage}</p>}
                    {n.quantity != null && <p className="text-xs text-gray-400">{n.quantity}</p>}
                  </div>
                ))}
              </div>
              <p className="text-xs text-gray-400 text-center mt-4">
                Full interactive graph requires a dedicated graph visualization library (e.g. React Flow, D3). Table view above shows all relationships.
              </p>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export default function GenealogyPage() {
  return <Suspense fallback={<div className="p-8 text-gray-400">Loading…</div>}><GenealogyContent /></Suspense>;
}
