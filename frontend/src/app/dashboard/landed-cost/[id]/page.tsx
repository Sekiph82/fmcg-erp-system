"use client";
import { useParams, useRouter } from "next/navigation";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { useAuth } from "@/context/AuthContext";
import {
  lcApi, LC_STATUS_COLOR, COST_TYPE_LABEL, ALLOC_METHOD_LABEL,
  LandedCostOut, fmtCurrency,
} from "@/lib/landed_cost";

export default function LandedCostDetailPage() {
  const { id } = useParams<{ id: string }>();
  const qc = useQueryClient();
  const router = useRouter();
  const { hasPermission } = useAuth();
  const [actualInputs, setActualInputs] = useState<Record<string, { amount: string; reference: string }>>({});

  const { data: doc, isLoading, error } = useQuery<LandedCostOut>({
    queryKey: ["lc-doc", id],
    queryFn: () => lcApi.get(id),
    enabled: !!id,
  });

  const allocate = useMutation({
    mutationFn: () => lcApi.allocate(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["lc-doc", id] }),
  });

  const post = useMutation({
    mutationFn: () => lcApi.post(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["lc-doc", id] }),
  });

  const recordActual = useMutation({
    mutationFn: (input: { lineId: string; amount: number; reference: string }) =>
      lcApi.recordActual(id, input.lineId, { amount_fc: input.amount, source_reference: input.reference }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["lc-doc", id] }),
  });

  const cancel = useMutation({
    mutationFn: () => lcApi.cancel(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["lc-doc", id] }),
  });

  const runAI = useMutation({
    mutationFn: () => lcApi.runAIForDoc(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["lc-doc", id] }),
  });

  if (isLoading) return <div className="p-8 text-gray-500">Loading…</div>;
  if (error || !doc) return <div className="p-8 text-red-500">Document not found.</div>;

  const costLines      = doc.cost_lines      ?? [];
  const grnLinks       = doc.grn_links       ?? [];
  const allocationLines = doc.allocation_lines ?? [];

  const canAllocate = ["DRAFT", "VALIDATED"].includes(doc.status);
  const canPost     = doc.status === "VALIDATED";
  const canCancel   = ["DRAFT", "VALIDATED"].includes(doc.status);
  const canRecordActual = hasPermission("finance.post")
    && ["DRAFT", "VALIDATED", "POSTED"].includes(doc.status);

  return (
    <div className="p-6 space-y-6 max-w-5xl">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">{doc.lc_no}</h1>
          <p className="text-sm text-gray-500">
            {doc.vendor_name ?? "No vendor"} · {doc.bill_no ?? "No bill no"} · {doc.bill_date ?? ""}
          </p>
        </div>
        <div className="flex items-center gap-2">
          <span className={`px-3 py-1 rounded-full text-xs font-semibold ${LC_STATUS_COLOR[doc.status]}`}>
            {doc.status}
          </span>
          {canAllocate && (
            <button onClick={() => allocate.mutate()}
              disabled={allocate.isPending}
              className="px-3 py-1.5 text-xs bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50">
              {allocate.isPending ? "…" : "Run Allocation"}
            </button>
          )}
          {canPost && (
            <button onClick={() => post.mutate()}
              disabled={post.isPending}
              className="px-3 py-1.5 text-xs bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:opacity-50">
              {post.isPending ? "…" : "Post"}
            </button>
          )}
          <button onClick={() => runAI.mutate()}
            disabled={runAI.isPending}
            className="px-3 py-1.5 text-xs border rounded-lg hover:bg-gray-50 text-purple-600 disabled:opacity-50">
            {runAI.isPending ? "…" : "Run AI"}
          </button>
          {canCancel && (
            <button onClick={() => cancel.mutate()}
              disabled={cancel.isPending}
              className="px-3 py-1.5 text-xs text-red-600 border border-red-300 rounded-lg hover:bg-red-50 disabled:opacity-50">
              Cancel
            </button>
          )}
        </div>
      </div>

      {/* Summary */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {[
          { label: "Currency / FX", value: `${doc.currency_code} @ ${doc.exchange_rate} · ${doc.exchange_rate_source ?? "legacy source unknown"} · ${doc.exchange_rate_date ?? "legacy date unknown"}` },
          { label: "Method",       value: ALLOC_METHOD_LABEL[doc.allocation_method] ?? doc.allocation_method },
          { label: "Total (FC)",   value: fmtCurrency(doc.total_lc_amount_fc, doc.currency_code) },
          { label: "Total (Base)", value: fmtCurrency(doc.total_lc_amount_base) },
        ].map((c) => (
          <div key={c.label} className="bg-white border rounded-xl p-4">
            <p className="text-xs text-gray-500">{c.label}</p>
            <p className="text-sm font-semibold text-gray-900 mt-1">{c.value}</p>
          </div>
        ))}
      </div>

      {/* Cost Lines */}
      <div className="bg-white border rounded-xl overflow-hidden">
        <div className="px-5 py-3 border-b bg-gray-50">
          <h2 className="text-sm font-semibold text-gray-700">Cost Components ({costLines.length})</h2>
          <p className="mt-1 text-xs text-gray-500">Header totals are translated into the document currency; each line keeps its own currency and saved Finance rate snapshot.</p>
        </div>
        <table className="w-full text-sm">
          <thead className="bg-gray-50 text-xs text-gray-500 uppercase">
            <tr>
              {["Type", "Description", "Vendor", "Estimated (FC)", "Actual (FC)", "Variance (FC)", "Variance (Base)", "Actual Source", "Ccy", "Rate", "Booked Base", "In Valuation", "Record Actual"].map((h) => (
                <th key={h} className="px-4 py-2 text-left font-medium">{h}</th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {costLines.map((cl) => (
              <tr key={cl.id} className="hover:bg-gray-50">
                <td className="px-4 py-2 text-xs font-medium">{COST_TYPE_LABEL[cl.cost_type as keyof typeof COST_TYPE_LABEL] ?? cl.cost_type}</td>
                <td className="px-4 py-2 text-gray-600 text-xs">{cl.description ?? "—"}</td>
                <td className="px-4 py-2 text-gray-600 text-xs">{cl.vendor_name ?? "—"}</td>
                <td className="px-4 py-2 font-medium">{fmtCurrency(cl.estimated_amount_fc ?? cl.amount_fc, cl.currency_code)}</td>
                <td className="px-4 py-2 font-medium">{cl.actual_record ? fmtCurrency(cl.actual_record.amount_fc, cl.currency_code) : "—"}</td>
                <td className={`px-4 py-2 font-medium ${Number(cl.variance_fc ?? 0) > 0 ? "text-red-600" : Number(cl.variance_fc ?? 0) < 0 ? "text-green-700" : "text-gray-500"}`}>
                  {cl.variance_fc == null ? "—" : fmtCurrency(cl.variance_fc, cl.currency_code)}
                </td>
                <td className="px-4 py-2 font-medium">{cl.variance_base == null ? "—" : fmtCurrency(cl.variance_base)}</td>
                <td className="px-4 py-2 text-gray-600 text-xs">{cl.actual_record?.source_reference ?? "—"}</td>
                <td className="px-4 py-2 text-gray-500 text-xs">{cl.currency_code}</td>
                <td className="px-4 py-2 text-gray-500 text-xs">
                  <div>{Number(cl.exchange_rate ?? 1).toFixed(6)}</div>
                  <div>{cl.exchange_rate_date ?? "Legacy date unknown"}</div>
                  <div>{cl.exchange_rate_source ?? "Legacy source unknown"}</div>
                </td>
                <td className="px-4 py-2 font-medium">{fmtCurrency(cl.amount_base)}</td>
                <td className="px-4 py-2">
                  <span className={`text-xs px-2 py-0.5 rounded-full ${cl.is_included_in_valuation ? "bg-green-100 text-green-700" : "bg-gray-100 text-gray-500"}`}>
                    {cl.is_included_in_valuation ? "Yes" : "No"}
                  </span>
                </td>
                <td className="px-4 py-2">
                  {canRecordActual && !cl.actual_record ? (
                    <div className="flex min-w-52 flex-col gap-1">
                      <input
                        type="number"
                        step="0.0001"
                        aria-label={`Actual amount for ${cl.cost_type}`}
                        placeholder="Actual amount"
                        value={actualInputs[cl.id]?.amount ?? ""}
                        onChange={(event) => setActualInputs((current) => ({
                          ...current,
                          [cl.id]: { amount: event.target.value, reference: current[cl.id]?.reference ?? "" },
                        }))}
                        className="w-full rounded border px-2 py-1 text-xs"
                      />
                      <input
                        type="text"
                        maxLength={200}
                        aria-label={`Actual source reference for ${cl.cost_type}`}
                        placeholder="Invoice / source reference"
                        value={actualInputs[cl.id]?.reference ?? ""}
                        onChange={(event) => setActualInputs((current) => ({
                          ...current,
                          [cl.id]: { amount: current[cl.id]?.amount ?? "", reference: event.target.value },
                        }))}
                        className="w-full rounded border px-2 py-1 text-xs"
                      />
                      <button
                        onClick={() => recordActual.mutate({
                          lineId: cl.id,
                          amount: Number(actualInputs[cl.id]?.amount),
                          reference: actualInputs[cl.id]?.reference ?? "",
                        })}
                        disabled={recordActual.isPending || !actualInputs[cl.id]?.amount || !actualInputs[cl.id]?.reference.trim()}
                        className="rounded bg-indigo-600 px-2 py-1 text-xs text-white disabled:opacity-50"
                      >
                        {recordActual.isPending ? "Saving…" : "Record actual"}
                      </button>
                    </div>
                  ) : cl.actual_record ? (
                    <span title={`Recorded ${new Date(cl.actual_record.recorded_at).toLocaleString()}`}>Recorded</span>
                  ) : "—"}
                </td>
              </tr>
            ))}
            {costLines.length === 0 && (
              <tr><td colSpan={13} className="px-4 py-4 text-center text-gray-400">No cost lines.</td></tr>
            )}
          </tbody>
        </table>
      </div>

      {canRecordActual && (
        <p className="text-xs text-gray-500">
          Actual entries require finance posting permission and a source reference. Before posting, recording an actual resets validation and clears stale allocations; after posting, it records the variance without changing the posted allocation or journal.
        </p>
      )}
      {recordActual.error instanceof Error && (
        <p role="alert" className="text-sm text-red-600">{recordActual.error.message}</p>
      )}

      {/* GRN Links */}
      <div className="bg-white border rounded-xl overflow-hidden">
        <div className="px-5 py-3 border-b bg-gray-50">
          <h2 className="text-sm font-semibold text-gray-700">Linked GRNs ({grnLinks.length})</h2>
        </div>
        {grnLinks.length === 0 ? (
          <p className="px-5 py-4 text-sm text-gray-400">No GRNs linked.</p>
        ) : (
          <table className="w-full text-sm">
            <thead className="bg-gray-50 text-xs text-gray-500 uppercase">
              <tr>
                {["GRN No", "PO No", "GRN Value (Base)", "Total Qty", "Allocation Share %"].map((h) => (
                  <th key={h} className="px-4 py-2 text-left font-medium">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {grnLinks.map((g) => (
                <tr key={g.id} className="hover:bg-gray-50">
                  <td className="px-4 py-2 font-mono text-xs">{g.grn_no ?? g.grn_id.slice(0, 8)}</td>
                  <td className="px-4 py-2 text-gray-600 text-xs">{g.po_no ?? "—"}</td>
                  <td className="px-4 py-2">{g.grn_value_base != null ? fmtCurrency(g.grn_value_base) : "—"}</td>
                  <td className="px-4 py-2 text-gray-600">{g.grn_total_qty ?? "—"}</td>
                  <td className="px-4 py-2 text-gray-600">{g.allocation_share != null ? `${g.allocation_share}%` : "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {/* Allocation Lines */}
      {allocationLines.length > 0 && (
        <div className="bg-white border rounded-xl overflow-hidden">
          <div className="px-5 py-3 border-b bg-gray-50">
            <h2 className="text-sm font-semibold text-gray-700">Allocation Results ({allocationLines.length} lines)</h2>
          </div>
          <table className="w-full text-sm">
            <thead className="bg-gray-50 text-xs text-gray-500 uppercase">
              <tr>
                {["Material", "Lot", "Qty", "Basis Used", "PO Value", "Share %", "Allocated Amount", "Per Unit LC", "Posted"].map((h) => (
                  <th key={h} className="px-4 py-2 text-left font-medium">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {allocationLines.map((al) => (
                <tr key={al.id} className="hover:bg-gray-50">
                  <td className="px-4 py-2 text-xs">{al.material_name ?? "—"}</td>
                  <td className="px-4 py-2 font-mono text-xs">{al.lot_no ?? "—"}</td>
                  <td className="px-4 py-2 text-gray-600">{al.received_qty ?? "—"}</td>
                  <td className="px-4 py-2 text-gray-600">{al.allocation_basis != null ? Number(al.allocation_basis).toFixed(6) : "—"}</td>
                  <td className="px-4 py-2">{al.purchase_value != null ? fmtCurrency(al.purchase_value) : "—"}</td>
                  <td className="px-4 py-2 text-gray-600">{al.allocation_share != null ? `${al.allocation_share}%` : "—"}</td>
                  <td className="px-4 py-2 font-semibold text-green-700">{fmtCurrency(al.allocated_amount)}</td>
                  <td className="px-4 py-2 text-gray-600 text-xs">{al.per_unit_lc_cost != null ? Number(al.per_unit_lc_cost).toFixed(6) : "—"}</td>
                  <td className="px-4 py-2">
                    <span className={`text-xs px-2 py-0.5 rounded-full ${al.is_posted ? "bg-green-100 text-green-700" : "bg-gray-100 text-gray-500"}`}>
                      {al.is_posted ? "Yes" : "No"}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {doc.notes && (
        <div className="bg-white border rounded-xl p-5">
          <p className="text-xs text-gray-500 mb-1">Notes</p>
          <p className="text-sm text-gray-700">{doc.notes}</p>
        </div>
      )}
    </div>
  );
}
