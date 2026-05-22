"use client";
import { useState } from "react";
import { useParams } from "next/navigation";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { vanSalesApi, VAN_STATUS_COLORS, TXN_STATUS_COLORS, PAYMENT_STATUS_COLORS, VISIT_STATUS_COLORS } from "@/lib/van_sales";
import Link from "next/link";

export default function VanDetailPage() {
  const { id } = useParams<{ id: string }>();
  const qc = useQueryClient();
  const [tab, setTab] = useState<"txns" | "stock" | "visits" | "recon">("txns");
  const today = new Date().toISOString().split("T")[0];

  const { data: van } = useQuery({ queryKey: ["van", id], queryFn: () => vanSalesApi.getVan(id) });
  const { data: stock = [] } = useQuery({ queryKey: ["van-stock", id], queryFn: () => vanSalesApi.getStock(id), enabled: tab === "stock" });
  const { data: txns = [] } = useQuery({ queryKey: ["van-txns", id], queryFn: () => vanSalesApi.listTransactions(id, today), enabled: tab === "txns" });
  const { data: visits = [] } = useQuery({ queryKey: ["van-visits", id], queryFn: () => vanSalesApi.listVisits(id, today), enabled: tab === "visits" });
  const { data: recons = [] } = useQuery({ queryKey: ["van-recons", id], queryFn: () => vanSalesApi.listReconciliations(id), enabled: tab === "recon" });
  const { data: summary } = useQuery({ queryKey: ["van-summary", id], queryFn: () => vanSalesApi.vanSummary(id) });

  const reconMut = useMutation({
    mutationFn: () => vanSalesApi.createReconciliation(id, { route_date: today }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["van-recons", id] }),
  });

  if (!van) return <div className="p-6 text-slate-500">Loading…</div>;

  const todayTotalSales = txns.filter(t => t.txn_type === "SALE").reduce((s, t) => s + t.total_amount, 0);
  const todayCollected = txns.reduce((s, t) => s + t.paid_amount, 0);

  return (
    <div className="p-6 space-y-6 text-slate-200">
      <div className="flex items-start justify-between">
        <div>
          <Link href="/dashboard/van-sales/vans" className="text-slate-500 text-sm hover:text-slate-300">← Vans</Link>
          <div className="flex items-center gap-3 mt-1">
            <h1 className="text-xl font-bold text-white">{van.van_code}</h1>
            <span className={`text-[10px] px-2 py-0.5 rounded-full font-medium ${VAN_STATUS_COLORS[van.status]}`}>{van.status}</span>
          </div>
          <p className="text-slate-500 text-sm">{van.plate_number ?? "No plate"}</p>
        </div>
        <Link href={`/dashboard/van-sales/pos?van_id=${id}`}
          className="px-4 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white text-sm font-medium">
          Open POS
        </Link>
      </div>

      {/* Today stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {[
          { label: "Today Sales", value: `KES ${todayTotalSales.toLocaleString()}`, color: "text-emerald-400" },
          { label: "Collected", value: `KES ${todayCollected.toLocaleString()}`, color: "text-blue-400" },
          { label: "Transactions", value: txns.length, color: "text-white" },
          { label: "Stock Lines", value: stock.length, color: "text-slate-300" },
        ].map((c) => (
          <div key={c.label} className="glow-card p-4">
            <p className="text-[10px] text-slate-500 uppercase tracking-wider mb-1">{c.label}</p>
            <p className={`text-2xl font-bold ${c.color}`}>{c.value}</p>
          </div>
        ))}
      </div>

      {/* Tabs */}
      <div className="flex gap-1 border-b border-white/[0.07]">
        {(["txns", "stock", "visits", "recon"] as const).map((t) => (
          <button key={t} onClick={() => setTab(t)}
            className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${tab === t ? "border-indigo-500 text-indigo-300" : "border-transparent text-slate-500 hover:text-slate-300"}`}>
            {t === "txns" ? "Transactions" : t === "stock" ? "Van Stock" : t === "visits" ? "Visits" : "Reconciliation"}
          </button>
        ))}
      </div>

      {tab === "txns" && (
        <div className="rounded-xl border border-white/[0.07] overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-white/[0.03] text-slate-500 text-xs uppercase tracking-wider">
              <tr>
                <th className="px-4 py-3 text-left">Txn No</th>
                <th className="px-4 py-3 text-left">Type</th>
                <th className="px-4 py-3 text-left">Customer</th>
                <th className="px-4 py-3 text-right">Total</th>
                <th className="px-4 py-3 text-left">Status</th>
                <th className="px-4 py-3 text-left">Payment</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-white/[0.04]">
              {txns.map((t) => (
                <tr key={t.id} className="hover:bg-white/[0.02]">
                  <td className="px-4 py-3 font-mono text-xs text-indigo-300">{t.txn_no}</td>
                  <td className="px-4 py-3 text-xs text-slate-400">{t.txn_type}</td>
                  <td className="px-4 py-3 text-xs text-slate-400 font-mono">{t.customer_id.slice(0, 8)}…</td>
                  <td className="px-4 py-3 text-right text-white font-medium">KES {t.total_amount.toLocaleString()}</td>
                  <td className="px-4 py-3"><span className={`text-[10px] px-2 py-0.5 rounded-full font-medium ${TXN_STATUS_COLORS[t.status]}`}>{t.status}</span></td>
                  <td className="px-4 py-3"><span className={`text-[10px] px-2 py-0.5 rounded-full font-medium ${PAYMENT_STATUS_COLORS[t.payment_status]}`}>{t.payment_status}</span></td>
                </tr>
              ))}
              {txns.length === 0 && <tr><td colSpan={6} className="text-center py-6 text-slate-600">No transactions today</td></tr>}
            </tbody>
          </table>
        </div>
      )}

      {tab === "stock" && (
        <div className="rounded-xl border border-white/[0.07] overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-white/[0.03] text-slate-500 text-xs uppercase tracking-wider">
              <tr>
                <th className="px-4 py-3 text-left">Item</th>
                <th className="px-4 py-3 text-left">UOM</th>
                <th className="px-4 py-3 text-right">Qty</th>
                <th className="px-4 py-3 text-right">Reserved</th>
                <th className="px-4 py-3 text-right">Available</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-white/[0.04]">
              {stock.map((s) => (
                <tr key={s.id} className="hover:bg-white/[0.02]">
                  <td className="px-4 py-3 font-mono text-xs text-slate-400">{s.item_id.slice(0, 8)}…</td>
                  <td className="px-4 py-3 text-slate-300">{s.uom}</td>
                  <td className="px-4 py-3 text-right text-white font-medium">{s.quantity}</td>
                  <td className="px-4 py-3 text-right text-amber-400">{s.reserved_qty}</td>
                  <td className="px-4 py-3 text-right text-emerald-400">{(s.quantity - s.reserved_qty).toFixed(3)}</td>
                </tr>
              ))}
              {stock.length === 0 && <tr><td colSpan={5} className="text-center py-6 text-slate-600">No stock loaded</td></tr>}
            </tbody>
          </table>
        </div>
      )}

      {tab === "visits" && (
        <div className="space-y-2">
          {visits.sort((a, b) => (a.sequence_no ?? 99) - (b.sequence_no ?? 99)).map((v) => (
            <div key={v.id} className="flex items-center justify-between p-3 rounded-lg bg-white/[0.025] border border-white/[0.04]">
              <div className="flex items-center gap-3">
                <span className="text-slate-500 text-xs w-6">{v.sequence_no ?? "—"}</span>
                <div>
                  <p className="text-sm text-white font-mono">{v.customer_id.slice(0, 8)}…</p>
                  <p className="text-xs text-slate-500">{v.planned_time ? new Date(v.planned_time).toLocaleTimeString() : "No time"}</p>
                </div>
              </div>
              <span className={`text-[10px] px-2 py-0.5 rounded-full font-medium ${VISIT_STATUS_COLORS[v.status]}`}>{v.status}</span>
            </div>
          ))}
          {visits.length === 0 && <p className="text-center py-6 text-slate-600">No visits planned today</p>}
        </div>
      )}

      {tab === "recon" && (
        <div className="space-y-4">
          <div className="flex justify-end">
            <button onClick={() => reconMut.mutate()} disabled={reconMut.isPending}
              className="px-4 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white text-sm font-medium disabled:opacity-50">
              {reconMut.isPending ? "Submitting…" : "Submit Today's Reconciliation"}
            </button>
          </div>
          <div className="space-y-2">
            {recons.map((r) => (
              <div key={r.id} className="p-4 glow-card">
                <div className="flex items-center justify-between mb-2">
                  <p className="text-sm font-semibold text-white">{r.route_date}</p>
                  <span className={`text-[10px] px-2 py-0.5 rounded-full font-medium ${r.status === "APPROVED" ? "bg-emerald-500/20 text-emerald-300" : r.status === "DISCREPANCY" ? "bg-red-500/20 text-red-300" : "bg-slate-500/20 text-slate-400"}`}>{r.status}</span>
                </div>
                <div className="grid grid-cols-3 gap-2 text-xs">
                  <div><p className="text-slate-500">Sales</p><p className="text-white font-medium">KES {(r.total_sales ?? 0).toLocaleString()}</p></div>
                  <div><p className="text-slate-500">Cash</p><p className="text-emerald-400 font-medium">KES {(r.total_cash ?? 0).toLocaleString()}</p></div>
                  <div><p className="text-slate-500">M-Pesa</p><p className="text-blue-400 font-medium">KES {(r.total_mpesa ?? 0).toLocaleString()}</p></div>
                </div>
              </div>
            ))}
            {recons.length === 0 && <p className="text-center py-6 text-slate-600">No reconciliations</p>}
          </div>
        </div>
      )}
    </div>
  );
}
