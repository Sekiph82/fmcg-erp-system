"use client";

import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { ScanInput } from "@/components/ScanInput";
import { describeShopFloorError, sfApi, type BarcodeResolution, type SFOperationMaterial } from "@/lib/shopFloor";

/**
 * M37.S04: scan a prepared-lot label, warehouse lot label, supplier GS1 label or material code,
 * see what it is, confirm, and record consumption. The server re-validates every scan and logs
 * it (accepted or rejected) with server time, device time, session, machine and line.
 */
export function MaterialScanPanel({
  woId, sessionId, materials, disabled,
}: { woId: string; sessionId: string; materials: SFOperationMaterial[]; disabled?: boolean }) {
  const qc = useQueryClient();
  const [scan, setScan] = useState<{ code: string; at: string; info: BarcodeResolution } | null>(null);
  const [qty, setQty] = useState("");
  const [message, setMessage] = useState<{ ok: boolean; text: string } | null>(null);

  const line = scan ? materials.find((m) => m.item_id && m.item_id === scan.info.data.material_id) : undefined;
  const isPrepared = scan?.info.type === "PREPARED_LOT";
  const labelQty = scan?.info.data.quantity ?? null;

  const resolve = useMutation({
    mutationFn: ({ code }: { code: string; at: string }) => sfApi.resolveBarcode(code),
    onSuccess: (info, { code, at }) => {
      setScan({ code, at, info });
      setQty(info.type !== "PREPARED_LOT" && info.data.quantity ? String(info.data.quantity) : "");
      setMessage(null);
    },
    onError: (error) => { setScan(null); setMessage({ ok: false, text: describeShopFloorError(error).message }); },
  });

  const consume = useMutation({
    mutationFn: () => sfApi.scanConsume(woId, {
      session_id: sessionId,
      code: scan!.code,
      qty: isPrepared ? undefined : Number(qty),
      client_scanned_at: scan!.at,
    }),
    onSuccess: (material) => {
      setMessage({ ok: true, text: `${material.item_name ?? "Material"}: ${isPrepared ? labelQty : qty} ${material.uom} recorded.` });
      setScan(null);
      setQty("");
      qc.invalidateQueries({ queryKey: ["sf-work-order-materials", woId] });
      qc.invalidateQueries({ queryKey: ["sf-activity", woId] });
    },
    onError: (error) => {
      setMessage({ ok: false, text: describeShopFloorError(error).message });
      setScan(null);
      qc.invalidateQueries({ queryKey: ["sf-activity", woId] });
    },
  });

  const qtyOk = isPrepared || (Number(qty) > 0 && Number.isFinite(Number(qty)));
  const d = scan?.info.data;

  return (
    <section className="rounded-xl border-2 border-indigo-200 bg-indigo-50/40 p-3 space-y-3" aria-label="Scan material">
      <ScanInput
        id="material-scan-input"
        label="Scan material label (prepared lot, lot, GS1 or material code)"
        disabled={disabled || resolve.isPending || consume.isPending}
        onScan={(code, at) => resolve.mutate({ code, at })}
      />
      {message && (
        <p role={message.ok ? "status" : "alert"} data-testid="material-scan-message"
           className={`rounded-lg px-3 py-2 text-sm ${message.ok ? "bg-green-50 text-green-900" : "bg-red-50 text-red-800"}`}>
          {message.text}
        </p>
      )}
      {scan && d && (
        <div className="rounded-lg border border-gray-200 bg-white p-3 space-y-2" data-testid="material-scan-preview">
          <p className="text-xs uppercase tracking-wide text-gray-500">{scan.info.type.replace("_", " ")} · {scan.code}</p>
          <p className="font-semibold text-gray-900">{d.material_name ?? "Unknown material"} <span className="text-gray-500 font-normal">{d.material_code}</span></p>
          <p className="text-sm text-gray-700">
            Lot {d.lot_number ?? "—"}{d.expiry_date ? ` · expires ${d.expiry_date}` : ""}
            {isPrepared && labelQty ? ` · label ${labelQty} ${d.uom ?? ""}` : ""}
          </p>
          {!line && <p className="text-sm text-red-700" role="alert">Not in this operation&apos;s recipe. Confirming will be refused and logged.</p>}
          {(d.is_quarantine || d.is_expired || d.consumed) && (
            <p className="text-sm text-red-700" role="alert">
              {d.consumed ? "This prepared lot was already consumed." : d.is_quarantine ? "Lot is in quarantine." : "Lot is expired."}
            </p>
          )}
          {!isPrepared && (
            <div>
              <label htmlFor="material-scan-qty" className="text-xs text-gray-600">Quantity ({line?.uom ?? d.uom ?? ""})</label>
              <input id="material-scan-qty" type="number" inputMode="decimal" min="0" step="any" value={qty}
                     onChange={(e) => setQty(e.target.value)}
                     className="w-full min-h-11 rounded-lg border border-gray-300 px-2 text-base" />
            </div>
          )}
          <div className="flex gap-2">
            <button type="button" onClick={() => consume.mutate()} disabled={!qtyOk || consume.isPending || disabled}
                    data-testid="material-scan-confirm"
                    className="min-h-12 flex-1 rounded-lg bg-indigo-700 font-semibold text-white disabled:opacity-40">
              {consume.isPending ? "RECORDING…" : "Confirm consumption"}
            </button>
            <button type="button" onClick={() => setScan(null)} className="min-h-12 rounded-lg border border-gray-300 px-4">Cancel</button>
          </div>
        </div>
      )}
    </section>
  );
}
