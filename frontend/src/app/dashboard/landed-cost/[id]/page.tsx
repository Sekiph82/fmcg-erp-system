"use client";
import { useParams, useRouter } from "next/navigation";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  lcApi, LC_STATUS_COLOR, COST_TYPE_LABEL, ALLOC_METHOD_LABEL,
  LandedCostOut, fmtCurrency,
} from "@/lib/landed_cost";

export default function LandedCostDetailPage() {
  const { id } = useParams<{ id: string }>();
  const qc = useQueryClient();
  const router = useRouter();

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
          { label: "Currency",     value: `${doc.currency_code} @ ${doc.exchange_rate}` },
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
        </div>
        <table className="w-full text-sm">
          <thead className="bg-gray-50 text-xs text-gray-500 uppercase">
            <tr>
              {["Type", "Description", "Vendor", "Amount (FC)", "Ccy", "Rate", "Amount (Base)", "In Valuation"].map((h) => (
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
                <td className="px-4 py-2 font-medium">{Number(cl.amount_fc ?? 0).toLocaleString()}</td>
                <td className="px-4 py-2 text-gray-500 text-xs">{cl.currency_code}</td>
                <td className="px-4 py-2 text-gray-500 text-xs">{Number(cl.exchange_rate ?? 1).toFixed(4)}</td>
                <td className="px-4 py-2 font-medium">{fmtCurrency(cl.amount_base)}</td>
                <td className="px-4 py-2">
                  <span className={`text-xs px-2 py-0.5 rounded-full ${cl.is_included_in_valuation ? "bg-green-100 text-green-700" : "bg-gray-100 text-gray-500"}`}>
                    {cl.is_included_in_valuation ? "Yes" : "No"}
                  </span>
                </td>
              </tr>
            ))}
            {costLines.length === 0 && (
              <tr><td colSpan={8} className="px-4 py-4 text-center text-gray-400">No cost lines.</td></tr>
            )}
          </tbody>
        </table>
      </div>

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
                {["Material", "Lot", "Qty", "PO Value", "Share %", "Allocated Amount", "Per Unit LC", "Posted"].map((h) => (
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
