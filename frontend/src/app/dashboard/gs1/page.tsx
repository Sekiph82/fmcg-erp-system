"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { gs1Api, statusColor, BarcodeGenerateResponse, BarcodeType, PrintJob } from "@/lib/gs1";

// ── Local types ────────────────────────────────────────────────────────────────

type LabelSize = "50x30" | "70x40" | "100x50" | "a4";
type PrinterPreset = "browser" | "zebra" | "tsc" | "godex" | "a4office";

interface PrintConfig {
  b64: string;
  aiString: string;
  gtin: string;
  lotNo: string;
  expiry?: string;
  productionDate?: string;
  productName?: string;
  sku?: string;
  netWeight?: string;
  labelSize: LabelSize;
  preset: PrinterPreset;
  copies: number;
}

// ── Constants ──────────────────────────────────────────────────────────────────

const LABEL_SIZES: { value: LabelSize; label: string }[] = [
  { value: "50x30",  label: "50×30 mm — Thermal Small" },
  { value: "70x40",  label: "70×40 mm — Thermal Standard" },
  { value: "100x50", label: "100×50 mm — Thermal Wide" },
  { value: "a4",     label: "A4 — Office / Sheet Labels" },
];

const PRINTER_PRESETS: { value: PrinterPreset; label: string; hint: string }[] = [
  { value: "browser",  label: "Browser Default",  hint: "System print dialog, any printer" },
  { value: "zebra",    label: "Zebra Thermal",     hint: "Zebra ZD/ZT series via browser driver" },
  { value: "tsc",      label: "TSC Thermal",       hint: "TSC TTP series via browser driver" },
  { value: "godex",    label: "Godex Thermal",     hint: "Godex G/EZ series via browser driver" },
  { value: "a4office", label: "A4 Office Printer", hint: "Standard A4 sheet, 4-up grid" },
];

// ── Print helpers ──────────────────────────────────────────────────────────────

function getPageCSS(size: LabelSize): string {
  if (size === "50x30")  return "@page { size: 50mm 30mm; margin: 2mm; }";
  if (size === "70x40")  return "@page { size: 70mm 40mm; margin: 3mm; }";
  if (size === "100x50") return "@page { size: 100mm 50mm; margin: 3mm; }";
  return "@page { size: A4; margin: 10mm; }";
}

function buildLabelHTML(cfg: PrintConfig & { index: number; isLast: boolean }): string {
  const { b64, aiString, gtin, lotNo, expiry, productionDate, productName, sku, netWeight, labelSize, index, copies, isLast } = cfg;
  const isA4 = labelSize === "a4";
  const breakAttr = !isLast ? 'style="page-break-after:always"' : "";
  const maxImgH = labelSize === "50x30" ? "14mm" : labelSize === "70x40" ? "20mm" : "28mm";

  const metaLines = [
    productName && `<div class="ml"><b>Product:</b> ${productName}</div>`,
    sku         && `<div class="ml"><b>SKU:</b> ${sku}</div>`,
                   `<div class="ml"><b>GTIN:</b> <span class="mn">${gtin}</span></div>`,
                   `<div class="ml"><b>Lot:</b> ${lotNo}</div>`,
    expiry         && `<div class="ml"><b>Expiry:</b> ${expiry}</div>`,
    productionDate && `<div class="ml"><b>Prod:</b> ${productionDate}</div>`,
    netWeight      && `<div class="ml"><b>Net Wt:</b> ${netWeight}</div>`,
  ].filter(Boolean).join("");

  const badge = copies > 1 ? `<div class="badge">${index + 1}/${copies}</div>` : "";

  const inner = `
    <img src="data:image/png;base64,${b64}" alt="barcode" style="max-width:100%;max-height:${maxImgH};display:block;margin:0 auto 1.5mm"/>
    <div class="ai">${aiString}</div>
    ${metaLines}${badge}`;

  if (isA4) return `<div class="cell" ${breakAttr}>${inner}</div>`;
  return `<div class="page" ${breakAttr}><div class="inner">${inner}</div></div>`;
}

function openPrintWindow(cfg: PrintConfig): void {
  const { labelSize, copies } = cfg;
  const isA4 = labelSize === "a4";
  const fs = labelSize === "50x30" ? 7 : labelSize === "70x40" ? 8 : 9;

  const labels = Array.from({ length: copies }, (_, i) =>
    buildLabelHTML({ ...cfg, index: i, isLast: i === copies - 1 })
  );
  const body = isA4 ? `<div class="grid">${labels.join("")}</div>` : labels.join("");

  const html = `<!DOCTYPE html><html><head><meta charset="utf-8"/>
<title>GS1 Label — ${cfg.gtin} / ${cfg.lotNo}</title>
<style>
${getPageCSS(labelSize)}
*{box-sizing:border-box}
body{margin:0;padding:0;font-family:monospace;font-size:${fs}px;background:#fff;color:#000}
.page{width:100%;height:100vh;display:flex;align-items:center;justify-content:center}
.inner{text-align:center}
.grid{display:grid;grid-template-columns:repeat(2,1fr);gap:6mm;padding:4mm}
.cell{border:.4mm solid #ccc;padding:3mm;text-align:center;break-inside:avoid}
.ai{font-size:${fs - 1}px;color:#333;margin-bottom:1.5mm;word-break:break-all}
.ml{font-size:${fs}px;text-align:left;line-height:1.4}
.mn{font-family:monospace}
.badge{margin-top:1.5mm;font-size:${fs - 1}px;color:#888;text-align:right}
@media print{body{-webkit-print-color-adjust:exact;print-color-adjust:exact}}
</style></head>
<body>${body}</body></html>`;

  const win = window.open("", "_blank", `width=${isA4 ? 820 : 500},height=${isA4 ? 640 : 400}`);
  if (!win) { alert("Popup blocked — allow popups for this site to print labels."); return; }
  win.document.write(html);
  win.document.close();
  setTimeout(() => { win.focus(); win.print(); }, 400);
}

// ── StatCard ───────────────────────────────────────────────────────────────────

function StatCard({ label, value, sub }: { label: string; value: number | string; sub?: string }) {
  return (
    <div className="bg-white border rounded-lg p-4">
      <p className="text-xs text-gray-500 uppercase tracking-wide">{label}</p>
      <p className="text-2xl font-bold text-gray-900 mt-1">{value}</p>
      {sub && <p className="text-xs text-gray-400 mt-0.5">{sub}</p>}
    </div>
  );
}

// ── PrintHistorySection ────────────────────────────────────────────────────────

function PrintHistorySection() {
  const { data, isLoading, isError } = useQuery({
    queryKey: ["gs1-print-jobs"],
    queryFn: () => gs1Api.listPrintJobs(),
  });

  if (isLoading) return <div className="p-4 text-gray-400 text-sm">Loading print history…</div>;
  if (isError || !data) return <div className="p-4 text-red-400 text-sm">Failed to load print history</div>;

  return (
    <div className="bg-white border rounded-lg overflow-hidden">
      <div className="px-4 py-3 border-b">
        <h2 className="text-sm font-medium text-gray-700">Print Job History</h2>
      </div>
      <table className="w-full text-sm">
        <thead className="bg-gray-50 text-xs text-gray-500 uppercase">
          <tr>
            <th className="px-4 py-2 text-left">Job No</th>
            <th className="px-4 py-2 text-left">Trigger</th>
            <th className="px-4 py-2 text-left">Status</th>
            <th className="px-4 py-2 text-left">Items</th>
            <th className="px-4 py-2 text-left">Printer</th>
            <th className="px-4 py-2 text-left">Printed At</th>
            <th className="px-4 py-2 text-left">Created</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-100">
          {data.length === 0 && (
            <tr>
              <td colSpan={7} className="px-4 py-6 text-center text-gray-400">No print jobs yet</td>
            </tr>
          )}
          {data.map((job: PrintJob) => (
            <tr key={job.id} className="hover:bg-gray-50">
              <td className="px-4 py-2 font-mono text-xs">{job.job_no}</td>
              <td className="px-4 py-2 text-gray-600 text-xs">{job.trigger}</td>
              <td className="px-4 py-2">
                <span className={`px-2 py-0.5 rounded text-xs font-medium ${statusColor[job.status] ?? ""}`}>
                  {job.status}
                </span>
              </td>
              <td className="px-4 py-2">{job.item_count}</td>
              <td className="px-4 py-2 text-gray-500 text-xs">{job.printer_name || "—"}</td>
              <td className="px-4 py-2 text-gray-500 text-xs">
                {job.printed_at ? new Date(job.printed_at).toLocaleString() : "—"}
              </td>
              <td className="px-4 py-2 text-gray-400 text-xs">
                {new Date(job.created_at).toLocaleDateString()}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

// ── Main page ──────────────────────────────────────────────────────────────────

export default function GS1DashboardPage() {
  const qc = useQueryClient();
  const { data, isLoading, isError } = useQuery({
    queryKey: ["gs1-dashboard"],
    queryFn: gs1Api.getDashboard,
  });

  // Barcode / product fields
  const [showForm, setShowForm]           = useState(false);
  const [gtin, setGtin]                   = useState("");
  const [lotNo, setLotNo]                 = useState("");
  const [expiry, setExpiry]               = useState("");
  const [productionDate, setProdDate]     = useState("");
  const [productName, setProductName]     = useState("");
  const [sku, setSku]                     = useState("");
  const [netWeight, setNetWeight]         = useState("");
  const [barcodeType, setBarcodeType]     = useState<BarcodeType>("GS1_128");
  // Print settings
  const [labelSize, setLabelSize]         = useState<LabelSize>("70x40");
  const [printerPreset, setPreset]        = useState<PrinterPreset>("browser");
  const [copies, setCopies]               = useState(1);
  // UI state
  const [formError, setFormError]         = useState("");
  const [generated, setGenerated]         = useState<BarcodeGenerateResponse | null>(null);

  // ── Mutations ────────────────────────────────────────────────────────────────

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
    mutationFn: () => {
      setFormError("");
      if (!gtin.trim()) { setFormError("GTIN is required."); throw new Error("validation"); }
      if (!lotNo.trim()) { setFormError("Lot Number is required."); throw new Error("validation"); }
      if (copies < 1 || copies > 100) { setFormError("Copies must be 1–100."); throw new Error("validation"); }
      return gs1Api.generateBarcode({
        gtin: gtin.trim(),
        lot_number: lotNo.trim(),
        expiry_date: expiry || undefined,
        production_date: productionDate || undefined,
        barcode_type: barcodeType,
        save_record: true,
      });
    },
    onSuccess: (r) => {
      setGenerated(r);
      qc.invalidateQueries({ queryKey: ["gs1-dashboard"] });
    },
    onError: (err: Error) => {
      if (err.message !== "validation") setFormError(err.message);
    },
  });

  // Row Print: fetch barcode image + create/complete job + open window
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
        openPrintWindow({
          b64: barcode.barcode_image_b64,
          aiString: barcode.gs1_ai_string,
          gtin: barcode.gtin,
          lotNo: barcode.lot_number ?? "",
          expiry: barcode.expiry_date ?? undefined,
          productionDate: barcode.production_date ?? undefined,
          labelSize,
          preset: printerPreset,
          copies: 1,
        });
      } else {
        alert("No barcode image — regenerate with save_record=true.");
      }
      qc.invalidateQueries({ queryKey: ["gs1-dashboard"] });
      qc.invalidateQueries({ queryKey: ["gs1-print-jobs"] });
    },
    onError: (err: Error) => alert(`Print failed: ${err.message}`),
  });

  // Form Print: create/complete job then open window with full product fields + copies
  const printGeneratedMut = useMutation({
    mutationFn: async () => {
      if (!generated?.record_id || !generated.barcode_image_b64)
        throw new Error("No saved barcode — regenerate first.");
      const job = await gs1Api.createPrintJob({
        trigger: "MANUAL",
        items: [{ lot_barcode_id: generated.record_id, copies }],
      });
      await gs1Api.completePrintJob(job.id);
      return generated;
    },
    onSuccess: (gen) => {
      if (!gen.barcode_image_b64) return;
      openPrintWindow({
        b64: gen.barcode_image_b64,
        aiString: gen.gs1_ai_string,
        gtin: gen.gtin,
        lotNo: gen.lot_number ?? "",
        expiry: gen.expiry_date ?? undefined,
        productionDate: gen.production_date ?? undefined,
        productName: productName || undefined,
        sku: sku || undefined,
        netWeight: netWeight || undefined,
        labelSize,
        preset: printerPreset,
        copies,
      });
      qc.invalidateQueries({ queryKey: ["gs1-dashboard"] });
      qc.invalidateQueries({ queryKey: ["gs1-print-jobs"] });
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

  const presetHint = PRINTER_PRESETS.find((p) => p.value === printerPreset)?.hint ?? "";
  const sizeLabelShort = LABEL_SIZES.find((s) => s.value === labelSize)?.label.split(" — ")[0] ?? labelSize;

  return (
    <div className="p-6 space-y-6">

      {/* ── Header ─────────────────────────────────────────────────────────── */}
      <div className="flex items-center justify-between flex-wrap gap-2">
        <div>
          <h1 className="text-xl font-semibold text-gray-900">GS1 Barcode &amp; Label Printing</h1>
          <p className="text-sm text-gray-500">
            Global product identification · SSCC pallet tracking · Label management
          </p>
        </div>
        <div className="flex gap-2 flex-wrap">
          <button
            onClick={() => { setShowForm((v) => !v); setGenerated(null); setFormError(""); }}
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

      {/* ── Generate Label Form ─────────────────────────────────────────────── */}
      {showForm && (
        <div className="bg-white border rounded-lg p-5 space-y-4">
          <h2 className="text-sm font-semibold text-gray-800">Generate Barcode Label</h2>

          {/* Row 1 — Barcode fields */}
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
              <label className="block text-xs text-gray-500 mb-1">Production Date</label>
              <input
                type="date"
                value={productionDate}
                onChange={(e) => setProdDate(e.target.value)}
                className="w-full border rounded px-2 py-1.5 text-sm"
              />
            </div>
          </div>

          {/* Row 2 — Product fields */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            <div>
              <label className="block text-xs text-gray-500 mb-1">Product Name</label>
              <input
                value={productName}
                onChange={(e) => setProductName(e.target.value)}
                placeholder="e.g. Shampoo 250ml"
                className="w-full border rounded px-2 py-1.5 text-sm"
              />
            </div>
            <div>
              <label className="block text-xs text-gray-500 mb-1">SKU</label>
              <input
                value={sku}
                onChange={(e) => setSku(e.target.value)}
                placeholder="e.g. SKU-001"
                className="w-full border rounded px-2 py-1.5 text-sm"
              />
            </div>
            <div>
              <label className="block text-xs text-gray-500 mb-1">Net Weight / Volume</label>
              <input
                value={netWeight}
                onChange={(e) => setNetWeight(e.target.value)}
                placeholder="e.g. 250g"
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

          {/* Row 3 — Print settings */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3 border-t pt-4">
            <div>
              <label className="block text-xs text-gray-500 mb-1">Label Template</label>
              <select
                value={labelSize}
                onChange={(e) => setLabelSize(e.target.value as LabelSize)}
                className="w-full border rounded px-2 py-1.5 text-sm"
              >
                {LABEL_SIZES.map((s) => (
                  <option key={s.value} value={s.value}>{s.label}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-xs text-gray-500 mb-1">Printer Preset</label>
              <select
                value={printerPreset}
                onChange={(e) => setPreset(e.target.value as PrinterPreset)}
                className="w-full border rounded px-2 py-1.5 text-sm"
              >
                {PRINTER_PRESETS.map((p) => (
                  <option key={p.value} value={p.value}>{p.label}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-xs text-gray-500 mb-1">Copies (1–100)</label>
              <input
                type="number"
                min={1}
                max={100}
                value={copies}
                onChange={(e) => setCopies(Math.max(1, Math.min(100, Number(e.target.value))))}
                className="w-full border rounded px-2 py-1.5 text-sm"
              />
            </div>
            <div className="flex items-end pb-1">
              <p className="text-xs text-gray-400">{presetHint}</p>
            </div>
          </div>

          {/* Generate button */}
          <div className="flex items-center gap-3 flex-wrap">
            <button
              onClick={() => generateMut.mutate()}
              disabled={!gtin || !lotNo || generateMut.isPending}
              className="px-4 py-1.5 text-sm bg-green-600 text-white rounded hover:bg-green-700 disabled:opacity-50"
            >
              {generateMut.isPending ? "Generating…" : "Generate Barcode"}
            </button>
            {formError && <span className="text-sm text-red-500">{formError}</span>}
          </div>

          {/* Generated preview */}
          {generated && (
            <div className="mt-2 border-t pt-4 flex items-start gap-6 flex-wrap">
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
              <div className="space-y-1 text-sm flex-1">
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
                {generated.production_date && (
                  <p><span className="text-gray-500">Production: </span>{generated.production_date}</p>
                )}
                {generated.record_id ? (
                  <div className="flex gap-2 mt-2 flex-wrap">
                    <button
                      onClick={() => printGeneratedMut.mutate()}
                      disabled={printGeneratedMut.isPending}
                      className="px-3 py-1 text-xs bg-gray-800 text-white rounded hover:bg-gray-700 disabled:opacity-50"
                    >
                      {printGeneratedMut.isPending
                        ? "Printing…"
                        : `Print ${copies} Label${copies > 1 ? "s" : ""} (${sizeLabelShort})`}
                    </button>
                    <button
                      onClick={() => {
                        if (!generated.barcode_image_b64) { alert("No barcode image available."); return; }
                        openPrintWindow({
                          b64: generated.barcode_image_b64,
                          aiString: generated.gs1_ai_string,
                          gtin: generated.gtin,
                          lotNo: generated.lot_number ?? "",
                          expiry: generated.expiry_date ?? undefined,
                          productionDate: generated.production_date ?? undefined,
                          productName: productName || undefined,
                          sku: sku || undefined,
                          netWeight: netWeight || undefined,
                          labelSize,
                          preset: printerPreset,
                          copies,
                        });
                      }}
                      className="px-3 py-1 text-xs bg-indigo-600 text-white rounded hover:bg-indigo-700"
                    >
                      Preview / Export PDF
                    </button>
                  </div>
                ) : (
                  <p className="text-xs text-amber-600 mt-1">
                    Barcode not saved — re-generate with save_record=true to enable printing.
                  </p>
                )}
              </div>
            </div>
          )}
        </div>
      )}

      {/* ── KPI Grid ────────────────────────────────────────────────────────── */}
      <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-5 gap-4">
        <StatCard label="Products Configured"  value={data.total_products_configured} />
        <StatCard label="Total GTINs"          value={data.total_gtins} />
        <StatCard label="Barcodes Generated"   value={data.total_barcodes_generated} />
        <StatCard label="Labels Printed"       value={data.total_labels_printed} />
        <StatCard label="SSCC Pallets"         value={data.total_sscc_pallets} sub={`${data.active_sscc_pallets} active`} />
        <StatCard label="Print Jobs"           value={data.total_print_jobs} sub={`${data.pending_print_jobs} pending`} />
        <StatCard label="Label Templates"      value={data.total_label_templates} />
        <StatCard label="AI Alerts Pending"    value={data.ai_recommendations_pending} />
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

      {/* ── Print Job History ─────────────────────────────────────────────────── */}
      <PrintHistorySection />

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
