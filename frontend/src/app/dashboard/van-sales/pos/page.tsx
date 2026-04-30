"use client";
import { useState } from "react";
import { useMutation, useQueryClient, useQuery } from "@tanstack/react-query";
import { vanSalesApi } from "@/lib/van_sales";
import { useSearchParams } from "next/navigation";

interface PosLine {
  item_id: string;
  uom: string;
  quantity: number;
  unit_price: number;
  discount_pct: number;
  tax_pct: number;
}

function calcLine(l: PosLine) {
  const gross = l.quantity * l.unit_price;
  const disc = gross * l.discount_pct / 100;
  const taxable = gross - disc;
  const tax = taxable * l.tax_pct / 100;
  return { gross, disc, tax, total: taxable + tax };
}

export default function POSPage() {
  const sp = useSearchParams();
  const vanId = sp.get("van_id") ?? "";
  const qc = useQueryClient();

  const [customerId, setCustomerId] = useState("");
  const [lines, setLines] = useState<PosLine[]>([]);
  const [txnType, setTxnType] = useState<"SALE" | "RETURN">("SALE");
  const [payMethod, setPayMethod] = useState("CASH");
  const [payRef, setPayRef] = useState("");
  const [step, setStep] = useState<"items" | "payment" | "receipt">("items");
  const [createdTxn, setCreatedTxn] = useState<any>(null);
  const [error, setError] = useState("");

  const { data: vans = [] } = useQuery({ queryKey: ["vans"], queryFn: () => vanSalesApi.listVans() });
  const [selectedVan, setSelectedVan] = useState(vanId);

  const totals = lines.reduce((acc, l) => {
    const c = calcLine(l);
    return { subtotal: acc.subtotal + c.gross, disc: acc.disc + c.disc, tax: acc.tax + c.tax, total: acc.total + c.total };
  }, { subtotal: 0, disc: 0, tax: 0, total: 0 });

  const txnMut = useMutation({
    mutationFn: (data: any) => vanSalesApi.createTransaction(selectedVan, data),
    onSuccess: (t) => { setCreatedTxn(t); setStep("payment"); },
    onError: (e: any) => setError(e?.message ?? "Failed to create transaction"),
  });

  const payMut = useMutation({
    mutationFn: (data: any) => vanSalesApi.addPayment(createdTxn.id, data),
    onSuccess: () => { setStep("receipt"); qc.invalidateQueries({ queryKey: ["van-txns"] }); },
    onError: (e: any) => setError(e?.message ?? "Payment failed"),
  });

  const addLine = () => setLines([...lines, { item_id: "", uom: "PCS", quantity: 1, unit_price: 0, discount_pct: 0, tax_pct: 16 }]);
  const updateLine = (i: number, k: keyof PosLine, v: any) => setLines(lines.map((l, idx) => idx === i ? { ...l, [k]: v } : l));
  const removeLine = (i: number) => setLines(lines.filter((_, idx) => idx !== i));

  const handleConfirm = () => {
    setError("");
    if (!selectedVan) { setError("Select a van"); return; }
    if (!customerId) { setError("Enter customer ID"); return; }
    if (lines.length === 0) { setError("Add at least one item"); return; }
    txnMut.mutate({
      customer_id: customerId,
      txn_type: txnType,
      txn_datetime: new Date().toISOString(),
      offline_id: `pos-${Date.now()}`,
      lines: lines.map((l) => ({ ...l })),
    });
  };

  const handlePay = () => {
    payMut.mutate({
      method: payMethod,
      amount: totals.total,
      reference_no: payRef || undefined,
      collected_at: new Date().toISOString(),
    });
  };

  const reset = () => {
    setLines([]); setCustomerId(""); setStep("items");
    setCreatedTxn(null); setError(""); setPayRef("");
  };

  return (
    <div className="p-4 max-w-xl mx-auto text-slate-200">
      <div className="flex items-center justify-between mb-4">
        <h1 className="text-xl font-bold text-white">Mobile POS</h1>
        <div className="flex gap-2">
          <button onClick={() => setTxnType("SALE")}
            className={`px-3 py-1.5 rounded-lg text-xs font-medium border transition-colors ${txnType === "SALE" ? "bg-emerald-600 border-emerald-500 text-white" : "border-white/[0.08] text-slate-400"}`}>
            SALE
          </button>
          <button onClick={() => setTxnType("RETURN")}
            className={`px-3 py-1.5 rounded-lg text-xs font-medium border transition-colors ${txnType === "RETURN" ? "bg-red-600 border-red-500 text-white" : "border-white/[0.08] text-slate-400"}`}>
            RETURN
          </button>
        </div>
      </div>

      {step === "items" && (
        <div className="space-y-4">
          {/* Van selector */}
          <div>
            <label className="text-xs text-slate-400 mb-1 block">Van</label>
            <select value={selectedVan} onChange={(e) => setSelectedVan(e.target.value)}
              className="w-full bg-[#0d1829] border border-white/[0.08] rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-indigo-500">
              <option value="">Select van…</option>
              {vans.map((v) => <option key={v.id} value={v.id}>{v.van_code} — {v.plate_number ?? "no plate"}</option>)}
            </select>
          </div>

          {/* Customer */}
          <div>
            <label className="text-xs text-slate-400 mb-1 block">Customer ID</label>
            <input value={customerId} onChange={(e) => setCustomerId(e.target.value)}
              className="w-full bg-white/[0.04] border border-white/[0.08] rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-indigo-500 font-mono"
              placeholder="UUID or scan barcode" />
          </div>

          {/* Lines */}
          <div className="space-y-3">
            {lines.map((l, i) => (
              <div key={i} className="glow-card p-3 space-y-2">
                <div className="flex items-center justify-between">
                  <p className="text-xs text-slate-400 font-semibold">Line {i + 1}</p>
                  <button onClick={() => removeLine(i)} className="text-red-400 text-xs hover:text-red-300">✕</button>
                </div>
                <div className="grid grid-cols-2 gap-2">
                  <div>
                    <label className="text-[10px] text-slate-500">Item ID</label>
                    <input value={l.item_id} onChange={(e) => updateLine(i, "item_id", e.target.value)}
                      className="w-full bg-white/[0.04] border border-white/[0.08] rounded px-2 py-1.5 text-xs text-white focus:outline-none font-mono" placeholder="UUID" />
                  </div>
                  <div>
                    <label className="text-[10px] text-slate-500">UOM</label>
                    <input value={l.uom} onChange={(e) => updateLine(i, "uom", e.target.value)}
                      className="w-full bg-white/[0.04] border border-white/[0.08] rounded px-2 py-1.5 text-xs text-white focus:outline-none" />
                  </div>
                  <div>
                    <label className="text-[10px] text-slate-500">Qty</label>
                    <input type="number" value={l.quantity} onChange={(e) => updateLine(i, "quantity", parseFloat(e.target.value) || 0)}
                      className="w-full bg-white/[0.04] border border-white/[0.08] rounded px-2 py-1.5 text-xs text-white focus:outline-none" min={0.001} step={0.001} />
                  </div>
                  <div>
                    <label className="text-[10px] text-slate-500">Unit Price</label>
                    <input type="number" value={l.unit_price} onChange={(e) => updateLine(i, "unit_price", parseFloat(e.target.value) || 0)}
                      className="w-full bg-white/[0.04] border border-white/[0.08] rounded px-2 py-1.5 text-xs text-white focus:outline-none" min={0} />
                  </div>
                  <div>
                    <label className="text-[10px] text-slate-500">Disc %</label>
                    <input type="number" value={l.discount_pct} onChange={(e) => updateLine(i, "discount_pct", parseFloat(e.target.value) || 0)}
                      className="w-full bg-white/[0.04] border border-white/[0.08] rounded px-2 py-1.5 text-xs text-white focus:outline-none" min={0} max={100} />
                  </div>
                  <div>
                    <label className="text-[10px] text-slate-500">Tax %</label>
                    <input type="number" value={l.tax_pct} onChange={(e) => updateLine(i, "tax_pct", parseFloat(e.target.value) || 0)}
                      className="w-full bg-white/[0.04] border border-white/[0.08] rounded px-2 py-1.5 text-xs text-white focus:outline-none" min={0} />
                  </div>
                </div>
                <div className="text-right text-xs text-emerald-400 font-medium">
                  Line Total: KES {calcLine(l).total.toFixed(2)}
                </div>
              </div>
            ))}
            <button onClick={addLine}
              className="w-full py-2 rounded-lg border border-dashed border-white/[0.15] text-slate-400 text-sm hover:border-indigo-500 hover:text-indigo-400 transition-colors">
              + Add Item
            </button>
          </div>

          {/* Summary */}
          {lines.length > 0 && (
            <div className="glow-card p-4 space-y-1 text-sm">
              <div className="flex justify-between text-slate-400"><span>Subtotal</span><span>KES {totals.subtotal.toFixed(2)}</span></div>
              <div className="flex justify-between text-amber-400"><span>Discount</span><span>- KES {totals.disc.toFixed(2)}</span></div>
              <div className="flex justify-between text-slate-400"><span>Tax</span><span>KES {totals.tax.toFixed(2)}</span></div>
              <div className="flex justify-between text-white font-bold text-base pt-1 border-t border-white/[0.07]"><span>Total</span><span>KES {totals.total.toFixed(2)}</span></div>
            </div>
          )}

          {error && <div className="text-sm text-red-400 rounded-lg border border-red-500/20 bg-red-500/10 p-3">{error}</div>}

          <button onClick={handleConfirm} disabled={txnMut.isPending}
            className={`w-full py-3 rounded-xl font-semibold text-white text-sm transition-colors disabled:opacity-50 ${txnType === "SALE" ? "bg-emerald-600 hover:bg-emerald-500" : "bg-red-600 hover:bg-red-500"}`}>
            {txnMut.isPending ? "Processing…" : txnType === "SALE" ? "Confirm Sale" : "Confirm Return"}
          </button>
        </div>
      )}

      {step === "payment" && createdTxn && (
        <div className="space-y-4">
          <div className="rounded-xl border border-emerald-500/30 bg-emerald-500/10 p-4">
            <p className="text-sm text-emerald-300 font-semibold">Transaction Created: {createdTxn.txn_no}</p>
            <p className="text-2xl font-bold text-white mt-2">KES {createdTxn.total_amount?.toLocaleString()}</p>
          </div>

          <div>
            <label className="text-xs text-slate-400 mb-1 block">Payment Method</label>
            <div className="grid grid-cols-3 gap-2">
              {["CASH", "MPESA", "CARD"].map((m) => (
                <button key={m} onClick={() => setPayMethod(m)}
                  className={`py-2 rounded-lg text-xs font-medium border transition-colors ${payMethod === m ? "bg-indigo-600 border-indigo-500 text-white" : "border-white/[0.08] text-slate-400"}`}>
                  {m}
                </button>
              ))}
            </div>
          </div>

          {payMethod !== "CASH" && (
            <div>
              <label className="text-xs text-slate-400 mb-1 block">Reference / Receipt No</label>
              <input value={payRef} onChange={(e) => setPayRef(e.target.value)}
                className="w-full bg-white/[0.04] border border-white/[0.08] rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-indigo-500"
                placeholder={payMethod === "MPESA" ? "M-Pesa code" : "Reference"} />
            </div>
          )}

          {error && <div className="text-sm text-red-400">{error}</div>}

          <button onClick={handlePay} disabled={payMut.isPending}
            className="w-full py-3 rounded-xl bg-indigo-600 hover:bg-indigo-500 font-semibold text-white text-sm disabled:opacity-50">
            {payMut.isPending ? "Processing…" : `Collect KES ${createdTxn.total_amount?.toLocaleString()}`}
          </button>

          <button onClick={reset} className="w-full py-2 text-slate-500 text-sm hover:text-slate-300">← Back to sale</button>
        </div>
      )}

      {step === "receipt" && createdTxn && (
        <div className="space-y-4 text-center">
          <div className="rounded-xl border border-emerald-500/30 bg-emerald-500/10 p-6">
            <p className="text-4xl mb-3">✅</p>
            <p className="text-lg font-bold text-white">Payment Complete</p>
            <p className="text-sm text-slate-400 mt-1">{createdTxn.txn_no}</p>
            <p className="text-2xl font-bold text-emerald-400 mt-3">KES {createdTxn.total_amount?.toLocaleString()}</p>
            <p className="text-xs text-slate-500 mt-2">via {payMethod}</p>
          </div>
          <button onClick={reset}
            className="w-full py-3 rounded-xl bg-indigo-600 hover:bg-indigo-500 font-semibold text-white text-sm">
            New Transaction
          </button>
        </div>
      )}
    </div>
  );
}
