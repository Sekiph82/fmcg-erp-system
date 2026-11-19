"use client";

import { useState } from "react";
import Link from "next/link";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ScanInput } from "@/components/ScanInput";
import {
  describeShopFloorError, sfApi, type BarcodeResolution, type DispensingOrder, type PreparedLotLabel,
} from "@/lib/shopFloor";

type Line = DispensingOrder["materials"][number];

function printLabel(label: PreparedLotLabel) {
  const w = window.open("", "_blank", "width=420,height=600");
  if (!w) return;
  const esc = (v: unknown) => String(v ?? "").replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]!));
  w.document.write(`<!doctype html><html><head><title>${esc(label.prepared_lot_no)}</title>
<style>body{font-family:system-ui,sans-serif;margin:8mm}h1{font-size:18px;margin:0}p{margin:2px 0;font-size:13px}
.codes{display:flex;gap:8px;align-items:center;margin-top:6px}.codes img{max-width:100%}</style></head><body>
<h1>${esc(label.material_name)}</h1><p>${esc(label.material_code)}</p>
<p><b>Lot:</b> ${esc(label.lot_number)} ${label.expiry_date ? `· <b>Exp:</b> ${esc(label.expiry_date)}` : ""}</p>
<p><b>Qty:</b> ${esc(label.quantity)} ${esc(label.uom)} · <b>Weighed:</b> ${esc(label.weighed_at?.slice(0, 16).replace("T", " "))}</p>
<div class="codes">
${label.code128_svg_b64 ? `<img alt="barcode" src="data:image/svg+xml;base64,${label.code128_svg_b64}" style="height:70px">` : ""}
${label.qr_png_b64 ? `<img alt="QR" src="data:image/png;base64,${label.qr_png_b64}" style="height:90px">` : ""}
</div><p style="font-family:monospace;font-size:14px">${esc(label.prepared_lot_no)}</p>
<script>window.onload=()=>{window.print()}</script></body></html>`);
  w.document.close();
}

function DispenseForm({ line, onDone }: { line: Line; onDone: (label: PreparedLotLabel) => void }) {
  const remaining = Math.max(Number(line.required_qty) - Number(line.issued_qty), 0);
  const [source, setSource] = useState<BarcodeResolution | null>(null);
  const [target, setTarget] = useState(""); // bag/batch target; empty = no tolerance check
  const [actual, setActual] = useState("");
  const [tolerance, setTolerance] = useState("2");
  const [error, setError] = useState("");

  const resolve = useMutation({
    mutationFn: (code: string) => sfApi.resolveBarcode(code),
    onSuccess: (info) => {
      setError("");
      if (info.data.material_id !== line.item_id) {
        setSource(null);
        setError(`Scanned ${info.data.material_name ?? info.type} — this line needs ${line.item_name}.`);
      } else setSource(info);
    },
    onError: (e) => { setSource(null); setError(describeShopFloorError(e).message); },
  });
  const dispense = useMutation({
    mutationFn: () => sfApi.dispense({
      exec_material_id: line.id,
      source_lot_code: source!.code,
      actual_quantity: Number(actual),
      target_quantity: target ? Number(target) : undefined,
      tolerance_pct: target && tolerance ? Number(tolerance) : undefined,
    }),
    onSuccess: (label) => { setSource(null); setActual(""); onDone(label); },
    onError: (e) => setError(describeShopFloorError(e).message),
  });

  return (
    <div className="mt-2 space-y-2 rounded-lg border border-gray-200 bg-gray-50 p-3">
      <ScanInput id={`source-lot-${line.id}`} label="1. Scan warehouse source lot" onScan={(code) => resolve.mutate(code)} disabled={resolve.isPending} />
      {source && (
        <p className="text-sm text-gray-800" data-testid="dispense-source">
          ✓ {source.data.material_name} · lot <b>{source.data.lot_number}</b>
          {source.data.expiry_date ? ` · exp ${source.data.expiry_date}` : ""}
          {source.data.is_quarantine ? " · QUARANTINE" : ""}{source.data.is_expired ? " · EXPIRED" : ""}
        </p>
      )}
      <div className="grid grid-cols-3 gap-2">
        <label className="text-xs text-gray-600">Target ({line.uom})
          <input type="number" inputMode="decimal" value={target} placeholder={remaining ? `≤ ${remaining}` : ""} onChange={(e) => setTarget(e.target.value)} className="w-full min-h-11 rounded-lg border px-2 text-base" />
        </label>
        <label className="text-xs text-gray-600">2. Weighed ({line.uom})
          <input type="number" inputMode="decimal" value={actual} onChange={(e) => setActual(e.target.value)} className="w-full min-h-11 rounded-lg border px-2 text-base" data-testid={`dispense-actual-${line.id}`} />
        </label>
        <label className="text-xs text-gray-600">Tolerance %
          <input type="number" inputMode="decimal" value={tolerance} onChange={(e) => setTolerance(e.target.value)} className="w-full min-h-11 rounded-lg border px-2 text-base" />
        </label>
      </div>
      {error && <p role="alert" className="text-sm text-red-700">{error}</p>}
      <button type="button" onClick={() => dispense.mutate()} disabled={!source || !(Number(actual) > 0) || dispense.isPending}
              className="min-h-12 w-full rounded-lg bg-indigo-700 font-semibold text-white disabled:opacity-40">
        {dispense.isPending ? "Issuing…" : "3. Issue to order & print label"}
      </button>
    </div>
  );
}

export default function DispensingPage() {
  const qc = useQueryClient();
  const [openLine, setOpenLine] = useState<string | null>(null);
  const [lastLabel, setLastLabel] = useState<PreparedLotLabel | null>(null);
  const orders = useQuery({ queryKey: ["sf-dispensing-orders"], queryFn: sfApi.dispensingOrders, refetchInterval: 30_000 });

  const reprint = async (no: string) => printLabel(await sfApi.preparedLotLabel(no));

  return (
    <div className="mx-auto max-w-3xl space-y-4 px-4 pb-10">
      <Link href="/dashboard/shop-floor" className="text-sm text-indigo-700">← Shop Floor</Link>
      <div>
        <h1 className="text-xl font-bold text-gray-900">Material Dispensing</h1>
        <p className="text-sm text-gray-600">Weigh raw material from a warehouse lot, issue it to the order and print the label the operator scans at the machine.</p>
      </div>
      {lastLabel && (
        <div role="status" className="rounded-lg border border-green-200 bg-green-50 p-3 text-sm text-green-900">
          Prepared lot <b className="font-mono">{lastLabel.prepared_lot_no}</b> issued: {lastLabel.material_name}, lot {lastLabel.lot_number}, {lastLabel.quantity} {lastLabel.uom}.{" "}
          <button type="button" className="underline" onClick={() => printLabel(lastLabel)}>Print again</button>
        </div>
      )}
      {orders.isLoading ? <p className="text-sm text-gray-600">Loading orders…</p>
        : orders.isError ? <p role="alert" className="rounded-lg bg-red-50 p-3 text-sm text-red-800">{describeShopFloorError(orders.error).message}</p>
        : !orders.data?.length ? <p className="rounded-lg bg-gray-50 p-3 text-sm text-gray-700">No released or in-progress orders with raw materials assigned to operations.</p>
        : orders.data.map((order) => (
          <section key={order.id} className="rounded-xl border border-gray-200 bg-white p-3 space-y-2">
            <h2 className="font-semibold text-gray-900">{order.order_no} · {order.product_name ?? "—"} <span className="text-xs text-gray-500">{order.status}</span></h2>
            {order.materials.map((line) => (
              <article key={line.id} className="border-t border-gray-100 pt-2">
                <div className="flex flex-wrap items-baseline justify-between gap-2">
                  <p className="font-medium text-gray-900">{line.item_name} <span className="text-xs text-gray-500">{line.item_code} · {line.operation}</span></p>
                  <button type="button" onClick={() => setOpenLine(openLine === line.id ? null : line.id)}
                          className="min-h-11 rounded-lg border border-indigo-300 px-3 text-sm font-semibold text-indigo-800">
                    {openLine === line.id ? "Close" : "Dispense"}
                  </button>
                </div>
                <p className="text-sm text-gray-700">Required {line.required_qty} · Issued {line.issued_qty} · Consumed {line.consumed_qty} {line.uom}</p>
                {line.prepared_lots.length > 0 && (
                  <ul className="mt-1 space-y-1 text-xs text-gray-700">
                    {line.prepared_lots.map((pl) => (
                      <li key={pl.prepared_lot_no} className="flex flex-wrap items-center gap-2">
                        <span className="font-mono">{pl.prepared_lot_no}</span> · lot {pl.lot_no} · {pl.qty} {line.uom}
                        · {pl.dispensed_at?.slice(0, 16).replace("T", " ")}
                        <span className={pl.consumed ? "text-green-700" : "text-amber-700"}>{pl.consumed ? "consumed" : "at machine"}</span>
                        <button type="button" className="underline" onClick={() => void reprint(pl.prepared_lot_no)}>label</button>
                      </li>
                    ))}
                  </ul>
                )}
                {openLine === line.id && (
                  <DispenseForm line={line} onDone={(label) => {
                    setLastLabel(label);
                    printLabel(label);
                    qc.invalidateQueries({ queryKey: ["sf-dispensing-orders"] });
                  }} />
                )}
              </article>
            ))}
          </section>
        ))}
    </div>
  );
}
