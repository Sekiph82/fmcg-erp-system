"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { gs1Api } from "@/lib/gs1";

type ReportTab = "print-history" | "sscc-tracking" | "packaging-hierarchy" | "barcode-usage";

export default function GS1ReportsPage() {
  const [tab, setTab] = useState<ReportTab>("print-history");

  const { data: printHistory } = useQuery({ queryKey: ["gs1-print-history"], queryFn: gs1Api.getPrintHistory, enabled: tab === "print-history" });
  const { data: ssccTracking } = useQuery({ queryKey: ["gs1-sscc-tracking"], queryFn: gs1Api.getSSCCTracking, enabled: tab === "sscc-tracking" });
  const { data: hierarchy } = useQuery({ queryKey: ["gs1-hierarchy"], queryFn: gs1Api.getPackagingHierarchy, enabled: tab === "packaging-hierarchy" });
  const { data: barcodeUsage } = useQuery({ queryKey: ["gs1-barcode-usage"], queryFn: gs1Api.getBarcodeUsage, enabled: tab === "barcode-usage" });

  const tabs: { id: ReportTab; label: string }[] = [
    { id: "print-history", label: "Label Print History" },
    { id: "sscc-tracking", label: "SSCC Tracking" },
    { id: "packaging-hierarchy", label: "Packaging Hierarchy" },
    { id: "barcode-usage", label: "Barcode Usage" },
  ];

  function downloadCSV(data: Record<string, unknown>[], filename: string) {
    if (!data?.length) return;
    const headers = Object.keys(data[0]);
    const rows = data.map((r) => headers.map((h) => JSON.stringify(r[h] ?? "")).join(","));
    const csv = [headers.join(","), ...rows].join("\n");
    const blob = new Blob([csv], { type: "text/csv" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    a.click();
  }

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold text-gray-900">GS1 Reports</h1>
      </div>

      {/* Tabs */}
      <div className="border-b flex gap-1">
        {tabs.map((t) => (
          <button
            key={t.id}
            onClick={() => setTab(t.id)}
            className={`px-4 py-2 text-sm font-medium border-b-2 -mb-px transition-colors ${tab === t.id ? "border-blue-600 text-blue-600" : "border-transparent text-gray-500 hover:text-gray-700"}`}
          >
            {t.label}
          </button>
        ))}
      </div>

      {/* Print History */}
      {tab === "print-history" && (
        <div className="bg-white border rounded-lg overflow-hidden">
          <div className="px-4 py-3 border-b flex items-center justify-between">
            <h2 className="text-sm font-medium text-gray-700">Label Print History</h2>
            <button onClick={() => downloadCSV((printHistory || []) as Record<string, unknown>[], "print_history.csv")} className="text-xs text-blue-600 hover:underline">Export CSV</button>
          </div>
          <table className="w-full text-sm">
            <thead className="bg-gray-50 text-xs text-gray-500 uppercase">
              <tr>{["Job No.", "Trigger", "Status", "Printed By", "Printed At", "Qty", "Template", "Created"].map((h) => <th key={h} className="px-3 py-2 text-left">{h}</th>)}</tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {!(printHistory as unknown[])?.length && <tr><td colSpan={8} className="px-4 py-6 text-center text-gray-400">No print history</td></tr>}
              {(printHistory as Record<string, string>[] || []).map((r, i) => (
                <tr key={i} className="hover:bg-gray-50">
                  <td className="px-3 py-2 font-mono text-xs">{r.job_no}</td>
                  <td className="px-3 py-2 text-xs">{r.trigger}</td>
                  <td className="px-3 py-2 text-xs">{r.status}</td>
                  <td className="px-3 py-2">{r.printed_by || "—"}</td>
                  <td className="px-3 py-2 text-gray-500 text-xs">{r.printed_at ? new Date(r.printed_at).toLocaleString() : "—"}</td>
                  <td className="px-3 py-2">{r.quantity}</td>
                  <td className="px-3 py-2 text-gray-500">{r.template_name || "—"}</td>
                  <td className="px-3 py-2 text-gray-400 text-xs">{new Date(r.created_at).toLocaleDateString()}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* SSCC Tracking */}
      {tab === "sscc-tracking" && (
        <div className="bg-white border rounded-lg overflow-hidden">
          <div className="px-4 py-3 border-b flex items-center justify-between">
            <h2 className="text-sm font-medium text-gray-700">SSCC Tracking Report</h2>
            <button onClick={() => downloadCSV((ssccTracking || []) as Record<string, unknown>[], "sscc_tracking.csv")} className="text-xs text-blue-600 hover:underline">Export CSV</button>
          </div>
          <table className="w-full text-sm">
            <thead className="bg-gray-50 text-xs text-gray-500 uppercase">
              <tr>{["SSCC Code", "Pallet ID", "Status", "Location", "Shipment Ref", "Lot Count", "Created"].map((h) => <th key={h} className="px-3 py-2 text-left">{h}</th>)}</tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {!(ssccTracking as unknown[])?.length && <tr><td colSpan={7} className="px-4 py-6 text-center text-gray-400">No SSCC data</td></tr>}
              {(ssccTracking as Record<string, string>[] || []).map((r, i) => (
                <tr key={i} className="hover:bg-gray-50">
                  <td className="px-3 py-2 font-mono text-xs">{r.sscc_code}</td>
                  <td className="px-3 py-2">{r.pallet_id || "—"}</td>
                  <td className="px-3 py-2"><span className="text-xs px-1.5 py-0.5 bg-gray-100 rounded">{r.status}</span></td>
                  <td className="px-3 py-2 text-gray-500">{r.warehouse_location || "—"}</td>
                  <td className="px-3 py-2 text-gray-500 text-xs">{r.shipment_reference || "—"}</td>
                  <td className="px-3 py-2">{r.lot_count}</td>
                  <td className="px-3 py-2 text-gray-400 text-xs">{new Date(r.created_at).toLocaleDateString()}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Packaging Hierarchy */}
      {tab === "packaging-hierarchy" && (
        <div className="bg-white border rounded-lg overflow-hidden">
          <div className="px-4 py-3 border-b flex items-center justify-between">
            <h2 className="text-sm font-medium text-gray-700">Packaging Hierarchy Report</h2>
            <button onClick={() => downloadCSV((hierarchy || []) as Record<string, unknown>[], "packaging_hierarchy.csv")} className="text-xs text-blue-600 hover:underline">Export CSV</button>
          </div>
          <table className="w-full text-sm">
            <thead className="bg-gray-50 text-xs text-gray-500 uppercase">
              <tr>{["Product", "GTIN", "Level", "Units/Inner Pack", "Inner Packs/Carton", "Cartons/Pallet", "Total Units/Pallet"].map((h) => <th key={h} className="px-3 py-2 text-left">{h}</th>)}</tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {!(hierarchy as unknown[])?.length && <tr><td colSpan={7} className="px-4 py-6 text-center text-gray-400">No packaging hierarchy data</td></tr>}
              {(hierarchy as Record<string, string>[] || []).map((r, i) => (
                <tr key={i} className="hover:bg-gray-50">
                  <td className="px-3 py-2 font-medium">{r.product_name}</td>
                  <td className="px-3 py-2 font-mono text-xs">{r.gtin || "—"}</td>
                  <td className="px-3 py-2 text-xs">{r.packaging_level}</td>
                  <td className="px-3 py-2 text-center">{r.units_per_inner_pack || "—"}</td>
                  <td className="px-3 py-2 text-center">{r.inner_packs_per_carton || "—"}</td>
                  <td className="px-3 py-2 text-center">{r.cartons_per_pallet || "—"}</td>
                  <td className="px-3 py-2 text-center font-medium">{r.total_units_per_pallet || "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Barcode Usage */}
      {tab === "barcode-usage" && (
        <div className="bg-white border rounded-lg overflow-hidden">
          <div className="px-4 py-3 border-b flex items-center justify-between">
            <h2 className="text-sm font-medium text-gray-700">Barcode Usage Report</h2>
            <button onClick={() => downloadCSV((barcodeUsage || []) as Record<string, unknown>[], "barcode_usage.csv")} className="text-xs text-blue-600 hover:underline">Export CSV</button>
          </div>
          <table className="w-full text-sm">
            <thead className="bg-gray-50 text-xs text-gray-500 uppercase">
              <tr>{["Product", "GTIN", "Barcode Type", "Total Generated", "Total Printed", "Print Rate"].map((h) => <th key={h} className="px-3 py-2 text-left">{h}</th>)}</tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {!(barcodeUsage as unknown[])?.length && <tr><td colSpan={6} className="px-4 py-6 text-center text-gray-400">No barcode usage data</td></tr>}
              {(barcodeUsage as Record<string, string>[] || []).map((r, i) => {
                const rate = r.total_generated ? Math.round((Number(r.total_printed || 0) / Number(r.total_generated)) * 100) : 0;
                return (
                  <tr key={i} className="hover:bg-gray-50">
                    <td className="px-3 py-2 font-medium">{r.product_name}</td>
                    <td className="px-3 py-2 font-mono text-xs">{r.gtin || "—"}</td>
                    <td className="px-3 py-2"><span className="text-xs px-1.5 py-0.5 bg-blue-50 text-blue-700 rounded">{r.barcode_type}</span></td>
                    <td className="px-3 py-2 text-center">{r.total_generated}</td>
                    <td className="px-3 py-2 text-center">{r.total_printed || 0}</td>
                    <td className="px-3 py-2 text-center">
                      <div className="flex items-center gap-2">
                        <div className="flex-1 bg-gray-200 rounded-full h-1.5">
                          <div className="bg-blue-500 h-1.5 rounded-full" style={{ width: `${rate}%` }} />
                        </div>
                        <span className="text-xs text-gray-500 w-8">{rate}%</span>
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
