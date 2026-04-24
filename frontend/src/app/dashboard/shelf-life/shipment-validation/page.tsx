"use client";
import { useState } from "react";
import { shelfLifeApi, FEFOValidateShipmentResponse } from "@/lib/shelfLife";

export default function ShipmentValidationPage() {
  const [lotId, setLotId] = useState("");
  const [qty, setQty] = useState("");
  const [customerId, setCustomerId] = useState("");
  const [productId, setProductId] = useState("");
  const [result, setResult] = useState<FEFOValidateShipmentResponse | null>(null);
  const [loading, setLoading] = useState(false);

  const validate = async () => {
    if (!lotId) return;
    setLoading(true);
    setResult(null);
    try {
      const r = await shelfLifeApi.validateShipment({
        lot_id: lotId,
        quantity: parseFloat(qty) || 0,
        customer_id: customerId || undefined,
        product_id: productId || undefined,
      });
      setResult(r);
    } catch (e: any) {
      alert(`Error: ${e.message}`);
    } finally { setLoading(false); }
  };

  return (
    <div className="p-6 space-y-6">
      <div>
        <h1 className="text-xl font-bold text-gray-900">Shipment Shelf-Life Validation</h1>
        <p className="text-sm text-gray-500">Validate a lot before shipment — checks expiry, customer rules, min remaining shelf life</p>
      </div>

      <div className="bg-white rounded-xl border border-gray-200 p-6 space-y-4 max-w-2xl">
        <h2 className="font-semibold text-gray-800">Validate Lot for Shipment</h2>

        <div className="grid grid-cols-2 gap-4">
          <div className="col-span-2">
            <label className="text-xs font-medium text-gray-600">Lot ID *</label>
            <input className="mt-1 w-full border rounded-lg px-3 py-2 text-sm"
              placeholder="UUID of lot" value={lotId} onChange={e => setLotId(e.target.value)} />
          </div>
          <div>
            <label className="text-xs font-medium text-gray-600">Quantity</label>
            <input type="number" className="mt-1 w-full border rounded-lg px-3 py-2 text-sm"
              value={qty} onChange={e => setQty(e.target.value)} />
          </div>
          <div>
            <label className="text-xs font-medium text-gray-600">Product ID</label>
            <input className="mt-1 w-full border rounded-lg px-3 py-2 text-sm"
              placeholder="Optional UUID" value={productId} onChange={e => setProductId(e.target.value)} />
          </div>
          <div className="col-span-2">
            <label className="text-xs font-medium text-gray-600">Customer ID (for customer-specific rules)</label>
            <input className="mt-1 w-full border rounded-lg px-3 py-2 text-sm"
              placeholder="Optional UUID" value={customerId} onChange={e => setCustomerId(e.target.value)} />
          </div>
        </div>

        <button onClick={validate} disabled={!lotId || loading}
          className="w-full py-2 text-sm bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:opacity-50 font-medium">
          {loading ? "Validating…" : "Validate for Shipment"}
        </button>

        {result && (
          <div className={`rounded-xl border p-5 space-y-3 ${result.allowed ? "bg-green-50 border-green-200" : "bg-red-50 border-red-200"}`}>
            <div className="flex items-center gap-3">
              <div className={`h-10 w-10 rounded-full flex items-center justify-center text-white text-xl ${result.allowed ? "bg-green-600" : "bg-red-600"}`}>
                {result.allowed ? "✓" : "✗"}
              </div>
              <div>
                <p className={`font-bold text-lg ${result.allowed ? "text-green-800" : "text-red-800"}`}>
                  Shipment {result.allowed ? "Approved" : "BLOCKED"}
                </p>
                {result.requires_approval && (
                  <p className="text-sm text-amber-700 font-medium">⚠ Requires supervisor approval</p>
                )}
              </div>
            </div>

            <div className="grid grid-cols-3 gap-3 text-sm">
              <div className="bg-white/60 rounded-lg p-3 text-center">
                <p className="text-xs text-gray-500">Remaining Days</p>
                <p className="text-xl font-bold text-gray-800">{result.remaining_days ?? "—"}</p>
              </div>
              <div className="bg-white/60 rounded-lg p-3 text-center">
                <p className="text-xs text-gray-500">% Shelf Life</p>
                <p className="text-xl font-bold text-gray-800">
                  {result.pct_remaining ? `${parseFloat(result.pct_remaining).toFixed(1)}%` : "—"}
                </p>
              </div>
              <div className="bg-white/60 rounded-lg p-3 text-center">
                <p className="text-xs text-gray-500">Customer Minimum</p>
                <p className="text-xl font-bold text-gray-800">{result.customer_min_days ? `${result.customer_min_days}d` : "—"}</p>
              </div>
            </div>

            {result.errors.length > 0 && (
              <div className="space-y-1">
                <p className="text-xs font-semibold text-red-700 uppercase">Errors</p>
                {result.errors.map((e, i) => (
                  <div key={i} className="flex items-start gap-2 text-sm text-red-700">
                    <span className="mt-0.5">✗</span><span>{e}</span>
                  </div>
                ))}
              </div>
            )}
            {result.warnings.length > 0 && (
              <div className="space-y-1">
                <p className="text-xs font-semibold text-amber-700 uppercase">Warnings</p>
                {result.warnings.map((w, i) => (
                  <div key={i} className="flex items-start gap-2 text-sm text-amber-700">
                    <span className="mt-0.5">⚠</span><span>{w}</span>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </div>

      {/* Info Box */}
      <div className="bg-blue-50 border border-blue-200 rounded-xl p-4 max-w-2xl">
        <p className="text-sm font-semibold text-blue-800 mb-2">What this validation checks:</p>
        <ul className="text-xs text-blue-700 space-y-1">
          <li>• Lot expiry date vs today</li>
          <li>• Item-level minimum remaining shelf life for shipment</li>
          <li>• Customer-specific minimum remaining days or % rules</li>
          <li>• Explicit shipment block flags on the lot profile</li>
          <li>• Near-expiry shipment policy (block / warn / approval required)</li>
        </ul>
      </div>
    </div>
  );
}
