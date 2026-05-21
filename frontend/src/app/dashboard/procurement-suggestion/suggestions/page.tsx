"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useSearchParams } from "next/navigation";
import {
  psApi, PSLineOut, PSUrgencyLevel, PSSuggestionStatus,
  urgencyBadge, statusBadge, fmt,
} from "@/lib/procurement_suggestion";

const URGENCY_OPTIONS: Array<PSUrgencyLevel | ""> = ["", "CRITICAL", "HIGH", "MEDIUM", "LOW"];
const STATUS_OPTIONS: Array<PSSuggestionStatus | ""> = ["", "DRAFT", "REVIEWED", "APPROVED", "CONVERTED", "REJECTED"];

function SupplierPanel({ line, onClose }: { line: PSLineOut; onClose: () => void }) {
  const { data: compare } = useQuery({
    queryKey: ["ps-compare", line.material_id],
    queryFn: () => psApi.compareSuppliers(line.material_id),
    enabled: !!line.material_id,
  });

  return (
    <div className="fixed inset-0 bg-black/40 flex items-end justify-center z-50 p-4">
      <div className="bg-white rounded-xl w-full max-w-3xl max-h-[80vh] overflow-y-auto shadow-xl">
        <div className="sticky top-0 bg-white px-5 py-4 border-b border-gray-100 flex items-center justify-between">
          <div>
            <h2 className="font-semibold text-gray-900">Supplier Comparison</h2>
            <p className="text-sm text-gray-500">{compare?.material_name} ({compare?.material_code})</p>
          </div>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-700 text-xl">×</button>
        </div>
        <div className="p-5">
          {!compare ? (
            <p className="text-gray-400">Loading suppliers…</p>
          ) : compare.suppliers.length === 0 ? (
            <p className="text-gray-400">No supplier price mappings found for this material.</p>
          ) : (
            <table className="w-full text-sm">
              <thead className="bg-gray-50 text-xs text-gray-500 uppercase">
                <tr>
                  <th className="text-left px-3 py-2">Supplier</th>
                  <th className="text-left px-3 py-2">Priority</th>
                  <th className="text-right px-3 py-2">Unit Price</th>
                  <th className="text-right px-3 py-2">MOQ</th>
                  <th className="text-right px-3 py-2">Lead Days</th>
                  <th className="text-right px-3 py-2">Score</th>
                  <th className="text-left px-3 py-2">Status</th>
                </tr>
              </thead>
              <tbody>
                {compare.suppliers.map((s) => (
                  <tr
                    key={s.supplier_id}
                    className={`border-t border-gray-100 ${compare.recommended_supplier_id === s.supplier_id ? "bg-green-50" : ""}`}
                  >
                    <td className="px-3 py-2 font-medium">
                      {s.supplier_name}
                      {compare.recommended_supplier_id === s.supplier_id && (
                        <span className="ml-2 text-xs bg-green-100 text-green-700 px-1.5 py-0.5 rounded">Recommended</span>
                      )}
                    </td>
                    <td className="px-3 py-2 text-gray-500">{s.priority}</td>
                    <td className="px-3 py-2 text-right">{s.currency} {fmt(s.unit_price)}</td>
                    <td className="px-3 py-2 text-right">{fmt(s.moq, 0)}</td>
                    <td className="px-3 py-2 text-right">{s.total_lead_days}d</td>
                    <td className="px-3 py-2 text-right font-mono">{fmt(s.score, 1)}</td>
                    <td className="px-3 py-2 text-xs">{s.is_preferred ? "⭐ Preferred" : ""}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>
    </div>
  );
}

export default function SuggestionListPage() {
  const params = useSearchParams();
  const runId  = params.get("run_id") ?? "";
  const qc     = useQueryClient();

  const [urgency, setUrgency] = useState<PSUrgencyLevel | "">("");
  const [statusFilter, setStatusFilter] = useState<PSSuggestionStatus | "">("");
  const [riskOnly, setRiskOnly] = useState(false);
  const [selected, setSelected] = useState<PSLineOut | null>(null);

  const { data: lines, isLoading } = useQuery({
    queryKey: ["ps-suggestions", runId, urgency, statusFilter, riskOnly],
    queryFn: () => psApi.listSuggestions(runId, {
      urgency:   urgency || undefined,
      status:    statusFilter || undefined,
      risk_only: riskOnly || undefined,
    }),
    enabled: !!runId,
  });

  const approve = useMutation({
    mutationFn: (id: string) => psApi.approveSuggestion(id),
    onSuccess:  () => qc.invalidateQueries({ queryKey: ["ps-suggestions"] }),
  });

  const reject = useMutation({
    mutationFn: ({ id, reason }: { id: string; reason: string }) => psApi.rejectSuggestion(id, reason),
    onSuccess:  () => qc.invalidateQueries({ queryKey: ["ps-suggestions"] }),
  });

  if (!runId) return (
    <div className="p-8 text-gray-400">
      No run selected. <a href="/dashboard/procurement-suggestion" className="text-blue-600 underline">Go to dashboard</a>
    </div>
  );

  return (
    <div className="p-6 space-y-4">
      {selected && <SupplierPanel line={selected} onClose={() => setSelected(null)} />}

      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold text-gray-900">Procurement Suggestions</h1>
          <p className="text-sm text-gray-500 font-mono">Run: {runId}</p>
        </div>
        <a href="/dashboard/procurement-suggestion" className="text-sm text-blue-600 hover:underline">← Dashboard</a>
      </div>

      {/* Filters */}
      <div className="flex flex-wrap gap-3 items-center">
        <select
          value={urgency}
          onChange={(e) => setUrgency(e.target.value as PSUrgencyLevel | "")}
          className="border rounded px-2 py-1.5 text-sm"
        >
          {URGENCY_OPTIONS.map((o) => <option key={o} value={o}>{o || "All Urgencies"}</option>)}
        </select>
        <select
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value as PSSuggestionStatus | "")}
          className="border rounded px-2 py-1.5 text-sm"
        >
          {STATUS_OPTIONS.map((o) => <option key={o} value={o}>{o || "All Statuses"}</option>)}
        </select>
        <label className="flex items-center gap-2 text-sm text-gray-600 cursor-pointer">
          <input type="checkbox" checked={riskOnly} onChange={(e) => setRiskOnly(e.target.checked)} />
          Risk Flagged Only
        </label>
        <a
          href={`/dashboard/procurement-suggestion/groups?run_id=${runId}`}
          className="ml-auto px-3 py-1.5 text-sm border rounded hover:bg-gray-50"
        >
          View Grouped Orders →
        </a>
      </div>

      {/* Table */}
      <div className="bg-white border border-gray-200 rounded-lg overflow-x-auto">
        <table className="w-full text-sm">
          <thead className="bg-gray-50 text-xs text-gray-500 uppercase">
            <tr>
              <th className="text-left px-3 py-2">Material</th>
              <th className="text-left px-3 py-2">UOM</th>
              <th className="text-right px-3 py-2">Required</th>
              <th className="text-right px-3 py-2">Available</th>
              <th className="text-right px-3 py-2">Shortage</th>
              <th className="text-right px-3 py-2">Order Qty</th>
              <th className="text-left px-3 py-2">Supplier</th>
              <th className="text-right px-3 py-2">Est. Cost</th>
              <th className="text-left px-3 py-2">Order Date</th>
              <th className="text-left px-3 py-2">Req. Date</th>
              <th className="text-left px-3 py-2">Urgency</th>
              <th className="text-left px-3 py-2">Status</th>
              <th className="text-left px-3 py-2">Risk</th>
              <th className="text-left px-3 py-2">Actions</th>
            </tr>
          </thead>
          <tbody>
            {isLoading && (
              <tr><td colSpan={14} className="px-4 py-8 text-center text-gray-400">Loading…</td></tr>
            )}
            {!isLoading && !lines?.length && (
              <tr><td colSpan={14} className="px-4 py-8 text-center text-gray-400">No suggestions found.</td></tr>
            )}
            {(lines ?? []).map((l) => (
              <tr key={l.id} className="border-t border-gray-100 hover:bg-gray-50">
                <td className="px-3 py-2">
                  <p className="font-medium text-gray-800">{l.material_name}</p>
                  <p className="text-xs text-gray-400 font-mono">{l.material_code}</p>
                </td>
                <td className="px-3 py-2 text-gray-500">{l.uom}</td>
                <td className="px-3 py-2 text-right">{fmt(l.required_qty)}</td>
                <td className="px-3 py-2 text-right">{fmt(l.available_qty)}</td>
                <td className={`px-3 py-2 text-right font-medium ${l.shortage_qty > 0 ? "text-red-600" : "text-green-600"}`}>
                  {fmt(l.shortage_qty)}
                </td>
                <td className="px-3 py-2 text-right font-semibold">{fmt(l.adjusted_order_qty)}</td>
                <td className="px-3 py-2">
                  <button
                    onClick={() => setSelected(l)}
                    className="text-blue-600 hover:underline text-xs"
                  >
                    {l.supplier_name ?? "No supplier"}
                  </button>
                </td>
                <td className="px-3 py-2 text-right text-gray-700">
                  {l.estimated_total_cost ? `${l.currency} ${fmt(l.estimated_total_cost, 0)}` : "—"}
                </td>
                <td className="px-3 py-2 text-xs text-gray-600">{l.suggested_order_date ?? "—"}</td>
                <td className="px-3 py-2 text-xs text-gray-600">{l.required_date ?? "—"}</td>
                <td className="px-3 py-2">
                  <span className={`px-2 py-0.5 rounded-full text-xs border ${urgencyBadge(l.urgency_level)}`}>
                    {l.urgency_level}
                  </span>
                </td>
                <td className="px-3 py-2">
                  <span className={`px-2 py-0.5 rounded-full text-xs ${statusBadge(l.status)}`}>{l.status}</span>
                </td>
                <td className="px-3 py-2">
                  {l.risk_flag && (
                    <span title={l.risk_notes ?? ""} className="text-orange-500 cursor-help">⚠ Risk</span>
                  )}
                </td>
                <td className="px-3 py-2">
                  <div className="flex gap-1">
                    {l.status === "DRAFT" && (
                      <button
                        onClick={() => approve.mutate(l.id)}
                        className="px-2 py-0.5 text-xs bg-green-600 text-white rounded hover:bg-green-700"
                      >
                        Approve
                      </button>
                    )}
                    {l.status !== "REJECTED" && l.status !== "CONVERTED" && (
                      <button
                        onClick={() => {
                          const r = prompt("Rejection reason (optional):");
                          reject.mutate({ id: l.id, reason: r ?? "" });
                        }}
                        className="px-2 py-0.5 text-xs border border-red-300 text-red-600 rounded hover:bg-red-50"
                      >
                        Reject
                      </button>
                    )}
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
