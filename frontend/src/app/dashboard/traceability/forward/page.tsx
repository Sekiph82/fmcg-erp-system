"use client";
import { useSearchParams } from "next/navigation";
import { useCallback, useState, useEffect, Suspense } from "react";
import { traceApi, ForwardTraceResult } from "@/lib/traceability";

function ForwardTraceContent() {
  const params = useSearchParams();
  const initialLotId = params.get("lot_id") || "";
  const [lotId, setLotId] = useState(initialLotId);
  const [result, setResult] = useState<ForwardTraceResult | null>(null);
  const [loading, setLoading] = useState(false);

  const handleTrace = useCallback(async (traceId: string) => {
    if (!traceId) return;
    setLoading(true);
    setResult(null);
    try {
      const r = await traceApi.forwardTrace(traceId);
      setResult(r);
    } catch (e: any) { alert(e.message); }
    finally { setLoading(false); }
  }, []);

  useEffect(() => { if (initialLotId) handleTrace(initialLotId); }, [initialLotId, handleTrace]);

  const fmtQty = (q: string) => parseFloat(q).toLocaleString(undefined, { maximumFractionDigits: 2 });

  return (
    <div className="p-6 space-y-6">
      <div>
        <h1 className="text-xl font-bold text-gray-900">Forward Traceability</h1>
        <p className="text-sm text-gray-500">Trace a lot forward to finished goods, shipments, and customer deliveries</p>
      </div>

      <div className="bg-white rounded-xl border border-gray-200 p-5 flex gap-3">
        <div className="flex-1">
          <label className="text-xs font-medium text-gray-600">Lot ID</label>
          <input className="mt-1 w-full border rounded-lg px-3 py-2 text-sm"
            placeholder="UUID of the lot to trace forward" value={lotId}
            onChange={e => setLotId(e.target.value)} />
        </div>
        <div className="flex items-end">
          <button onClick={() => handleTrace(lotId)} disabled={!lotId || loading}
            className="px-5 py-2 bg-green-700 text-white text-sm rounded-lg hover:bg-green-800 disabled:opacity-50">
            {loading ? "Tracing…" : "Forward Trace →"}
          </button>
        </div>
      </div>

      {result && (
        <div className="space-y-4">
          {/* Quantity breakdown */}
          <div className="grid grid-cols-3 md:grid-cols-6 gap-3">
            {[
              { label: "In Stock",     value: result.qty_in_stock,   color: "border-green-200 bg-green-50 text-green-700" },
              { label: "Shipped",      value: result.qty_shipped,    color: "border-blue-200 bg-blue-50 text-blue-700" },
              { label: "Returned",     value: result.qty_returned,   color: "border-purple-200 bg-purple-50 text-purple-700" },
              { label: "Quarantined",  value: result.qty_quarantined,color: "border-red-200 bg-red-50 text-red-700" },
              { label: "Scrapped",     value: result.qty_scrapped,   color: "border-gray-200 bg-gray-50 text-gray-700" },
              { label: "Reworked",     value: result.qty_reworked,   color: "border-amber-200 bg-amber-50 text-amber-700" },
            ].map(s => (
              <div key={s.label} className={`rounded-xl border p-3 text-center ${s.color}`}>
                <p className="text-xl font-bold">{fmtQty(s.value)}</p>
                <p className="text-xs mt-0.5">{s.label}</p>
              </div>
            ))}
          </div>

          {/* Stats */}
          <div className="bg-white rounded-xl border border-gray-200 p-4 flex gap-6">
            <div>
              <p className="text-xs text-gray-500">Total Affected</p>
              <p className="text-2xl font-bold text-gray-800">{fmtQty(result.total_affected_qty)}</p>
            </div>
            <div>
              <p className="text-xs text-gray-500">Affected Lots</p>
              <p className="text-2xl font-bold text-gray-800">{result.affected_lots.length}</p>
            </div>
            <div>
              <p className="text-xs text-gray-500">Shipments</p>
              <p className="text-2xl font-bold text-gray-800">{result.affected_shipments.length}</p>
            </div>
            <div>
              <p className="text-xs text-gray-500">Customers</p>
              <p className="text-2xl font-bold text-gray-800">{result.affected_customers.length}</p>
            </div>
          </div>

          {/* Affected lots */}
          {result.affected_lots.length > 0 && (
            <div className="bg-white rounded-xl border border-gray-200 p-5">
              <h2 className="font-semibold text-gray-800 mb-3">Descendant Lots</h2>
              <div className="space-y-1.5">
                {result.affected_lots.map((l, i) => (
                  <div key={i} className="flex items-center gap-3 p-2 bg-gray-50 rounded-lg">
                    <span className="text-xs bg-green-100 text-green-700 px-2 py-0.5 rounded">{l.rel_type.replace("_"," ")}</span>
                    {l.child_stage && <span className="text-xs bg-blue-100 text-blue-700 px-2 py-0.5 rounded">{l.child_stage}</span>}
                    <span className="font-mono text-xs text-gray-700 flex-1">{l.lot_id}</span>
                    <span className="text-sm text-gray-600">{l.quantity.toLocaleString()} units</span>
                    <a href={`/dashboard/traceability/forward?lot_id=${l.lot_id}`}
                      className="text-xs text-green-600 hover:underline">Trace further →</a>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Shipments */}
          {result.affected_shipments.length > 0 && (
            <div className="bg-white rounded-xl border border-gray-200 p-5">
              <h2 className="font-semibold text-gray-800 mb-3">Shipments ({result.affected_shipments.length})</h2>
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead className="bg-gray-50 text-xs uppercase text-gray-500">
                    <tr>
                      {["Customer ID","Lot ID","Quantity","Shipment Date"].map(h => (
                        <th key={h} className="px-3 py-2 text-left">{h}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-100">
                    {result.affected_shipments.map((s, i) => (
                      <tr key={i} className="hover:bg-gray-50">
                        <td className="px-3 py-2 font-mono text-xs">{s.customer_id ? s.customer_id.slice(0,10) : "—"}</td>
                        <td className="px-3 py-2 font-mono text-xs">{s.lot_id.slice(0,10)}…</td>
                        <td className="px-3 py-2">{s.quantity.toLocaleString()}</td>
                        <td className="px-3 py-2 text-gray-400">{s.event_date ? new Date(s.event_date).toLocaleDateString() : "—"}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {result.affected_lots.length === 0 && result.affected_shipments.length === 0 && (
            <div className="bg-gray-50 rounded-xl border border-gray-200 p-6 text-center text-gray-400">
              No descendant lots or shipments found. This lot appears to be in its original state with no forward traceability recorded.
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export default function ForwardTracePage() {
  return <Suspense fallback={<div className="p-8 text-gray-400">Loading…</div>}><ForwardTraceContent /></Suspense>;
}
