"use client";
import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useSearchParams } from "next/navigation";
import Link from "next/link";
import { faApi, fmtCurrency, DisposalMethod } from "@/lib/fixed_assets";

const DISPOSAL_METHODS: DisposalMethod[] = ["SALE","RETIREMENT","SCRAP","WRITEOFF"];

export default function FADisposalPage() {
  const params = useSearchParams();
  const preselected = params.get("asset_id") ?? "";
  const qc = useQueryClient();

  const [assetId,       setAssetId]       = useState(preselected);
  const [disposalDate,  setDisposalDate]  = useState(new Date().toISOString().slice(0, 10));
  const [method,        setMethod]        = useState<DisposalMethod>("SALE");
  const [proceeds,      setProceeds]      = useState("0");
  const [buyerName,     setBuyerName]     = useState("");
  const [reason,        setReason]        = useState("");
  const [confirmed,     setConfirmed]     = useState(false);
  const [done,          setDone]          = useState(false);

  const { data: asset } = useQuery({
    queryKey: ["fa-asset", assetId],
    queryFn: () => faApi.getAsset(assetId),
    enabled: !!assetId,
  });

  const { data: assets = [] } = useQuery({
    queryKey: ["fa-assets-active"],
    queryFn: () => faApi.listAssets({ status: "ACTIVE" }),
  });

  const dispose = useMutation({
    mutationFn: () => faApi.dispose(assetId, {
      disposal_date: disposalDate,
      disposal_method: method,
      sale_proceeds: Number(proceeds),
      buyer_name: buyerName || undefined,
      reason: reason || undefined,
    }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["fa-assets"] });
      setDone(true);
    },
  });

  const gainLoss = asset ? Number(proceeds) - asset.net_book_value : 0;

  if (done) return (
    <div className="p-6">
      <div className="liquid-glass p-6 max-w-lg mx-auto text-center space-y-4">
        <div className="text-4xl">✅</div>
        <h2 className="text-xl font-bold text-gray-900">Disposal Recorded</h2>
        <p className="text-gray-500 text-sm">Asset has been disposed and gain/loss entry created.</p>
        <Link href="/dashboard/fixed-assets/assets" className="glow-button inline-block">
          Back to Asset Register
        </Link>
      </div>
    </div>
  );

  return (
    <div className="p-6 space-y-5 max-w-xl">
      <h1 className="text-2xl font-bold text-gray-900">Asset Disposal / Retirement</h1>

      <div className="liquid-glass p-5 space-y-4">
        {/* Asset select */}
        <div className="flex flex-col gap-1">
          <label className="text-xs text-gray-500">Asset</label>
          <select
            value={assetId}
            onChange={(e) => { setAssetId(e.target.value); setConfirmed(false); }}
            className="rounded-lg border border-gray-300 px-3 py-2 text-sm"
          >
            <option value="">— Select asset —</option>
            {assets.map((a) => (
              <option key={a.id} value={a.id}>{a.asset_code} — {a.asset_name}</option>
            ))}
          </select>
        </div>

        {asset && (
          <div className="bg-blue-50 border border-blue-200 rounded-lg p-3 text-xs space-y-1">
            <p><span className="text-gray-500">Current NBV:</span> <strong className="text-green-600">{fmtCurrency(asset.net_book_value)}</strong></p>
            <p><span className="text-gray-500">Accumulated Depr.:</span> {fmtCurrency(asset.accumulated_depreciation)}</p>
          </div>
        )}

        <div className="grid grid-cols-2 gap-4">
          <div className="flex flex-col gap-1">
            <label className="text-xs text-gray-500">Disposal Date</label>
            <input type="date" value={disposalDate} onChange={(e) => setDisposalDate(e.target.value)}
              className="rounded-lg border border-gray-300 px-3 py-2 text-sm" />
          </div>
          <div className="flex flex-col gap-1">
            <label className="text-xs text-gray-500">Disposal Method</label>
            <select value={method} onChange={(e) => setMethod(e.target.value as DisposalMethod)}
              className="rounded-lg border border-gray-300 px-3 py-2 text-sm">
              {DISPOSAL_METHODS.map(m => <option key={m} value={m}>{m}</option>)}
            </select>
          </div>
        </div>

        {method === "SALE" && (
          <div className="grid grid-cols-2 gap-4">
            <div className="flex flex-col gap-1">
              <label className="text-xs text-gray-500">Sale Proceeds (KES)</label>
              <input type="number" value={proceeds} onChange={(e) => setProceeds(e.target.value)}
                className="rounded-lg border border-gray-300 px-3 py-2 text-sm" min="0" />
            </div>
            <div className="flex flex-col gap-1">
              <label className="text-xs text-gray-500">Buyer Name</label>
              <input type="text" value={buyerName} onChange={(e) => setBuyerName(e.target.value)}
                className="rounded-lg border border-gray-300 px-3 py-2 text-sm" />
            </div>
          </div>
        )}

        <div className="flex flex-col gap-1">
          <label className="text-xs text-gray-500">Reason</label>
          <textarea value={reason} onChange={(e) => setReason(e.target.value)}
            className="rounded-lg border border-gray-300 px-3 py-2 text-sm" rows={2} />
        </div>

        {asset && (
          <div className={`rounded-lg p-3 text-sm border ${gainLoss >= 0 ? "bg-green-50 border-green-200 text-green-700" : "bg-red-50 border-red-200 text-red-700"}`}>
            <span className="font-semibold">{gainLoss >= 0 ? "Gain on Disposal:" : "Loss on Disposal:"}</span>{" "}
            {fmtCurrency(Math.abs(gainLoss))}
          </div>
        )}

        <label className="flex items-center gap-2 cursor-pointer select-none">
          <input type="checkbox" checked={confirmed} onChange={(e) => setConfirmed(e.target.checked)} className="rounded" />
          <span className="text-sm text-gray-700">I confirm this disposal is approved and irreversible</span>
        </label>

        <button
          onClick={() => dispose.mutate()}
          disabled={!assetId || !confirmed || dispose.isPending}
          className="glow-button w-full"
        >
          {dispose.isPending ? "Processing…" : "Record Disposal"}
        </button>
      </div>
    </div>
  );
}
