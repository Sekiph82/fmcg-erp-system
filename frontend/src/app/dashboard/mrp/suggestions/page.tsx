"use client";
import React, { useState } from "react";
import Link from "next/link";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { mrpApi, STATUS_COLOR, SUGGESTION_TYPE_COLOR, fmtQty, MRPSuggestion } from "@/lib/mrp";

const Badge = ({ s, colorMap }: { s: string; colorMap: Record<string, string> }) => (
  <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${colorMap[s] ?? "bg-gray-100 text-gray-600"}`}>{s}</span>
);

export default function SuggestionsPage() {
  const qc = useQueryClient();
  const [typeFilter, setTypeFilter] = useState("");
  const [statusFilter, setStatusFilter] = useState("DRAFT");
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [rejectTarget, setRejectTarget] = useState<string | null>(null);
  const [rejectReason, setRejectReason] = useState("");

  const { data: suggestions = [], isLoading } = useQuery({
    queryKey: ["mrp-suggestions", typeFilter, statusFilter],
    queryFn: () => mrpApi.listSuggestions({
      suggestion_type: typeFilter || undefined,
      status: statusFilter || undefined,
      limit: 200,
    }),
  });

  const approveMutation = useMutation({
    mutationFn: (id: string) => mrpApi.approveSuggestion(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["mrp-suggestions"] }),
  });

  const rejectMutation = useMutation({
    mutationFn: ({ id, reason }: { id: string; reason: string }) =>
      mrpApi.rejectSuggestion(id, reason),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["mrp-suggestions"] });
      setRejectTarget(null);
      setRejectReason("");
    },
  });

  const convertMutation = useMutation({
    mutationFn: (id: string) => mrpApi.convertSuggestion(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["mrp-suggestions"] }),
  });

  const approveSelected = async () => {
    for (const id of Array.from(selected)) {
      await approveMutation.mutateAsync(id);
    }
    setSelected(new Set());
  };

  const sel = "rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 px-3 py-2 text-sm";

  const prodCount  = suggestions.filter(s => s.suggestion_type === "PRODUCTION").length;
  const procCount  = suggestions.filter(s => s.suggestion_type === "PROCUREMENT").length;
  const totalEst   = suggestions.reduce((a, s) => a + (Number(s.estimated_cost) || 0), 0);

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900 p-6 space-y-6">
      <div className="flex items-center gap-3 mb-1">
        <Link href="/dashboard/mrp" className="text-sm text-gray-500 hover:text-indigo-600">← MRP Dashboard</Link>
      </div>
      <h1 className="text-2xl font-bold text-gray-900 dark:text-white" style={{ borderLeft: "4px solid #6366f1", paddingLeft: 12 }}>
        MRP Suggestions
      </h1>

      {/* Summary cards */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-4">
          <p className="text-xs text-gray-500">Production Orders</p>
          <p className="text-2xl font-bold text-orange-600 mt-1">{prodCount}</p>
        </div>
        <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-4">
          <p className="text-xs text-gray-500">Purchase Requests</p>
          <p className="text-2xl font-bold text-teal-600 mt-1">{procCount}</p>
        </div>
        <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-4">
          <p className="text-xs text-gray-500">Selected</p>
          <p className="text-2xl font-bold text-indigo-600 mt-1">{selected.size}</p>
        </div>
        <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-4">
          <p className="text-xs text-gray-500">Est. Procurement Cost</p>
          <p className="text-xl font-bold text-gray-900 dark:text-white mt-1">
            {totalEst > 0 ? `$${totalEst.toLocaleString(undefined, { maximumFractionDigits: 0 })}` : "—"}
          </p>
        </div>
      </div>

      {/* Filters + bulk actions */}
      <div className="flex flex-wrap gap-3 items-center bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-xl p-3">
        <select className={sel} value={typeFilter} onChange={e => setTypeFilter(e.target.value)}>
          <option value="">All Types</option>
          <option value="PRODUCTION">Production</option>
          <option value="PROCUREMENT">Procurement</option>
        </select>
        <select className={sel} value={statusFilter} onChange={e => setStatusFilter(e.target.value)}>
          <option value="">All Statuses</option>
          <option value="DRAFT">Draft</option>
          <option value="APPROVED">Approved</option>
          <option value="REJECTED">Rejected</option>
          <option value="CONVERTED">Converted</option>
        </select>
        {selected.size > 0 && (
          <>
            <button onClick={approveSelected}
              className="px-4 py-2 text-sm bg-green-600 text-white rounded-lg hover:bg-green-700">
              ✓ Approve {selected.size}
            </button>
            <button onClick={() => setSelected(new Set())}
              className="px-3 py-2 text-sm bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200">
              Clear
            </button>
          </>
        )}
      </div>

      {/* Reject modal */}
      {rejectTarget && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
          <div className="bg-white dark:bg-gray-800 rounded-xl p-6 w-96 shadow-xl">
            <h3 className="text-sm font-semibold mb-3">Reject Suggestion</h3>
            <textarea
              className="w-full rounded-lg border border-gray-300 dark:border-gray-600 px-3 py-2 text-sm bg-white dark:bg-gray-700"
              rows={3} placeholder="Reason for rejection…"
              value={rejectReason} onChange={e => setRejectReason(e.target.value)}
            />
            <div className="flex gap-3 mt-4">
              <button onClick={() => rejectMutation.mutate({ id: rejectTarget!, reason: rejectReason })}
                disabled={!rejectReason || rejectMutation.isPending}
                className="px-4 py-2 text-sm bg-red-600 text-white rounded-lg hover:bg-red-700 disabled:opacity-60">
                Reject
              </button>
              <button onClick={() => { setRejectTarget(null); setRejectReason(""); }}
                className="px-4 py-2 text-sm bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200">
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Table */}
      <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 dark:bg-gray-700 text-xs uppercase text-gray-500">
              <tr>
                <th className="px-3 py-3 w-8">
                  <input type="checkbox" className="rounded"
                    checked={selected.size === suggestions.filter(s => s.status === "DRAFT").length && suggestions.length > 0}
                    onChange={e => {
                      if (e.target.checked) setSelected(new Set(suggestions.filter(s => s.status === "DRAFT").map(s => s.id)));
                      else setSelected(new Set());
                    }} />
                </th>
                {["Type", "SKU / Code", "Item", "Driver Product", "Qty", "UOM", "Net Req.", "MOQ",
                  "Required By", "Planned Start", "Supplier", "Est. Cost", "Status", "Actions"].map(h => (
                  <th key={h} className="px-3 py-3 text-left font-medium whitespace-nowrap">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100 dark:divide-gray-700">
              {suggestions.map((s, i) => {
                const isProd = s.suggestion_type === "PRODUCTION";
                return (
                  <tr key={i} className="hover:bg-gray-50 dark:hover:bg-gray-750">
                    <td className="px-3 py-2">
                      {s.status === "DRAFT" && (
                        <input type="checkbox" className="rounded"
                          checked={selected.has(s.id)}
                          onChange={e => {
                            const ns = new Set(selected);
                            e.target.checked ? ns.add(s.id) : ns.delete(s.id);
                            setSelected(ns);
                          }} />
                      )}
                    </td>
                    <td className="px-3 py-2"><Badge s={s.suggestion_type} colorMap={SUGGESTION_TYPE_COLOR} /></td>
                    <td className="px-3 py-2 font-mono text-xs">
                      {isProd ? (s.product_sku ?? "—") : (s.material_code ?? "—")}
                    </td>
                    <td className="px-3 py-2 text-xs font-medium">
                      {isProd ? (s.product_name ?? "—") : (s.material_name ?? "—")}
                    </td>
                    <td className="px-3 py-2 text-xs text-gray-400">
                      {!isProd && s.driver_product_id ? s.driver_product_id.slice(0, 8) + "…" : "—"}
                    </td>
                    <td className="px-3 py-2 text-right font-bold text-orange-700">{fmtQty(s.suggested_qty)}</td>
                    <td className="px-3 py-2 text-gray-500">{s.uom ?? "—"}</td>
                    <td className="px-3 py-2 text-right text-xs">{fmtQty(s.net_requirement_qty)}</td>
                    <td className="px-3 py-2 text-right text-xs">{s.moq ? fmtQty(s.moq) : "—"}</td>
                    <td className="px-3 py-2 font-mono text-xs">{s.required_date}</td>
                    <td className="px-3 py-2 font-mono text-xs">{s.planned_start_date ?? "—"}</td>
                    <td className="px-3 py-2 text-xs">{s.preferred_supplier_name ?? "—"}</td>
                    <td className="px-3 py-2 text-right text-xs">
                      {s.estimated_cost ? `$${Number(s.estimated_cost).toFixed(0)}` : "—"}
                    </td>
                    <td className="px-3 py-2"><Badge s={s.status} colorMap={STATUS_COLOR} /></td>
                    <td className="px-3 py-2">
                      <div className="flex gap-1">
                        {s.status === "DRAFT" && (
                          <>
                            <button onClick={() => approveMutation.mutate(s.id)}
                              className="px-2 py-1 text-xs bg-green-100 text-green-700 rounded hover:bg-green-200">✓</button>
                            <button onClick={() => setRejectTarget(s.id)}
                              className="px-2 py-1 text-xs bg-red-100 text-red-700 rounded hover:bg-red-200">✗</button>
                          </>
                        )}
                        {s.status === "APPROVED" && (
                          <button onClick={() => convertMutation.mutate(s.id)}
                            disabled={convertMutation.isPending}
                            className="px-2 py-1 text-xs bg-indigo-100 text-indigo-700 rounded hover:bg-indigo-200">
                            Convert
                          </button>
                        )}
                        {s.status === "CONVERTED" && (
                          <span className="text-xs text-green-600">✓ Done</span>
                        )}
                      </div>
                    </td>
                  </tr>
                );
              })}
              {suggestions.length === 0 && !isLoading && (
                <tr><td colSpan={15} className="px-4 py-8 text-center text-gray-400">No suggestions found</td></tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
