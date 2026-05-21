"use client";
import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useSearchParams } from "next/navigation";
import Link from "next/link";
import { faApi } from "@/lib/fixed_assets";

export default function FATransferPage() {
  const params = useSearchParams();
  const qc = useQueryClient();
  const [assetId,      setAssetId]      = useState(params.get("asset_id") ?? "");
  const [effectiveDate,setEffectiveDate]= useState(new Date().toISOString().slice(0, 10));
  const [location,     setLocation]     = useState("");
  const [plant,        setPlant]        = useState("");
  const [department,   setDepartment]   = useState("");
  const [costCenter,   setCostCenter]   = useState("");
  const [reason,       setReason]       = useState("");
  const [done,         setDone]         = useState(false);

  const { data: assets = [] } = useQuery({
    queryKey: ["fa-assets-active"],
    queryFn: () => faApi.listAssets({ status: "ACTIVE" }),
  });
  const { data: asset } = useQuery({
    queryKey: ["fa-asset", assetId],
    queryFn: () => faApi.getAsset(assetId),
    enabled: !!assetId,
  });

  const transfer = useMutation({
    mutationFn: () => faApi.transfer(assetId, {
      effective_date: effectiveDate,
      new_location: location || undefined,
      new_plant: plant || undefined,
      new_department: department || undefined,
      new_cost_center: costCenter || undefined,
      reason: reason || undefined,
    }),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["fa-asset", assetId] }); setDone(true); },
  });

  if (done) return (
    <div className="p-6">
      <div className="liquid-glass p-6 max-w-md mx-auto text-center space-y-4">
        <div className="text-4xl">✅</div>
        <h2 className="text-xl font-bold text-gray-900">Transfer Recorded</h2>
        <Link href="/dashboard/fixed-assets/assets" className="glow-button inline-block">Back to Assets</Link>
      </div>
    </div>
  );

  return (
    <div className="p-6 space-y-5 max-w-xl">
      <h1 className="text-2xl font-bold text-gray-900">Asset Transfer</h1>

      <div className="liquid-glass p-5 space-y-4">
        <div className="flex flex-col gap-1">
          <label className="text-xs text-gray-500">Asset</label>
          <select value={assetId} onChange={(e) => setAssetId(e.target.value)}
            className="rounded-lg border border-gray-300 px-3 py-2 text-sm">
            <option value="">— Select asset —</option>
            {assets.map((a) => <option key={a.id} value={a.id}>{a.asset_code} — {a.asset_name}</option>)}
          </select>
        </div>

        {asset && (
          <div className="bg-blue-50 border border-blue-200 rounded-lg p-3 text-xs space-y-1">
            <p><span className="text-gray-500">Current Location:</span> {asset.location ?? "—"}</p>
            <p><span className="text-gray-500">Cost Center:</span> {asset.cost_center ?? "—"}</p>
            <p><span className="text-gray-500">Department:</span> {asset.department ?? "—"}</p>
          </div>
        )}

        <div className="flex flex-col gap-1">
          <label className="text-xs text-gray-500">Effective Date</label>
          <input type="date" value={effectiveDate} onChange={(e) => setEffectiveDate(e.target.value)}
            className="rounded-lg border border-gray-300 px-3 py-2 text-sm" />
        </div>

        <div className="grid grid-cols-2 gap-4">
          {[
            ["New Location", location, setLocation],
            ["New Plant", plant, setPlant],
            ["New Department", department, setDepartment],
            ["New Cost Center", costCenter, setCostCenter],
          ].map(([label, val, setter]) => (
            <div key={label as string} className="flex flex-col gap-1">
              <label className="text-xs text-gray-500">{label as string}</label>
              <input type="text" value={val as string} onChange={(e) => (setter as any)(e.target.value)}
                className="rounded-lg border border-gray-300 px-3 py-2 text-sm" />
            </div>
          ))}
        </div>

        <div className="flex flex-col gap-1">
          <label className="text-xs text-gray-500">Reason</label>
          <textarea value={reason} onChange={(e) => setReason(e.target.value)}
            className="rounded-lg border border-gray-300 px-3 py-2 text-sm" rows={2} />
        </div>

        <button
          onClick={() => transfer.mutate()}
          disabled={!assetId || transfer.isPending}
          className="glow-button w-full"
        >
          {transfer.isPending ? "Recording…" : "Record Transfer"}
        </button>
      </div>
    </div>
  );
}
