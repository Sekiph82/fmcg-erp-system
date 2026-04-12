"use client";

import { useState, useRef } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  integrationsApi,
  BarcodeGenerateRequest,
  BarcodeLabel,
  BarcodeScanResult,
} from "@/lib/integrations";

type EntityType = "PRODUCT" | "LOT" | "LOCATION" | "MATERIAL";
const ENTITY_TYPES: EntityType[] = ["PRODUCT", "LOT", "LOCATION", "MATERIAL"];

export default function BarcodePage() {
  const qc = useQueryClient();
  const [activeTab, setActiveTab] = useState<"scan" | "generate" | "labels">("scan");

  // Scan state
  const [scanInput, setScanInput] = useState("");
  const [scanResult, setScanResult] = useState<BarcodeScanResult | null | "notfound">(null);
  const scanRef = useRef<HTMLInputElement>(null);

  // Generate state
  const [genForm, setGenForm] = useState<BarcodeGenerateRequest>({
    entity_type: "PRODUCT",
    entity_id: "",
    barcode_format: "CODE128",
    label_template: "standard",
  });
  const [genResult, setGenResult] = useState<{ svg: string; label: BarcodeLabel } | null>(null);
  const [genError, setGenError] = useState("");

  // Labels filter
  const [entityTypeFilter, setEntityTypeFilter] = useState<EntityType | "">("");

  const { data: labels = [], isLoading: labelsLoading } = useQuery({
    queryKey: ["barcode-labels", entityTypeFilter],
    queryFn: () => integrationsApi.listBarcodeLabels(entityTypeFilter || undefined),
    enabled: activeTab === "labels",
  });

  const scanMut = useMutation({
    mutationFn: (val: string) => integrationsApi.scanBarcode(val),
    onSuccess: (data) => setScanResult(data ?? "notfound"),
  });

  const generateMut = useMutation({
    mutationFn: integrationsApi.generateBarcode,
    onSuccess: (data) => {
      setGenResult(data);
      setGenError("");
      qc.invalidateQueries({ queryKey: ["barcode-labels"] });
    },
    onError: (e: Error) => setGenError(e.message),
  });

  const printMut = useMutation({
    mutationFn: (labelId: string) => integrationsApi.printBarcode(labelId),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["barcode-labels"] }),
  });

  function handleScan() {
    if (!scanInput.trim()) return;
    setScanResult(null);
    scanMut.mutate(scanInput.trim());
  }

  return (
    <div className="max-w-4xl mx-auto px-4 py-6 space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900">📷 Barcode System</h1>
        <p className="text-gray-500 text-sm mt-0.5">Scan, generate, and manage barcode labels</p>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 bg-gray-100 rounded-xl p-1 w-fit">
        {(["scan", "generate", "labels"] as const).map((tab) => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors capitalize ${
              activeTab === tab
                ? "bg-white text-gray-900 shadow-sm"
                : "text-gray-600 hover:text-gray-900"
            }`}
          >
            {tab === "scan" ? "📷 Scan" : tab === "generate" ? "✨ Generate" : "📋 Labels"}
          </button>
        ))}
      </div>

      {/* Scan tab */}
      {activeTab === "scan" && (
        <div className="space-y-4">
          <div className="bg-white border border-gray-200 rounded-xl p-6 space-y-4">
            <h2 className="font-semibold text-gray-900">Scan Barcode</h2>
            <p className="text-sm text-gray-500">
              Scan a barcode using a scanner device or type the value manually.
            </p>

            <div className="flex gap-2">
              <input
                ref={scanRef}
                type="text"
                value={scanInput}
                onChange={(e) => setScanInput(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && handleScan()}
                placeholder="Scan or type barcode value (e.g. PRD1A2B3C4D5E6F)"
                className="flex-1 border border-gray-300 rounded-lg px-3 py-2 text-sm font-mono focus:outline-none focus:ring-2 focus:ring-indigo-400"
                autoFocus
              />
              <button
                onClick={handleScan}
                disabled={scanMut.isPending || !scanInput.trim()}
                className="px-4 py-2 bg-indigo-600 text-white rounded-lg text-sm font-medium hover:bg-indigo-700 disabled:opacity-50"
              >
                {scanMut.isPending ? "..." : "Lookup"}
              </button>
            </div>

            {scanResult === "notfound" && (
              <div className="bg-red-50 border border-red-200 rounded-lg p-4">
                <p className="text-sm text-red-700 font-medium">Barcode not found</p>
                <p className="text-xs text-red-500 mt-1">
                  No entity is registered with barcode value &quot;{scanInput}&quot;
                </p>
              </div>
            )}

            {scanResult && scanResult !== "notfound" && (
              <div className="bg-emerald-50 border border-emerald-200 rounded-xl p-4 space-y-3">
                <div className="flex items-center gap-2">
                  <span className="text-2xl">✅</span>
                  <div>
                    <p className="font-semibold text-emerald-800">{scanResult.entity_name ?? scanResult.entity_id}</p>
                    <p className="text-xs text-emerald-600">{scanResult.entity_type} · {scanResult.barcode_value}</p>
                  </div>
                </div>
                {Object.keys(scanResult.details).length > 0 && (
                  <div className="grid grid-cols-2 gap-2 text-xs">
                    {Object.entries(scanResult.details).map(([k, v]) => (
                      <div key={k} className="bg-white rounded-lg p-2">
                        <p className="text-gray-500 capitalize">{k.replace(/_/g, " ")}</p>
                        <p className="font-medium text-gray-900">{String(v ?? "—")}</p>
                      </div>
                    ))}
                  </div>
                )}
                <button
                  onClick={() => { setScanInput(""); setScanResult(null); scanRef.current?.focus(); }}
                  className="text-xs text-emerald-700 underline"
                >
                  Scan another
                </button>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Generate tab */}
      {activeTab === "generate" && (
        <div className="space-y-4">
          <div className="bg-white border border-gray-200 rounded-xl p-6 space-y-4">
            <h2 className="font-semibold text-gray-900">Generate Barcode Label</h2>

            {genError && (
              <p className="text-sm text-red-600 bg-red-50 rounded-lg px-3 py-2">{genError}</p>
            )}

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label className="block text-xs font-medium text-gray-700 mb-1">Entity Type</label>
                <select
                  value={genForm.entity_type}
                  onChange={(e) => setGenForm((f) => ({ ...f, entity_type: e.target.value as EntityType }))}
                  className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400"
                >
                  {ENTITY_TYPES.map((t) => (
                    <option key={t} value={t}>{t}</option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-xs font-medium text-gray-700 mb-1">Entity ID (UUID)</label>
                <input
                  type="text"
                  value={genForm.entity_id}
                  onChange={(e) => setGenForm((f) => ({ ...f, entity_id: e.target.value }))}
                  placeholder="e.g. 123e4567-e89b-12d3-..."
                  className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm font-mono focus:outline-none focus:ring-2 focus:ring-indigo-400"
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-gray-700 mb-1">Format</label>
                <select
                  value={genForm.barcode_format}
                  onChange={(e) => setGenForm((f) => ({ ...f, barcode_format: e.target.value as "CODE128" }))}
                  className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400"
                >
                  {["CODE128", "QR", "EAN13", "CODE39"].map((f) => (
                    <option key={f} value={f}>{f}</option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-xs font-medium text-gray-700 mb-1">Label Template</label>
                <select
                  value={genForm.label_template}
                  onChange={(e) => setGenForm((f) => ({ ...f, label_template: e.target.value }))}
                  className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400"
                >
                  {["standard", "compact", "shipping", "warehouse"].map((t) => (
                    <option key={t} value={t}>{t}</option>
                  ))}
                </select>
              </div>
            </div>

            <button
              onClick={() => generateMut.mutate(genForm)}
              disabled={generateMut.isPending || !genForm.entity_id}
              className="px-6 py-2 bg-indigo-600 text-white rounded-lg text-sm font-medium hover:bg-indigo-700 disabled:opacity-50"
            >
              {generateMut.isPending ? "Generating..." : "Generate Barcode"}
            </button>
          </div>

          {genResult && (
            <div className="bg-white border border-gray-200 rounded-xl p-6 space-y-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="font-semibold text-gray-900">{genResult.label.entity_name ?? genResult.label.entity_id}</p>
                  <p className="text-xs text-gray-500 font-mono">{genResult.label.barcode_value}</p>
                </div>
                <button
                  onClick={() => printMut.mutate(genResult.label.id)}
                  disabled={printMut.isPending}
                  className="px-3 py-1.5 text-sm bg-gray-900 text-white rounded-lg hover:bg-gray-800"
                >
                  🖨️ Print
                </button>
              </div>

              {/* SVG barcode display */}
              <div
                className="bg-white border border-gray-200 rounded-lg p-4 overflow-x-auto"
                dangerouslySetInnerHTML={{ __html: genResult.svg }}
              />

              <div className="grid grid-cols-3 gap-3 text-xs">
                {[
                  ["Type", genResult.label.entity_type],
                  ["Format", genResult.label.barcode_format],
                  ["Template", genResult.label.label_template],
                  ["Print count", genResult.label.print_count],
                  ["Created", new Date(genResult.label.created_at).toLocaleDateString()],
                  ["Last printed", genResult.label.last_printed_at
                    ? new Date(genResult.label.last_printed_at).toLocaleDateString()
                    : "Never"],
                ].map(([k, v]) => (
                  <div key={k} className="bg-gray-50 rounded-lg p-2">
                    <p className="text-gray-500">{k}</p>
                    <p className="font-medium text-gray-900">{String(v)}</p>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Labels tab */}
      {activeTab === "labels" && (
        <div className="space-y-4">
          <div className="flex gap-2 flex-wrap">
            {(["", ...ENTITY_TYPES] as const).map((t) => (
              <button
                key={t}
                onClick={() => setEntityTypeFilter(t as EntityType | "")}
                className={`px-3 py-1 rounded-full text-xs font-medium border transition-colors ${
                  entityTypeFilter === t
                    ? "bg-indigo-600 text-white border-indigo-600"
                    : "bg-white text-gray-600 border-gray-200 hover:border-indigo-300"
                }`}
              >
                {t || "All Types"}
              </button>
            ))}
          </div>

          <div className="bg-white border border-gray-200 rounded-xl overflow-hidden">
            {labelsLoading ? (
              <div className="p-8 text-center text-gray-400 text-sm">Loading...</div>
            ) : labels.length === 0 ? (
              <div className="p-8 text-center text-gray-400 text-sm">No barcode labels found</div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead className="bg-gray-50 border-b border-gray-200">
                    <tr>
                      {["Barcode Value", "Entity", "Type", "Format", "Prints", "Last Printed", ""].map((h) => (
                        <th key={h} className="px-4 py-3 text-left text-xs font-semibold text-gray-500">{h}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-100">
                    {labels.map((label: BarcodeLabel) => (
                      <tr key={label.id} className="hover:bg-gray-50">
                        <td className="px-4 py-3 font-mono text-xs text-indigo-700">{label.barcode_value}</td>
                        <td className="px-4 py-3 text-xs text-gray-900">{label.entity_name ?? label.entity_id.slice(0, 8)}</td>
                        <td className="px-4 py-3 text-xs text-gray-600">{label.entity_type}</td>
                        <td className="px-4 py-3 text-xs text-gray-600">{label.barcode_format}</td>
                        <td className="px-4 py-3 text-xs text-gray-600">{label.print_count}</td>
                        <td className="px-4 py-3 text-xs text-gray-500">
                          {label.last_printed_at
                            ? new Date(label.last_printed_at).toLocaleDateString()
                            : "Never"}
                        </td>
                        <td className="px-4 py-3">
                          <button
                            onClick={() => printMut.mutate(label.id)}
                            disabled={printMut.isPending}
                            className="px-2 py-1 text-xs bg-gray-100 text-gray-700 rounded hover:bg-gray-200"
                          >
                            Print
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
