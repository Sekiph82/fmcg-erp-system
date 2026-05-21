"use client";
import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { vanSalesApi } from "@/lib/van_sales";

interface LoadLine { item_id: string; quantity: number; uom: string; unit_cost: string; }

export default function VanStockPage() {
  const qc = useQueryClient();
  const [selectedVanId, setSelectedVanId] = useState("");
  const [loadLines, setLoadLines] = useState<LoadLine[]>([]);
  const [showLoad, setShowLoad] = useState(false);

  const { data: vans = [] } = useQuery({ queryKey: ["vans"], queryFn: () => vanSalesApi.listVans() });
  const { data: stock = [] } = useQuery({
    queryKey: ["van-stock", selectedVanId],
    queryFn: () => vanSalesApi.getStock(selectedVanId),
    enabled: !!selectedVanId,
  });

  const loadMut = useMutation({
    mutationFn: () => vanSalesApi.loadStock(selectedVanId, {
      lines: loadLines.map((l) => ({ item_id: l.item_id, quantity: l.quantity, uom: l.uom, unit_cost: l.unit_cost ? parseFloat(l.unit_cost) : undefined } as any)),
    }),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["van-stock", selectedVanId] }); setShowLoad(false); setLoadLines([]); },
  });

  const addLoadLine = () => setLoadLines([...loadLines, { item_id: "", quantity: 1, uom: "PCS", unit_cost: "" }]);
  const updLoad = (i: number, k: keyof LoadLine, v: any) => setLoadLines(loadLines.map((l, idx) => idx === i ? { ...l, [k]: v } : l));

  const totalQty = stock.reduce((s, i) => s + Number(i.quantity), 0);

  return (
    <div className="p-6 space-y-5 text-slate-200">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-white">Van Stock</h1>
          <p className="text-slate-500 text-sm mt-0.5">Load and track field inventory</p>
        </div>
        {selectedVanId && (
          <button onClick={() => setShowLoad(true)}
            className="px-4 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white text-sm font-medium">
            + Load Stock
          </button>
        )}
      </div>

      <div>
        <label className="text-xs text-slate-400 mb-1 block">Select Van</label>
        <select value={selectedVanId} onChange={(e) => setSelectedVanId(e.target.value)}
          className="bg-[#0d1829] border border-white/[0.08] rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-indigo-500 w-64">
          <option value="">Select van…</option>
          {vans.map((v) => <option key={v.id} value={v.id}>{v.van_code} — {v.plate_number ?? "no plate"}</option>)}
        </select>
      </div>

      {selectedVanId && !showLoad && (
        <>
          <div className="grid grid-cols-2 gap-4">
            <div className="glow-card p-4">
              <p className="text-[10px] text-slate-500 uppercase tracking-wider mb-1">Stock Lines</p>
              <p className="text-2xl font-bold text-white">{stock.length}</p>
            </div>
            <div className="glow-card p-4">
              <p className="text-[10px] text-slate-500 uppercase tracking-wider mb-1">Total Units</p>
              <p className="text-2xl font-bold text-emerald-400">{totalQty.toFixed(1)}</p>
            </div>
          </div>

          <div className="rounded-xl border border-white/[0.07] overflow-hidden">
            <table className="w-full text-sm">
              <thead className="bg-white/[0.03] text-slate-500 text-xs uppercase tracking-wider">
                <tr>
                  <th className="px-4 py-3 text-left">Item</th>
                  <th className="px-4 py-3 text-left">UOM</th>
                  <th className="px-4 py-3 text-right">Qty</th>
                  <th className="px-4 py-3 text-right">Reserved</th>
                  <th className="px-4 py-3 text-right">Available</th>
                  <th className="px-4 py-3 text-right">Unit Cost</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-white/[0.04]">
                {stock.map((s) => (
                  <tr key={s.id} className="hover:bg-white/[0.02]">
                    <td className="px-4 py-3 font-mono text-xs text-slate-400">{s.item_id.slice(0, 8)}…</td>
                    <td className="px-4 py-3 text-slate-300">{s.uom}</td>
                    <td className="px-4 py-3 text-right text-white font-medium">{s.quantity}</td>
                    <td className="px-4 py-3 text-right text-amber-400">{s.reserved_qty}</td>
                    <td className="px-4 py-3 text-right text-emerald-400">{(Number(s.quantity) - Number(s.reserved_qty)).toFixed(3)}</td>
                    <td className="px-4 py-3 text-right text-slate-400">{s.unit_cost ?? "—"}</td>
                  </tr>
                ))}
                {stock.length === 0 && <tr><td colSpan={6} className="text-center py-6 text-slate-600">No stock loaded on this van</td></tr>}
              </tbody>
            </table>
          </div>
        </>
      )}

      {/* Load stock panel */}
      {showLoad && (
        <div className="space-y-4">
          <h2 className="text-sm font-semibold text-white">Load Stock to Van</h2>
          {loadLines.map((l, i) => (
            <div key={i} className="glow-card p-4 space-y-2">
              <div className="grid grid-cols-2 gap-2">
                {[
                  { key: "item_id", label: "Item ID", placeholder: "UUID" },
                  { key: "uom", label: "UOM", placeholder: "PCS" },
                  { key: "quantity", label: "Quantity", placeholder: "100", type: "number" },
                  { key: "unit_cost", label: "Unit Cost", placeholder: "0.00", type: "number" },
                ].map(({ key, label, placeholder, type }) => (
                  <div key={key}>
                    <label className="text-[10px] text-slate-500">{label}</label>
                    <input type={type ?? "text"} value={(l as any)[key]} onChange={(e) => updLoad(i, key as keyof LoadLine, e.target.value)}
                      placeholder={placeholder}
                      className="w-full bg-white/[0.04] border border-white/[0.08] rounded px-2 py-1.5 text-xs text-white focus:outline-none" />
                  </div>
                ))}
              </div>
            </div>
          ))}
          <button onClick={addLoadLine} className="w-full py-2 rounded-lg border border-dashed border-white/[0.15] text-slate-400 text-sm hover:border-indigo-500">
            + Add Item
          </button>
          <div className="flex gap-3">
            <button onClick={() => loadMut.mutate()} disabled={loadMut.isPending || loadLines.length === 0}
              className="px-5 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white text-sm font-medium disabled:opacity-50">
              {loadMut.isPending ? "Loading…" : "Confirm Load"}
            </button>
            <button onClick={() => { setShowLoad(false); setLoadLines([]); }}
              className="px-4 py-2 rounded-lg border border-white/[0.08] text-slate-400 text-sm">Cancel</button>
          </div>
        </div>
      )}
    </div>
  );
}
