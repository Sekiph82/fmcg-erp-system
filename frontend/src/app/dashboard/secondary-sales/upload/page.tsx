"use client";

import { useState, useEffect, useRef } from "react";
import { useRouter } from "next/navigation";
import { secondarySalesApi, UploadSource, SecondarySalesLineInput } from "@/lib/secondarySales";

export default function SecondarySalesUploadPage() {
  const router = useRouter();
  const fileRef = useRef<HTMLInputElement>(null);
  const [distributors, setDistributors] = useState<{ id: string; name: string }[]>([]);
  const [form, setForm] = useState({
    distributor_id: "",
    period_from: "",
    period_to: "",
    upload_source: "MANUAL_CSV" as UploadSource,
    notes: "",
  });
  const [lines, setLines] = useState<SecondarySalesLineInput[]>([
    { product_sku: "", retailer_name: "", quantity_sold: 0 },
  ]);
  const [csvPreview, setCsvPreview] = useState<string[][]>([]);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    // Load distributors from distributors API
    import("@/lib/api").then(({ apiClient }) => {
      apiClient.get("/api/v1/distributors/").then((res) => {
        const data = res.data?.data ?? res.data;
        setDistributors((data || []).map((d: any) => ({ id: d.id, name: d.name })));
      });
    });
  }, []);

  const addLine = () =>
    setLines((prev) => [...prev, { product_sku: "", retailer_name: "", quantity_sold: 0 }]);

  const removeLine = (idx: number) =>
    setLines((prev) => prev.filter((_, i) => i !== idx));

  const updateLine = (idx: number, field: keyof SecondarySalesLineInput, value: any) =>
    setLines((prev) => prev.map((l, i) => (i === idx ? { ...l, [field]: value } : l)));

  const handleCsvParse = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = (ev) => {
      const text = ev.target?.result as string;
      const rows = text.split("\n").map((r) => r.split(",").map((c) => c.trim().replace(/^"|"$/g, "")));
      setCsvPreview(rows.slice(0, 6));

      // Auto-map CSV to lines (expect: retailer_name, product_sku, quantity_sold, unit_price, sale_date)
      const parsed: SecondarySalesLineInput[] = rows.slice(1)
        .filter((r) => r.length >= 3 && r[0])
        .map((r) => ({
          retailer_name: r[0] || undefined,
          product_sku: r[1] || undefined,
          quantity_sold: parseFloat(r[2]) || 0,
          unit_price: r[3] ? parseFloat(r[3]) : undefined,
          sale_date: r[4] || undefined,
        }));
      if (parsed.length > 0) setLines(parsed);
    };
    reader.readAsText(file);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!form.distributor_id) { setError("Select a distributor"); return; }
    if (lines.every((l) => !l.quantity_sold)) { setError("Add at least one line with quantity"); return; }
    setSubmitting(true);
    setError("");
    try {
      const validLines = lines.filter((l) => l.quantity_sold > 0);
      await secondarySalesApi.upload({
        ...form,
        lines: validLines,
      });
      router.push("/dashboard/secondary-sales");
    } catch (err: any) {
      setError(err?.response?.data?.detail || "Upload failed");
      setSubmitting(false);
    }
  };

  return (
    <div className="p-6 max-w-4xl mx-auto space-y-6">
      <div>
        <button onClick={() => router.back()} className="text-sm text-blue-600 hover:underline mb-4 inline-block">
          ← Back
        </button>
        <h1 className="text-2xl font-bold text-gray-900">Upload Secondary Sales Data</h1>
        <p className="text-sm text-gray-500 mt-1">Enter distributor sell-out data manually or via CSV</p>
      </div>

      <form onSubmit={handleSubmit} className="space-y-6">
        {/* Header fields */}
        <div className="bg-white rounded-lg border p-5 space-y-4">
          <h2 className="font-semibold text-gray-800">Upload Details</h2>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium mb-1">Distributor *</label>
              <select
                required
                value={form.distributor_id}
                onChange={(e) => setForm({ ...form, distributor_id: e.target.value })}
                className="w-full border rounded-lg px-3 py-2 text-sm"
              >
                <option value="">Select distributor…</option>
                {distributors.map((d) => (
                  <option key={d.id} value={d.id}>{d.name}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">Upload Source</label>
              <select
                value={form.upload_source}
                onChange={(e) => setForm({ ...form, upload_source: e.target.value as UploadSource })}
                className="w-full border rounded-lg px-3 py-2 text-sm"
              >
                {(["MANUAL_CSV", "POS", "ERP_INTEGRATION", "MOBILE", "API"] as UploadSource[]).map((s) => (
                  <option key={s} value={s}>{s}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">Period From *</label>
              <input
                required
                type="date"
                value={form.period_from}
                onChange={(e) => setForm({ ...form, period_from: e.target.value })}
                className="w-full border rounded-lg px-3 py-2 text-sm"
              />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">Period To *</label>
              <input
                required
                type="date"
                value={form.period_to}
                onChange={(e) => setForm({ ...form, period_to: e.target.value })}
                className="w-full border rounded-lg px-3 py-2 text-sm"
              />
            </div>
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">Notes</label>
            <textarea
              value={form.notes}
              onChange={(e) => setForm({ ...form, notes: e.target.value })}
              className="w-full border rounded-lg px-3 py-2 text-sm"
              rows={2}
            />
          </div>
        </div>

        {/* CSV Upload */}
        <div className="bg-white rounded-lg border p-5 space-y-3">
          <h2 className="font-semibold text-gray-800">CSV Import (Optional)</h2>
          <p className="text-xs text-gray-500">
            CSV columns: <code>retailer_name, product_sku, quantity_sold, unit_price (opt), sale_date (opt)</code>
          </p>
          <input
            ref={fileRef}
            type="file"
            accept=".csv"
            onChange={handleCsvParse}
            className="text-sm"
          />
          {csvPreview.length > 0 && (
            <div className="overflow-x-auto border rounded text-xs">
              <table className="min-w-full">
                {csvPreview.map((row, ri) => (
                  <tr key={ri} className={ri === 0 ? "bg-gray-50 font-semibold" : ""}>
                    {row.map((cell, ci) => (
                      <td key={ci} className="px-2 py-1 border-r">{cell}</td>
                    ))}
                  </tr>
                ))}
              </table>
            </div>
          )}
        </div>

        {/* Lines */}
        <div className="bg-white rounded-lg border p-5 space-y-3">
          <div className="flex items-center justify-between">
            <h2 className="font-semibold text-gray-800">Sales Lines ({lines.length})</h2>
            <button type="button" onClick={addLine} className="text-sm text-blue-600 hover:underline">
              + Add Line
            </button>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="text-xs text-gray-500 uppercase border-b">
                <tr>
                  <th className="py-2 text-left pr-3">Retailer Name</th>
                  <th className="py-2 text-left pr-3">Product SKU</th>
                  <th className="py-2 text-left pr-3">Qty Sold *</th>
                  <th className="py-2 text-left pr-3">Unit Price</th>
                  <th className="py-2 text-left pr-3">Sale Date</th>
                  <th className="py-2"></th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {lines.map((line, idx) => (
                  <tr key={idx}>
                    <td className="py-1 pr-2">
                      <input
                        value={line.retailer_name || ""}
                        onChange={(e) => updateLine(idx, "retailer_name", e.target.value)}
                        className="w-32 border rounded px-2 py-1 text-xs"
                        placeholder="Retailer…"
                      />
                    </td>
                    <td className="py-1 pr-2">
                      <input
                        value={line.product_sku || ""}
                        onChange={(e) => updateLine(idx, "product_sku", e.target.value)}
                        className="w-28 border rounded px-2 py-1 text-xs"
                        placeholder="SKU…"
                      />
                    </td>
                    <td className="py-1 pr-2">
                      <input
                        type="number"
                        step="0.001"
                        value={line.quantity_sold || ""}
                        onChange={(e) => updateLine(idx, "quantity_sold", parseFloat(e.target.value) || 0)}
                        className="w-24 border rounded px-2 py-1 text-xs"
                      />
                    </td>
                    <td className="py-1 pr-2">
                      <input
                        type="number"
                        step="0.01"
                        value={line.unit_price || ""}
                        onChange={(e) => updateLine(idx, "unit_price", parseFloat(e.target.value) || undefined)}
                        className="w-24 border rounded px-2 py-1 text-xs"
                      />
                    </td>
                    <td className="py-1 pr-2">
                      <input
                        type="date"
                        value={line.sale_date || ""}
                        onChange={(e) => updateLine(idx, "sale_date", e.target.value || undefined)}
                        className="border rounded px-2 py-1 text-xs"
                      />
                    </td>
                    <td className="py-1">
                      <button
                        type="button"
                        onClick={() => removeLine(idx)}
                        className="text-red-400 hover:text-red-600 text-xs"
                      >
                        ✕
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {error && <p className="text-red-600 text-sm">{error}</p>}

        <div className="flex gap-3">
          <button
            type="button"
            onClick={() => router.back()}
            className="flex-1 py-2 border rounded-lg text-sm hover:bg-gray-50"
          >
            Cancel
          </button>
          <button
            type="submit"
            disabled={submitting}
            className="flex-1 py-2 bg-blue-600 text-white rounded-lg text-sm hover:bg-blue-700 disabled:opacity-50"
          >
            {submitting ? "Uploading…" : "Upload & Validate"}
          </button>
        </div>
      </form>
    </div>
  );
}
