"use client";

import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { gs1Api, type GS1DecodeResponse } from "@/lib/gs1";

const AI_LABELS: Record<string, string> = {
  "00": "SSCC",
  "01": "GTIN",
  "02": "GTIN of contained trade items",
  "10": "Batch/Lot Number",
  "11": "Production Date (YYMMDD)",
  "13": "Packaging Date (YYMMDD)",
  "15": "Best Before Date (YYMMDD)",
  "17": "Expiry Date (YYMMDD)",
  "20": "Product variant",
  "21": "Serial Number",
  "22": "Consumer product variant",
  "30": "Variable count",
  "37": "Count of trade items",
};

export default function ScanDebugPage() {
  const [input, setInput] = useState("");
  const [result, setResult] = useState<GS1DecodeResponse | null>(null);

  const decode = useMutation({
    mutationFn: gs1Api.decodeGS1,
    onSuccess: (r) => setResult(r),
  });

  const EXAMPLES = [
    { label: "GTIN + Lot + Expiry", value: "(01)07628700000023(10)LOT-2024-001(17)251231" },
    { label: "GTIN only (EAN-13)", value: "(01)05012345678900" },
    { label: "Full GS1-128", value: "(01)00012345678905(10)BATCH-A(17)251230(11)240101" },
    { label: "SSCC Pallet", value: "(00)012345678000000000" },
    { label: "Serial + GTIN", value: "(01)00012345678905(21)SN-00001" },
  ];

  return (
    <div className="p-6 space-y-6">
      <div>
        <h1 className="text-xl font-semibold text-gray-900">Scan Simulator / Debug</h1>
        <p className="text-sm text-gray-500">Decode and validate GS1 barcode strings — GTIN, lot, expiry, SSCC</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Input Panel */}
        <div className="space-y-4">
          <div className="bg-white border rounded-lg p-4">
            <h2 className="text-sm font-medium text-gray-700 mb-3">Enter GS1 String</h2>
            <textarea
              rows={4}
              className="w-full border rounded px-3 py-2 text-sm font-mono"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="(01)07628700000023(10)LOT-001(17)251231"
            />
            <div className="flex gap-2 mt-2">
              <button
                onClick={() => decode.mutate(input)}
                disabled={!input.trim() || decode.isPending}
                className="px-4 py-1.5 bg-blue-600 text-white text-sm rounded hover:bg-blue-700 disabled:opacity-50"
              >
                {decode.isPending ? "Decoding…" : "Decode & Validate"}
              </button>
              <button onClick={() => { setInput(""); setResult(null); }} className="px-3 py-1.5 text-sm border rounded">Clear</button>
            </div>
          </div>

          {/* Examples */}
          <div className="bg-white border rounded-lg p-4">
            <h2 className="text-sm font-medium text-gray-700 mb-3">Example GS1 Strings</h2>
            <div className="space-y-2">
              {EXAMPLES.map((ex) => (
                <button
                  key={ex.label}
                  onClick={() => setInput(ex.value)}
                  className="w-full text-left border rounded p-2 hover:bg-gray-50"
                >
                  <p className="text-xs font-medium text-gray-700">{ex.label}</p>
                  <p className="text-xs font-mono text-gray-500 mt-0.5">{ex.value}</p>
                </button>
              ))}
            </div>
          </div>

          {/* GS1 AI Reference */}
          <div className="bg-gray-50 border rounded-lg p-3">
            <h2 className="text-xs font-medium text-gray-600 mb-2">GS1 Application Identifiers (AI) Reference</h2>
            <div className="space-y-1">
              {Object.entries(AI_LABELS).map(([ai, label]) => (
                <div key={ai} className="flex items-start gap-2 text-xs">
                  <span className="font-mono text-blue-700 font-medium w-6 shrink-0">({ai})</span>
                  <span className="text-gray-600">{label}</span>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Result Panel */}
        <div className="bg-white border rounded-lg p-4 space-y-4">
          <h2 className="text-sm font-medium text-gray-700">Decode Result</h2>

          {!result && (
            <div className="text-center text-gray-400 py-12">
              <p className="text-2xl mb-2">📷</p>
              <p className="text-sm">Enter a GS1 string and click Decode</p>
            </div>
          )}

          {result && (
            <>
              {/* Validation Status */}
              <div className={`rounded-lg p-3 ${result.is_valid ? "bg-green-50 border border-green-200" : "bg-red-50 border border-red-200"}`}>
                <div className="flex items-center gap-2">
                  <span className="text-lg">{result.is_valid ? "✅" : "❌"}</span>
                  <span className={`text-sm font-medium ${result.is_valid ? "text-green-700" : "text-red-700"}`}>
                    {result.is_valid ? "Valid GS1 String" : "Validation Failed"}
                  </span>
                </div>
                {result.validation_errors.length > 0 && (
                  <ul className="mt-2 space-y-0.5">
                    {result.validation_errors.map((e, i) => (
                      <li key={i} className="text-xs text-red-600">• {e}</li>
                    ))}
                  </ul>
                )}
              </div>

              {/* Parsed Segments */}
              <div>
                <h3 className="text-xs font-medium text-gray-600 mb-2">Parsed AI Segments</h3>
                <div className="space-y-1.5">
                  {Object.entries(result.segments).map(([ai, val]) => (
                    <div key={ai} className="flex items-start gap-3 text-sm bg-gray-50 rounded px-3 py-1.5">
                      <span className="font-mono text-blue-700 font-medium">({ai})</span>
                      <span className="text-gray-500 text-xs flex-1">{AI_LABELS[ai] || `AI ${ai}`}</span>
                      <span className="font-mono font-medium">{val}</span>
                    </div>
                  ))}
                  {Object.keys(result.segments).length === 0 && (
                    <p className="text-xs text-gray-400">No segments parsed</p>
                  )}
                </div>
              </div>

              {/* Matched Records */}
              {result.matched_product && (
                <div className="bg-green-50 rounded-lg p-3">
                  <h3 className="text-xs font-medium text-green-700 mb-1.5">✓ Product Found</h3>
                  <div className="text-xs space-y-0.5">
                    <div><span className="text-green-600">Name: </span>{result.matched_product.product_name}</div>
                    <div><span className="text-green-600">GTIN: </span><span className="font-mono">{result.matched_product.gtin}</span></div>
                    <div><span className="text-green-600">ID: </span><span className="font-mono text-xs">{result.matched_product.product_id}</span></div>
                  </div>
                </div>
              )}

              {result.matched_lot && (
                <div className="bg-blue-50 rounded-lg p-3">
                  <h3 className="text-xs font-medium text-blue-700 mb-1.5">✓ Lot Found</h3>
                  <div className="text-xs space-y-0.5">
                    <div><span className="text-blue-600">Lot: </span>{result.matched_lot.lot_number}</div>
                    <div><span className="text-blue-600">Expiry: </span>{result.matched_lot.expiry_date || "N/A"}</div>
                    <div><span className="text-blue-600">ID: </span><span className="font-mono">{result.matched_lot.lot_id}</span></div>
                  </div>
                </div>
              )}

              {/* Summary Fields */}
              <div className="grid grid-cols-2 gap-2 text-xs">
                {[
                  ["GTIN", result.gtin],
                  ["Lot Number", result.lot_number],
                  ["Expiry Date", result.expiry_date],
                  ["Production Date", result.production_date],
                  ["Serial Number", result.serial_number],
                  ["SSCC", result.sscc],
                ].map(([label, val]) => (
                  <div key={label} className="bg-gray-50 rounded px-2 py-1.5">
                    <span className="text-gray-400">{label}: </span>
                    <span className="font-medium font-mono">{val || "—"}</span>
                  </div>
                ))}
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
