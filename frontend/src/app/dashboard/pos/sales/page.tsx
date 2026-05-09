"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { posApi, POSSale, POSPaymentMethod, fmtKES } from "@/lib/pos";
import { Button } from "@/components/ui/Button";

function fmtDate(d: string) {
  return new Date(d).toLocaleString("en-KE", { day: "2-digit", month: "short", year: "numeric", hour: "2-digit", minute: "2-digit" });
}

function MethodBadge({ m }: { m: POSPaymentMethod }) {
  const cls: Record<POSPaymentMethod, string> = {
    CASH:  "bg-green-100 text-green-700",
    MPESA: "bg-blue-100 text-blue-700",
    CARD:  "bg-purple-100 text-purple-700",
    SPLIT: "bg-yellow-100 text-yellow-700",
  };
  return <span className={`text-xs font-semibold px-2 py-0.5 rounded-full ${cls[m]}`}>{m}</span>;
}

export default function POSSalesPage() {
  const qc = useQueryClient();
  const [selected, setSelected] = useState<POSSale | null>(null);

  const { data: sales = [], isLoading } = useQuery({
    queryKey: ["pos-sales"],
    queryFn: posApi.listSales,
  });

  const voidMut = useMutation({
    mutationFn: (id: string) => posApi.voidSale(id),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["pos-sales"] }); setSelected(null); },
  });

  const totals = {
    count: sales.length,
    total: sales.reduce((s, r) => s + r.sale_total, 0),
    voided: sales.filter(r => r.status === "VOIDED").length,
  };

  return (
    <div className="p-6 space-y-6 max-w-7xl mx-auto">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Sales History</h1>
          <p className="text-sm text-gray-500">All POS transactions</p>
        </div>
      </div>

      <div className="grid grid-cols-3 gap-4">
        <div className="bg-white rounded-xl border p-4">
          <div className="text-xs text-gray-500 font-medium">Total Sales</div>
          <div className="text-2xl font-bold text-gray-900">{totals.count}</div>
        </div>
        <div className="bg-white rounded-xl border p-4">
          <div className="text-xs text-gray-500 font-medium">Revenue</div>
          <div className="text-2xl font-bold text-gray-900">{fmtKES(totals.total)}</div>
        </div>
        <div className="bg-white rounded-xl border p-4">
          <div className="text-xs text-gray-500 font-medium">Voided</div>
          <div className="text-2xl font-bold text-red-600">{totals.voided}</div>
        </div>
      </div>

      <div className="bg-white rounded-xl border shadow-sm overflow-hidden">
        {isLoading ? (
          <div className="p-8 text-center text-gray-400">Loading sales…</div>
        ) : sales.length === 0 ? (
          <div className="p-8 text-center text-gray-400">No sales recorded yet.</div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-gray-50 border-b">
                <tr>
                  {["Sale #", "Cashier", "Customer", "Method", "Items", "Total", "Status", "Date", ""].map(h => (
                    <th key={h} className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {sales.map(s => (
                  <tr key={s.id} className="hover:bg-gray-50">
                    <td className="px-4 py-3 font-mono font-medium text-gray-900">{s.sale_no}</td>
                    <td className="px-4 py-3 text-gray-700">{s.cashier_name ?? "—"}</td>
                    <td className="px-4 py-3 text-gray-700">{s.customer_name ?? "—"}</td>
                    <td className="px-4 py-3"><MethodBadge m={s.payment_method} /></td>
                    <td className="px-4 py-3 text-gray-600">{s.lines.length}</td>
                    <td className="px-4 py-3 font-semibold text-gray-900">{fmtKES(s.sale_total)}</td>
                    <td className="px-4 py-3">
                      {s.status === "VOIDED"
                        ? <span className="text-xs font-semibold px-2 py-0.5 rounded-full bg-red-100 text-red-700">VOIDED</span>
                        : <span className="text-xs font-semibold px-2 py-0.5 rounded-full bg-green-100 text-green-700">COMPLETED</span>
                      }
                    </td>
                    <td className="px-4 py-3 text-xs text-gray-500">{fmtDate(s.created_at)}</td>
                    <td className="px-4 py-3">
                      <button onClick={() => setSelected(s)}
                        className="text-xs px-2 py-1 rounded bg-blue-50 text-blue-700 hover:bg-blue-100">
                        View
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {selected && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40" onClick={() => setSelected(null)}>
          <div className="bg-white rounded-2xl shadow-2xl w-full max-w-lg p-6 space-y-4" onClick={e => e.stopPropagation()}>
            <div className="flex justify-between items-start">
              <h2 className="text-lg font-bold">{selected.sale_no}</h2>
              <button onClick={() => setSelected(null)} className="text-gray-400 hover:text-gray-600 text-xl">✕</button>
            </div>
            <div className="grid grid-cols-2 gap-2 text-sm text-gray-600 bg-gray-50 rounded-lg p-3">
              <div><span className="font-medium">Cashier:</span> {selected.cashier_name ?? "—"}</div>
              <div><span className="font-medium">Payment:</span> <MethodBadge m={selected.payment_method} /></div>
              <div><span className="font-medium">Amount paid:</span> {selected.amount_paid != null ? fmtKES(selected.amount_paid) : "—"}</div>
              <div><span className="font-medium">Change:</span> {selected.change_given != null ? fmtKES(selected.change_given) : "—"}</div>
              {selected.mpesa_ref && <div className="col-span-2"><span className="font-medium">M-Pesa ref:</span> {selected.mpesa_ref}</div>}
            </div>
            <table className="w-full text-sm">
              <thead><tr className="border-b"><th className="text-left py-1">Product</th><th className="text-right py-1">Qty</th><th className="text-right py-1">Total</th></tr></thead>
              <tbody>
                {selected.lines.map(l => (
                  <tr key={l.id} className="border-b border-gray-50">
                    <td className="py-1.5">{l.product_name ?? l.product_id}</td>
                    <td className="py-1.5 text-right">{l.qty}</td>
                    <td className="py-1.5 text-right font-medium">{fmtKES(l.line_total)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            <div className="flex justify-between font-bold text-lg border-t pt-2">
              <span>Total</span><span>{fmtKES(selected.sale_total)}</span>
            </div>
            <div className="flex justify-end gap-2 pt-2">
              {selected.status === "COMPLETED" && (
                <Button variant="danger" onClick={() => voidMut.mutate(selected.id)} disabled={voidMut.isPending}>
                  {voidMut.isPending ? "Voiding…" : "Void Sale"}
                </Button>
              )}
              <Button variant="secondary" onClick={() => setSelected(null)}>Close</Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
