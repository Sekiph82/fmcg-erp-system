"use client";
import { useState } from "react";
import { shelfLifeApi, FEFORankResponse, FEFOValidateIssueResponse, SL_STATUS_BG, fmtDays } from "@/lib/shelfLife";

export default function ProductionValidationPage() {
  const [tab, setTab] = useState<"rank" | "validate">("rank");

  // FEFO Rank
  const [rankForm, setRankForm] = useState({ product_id: "", material_id: "", warehouse_id: "", quantity: "" });
  const [rankResult, setRankResult] = useState<FEFORankResponse | null>(null);
  const [ranking, setRanking] = useState(false);

  // Validate Issue
  const [valForm, setValForm] = useState({ lot_id: "", quantity: "", product_id: "", material_id: "" });
  const [valResult, setValResult] = useState<FEFOValidateIssueResponse | null>(null);
  const [validating, setValidating] = useState(false);

  const handleRank = async () => {
    setRanking(true);
    setRankResult(null);
    try {
      const r = await shelfLifeApi.rankFEFO({
        product_id: rankForm.product_id || undefined,
        material_id: rankForm.material_id || undefined,
        warehouse_id: rankForm.warehouse_id || undefined,
        quantity_needed: rankForm.quantity ? parseFloat(rankForm.quantity) : undefined,
        context: "production_issue",
      });
      setRankResult(r);
    } catch (e: any) { alert(e.message); }
    finally { setRanking(false); }
  };

  const handleValidate = async () => {
    if (!valForm.lot_id) return;
    setValidating(true);
    setValResult(null);
    try {
      const r = await shelfLifeApi.validateIssue({
        lot_id: valForm.lot_id,
        quantity: parseFloat(valForm.quantity) || 0,
        context: "production_issue",
        product_id: valForm.product_id || undefined,
        material_id: valForm.material_id || undefined,
      });
      setValResult(r);
    } catch (e: any) { alert(e.message); }
    finally { setValidating(false); }
  };

  return (
    <div className="p-6 space-y-6">
      <div>
        <h1 className="text-xl font-bold text-gray-900">Production Issue Shelf-Life Validation</h1>
        <p className="text-sm text-gray-500">FEFO lot ranking and issue validation for production consumption</p>
      </div>

      <div className="flex gap-1 bg-gray-100 p-1 rounded-lg w-fit">
        {(["rank","validate"] as const).map(t => (
          <button key={t} onClick={() => setTab(t)}
            className={`px-4 py-1.5 rounded text-sm font-medium ${tab === t ? "bg-white shadow text-gray-800" : "text-gray-500"}`}>
            {t === "rank" ? "FEFO Lot Ranking" : "Validate Specific Lot"}
          </button>
        ))}
      </div>

      {tab === "rank" && (
        <div className="bg-white rounded-xl border border-gray-200 p-6 space-y-4 max-w-2xl">
          <h2 className="font-semibold text-gray-800">FEFO Lot Ranking</h2>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="text-xs font-medium text-gray-600">Product ID</label>
              <input className="mt-1 w-full border rounded-lg px-3 py-2 text-sm"
                value={rankForm.product_id} onChange={e => setRankForm(f => ({ ...f, product_id: e.target.value }))} />
            </div>
            <div>
              <label className="text-xs font-medium text-gray-600">Material ID</label>
              <input className="mt-1 w-full border rounded-lg px-3 py-2 text-sm"
                value={rankForm.material_id} onChange={e => setRankForm(f => ({ ...f, material_id: e.target.value }))} />
            </div>
            <div>
              <label className="text-xs font-medium text-gray-600">Warehouse ID</label>
              <input className="mt-1 w-full border rounded-lg px-3 py-2 text-sm"
                value={rankForm.warehouse_id} onChange={e => setRankForm(f => ({ ...f, warehouse_id: e.target.value }))} />
            </div>
            <div>
              <label className="text-xs font-medium text-gray-600">Quantity Needed</label>
              <input type="number" className="mt-1 w-full border rounded-lg px-3 py-2 text-sm"
                value={rankForm.quantity} onChange={e => setRankForm(f => ({ ...f, quantity: e.target.value }))} />
            </div>
          </div>
          <button onClick={handleRank} disabled={ranking}
            className="w-full py-2 text-sm bg-purple-600 text-white rounded-lg hover:bg-purple-700 disabled:opacity-50">
            {ranking ? "Ranking…" : "Get FEFO Lot Ranking"}
          </button>

          {rankResult && (
            <div className="mt-4 space-y-3">
              <div className="flex items-center justify-between">
                <p className="font-medium text-gray-800">Strategy: <span className="text-purple-700">{rankResult.strategy_used.toUpperCase()}</span></p>
                {rankResult.recommended_lot_id && (
                  <span className="text-xs bg-green-100 text-green-700 px-2 py-0.5 rounded">
                    Recommended: {rankResult.recommended_lot_id.slice(0,8)}
                  </span>
                )}
              </div>

              <div className="space-y-2">
                {rankResult.candidates.map(c => (
                  <div key={c.lot_id}
                    className={`flex items-center gap-3 p-3 rounded-lg border ${c.is_recommended ? "border-green-200 bg-green-50" : "border-gray-200 bg-gray-50"}`}>
                    <span className={`h-6 w-6 rounded-full text-xs flex items-center justify-center font-bold ${c.is_recommended ? "bg-green-600 text-white" : "bg-gray-300 text-gray-600"}`}>
                      {c.rank}
                    </span>
                    <div className="flex-1">
                      <p className="text-sm font-mono text-gray-700">{c.lot_number} — {c.lot_id.slice(0,8)}</p>
                      <div className="flex gap-3 text-xs text-gray-500 mt-0.5">
                        <span>Expiry: {c.expiry_date || "—"}</span>
                        <span>Remaining: <span className="font-semibold">{fmtDays(c.remaining_days)}</span></span>
                        <span>Qty: {c.quantity_available}</span>
                      </div>
                      {c.exclusion_reason && (
                        <p className="text-xs text-red-600 mt-0.5">✗ {c.exclusion_reason}</p>
                      )}
                    </div>
                    <span className={`px-2 py-0.5 rounded text-xs ${SL_STATUS_BG[c.shelf_life_status]}`}>
                      {c.shelf_life_status}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {tab === "validate" && (
        <div className="bg-white rounded-xl border border-gray-200 p-6 space-y-4 max-w-2xl">
          <h2 className="font-semibold text-gray-800">Validate Specific Lot for Issue</h2>
          <div className="grid grid-cols-2 gap-4">
            <div className="col-span-2">
              <label className="text-xs font-medium text-gray-600">Lot ID *</label>
              <input className="mt-1 w-full border rounded-lg px-3 py-2 text-sm"
                value={valForm.lot_id} onChange={e => setValForm(f => ({ ...f, lot_id: e.target.value }))} />
            </div>
            <div>
              <label className="text-xs font-medium text-gray-600">Quantity</label>
              <input type="number" className="mt-1 w-full border rounded-lg px-3 py-2 text-sm"
                value={valForm.quantity} onChange={e => setValForm(f => ({ ...f, quantity: e.target.value }))} />
            </div>
            <div>
              <label className="text-xs font-medium text-gray-600">Product ID</label>
              <input className="mt-1 w-full border rounded-lg px-3 py-2 text-sm"
                value={valForm.product_id} onChange={e => setValForm(f => ({ ...f, product_id: e.target.value }))} />
            </div>
            <div>
              <label className="text-xs font-medium text-gray-600">Material ID</label>
              <input className="mt-1 w-full border rounded-lg px-3 py-2 text-sm"
                value={valForm.material_id} onChange={e => setValForm(f => ({ ...f, material_id: e.target.value }))} />
            </div>
          </div>
          <button onClick={handleValidate} disabled={!valForm.lot_id || validating}
            className="w-full py-2 text-sm bg-purple-600 text-white rounded-lg hover:bg-purple-700 disabled:opacity-50">
            {validating ? "Validating…" : "Validate for Production Issue"}
          </button>

          {valResult && (
            <div className={`rounded-xl border p-5 space-y-3 ${valResult.allowed ? "bg-green-50 border-green-200" : "bg-red-50 border-red-200"}`}>
              <div className="flex items-center gap-3">
                <div className={`h-10 w-10 rounded-full flex items-center justify-center text-white text-xl ${valResult.allowed ? "bg-green-600" : "bg-red-600"}`}>
                  {valResult.allowed ? "✓" : "✗"}
                </div>
                <div>
                  <p className={`font-bold text-lg ${valResult.allowed ? "text-green-800" : "text-red-800"}`}>
                    Issue {valResult.allowed ? "Allowed" : "BLOCKED"}
                  </p>
                  {valResult.requires_approval && (
                    <p className="text-sm text-amber-700 font-medium">⚠ Requires approval</p>
                  )}
                  {valResult.lot_status && (
                    <span className={`text-xs px-2 py-0.5 rounded ${SL_STATUS_BG[valResult.lot_status]}`}>
                      {valResult.lot_status}
                    </span>
                  )}
                </div>
                <div className="ml-auto text-right">
                  <p className="text-xs text-gray-500">Remaining</p>
                  <p className="text-2xl font-bold text-gray-800">{fmtDays(valResult.remaining_days)}</p>
                </div>
              </div>
              {valResult.errors.map((e, i) => <p key={i} className="text-sm text-red-700">✗ {e}</p>)}
              {valResult.warnings.map((w, i) => <p key={i} className="text-sm text-amber-700">⚠ {w}</p>)}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
