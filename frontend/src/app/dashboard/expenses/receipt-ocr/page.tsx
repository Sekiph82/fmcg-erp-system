"use client";
import { useEffect, useState } from "react";

interface OCRResult {
  id: string;
  status: string;
  extracted: {
    vendor: string | null;
    amount: number | null;
    currency: string | null;
    date: string | null;
    category: string | null;
    confidence_score: number | null;
  };
  is_duplicate: boolean;
  duplicate_of_id: string | null;
  processing_notes: string | null;
}

interface OCRRecord {
  id: string;
  file_name: string | null;
  extracted_vendor: string | null;
  extracted_amount: number | null;
  extracted_date: string | null;
  extracted_category: string | null;
  confidence_score: number | null;
  status: string;
  is_duplicate: boolean;
  linked_expense_claim_id: string | null;
  submitted_by: string | null;
  created_at: string;
}

interface Stats { total_receipts: number; duplicates_caught: number; linked_to_expenses: number; avg_confidence_score: number | null; }

const CONF_COLOR = (c: number | null) => {
  if (!c) return "text-gray-400";
  if (c >= 80) return "text-green-600";
  if (c >= 60) return "text-amber-600";
  return "text-red-500";
};

const STATUS_COLOR: Record<string, string> = {
  PROCESSED: "bg-green-100 text-green-700",
  LINKED: "bg-blue-100 text-blue-700",
  DUPLICATE: "bg-amber-100 text-amber-600",
  FAILED: "bg-red-100 text-red-600",
  PENDING: "bg-gray-100 text-gray-500",
};

export default function ReceiptOCRPage() {
  const [records, setRecords] = useState<OCRRecord[]>([]);
  const [stats, setStats] = useState<Stats | null>(null);
  const [loading, setLoading] = useState(true);
  const [imageUrl, setImageUrl] = useState("");
  const [fileName, setFileName] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [result, setResult] = useState<OCRResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [linkId, setLinkId] = useState<Record<string, string>>({});
  const [linking, setLinking] = useState<string | null>(null);

  const load = () => {
    setLoading(true);
    Promise.all([
      fetch("/api/v1/receipt-ocr/?limit=30").then(r => r.json()),
      fetch("/api/v1/receipt-ocr/stats/summary").then(r => r.json()),
    ]).then(([r, s]) => { setRecords(r); setStats(s); }).finally(() => setLoading(false));
  };
  useEffect(load, []);

  const submit = async () => {
    if (!imageUrl.trim()) return;
    setSubmitting(true); setError(null); setResult(null);
    try {
      const r = await fetch("/api/v1/receipt-ocr/", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ image_url: imageUrl, file_name: fileName || undefined }),
      });
      if (!r.ok) throw new Error(await r.text());
      const res = await r.json();
      setResult(res);
      setImageUrl(""); setFileName("");
      load();
    } catch (e) { setError(String(e)); }
    setSubmitting(false);
  };

  const linkExpense = async (recordId: string) => {
    const claimId = linkId[recordId];
    if (!claimId) return;
    setLinking(recordId);
    await fetch(`/api/v1/receipt-ocr/${recordId}/link-expense`, {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ expense_claim_id: claimId }),
    });
    setLinking(null);
    load();
  };

  return (
    <div className="p-6 space-y-6 max-w-5xl mx-auto">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">AI Receipt OCR</h1>
        <p className="text-sm text-gray-500 mt-0.5">
          Auto-extract vendor, amount, date, and category from receipt images.
        </p>
      </div>

      {error && <div className="bg-red-50 border border-red-200 rounded p-3 text-sm text-red-700">{error}</div>}

      {/* Stats */}
      {stats && (
        <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
          {[
            { label: "Total Receipts", value: stats.total_receipts, color: "text-gray-800" },
            { label: "Duplicates Caught", value: stats.duplicates_caught, color: "text-amber-600" },
            { label: "Linked to Claims", value: stats.linked_to_expenses, color: "text-blue-600" },
            { label: "Avg Confidence", value: stats.avg_confidence_score ? `${stats.avg_confidence_score}%` : "—", color: CONF_COLOR(stats.avg_confidence_score) },
          ].map(k => (
            <div key={k.label} className="bg-white border rounded-lg p-4 shadow-sm">
              <p className="text-xs text-gray-500">{k.label}</p>
              <p className={`text-2xl font-bold mt-1 ${k.color}`}>{k.value}</p>
            </div>
          ))}
        </div>
      )}

      {/* Submit form */}
      <div className="bg-white border rounded-lg p-5 shadow-sm space-y-3">
        <h2 className="text-sm font-semibold text-gray-700">Scan Receipt</h2>
        <p className="text-xs text-gray-400">
          Paste image URL or storage path. Production: integrate Google Vision / AWS Textract for real OCR.
        </p>
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
          <div className="sm:col-span-2">
            <label className="text-xs text-gray-500 block mb-1">Image URL *</label>
            <input type="text" value={imageUrl} onChange={(e) => setImageUrl(e.target.value)}
              placeholder="https://storage.company.com/receipts/naivas_1250.jpg"
              className="w-full border border-gray-300 rounded px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-blue-500" />
          </div>
          <div>
            <label className="text-xs text-gray-500 block mb-1">File Name (optional)</label>
            <input type="text" value={fileName} onChange={(e) => setFileName(e.target.value)}
              placeholder="e.g. receipt_naivas_1250.jpg"
              className="w-full border border-gray-300 rounded px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-blue-500" />
          </div>
        </div>
        <button onClick={submit} disabled={submitting || !imageUrl.trim()}
          className="bg-blue-600 hover:bg-blue-700 text-white text-sm font-medium px-5 py-2 rounded disabled:opacity-50">
          {submitting ? "Processing…" : "Extract Receipt Data"}
        </button>
      </div>

      {/* OCR Result */}
      {result && (
        <div className={`border rounded-lg p-4 shadow-sm space-y-3 ${result.is_duplicate ? "bg-amber-50 border-amber-300" : "bg-green-50 border-green-200"}`}>
          <div className="flex items-start justify-between">
            <p className={`text-sm font-semibold ${result.is_duplicate ? "text-amber-800" : "text-green-800"}`}>
              {result.is_duplicate ? "⚠ Duplicate Receipt Detected" : "✓ Receipt Extracted"}
            </p>
            <span className={`text-xs font-medium ${CONF_COLOR(result.extracted.confidence_score)}`}>
              Confidence: {result.extracted.confidence_score}%
            </span>
          </div>
          <div className="grid grid-cols-2 gap-2 sm:grid-cols-4 text-sm">
            <div><p className="text-xs text-gray-500">Vendor</p><p className="font-medium">{result.extracted.vendor}</p></div>
            <div><p className="text-xs text-gray-500">Amount</p><p className="font-medium">{result.extracted.currency} {result.extracted.amount?.toLocaleString() ?? "—"}</p></div>
            <div><p className="text-xs text-gray-500">Date</p><p className="font-medium">{result.extracted.date}</p></div>
            <div><p className="text-xs text-gray-500">Category</p><p className="font-medium">{result.extracted.category}</p></div>
          </div>
          {result.processing_notes && (
            <p className="text-xs text-gray-500 italic">{result.processing_notes}</p>
          )}
          <button onClick={() => setResult(null)} className="text-xs underline text-gray-500">Dismiss</button>
        </div>
      )}

      {/* Records list */}
      <div className="bg-white border rounded-lg shadow-sm overflow-hidden">
        <div className="px-4 py-3 border-b bg-gray-50 flex items-center justify-between">
          <h2 className="text-sm font-semibold text-gray-700">Receipt History ({records.length})</h2>
          <button onClick={load} disabled={loading} className="text-xs text-blue-600 hover:text-blue-800 disabled:opacity-50">Refresh</button>
        </div>
        {loading ? <div className="p-6 text-sm text-gray-400 text-center">Loading…</div> :
         records.length === 0 ? <div className="p-6 text-sm text-gray-400 text-center">No receipts scanned yet.</div> : (
          <div className="divide-y">
            {records.map((rec) => (
              <div key={rec.id} className={`px-4 py-3 ${rec.is_duplicate ? "bg-amber-50" : ""}`}>
                <div className="flex items-start gap-3">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 flex-wrap">
                      {rec.is_duplicate && <span className="text-xs bg-amber-500 text-white rounded px-2 py-0.5 font-bold">DUP</span>}
                      <span className="font-medium text-sm text-gray-900">{rec.extracted_vendor ?? "Unknown"}</span>
                      <span className={`text-xs rounded-full px-2 py-0.5 ${STATUS_COLOR[rec.status] ?? "bg-gray-100"}`}>{rec.status}</span>
                    </div>
                    <div className="text-xs text-gray-500 mt-0.5 flex gap-3 flex-wrap">
                      {rec.extracted_amount && <span className="font-semibold text-gray-700">KES {rec.extracted_amount.toLocaleString()}</span>}
                      {rec.extracted_date && <span>{rec.extracted_date}</span>}
                      {rec.extracted_category && <span>{rec.extracted_category}</span>}
                      <span className={`${CONF_COLOR(rec.confidence_score)}`}>
                        {rec.confidence_score}% confidence
                      </span>
                    </div>
                    {rec.file_name && <p className="text-xs text-gray-400 mt-0.5 truncate">{rec.file_name}</p>}
                  </div>
                  {rec.status === "PROCESSED" && !rec.linked_expense_claim_id && (
                    <div className="flex items-center gap-2 shrink-0">
                      <input
                        type="text"
                        placeholder="Claim ID"
                        value={linkId[rec.id] ?? ""}
                        onChange={(e) => setLinkId(p => ({ ...p, [rec.id]: e.target.value }))}
                        className="border border-gray-300 rounded px-2 py-1 text-xs w-28 focus:outline-none"
                      />
                      <button
                        onClick={() => linkExpense(rec.id)}
                        disabled={linking === rec.id || !linkId[rec.id]}
                        className="text-xs text-blue-600 hover:text-blue-800 disabled:opacity-50"
                      >
                        {linking === rec.id ? "…" : "Link"}
                      </button>
                    </div>
                  )}
                  {rec.linked_expense_claim_id && (
                    <span className="text-xs text-blue-500 shrink-0 font-mono">{rec.linked_expense_claim_id.slice(0, 8)}…</span>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Integration guide */}
      <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 text-sm text-blue-800">
        <p className="font-semibold mb-1">Production OCR Integration</p>
        <p className="text-xs text-blue-700">
          Current mode: <strong>stub</strong> (pattern-based extraction from filename).
          To enable real OCR:
          1. Install <code className="bg-blue-100 px-1 rounded">google-cloud-vision</code> or <code className="bg-blue-100 px-1 rounded">amazon-textract-textractor</code>.
          2. Replace <code className="bg-blue-100 px-1 rounded">_stub_extract()</code> in <code className="bg-blue-100 px-1 rounded">receipt_ocr.py</code> with actual API call.
          3. Parse structured JSON response into extracted fields.
          Mobile scanning: use device camera → upload to storage → POST URL to this API.
        </p>
      </div>
    </div>
  );
}
