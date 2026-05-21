"use client";
import { useState } from "react";
import { traceApi, TraceabilitySearchResult, TRACE_EVENT_LABEL, STAGE_COLOR } from "@/lib/traceability";

export default function TraceSearchPage() {
  const [form, setForm] = useState({
    lot_number: "", batch_number: "", product_id: "",
    material_id: "", supplier_id: "", customer_id: "",
    shipment_reference: "", date_from: "", date_to: "",
  });
  const [results, setResults] = useState<TraceabilitySearchResult[]>([]);
  const [searching, setSearching] = useState(false);
  const [searched, setSearched] = useState(false);

  const handleSearch = async () => {
    setSearching(true);
    try {
      const body: Record<string, unknown> = {};
      if (form.lot_number) body.lot_number = form.lot_number;
      if (form.batch_number) body.batch_number = form.batch_number;
      if (form.product_id) body.product_id = form.product_id;
      if (form.material_id) body.material_id = form.material_id;
      if (form.supplier_id) body.supplier_id = form.supplier_id;
      if (form.customer_id) body.customer_id = form.customer_id;
      if (form.date_from) body.date_from = form.date_from;
      if (form.date_to) body.date_to = form.date_to;
      const r = await traceApi.search(body);
      setResults(r);
      setSearched(true);
    } catch (e: any) { alert(e.message); }
    finally { setSearching(false); }
  };

  return (
    <div className="p-6 space-y-6">
      <div>
        <h1 className="text-xl font-bold text-gray-900">Traceability Search Console</h1>
        <p className="text-sm text-gray-500">Search by lot, batch, product, material, supplier, or customer</p>
      </div>

      {/* Search form */}
      <div className="bg-white rounded-xl border border-gray-200 p-5 space-y-4">
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {[
            { label: "Lot Number", key: "lot_number" },
            { label: "Batch Number", key: "batch_number" },
            { label: "Product ID", key: "product_id" },
            { label: "Material ID", key: "material_id" },
            { label: "Supplier ID", key: "supplier_id" },
            { label: "Customer ID", key: "customer_id" },
            { label: "Date From", key: "date_from", type: "date" },
            { label: "Date To", key: "date_to", type: "date" },
          ].map(f => (
            <div key={f.key}>
              <label className="text-xs font-medium text-gray-600">{f.label}</label>
              <input type={f.type || "text"} className="mt-1 w-full border rounded-lg px-3 py-2 text-sm"
                value={(form as any)[f.key]}
                onChange={e => setForm(prev => ({ ...prev, [f.key]: e.target.value }))} />
            </div>
          ))}
        </div>
        <button onClick={handleSearch} disabled={searching}
          className="px-6 py-2 bg-indigo-600 text-white text-sm rounded-lg hover:bg-indigo-700 disabled:opacity-50 font-medium">
          {searching ? "Searching…" : "Search Traceability"}
        </button>
      </div>

      {/* Results */}
      {searched && (
        <div className="space-y-4">
          <p className="text-sm text-gray-600">{results.length} result(s) found</p>
          {results.length === 0 ? (
            <div className="bg-gray-50 rounded-xl border border-gray-200 p-8 text-center text-gray-400">
              No lots found matching the search criteria
            </div>
          ) : results.map(r => (
            <div key={r.lot_id} className="bg-white rounded-xl border border-gray-200 p-5">
              <div className="flex items-start justify-between mb-3">
                <div>
                  <p className="font-semibold text-gray-800 text-lg">{r.lot_number || "—"}</p>
                  <div className="flex gap-3 text-xs text-gray-500 mt-1">
                    {r.batch_number && <span>Batch: {r.batch_number}</span>}
                    {r.stage && (
                      <span className={`px-2 py-0.5 rounded border text-xs ${STAGE_COLOR[r.stage]}`}>
                        {r.stage}
                      </span>
                    )}
                    <span>{r.genealogy_link_count} genealogy links</span>
                    {r.has_recall && <span className="text-red-600 font-semibold">⚠ In Recall</span>}
                  </div>
                </div>
                <div className="flex gap-2">
                  <a href={`/dashboard/traceability/backward?lot_id=${r.lot_id}`}
                    className="px-3 py-1.5 text-xs border border-gray-200 rounded-lg hover:bg-gray-50">
                    ← Backward Trace
                  </a>
                  <a href={`/dashboard/traceability/forward?lot_id=${r.lot_id}`}
                    className="px-3 py-1.5 text-xs border border-indigo-200 text-indigo-700 rounded-lg hover:bg-indigo-50">
                    Forward Trace →
                  </a>
                  <a href={`/dashboard/traceability/genealogy?lot_id=${r.lot_id}`}
                    className="px-3 py-1.5 text-xs bg-purple-600 text-white rounded-lg hover:bg-purple-700">
                    Genealogy
                  </a>
                </div>
              </div>

              {r.events.length > 0 && (
                <div>
                  <p className="text-xs font-medium text-gray-500 uppercase mb-2">Recent Events ({r.events.length})</p>
                  <div className="flex flex-wrap gap-2">
                    {r.events.slice(0, 8).map(e => (
                      <span key={e.id} className="px-2 py-1 bg-gray-100 text-gray-700 rounded text-xs">
                        {TRACE_EVENT_LABEL[e.trace_event_type]} — {new Date(e.event_datetime).toLocaleDateString()}
                      </span>
                    ))}
                    {r.events.length > 8 && (
                      <span className="px-2 py-1 text-gray-400 text-xs">+{r.events.length - 8} more</span>
                    )}
                  </div>
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
