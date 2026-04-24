"use client";
import { useSearchParams } from "next/navigation";
import { useState, useEffect, Suspense } from "react";
import { traceApi, BackwardTraceResult } from "@/lib/traceability";

function BackwardTraceContent() {
  const params = useSearchParams();
  const initialLotId = params.get("lot_id") || "";
  const [lotId, setLotId] = useState(initialLotId);
  const [maxDepth, setMaxDepth] = useState(8);
  const [result, setResult] = useState<BackwardTraceResult | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (initialLotId) handleTrace(initialLotId);
  }, []);

  const handleTrace = async (id?: string) => {
    const traceId = id || lotId;
    if (!traceId) return;
    setLoading(true);
    setResult(null);
    try {
      const r = await traceApi.backwardTrace(traceId, maxDepth);
      setResult(r);
    } catch (e: any) { alert(e.message); }
    finally { setLoading(false); }
  };

  return (
    <div className="p-6 space-y-6">
      <div>
        <h1 className="text-xl font-bold text-gray-900">Backward Traceability</h1>
        <p className="text-sm text-gray-500">Trace a lot back to its raw materials, production orders, and suppliers</p>
      </div>

      <div className="bg-white rounded-xl border border-gray-200 p-5 space-y-4">
        <div className="flex gap-3">
          <div className="flex-1">
            <label className="text-xs font-medium text-gray-600">Lot ID</label>
            <input className="mt-1 w-full border rounded-lg px-3 py-2 text-sm"
              placeholder="UUID of the lot to trace backward" value={lotId}
              onChange={e => setLotId(e.target.value)} />
          </div>
          <div className="w-32">
            <label className="text-xs font-medium text-gray-600">Max Depth</label>
            <select className="mt-1 w-full border rounded-lg px-3 py-2 text-sm"
              value={maxDepth} onChange={e => setMaxDepth(Number(e.target.value))}>
              {[3,5,8,10,12,15].map(d => <option key={d} value={d}>{d} levels</option>)}
            </select>
          </div>
          <div className="flex items-end">
            <button onClick={() => handleTrace()} disabled={!lotId || loading}
              className="px-5 py-2 bg-gray-800 text-white text-sm rounded-lg hover:bg-gray-900 disabled:opacity-50">
              {loading ? "Tracing…" : "← Trace Backward"}
            </button>
          </div>
        </div>
      </div>

      {result && (
        <div className="space-y-4">
          {/* Summary */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {[
              { label: "Genealogy Depth", value: result.genealogy_depth },
              { label: "Source Lots", value: result.source_lots.length },
              { label: "Production Orders", value: result.production_orders.length },
              { label: "Suppliers", value: result.suppliers.length },
            ].map(s => (
              <div key={s.label} className="bg-white rounded-xl border border-gray-200 p-3 text-center">
                <p className="text-xl font-bold text-gray-800">{s.value}</p>
                <p className="text-xs text-gray-500">{s.label}</p>
              </div>
            ))}
          </div>

          {/* Source lots */}
          {result.source_lots.length > 0 && (
            <div className="bg-white rounded-xl border border-gray-200 p-5">
              <h2 className="font-semibold text-gray-800 mb-3">Ancestor Lots ({result.source_lots.length})</h2>
              <div className="space-y-2">
                {result.source_lots.map((l, i) => (
                  <div key={i} className="flex items-center gap-3 p-2 bg-gray-50 rounded-lg">
                    <span className="text-xs bg-gray-200 text-gray-700 px-2 py-0.5 rounded">{l.rel_type.replace("_"," ")}</span>
                    {l.parent_stage && <span className="text-xs bg-blue-100 text-blue-700 px-2 py-0.5 rounded">{l.parent_stage}</span>}
                    <span className="font-mono text-xs text-gray-700 flex-1">{l.lot_id}</span>
                    <span className="text-sm font-medium text-gray-600">{l.quantity} units</span>
                    <a href={`/dashboard/traceability/backward?lot_id=${l.lot_id}`}
                      className="text-xs text-indigo-600 hover:underline">← Trace further</a>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Production Orders */}
          {result.production_orders.length > 0 && (
            <div className="bg-white rounded-xl border border-gray-200 p-5">
              <h2 className="font-semibold text-gray-800 mb-3">Production Orders ({result.production_orders.length})</h2>
              <div className="flex flex-wrap gap-2">
                {result.production_orders.map((po, i) => (
                  <span key={i} className="px-3 py-1.5 bg-indigo-50 border border-indigo-200 rounded-lg text-xs font-mono text-indigo-700">
                    {po.id}
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* Suppliers */}
          {result.suppliers.length > 0 && (
            <div className="bg-white rounded-xl border border-gray-200 p-5">
              <h2 className="font-semibold text-gray-800 mb-3">Suppliers ({result.suppliers.length})</h2>
              <div className="flex flex-wrap gap-2">
                {result.suppliers.map((s, i) => (
                  <span key={i} className="px-3 py-1.5 bg-purple-50 border border-purple-200 rounded-lg text-xs font-mono text-purple-700">
                    {s.id}
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* GRNs */}
          {result.grns.length > 0 && (
            <div className="bg-white rounded-xl border border-gray-200 p-5">
              <h2 className="font-semibold text-gray-800 mb-3">GRN Records ({result.grns.length})</h2>
              <div className="divide-y divide-gray-100">
                {result.grns.map((g, i) => (
                  <div key={i} className="py-2 flex items-center gap-4 text-sm">
                    <span className="font-mono text-xs text-gray-700">{g.grn_id}</span>
                    {g.supplier_id && <span className="text-xs text-purple-700">Supplier: {g.supplier_id.slice(0,8)}</span>}
                    <span className="text-gray-500">{g.quantity} units</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {result.source_lots.length === 0 && result.production_orders.length === 0 && (
            <div className="bg-amber-50 border border-amber-200 rounded-xl p-4 text-sm text-amber-700">
              No ancestor lots or production orders found. This may indicate missing traceability data — check if genealogy links were created at receipt and production stages.
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export default function BackwardTracePage() {
  return <Suspense fallback={<div className="p-8 text-gray-400">Loading…</div>}><BackwardTraceContent /></Suspense>;
}
