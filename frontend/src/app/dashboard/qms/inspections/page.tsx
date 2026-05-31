"use client";
import { useEffect, useState } from "react";
import { apiClient } from "@/lib/api";
import { STATUS_BG } from "@/lib/qms";

interface Inspection {
  id: string;
  inspection_no: string;
  qc_type: string;
  qc_sub_type: string | null;
  status: string;
  inspection_date: string;
  lot_number: string | null;
  batch_no: string | null;
  supplier_name: string | null;
  material_name: string | null;
  product_name: string | null;
  inspector_name: string | null;
  test_count: number;
  pass_count: number;
  fail_count: number;
  critical_fail: boolean;
  decision: string | null;
}

const QC_TYPE_COLORS: Record<string, string> = {
  INCOMING: "bg-sky-100 text-sky-800",
  IN_PROCESS: "bg-purple-100 text-purple-800",
  FINISHED_GOODS: "bg-emerald-100 text-emerald-800",
  RETEST: "bg-amber-100 text-amber-800",
};

export default function QCInspectionsPage() {
  const [inspections, setInspections] = useState<Inspection[]>([]);
  const [loading, setLoading] = useState(true);
  const [typeFilter, setTypeFilter] = useState("");
  const [statusFilter, setStatusFilter] = useState("");

  useEffect(() => {
    const params: Record<string, string> = {};
    if (typeFilter) params.qc_type = typeFilter;
    if (statusFilter) params.status = statusFilter;
    apiClient
      .get<Inspection[]>("/api/v1/quality/inspections/", { params })
      .then(r => setInspections(r.data))
      .catch(console.error)
      .finally(() => setLoading(false));
  }, [typeFilter, statusFilter]);

  return (
    <div className="p-6 space-y-5">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">QC Inspections</h1>
          <p className="text-sm text-gray-500 mt-0.5">Incoming · In-Process · Final · Retest inspections</p>
        </div>
        <a href="/dashboard/quality" className="text-sm text-indigo-600 hover:underline">
          ← Back to Quality
        </a>
      </div>

      <div className="flex gap-3">
        <select
          className="border rounded-lg px-3 py-2 text-sm text-gray-700 bg-white"
          value={typeFilter}
          onChange={e => setTypeFilter(e.target.value)}
        >
          <option value="">All Types</option>
          <option value="INCOMING">Incoming (IQC)</option>
          <option value="IN_PROCESS">In-Process (IPQC)</option>
          <option value="FINISHED_GOODS">Final (FQC)</option>
          <option value="RETEST">Retest</option>
        </select>
        <select
          className="border rounded-lg px-3 py-2 text-sm text-gray-700 bg-white"
          value={statusFilter}
          onChange={e => setStatusFilter(e.target.value)}
        >
          <option value="">All Statuses</option>
          <option value="PENDING">Pending</option>
          <option value="IN_PROGRESS">In Progress</option>
          <option value="PASSED">Passed</option>
          <option value="FAILED">Failed</option>
          <option value="CONDITIONAL_RELEASE">Conditional</option>
          <option value="CANCELLED">Cancelled</option>
        </select>
      </div>

      <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
        {loading ? (
          <p className="px-5 py-8 text-gray-400 text-sm">Loading…</p>
        ) : inspections.length === 0 ? (
          <p className="px-5 py-8 text-gray-400 text-sm">No inspections found</p>
        ) : (
          <table className="w-full text-sm">
            <thead className="bg-gray-50 text-xs uppercase text-gray-500">
              <tr>
                {["Inspection #", "Type", "Item", "Lot / Batch", "Date", "Inspector", "Results", "Status", "Decision"].map(h => (
                  <th key={h} className="px-4 py-3 text-left font-medium">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {inspections.map(i => (
                <tr key={i.id} className="hover:bg-gray-50">
                  <td className="px-4 py-3 font-medium text-indigo-700">{i.inspection_no}</td>
                  <td className="px-4 py-3">
                    <span className={`px-2 py-0.5 rounded text-xs ${QC_TYPE_COLORS[i.qc_type] || "bg-gray-100"}`}>
                      {i.qc_type.replace("_", " ")}
                    </span>
                    {i.qc_sub_type && (
                      <span className="ml-1 text-xs text-gray-400">{i.qc_sub_type}</span>
                    )}
                  </td>
                  <td className="px-4 py-3 text-gray-700">
                    {i.product_name || i.material_name || "—"}
                    {i.supplier_name && <span className="text-xs text-gray-400 block">{i.supplier_name}</span>}
                  </td>
                  <td className="px-4 py-3 text-gray-500">
                    {i.lot_number || i.batch_no || "—"}
                  </td>
                  <td className="px-4 py-3 text-gray-500">{new Date(i.inspection_date).toLocaleDateString()}</td>
                  <td className="px-4 py-3 text-gray-500">{i.inspector_name || "—"}</td>
                  <td className="px-4 py-3">
                    {i.test_count > 0 ? (
                      <span className={`text-xs ${i.critical_fail ? "text-red-700 font-semibold" : "text-gray-600"}`}>
                        {i.pass_count}/{i.test_count} pass
                        {i.critical_fail && " ⚠ CRIT"}
                      </span>
                    ) : <span className="text-gray-400 text-xs">—</span>}
                  </td>
                  <td className="px-4 py-3">
                    <span className={`px-2 py-0.5 rounded text-xs ${STATUS_BG[i.status] || "bg-gray-100"}`}>
                      {i.status.replace("_", " ")}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-gray-500 text-xs">
                    {i.decision?.replace("_", " ") || "—"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
