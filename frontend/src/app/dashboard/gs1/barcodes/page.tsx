"use client";

import { useState } from "react";
import { useQuery, useMutation } from "@tanstack/react-query";
import { gs1Api, type BarcodeGenerateResponse, type BarcodeType } from "@/lib/gs1";

const BARCODE_TYPES: BarcodeType[] = ["EAN13", "GS1_128", "QR_CODE", "CODE128"];

export default function BarcodesPage() {
  const [form, setForm] = useState({
    gtin: "",
    lot_number: "",
    expiry_date: "",
    production_date: "",
    serial_number: "",
    barcode_type: "GS1_128" as BarcodeType,
    save_record: true,
  });
  const [result, setResult] = useState<BarcodeGenerateResponse | null>(null);

  const generate = useMutation({
    mutationFn: gs1Api.generateBarcode,
    onSuccess: (r) => setResult(r),
  });

  const { data: barcodes } = useQuery({ queryKey: ["gs1-barcodes"], queryFn: () => gs1Api.listBarcodes({ limit: 100 }) });

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    generate.mutate({
      gtin: form.gtin || undefined,
      lot_number: form.lot_number || undefined,
      expiry_date: form.expiry_date || undefined,
      production_date: form.production_date || undefined,
      serial_number: form.serial_number || undefined,
      barcode_type: form.barcode_type,
      save_record: form.save_record,
    });
  }

  return (
    <div className="p-6 space-y-6">
      <h1 className="text-xl font-semibold text-gray-900">Barcode Generator</h1>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Form */}
        <div className="bg-white border rounded-lg p-4">
          <h2 className="text-sm font-medium text-gray-700 mb-3">Generate GS1 Barcode</h2>
          <form onSubmit={handleSubmit} className="space-y-3">
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="text-xs text-gray-500">GTIN (14 digits) *</label>
                <input
                  required
                  maxLength={14}
                  className="mt-0.5 w-full border rounded px-2 py-1.5 text-sm font-mono"
                  value={form.gtin}
                  onChange={(e) => setForm((p) => ({ ...p, gtin: e.target.value }))}
                  placeholder="00000000000000"
                />
              </div>
              <div>
                <label className="text-xs text-gray-500">Barcode Type</label>
                <select className="mt-0.5 w-full border rounded px-2 py-1.5 text-sm" value={form.barcode_type} onChange={(e) => setForm((p) => ({ ...p, barcode_type: e.target.value as BarcodeType }))}>
                  {BARCODE_TYPES.map((t) => <option key={t}>{t}</option>)}
                </select>
              </div>
              <div>
                <label className="text-xs text-gray-500">Lot / Batch Number</label>
                <input className="mt-0.5 w-full border rounded px-2 py-1.5 text-sm" value={form.lot_number} onChange={(e) => setForm((p) => ({ ...p, lot_number: e.target.value }))} placeholder="LOT-2024-001" />
              </div>
              <div>
                <label className="text-xs text-gray-500">Serial Number (AI 21)</label>
                <input className="mt-0.5 w-full border rounded px-2 py-1.5 text-sm" value={form.serial_number} onChange={(e) => setForm((p) => ({ ...p, serial_number: e.target.value }))} placeholder="SN-00001" />
              </div>
              <div>
                <label className="text-xs text-gray-500">Expiry Date (AI 17)</label>
                <input type="date" className="mt-0.5 w-full border rounded px-2 py-1.5 text-sm" value={form.expiry_date} onChange={(e) => setForm((p) => ({ ...p, expiry_date: e.target.value }))} />
              </div>
              <div>
                <label className="text-xs text-gray-500">Production Date (AI 11)</label>
                <input type="date" className="mt-0.5 w-full border rounded px-2 py-1.5 text-sm" value={form.production_date} onChange={(e) => setForm((p) => ({ ...p, production_date: e.target.value }))} />
              </div>
            </div>
            <label className="flex items-center gap-1.5 text-sm">
              <input type="checkbox" checked={form.save_record} onChange={(e) => setForm((p) => ({ ...p, save_record: e.target.checked }))} />
              Save to database
            </label>
            <button type="submit" disabled={generate.isPending} className="w-full py-2 bg-blue-600 text-white text-sm rounded hover:bg-blue-700 disabled:opacity-50">
              {generate.isPending ? "Generating…" : "Generate Barcode"}
            </button>
            {generate.isError && <p className="text-red-600 text-xs">{(generate.error as Error).message}</p>}
          </form>
        </div>

        {/* Result */}
        <div className="bg-white border rounded-lg p-4 space-y-3">
          <h2 className="text-sm font-medium text-gray-700">Preview</h2>
          {!result && <div className="text-gray-400 text-sm py-10 text-center">Generate a barcode to see preview</div>}
          {result && (
            <div className="space-y-3">
              <div className="flex items-center gap-2">
                <span className={`text-xs font-medium px-2 py-0.5 rounded ${result.check_digit_valid ? "bg-green-100 text-green-700" : "bg-red-100 text-red-700"}`}>
                  GTIN Check Digit: {result.check_digit_valid ? "VALID" : "INVALID"}
                </span>
              </div>

              <div className="bg-gray-50 rounded p-3 space-y-1.5">
                <p className="text-xs text-gray-500 font-medium uppercase">GS1 Human-Readable</p>
                <p className="font-mono text-sm text-gray-900 break-all">{result.gs1_ai_string}</p>
              </div>

              <div className="bg-gray-50 rounded p-3 space-y-1.5">
                <p className="text-xs text-gray-500 font-medium uppercase">QR Payload</p>
                <p className="font-mono text-xs text-gray-600 break-all">{result.qr_payload}</p>
              </div>

              {result.barcode_image_b64 && (
                <div className="border rounded p-2 bg-white">
                  <p className="text-xs text-gray-500 mb-1">Barcode Image</p>
                  {/* eslint-disable-next-line @next/next/no-img-element -- Backend-generated barcode data URI must render exactly as returned. */}
                  <img
                    src={`data:image/svg+xml;base64,${result.barcode_image_b64}`}
                    alt="barcode"
                    className="max-w-full"
                    onError={(e) => {
                      const img = e.currentTarget;
                      img.src = `data:image/png;base64,${result.barcode_image_b64}`;
                    }}
                  />
                </div>
              )}

              {result.qr_image_b64 && (
                <div className="border rounded p-2 bg-white inline-block">
                  <p className="text-xs text-gray-500 mb-1">QR Code</p>
                  {/* eslint-disable-next-line @next/next/no-img-element -- Backend-generated QR data URI must render exactly as returned. */}
                  <img src={`data:image/png;base64,${result.qr_image_b64}`} alt="qr code" className="w-32 h-32" />
                </div>
              )}

              <div className="grid grid-cols-2 gap-2 text-xs">
                <div><span className="text-gray-500">GTIN: </span><span className="font-mono font-medium">{result.gtin}</span></div>
                <div><span className="text-gray-500">Lot: </span><span>{result.lot_number || "—"}</span></div>
                <div><span className="text-gray-500">Expiry: </span><span>{result.expiry_date || "—"}</span></div>
                <div><span className="text-gray-500">Prod Date: </span><span>{result.production_date || "—"}</span></div>
              </div>

              <button
                onClick={() => {
                  const blob = new Blob([result.gs1_ai_string], { type: "text/plain" });
                  const url = URL.createObjectURL(blob);
                  const a = document.createElement("a");
                  a.href = url;
                  a.download = `barcode_${result.gtin}.txt`;
                  a.click();
                }}
                className="text-xs text-blue-600 hover:underline"
              >
                Download GS1 String
              </button>
            </div>
          )}
        </div>
      </div>

      {/* Barcode History */}
      <div className="bg-white border rounded-lg overflow-hidden">
        <div className="px-4 py-3 border-b"><h2 className="text-sm font-medium text-gray-700">Barcode History</h2></div>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 text-xs text-gray-500 uppercase">
              <tr>
                {["GTIN", "Lot", "Expiry", "Type", "GS1 AI String", "Qty", "Level", "Printed"].map((h) => (
                  <th key={h} className="px-3 py-2 text-left whitespace-nowrap">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {!barcodes?.length && <tr><td colSpan={8} className="px-4 py-6 text-center text-gray-400">No barcodes yet</td></tr>}
              {barcodes?.map((b) => (
                <tr key={b.id} className="hover:bg-gray-50">
                  <td className="px-3 py-2 font-mono text-xs">{b.gtin}</td>
                  <td className="px-3 py-2">{b.lot_number}</td>
                  <td className="px-3 py-2 text-gray-500">{b.expiry_date || "—"}</td>
                  <td className="px-3 py-2"><span className="px-1.5 py-0.5 bg-blue-50 text-blue-700 rounded text-xs">{b.barcode_type}</span></td>
                  <td className="px-3 py-2 font-mono text-xs text-gray-500 max-w-xs truncate">{b.gs1_ai_string}</td>
                  <td className="px-3 py-2">{b.quantity || "—"}</td>
                  <td className="px-3 py-2">{b.packaging_level || "—"}</td>
                  <td className="px-3 py-2">{b.is_printed ? <span className="text-green-600 text-xs">✓ Printed</span> : <span className="text-gray-400 text-xs">—</span>}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
