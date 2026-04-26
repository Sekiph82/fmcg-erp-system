"use client";
import { useState, useEffect } from "react";
import { plApi, PLHeader } from "@/lib/price_list";

export default function BulkImportPage() {
  const [headers, setHeaders] = useState<PLHeader[]>([]);
  const [headerId, setHeaderId] = useState("");
  const [importedBy, setImportedBy] = useState("");
  const [csvText, setCsvText] = useState("");
  const [result, setResult] = useState<{ imported: number; skipped: number; errors: string[] } | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => { plApi.listHeaders({ status: "DRAFT" }).then(setHeaders); }, []);

  const parseCSV = (text: string) => {
    const lines = text.trim().split("\n");
    const headers = lines[0].split(",").map((h) => h.trim().replace(/"/g, ""));
    return lines.slice(1).map((line) => {
      const vals = line.split(",").map((v) => v.trim().replace(/"/g, ""));
      return Object.fromEntries(headers.map((h, i) => [h, vals[i] || ""]));
    });
  };

  const doImport = async () => {
    if (!headerId || !csvText.trim() || !importedBy) return;
    setLoading(true);
    try {
      const rows = parseCSV(csvText).map((r) => ({
        product_code: r.product_code,
        uom: r.uom || "KG",
        base_price: Number(r.base_price),
        currency: r.currency || "KES",
        minimum_price: r.minimum_price ? Number(r.minimum_price) : undefined,
        valid_from: r.valid_from || undefined,
        valid_to: r.valid_to || undefined,
        notes: r.notes || undefined,
      }));
      const res = await plApi.bulkImport({ header_id: headerId, rows, imported_by: importedBy });
      setResult(res);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="p-6 space-y-6">
      <div>
        <h1 className="text-xl font-bold text-gray-900">Bulk Price Import</h1>
        <p className="text-sm text-gray-500 mt-1">Import price lines from CSV into a draft price list</p>
      </div>

      <div className="grid grid-cols-2 gap-6">
        <div className="bg-white rounded-xl border border-gray-200 p-5 space-y-4">
          <h2 className="font-semibold text-gray-900">Import Configuration</h2>
          <div>
            <label className="text-xs font-medium text-gray-700">Target Price List (DRAFT only)</label>
            <select value={headerId} onChange={(e) => setHeaderId(e.target.value)}
              className="mt-1 w-full border border-gray-300 rounded-lg px-3 py-2 text-sm">
              <option value="">Select a draft price list…</option>
              {headers.map((h) => <option key={h.id} value={h.id}>{h.price_list_code} — {h.price_list_name}</option>)}
            </select>
          </div>
          <div>
            <label className="text-xs font-medium text-gray-700">Imported By</label>
            <input value={importedBy} onChange={(e) => setImportedBy(e.target.value)}
              className="mt-1 w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" placeholder="Your name" />
          </div>
          <div>
            <label className="text-xs font-medium text-gray-700">CSV Data (paste here)</label>
            <div className="mt-1 text-xs text-gray-400 mb-1">Required: product_code, uom, base_price, currency</div>
            <textarea value={csvText} onChange={(e) => setCsvText(e.target.value)} rows={10}
              className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm font-mono"
              placeholder="product_code,uom,base_price,currency,minimum_price,valid_from,valid_to&#10;SKU-001,KG,150.00,KES,120.00,2026-01-01," />
          </div>
          <div className="flex gap-3">
            <button onClick={doImport} disabled={loading || !headerId || !csvText.trim() || !importedBy}
              className="flex-1 px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium disabled:opacity-50">
              {loading ? "Importing…" : "Import"}
            </button>
            <a href={plApi.downloadTemplate()} download="price_list_template.csv"
              className="px-4 py-2 border border-gray-300 rounded-lg text-sm text-gray-700 hover:bg-gray-50">
              Download Template
            </a>
          </div>
        </div>

        <div className="space-y-4">
          {result && (
            <div className={`bg-white rounded-xl border p-5 ${result.errors.length > 0 ? "border-yellow-300" : "border-green-300"}`}>
              <h3 className="font-semibold text-gray-900 mb-3">Import Result</h3>
              <div className="grid grid-cols-3 gap-3 text-center mb-4">
                <div>
                  <div className="text-2xl font-bold text-green-700">{result.imported}</div>
                  <div className="text-xs text-gray-500">Imported</div>
                </div>
                <div>
                  <div className="text-2xl font-bold text-yellow-700">{result.skipped}</div>
                  <div className="text-xs text-gray-500">Skipped</div>
                </div>
                <div>
                  <div className="text-2xl font-bold text-red-700">{result.errors.length}</div>
                  <div className="text-xs text-gray-500">Errors</div>
                </div>
              </div>
              {result.errors.length > 0 && (
                <div className="space-y-1">
                  <div className="text-xs font-semibold text-red-700">Errors:</div>
                  {result.errors.map((e, i) => (
                    <div key={i} className="text-xs text-red-600 bg-red-50 px-2 py-1 rounded">{e}</div>
                  ))}
                </div>
              )}
            </div>
          )}

          <div className="bg-white rounded-xl border border-gray-200 p-5">
            <h3 className="font-semibold text-gray-900 mb-3">CSV Format Guide</h3>
            <div className="text-xs text-gray-600 space-y-1">
              <div><strong>product_code</strong> — SKU code from product master (required)</div>
              <div><strong>uom</strong> — Unit of measure e.g. KG, PCS, CTN (required)</div>
              <div><strong>base_price</strong> — Price number e.g. 150.00 (required)</div>
              <div><strong>currency</strong> — ISO currency e.g. KES, USD (required)</div>
              <div><strong>minimum_price</strong> — Floor price (optional)</div>
              <div><strong>valid_from</strong> — YYYY-MM-DD (optional)</div>
              <div><strong>valid_to</strong> — YYYY-MM-DD (optional)</div>
              <div><strong>notes</strong> — Free text (optional)</div>
            </div>
            <div className="mt-3 bg-gray-50 p-2 rounded font-mono text-xs text-gray-600">
              product_code,uom,base_price,currency<br />
              SKU-001,KG,150.00,KES<br />
              SKU-002,CTN,1200.00,KES<br />
              SKU-003,PCS,45.00,KES
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
