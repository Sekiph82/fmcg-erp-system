"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { gs1Api, statusColor, BarcodeGenerateResponse, BarcodeType } from "@/lib/gs1";

function StatCard({ label, value, sub }: { label: string; value: number | string; sub?: string }) {
  return (
    <div className="bg-white border rounded-lg p-4">
      <p className="text-xs text-gray-500 uppercase tracking-wide">{label}</p>
      <p className="text-2xl font-bold text-gray-900 mt-1">{value}</p>
      {sub && <p className="text-xs text-gray-400 mt-0.5">{sub}</p>}
    </div>
  );
}

function printBarcodeInWindow(b64: string, aiString: string) {
  const win = window.open("", "_blank", "width=420,height=320");
  if (!win) {
    alert("Popup blocked — allow popups for this site to print labels.");
    return;
  }
  win.document.write(
    `<!DOCTYPE html><html><head><title>Barcode Label</title>` +
    `<style>body{margin:0;padding:16px;font-family:monospace;text-align:center}` +
    `img{max-width:320px;display:block;margin:0 auto}` +
    `p{font-size:11px;margin:6px 0 0}</style></head>` +
    `<body><img src="data:image/png;base64,${b64}"/><p>${aiString}</p></body></html>`
  );
  win.document.close();
  setTimeout(() => { win.focus(); win.print(); }, 300);
}

export default function GS1DashboardPage() {
  const qc = useQueryClient();
  const { data, isLoading, isError } = useQuery({
    queryKey: ["gs1-dashboard"],
    queryFn: gs1Api.getDashboard,
  });

  const [showForm, setShowForm] = useState(false);
  const [gtin, setGtin] = useState("");
  const [lotNo, setLotNo] = useState("");
  const [expiry, setExpiry] = useState("");
  const [barcodeType, setBarcodeType] = useState<BarcodeType>("GS1_128");
  const [generated, setGenerated] = useState<BarcodeGenerateResponse | null>(null);

  const validator = useMutation({
    mutationFn: gs1Api.runLabelValidator,
    onSuccess: (r) => {
      qc.invalidateQueries({ queryKey: ["gs1-dashboard"] });
      alert(`Label Validator ran — ${r.generated} recommendation(s) generated`);
    },
  });

  const optimizer = useMutation({
    mutationFn: gs1Api.runPackagingOptimizer,
    onSuccess: (r) => {
      qc.invalidateQueries({ queryKey: ["gs1-dashboard"] });
      alert(`Packaging Optimizer ran — ${r.generated} recommendation(s) generated`);
    },
  });

  const generateMut = useMutation({
    mutationFn: () =>
      gs1Api.generateBarcode({
        gtin,
        lot_number: lotNo,
        expiry_date: expiry || undefined,
        barcode_type: barcodeType,
        save_record: true,
      }),
    onSuccess: (r) => {
      setGenerated(r);
      qc.invalidateQueries({ queryKey: ["gs1-dashboard"] });
    },
  });

  const printMut = useMutation({
    mutationFn: async (recordId: string) => {
      const job = await gs1Api.createPrintJob({
        trigger: "MANUAL",
        items: [{ lot_barcode_id: recordId, copies: 1 }],
      });
      const barcode = await gs1Api.getBarcode(recordId);
      await gs1Api.completePrintJob(job.id);
      return barcode;
    },
    onSuccess: (barcode) => {
      if (barcode.barcode_image_b64) {
        printBarcodeInWindow(barcode.barcode_image_b64, barcode.gs1_ai_string);
      } else {
        alert("Barcode image not available — regenerate the barcode to include image data.");
      }
      qc.invalidateQueries({ queryKey: ["gs1-dashboard"] });
    },
    onError: (err: Error) => alert(`Print failed: ${err.message}`),
  });

  if (isLoading) return <div className="p-8 text-gray-400">Loading GS1 dashboard…</div>;
  if (isError || !data)
    return (
      <div className="p-8 text-red-500">
        Failed to load GS1 &amp; Label Printing dashboard. Ensure the database migration has been
        run (<code>alembic upgrade head</code>).
      </div>
    );

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold text-gray-900">GS1 Barcode &amp; Label Printing</h1>
          <p className="text-sm text-gray-500">
            Global product identification · SSCC pallet tracking · Label management
          </p>
        </div>
        <div className="flex gap-2">
          <button
            onClick={() => { setShowForm((v) => !v); setGenerated(null); }}
            className="px-3 py-1.5 text-sm bg-green-600 text-white rounded hover:bg-green-700"
          >
            {showForm ? "Close Form" : "Generate Label"}
          </button>
          <button
            onClick={() => validator.mutate()}
            disabled={validator.isPending}
            className="px-3 py-1.5 text-sm bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50"
          >
            {validator.isPending ? "Running…" : "Run Label Validator"}
          </button>
          <button
            onClick={() => optimizer.mutate()}
            disabled={optimizer.isPending}
            className="px-3 py-1.5 text-sm bg-purple-600 text-white rounded hover:bg-purple-700 disabled:opacity-50"
          >
            {optimizer.isPending ? "Running…" : "Packaging Optimizer"}
          </button>
        </div>
      </div>

      {/* ── Generate Label Form ──────────────────────────────────────────────── */}
      {showForm && (
        <div className="bg-white border rounded-lg p-5 space-y-4">
          <h2 className="text-sm font-semibold text-gray-800">Generate Barcode Label</h2>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            <div>
              <label className="block text-xs text-gray-500 mb-1">
                GTIN <span className="text-red-400">*</span>
              </label>
              <input
                value={gtin}
                onChange={(e) => setGtin(e.target.value)}
                placeholder="e.g. 05901234123457"
                className="w-full border rounded px-2 py-1.5 text-sm"
              />
            </div>
            <div>
              <label className="block text-xs text-gray-500 mb-1">
                Lot Number <span className="text-red-400">*</span>
              </label>
              <input
                value={lotNo}
                onChange={(e) => setLotNo(e.target.value)}
                placeholder="e.g. LOT-2026-001"
                className="w-full border rounded px-2 py-1.5 text-sm"
              />
            </div>
            <div>
              <label className="block text-xs text-gray-500 mb-1">Expiry Date</label>
              <input
                type="date"
                value={expiry}
                onChange={(e) => setExpiry(e.target.value)}
                className="w-full border rounded px-2 py-1.5 text-sm"
              />
            </div>
            <div>
              <label className="block text-xs text-gray-500 mb-1">Barcode Type</label>
              <select
                value={barcodeType}
                onChange={(e) => setBarcodeType(e.target.value as BarcodeType)}
                className="w-full border rounded px-2 py-1.5 text-sm"
              >
                <option value="GS1_128">GS1-128</option>
                <option value="EAN13">EAN-13</option>
                <option value="QR_CODE">QR Code</option>
                <option value="GS1_DATAMATRIX">GS1 DataMatrix</option>
                <option value="CODE128">Code 128</option>
              </select>
            </div>
          </div>
          <div className="flex items-center gap-3">
            <button
              onClick={() => generateMut.mutate()}
              disabled={!gtin || !lotNo || generateMut.isPending}
              className="px-4 py-1.5 text-sm bg-green-600 text-white rounded hover:bg-green-700 disabled:opacity-50"
            >
              {generateMut.isPending ? "Generating…" : "Generate Barcode"}
            </button>
            {generateMut.isError && (
              <span className="text-sm text-red-500">
                {(generateMut.error as Error).message}
              </span>
            )}
          </div>

          {generated && (
            <div className="mt-2 border-t pt-4 flex items-start gap-6">
              {generated.barcode_image_b64 && (
                <img
                  src={`data:image/png;base64,${generated.barcode_image_b64}`}
                  alt="barcode"
                  className="h-20 border rounded"
                />
              )}
              {generated.qr_image_b64 && (
                <img
                  src={`data:image/png;base64,${generated.qr_image_b64}`}
                  alt="qr code"
                  className="h-20 border rounded"
                />
              )}
              <div className="space-y-1 text-sm">
                <p>
                  <span className="text-gray-500">GS1 AI String: </span>
                  <code className="font-mono text-xs">{generated.gs1_ai_string}</code>
                </p>
                <p><span className="text-gray-500">GTIN: </span>{generated.gtin}</p>
                {generated.lot_number && (
                  <p><span className="text-gray-500">Lot: </span>{generated.lot_number}</p>
                )}
                {generated.expiry_date && (
                  <p><span className="text-gray-500">Expiry: </span>{generated.expiry_date}</p>
                )}
                {generated.record_id && (
                  <button
                    onClick={() => printMut.mutate(generated.record_id!)}
                    disabled={printMut.isPending}
                    className="mt-2 px-3 py-1 text-xs bg-gray-800 text-white rounded hover:bg-gray-700 disabled:opacity-50"
                  >
                    {printMut.isPending ? "Printing…" : "Print This Label"}
                  </button>
                )}
                {!generated.record_id && (
                  <p className="text-xs text-amber-600 mt-1">
                    Barcode generated (not saved) — re-generate with save_record=true to enable printing.
                  </p>
                )}
              </div>
            </div>
          )}
        </div>
      )}

      {/* ── KPI Grid ────────────────────────────────────────────────────────── */}
      <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-5 gap-4">
        <StatCard label="Products Configured" value={data.total_products_configured} />
        <StatCard label="Total GTINs" value={data.total_gtins} />
        <StatCard label="Barcodes Generated" value={data.total_barcodes_generated} />
        <StatCard label="Labels Printed" value={data.total_labels_printed} />
        <StatCard
          label="SSCC Pallets"
          value={data.total_sscc_pallets}
          sub={`${data.active_sscc_pallets} active`}
        />
        <StatCard
          label="Print Jobs"
          value={data.total_print_jobs}
          sub={`${data.pending_print_jobs} pending`}
        />
        <StatCard label="Label Templates" value={data.total_label_templates} />
        <StatCard label="AI Alerts Pending" value={data.ai_recommendations_pending} />
      </div>

      {/* ── Recent Barcodes ──────────────────────────────────────────────────── */}
      <div className="bg-white border rounded-lg overflow-hidden">
        <div className="px-4 py-3 border-b">
          <h2 className="text-sm font-medium text-gray-700">Recent Barcodes Generated</h2>
        </div>
        <table className="w-full text-sm">
          <thead className="bg-gray-50 text-xs text-gray-500 uppercase">
            <tr>
              <th className="px-4 py-2 text-left">GTIN</th>
              <th className="px-4 py-2 text-left">Lot Number</th>
              <th className="px-4 py-2 text-left">Expiry</th>
              <th className="px-4 py-2 text-left">Type</th>
              <th className="px-4 py-2 text-left">GS1 AI String</th>
              <th className="px-4 py-2 text-left">Printed</th>
              <th className="px-4 py-2 text-left">Action</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {data.recent_barcodes.length === 0 && (
              <tr>
                <td colSpan={7} className="px-4 py-6 text-center text-gray-400">
                  No barcodes generated yet — use &quot;Generate Label&quot; above
                </td>
              </tr>
            )}
            {data.recent_barcodes.map((b) => (
              <tr key={b.id} className="hover:bg-gray-50">
                <td className="px-4 py-2 font-mono text-xs">{b.gtin}</td>
                <td className="px-4 py-2">{b.lot_number}</td>
                <td className="px-4 py-2 text-gray-500">{b.expiry_date || "—"}</td>
                <td className="px-4 py-2">
                  <span className="px-2 py-0.5 bg-blue-50 text-blue-700 rounded text-xs">
                    {b.barcode_type}
                  </span>
                </td>
                <td className="px-4 py-2 font-mono text-xs text-gray-500 max-w-xs truncate">
                  {b.gs1_ai_string}
                </td>
                <td className="px-4 py-2">
                  {b.is_printed
                    ? <span className="text-green-600">✓</span>
                    : <span className="text-gray-400">—</span>}
                </td>
                <td className="px-4 py-2">
                  <button
                    onClick={() => printMut.mutate(b.id)}
                    disabled={printMut.isPending && printMut.variables === b.id}
                    className="px-2 py-0.5 text-xs bg-gray-700 text-white rounded hover:bg-gray-600 disabled:opacity-50"
                  >
                    {printMut.isPending && printMut.variables === b.id ? "…" : "Print"}
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* ── Recent SSCC ─────────────────────────────────────────────────────── */}
      <div className="bg-white border rounded-lg overflow-hidden">
        <div className="px-4 py-3 border-b">
          <h2 className="text-sm font-medium text-gray-700">Recent SSCC Pallets</h2>
        </div>
        <table className="w-full text-sm">
          <thead className="bg-gray-50 text-xs text-gray-500 uppercase">
            <tr>
              <th className="px-4 py-2 text-left">SSCC Code</th>
              <th className="px-4 py-2 text-left">Pallet ID</th>
              <th className="px-4 py-2 text-left">Status</th>
              <th className="px-4 py-2 text-left">Lots</th>
              <th className="px-4 py-2 text-left">Location</th>
              <th className="px-4 py-2 text-left">Created</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {data.recent_sscc.length === 0 && (
              <tr>
                <td colSpan={6} className="px-4 py-6 text-center text-gray-400">
                  No SSCC pallets yet
                </td>
              </tr>
            )}
            {data.recent_sscc.map((p) => (
              <tr key={p.id} className="hover:bg-gray-50">
                <td className="px-4 py-2 font-mono text-xs">{p.sscc_code}</td>
                <td className="px-4 py-2 text-gray-700">{p.pallet_id || "—"}</td>
                <td className="px-4 py-2">
                  <span className={`px-2 py-0.5 rounded text-xs font-medium ${statusColor[p.status] ?? ""}`}>
                    {p.status}
                  </span>
                </td>
                <td className="px-4 py-2">{p.lot_count}</td>
                <td className="px-4 py-2 text-gray-500">{p.warehouse_location || "—"}</td>
                <td className="px-4 py-2 text-gray-400">
                  {new Date(p.created_at).toLocaleDateString()}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
