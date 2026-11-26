"use client";
// Van sales offline outbox: shows what this device still has to send for the van, and sends it via /sync.
import { useCallback, useEffect, useState } from "react";
import { vanSalesApi, readOutbox, writeOutbox, type Outbox } from "@/lib/van_sales";
import { tx } from "@/lib/i18n/core";

export function VanOutbox({ vanId, version = 0 }: { vanId: string; version?: number }) {
  const [ob, setOb] = useState<Outbox>({ transactions: [], payments: [] });
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState<{ ok: boolean; text: string } | null>(null);
  const reload = useCallback(() => setOb(readOutbox(vanId)), [vanId]);
  useEffect(() => { reload(); window.addEventListener("online", reload); return () => window.removeEventListener("online", reload); }, [reload, version]);

  const pending = ob.transactions.length + ob.payments.length;
  if (!vanId || (pending === 0 && !msg)) return null;

  async function sync() {
    setBusy(true); setMsg(null);
    try {
      const r = await vanSalesApi.sync(vanId, { ...ob, device_id: navigator.userAgent.slice(0, 100) });
      if (r.errors.length === 0) {
        writeOutbox(vanId, { transactions: [], payments: [] });
        setMsg({ ok: true, text: `Synced: ${r.txns_created} sale(s), ${r.payments_created} payment(s)${r.duplicates_skipped ? `, ${r.duplicates_skipped} already on the server` : ""}.` });
      } else {
        // keep everything: a resend is safe (sales are matched by offline_id), and nothing is lost
        setMsg({ ok: false, text: `Sync finished with problems — kept on this device: ${r.errors.join("; ")}` });
      }
    } catch (e) {
      setMsg({ ok: false, text: `Not synced (${(e as Error).message}). Everything is still kept on this device.` });
    } finally { setBusy(false); reload(); }
  }

  return (
    <div className="rounded-lg border border-amber-500/30 bg-amber-500/10 p-3 text-sm space-y-2" role="region" aria-label={tx("Offline outbox")}>
      {pending > 0 && <div className="flex items-center justify-between gap-2">
        <span className="text-amber-200">{ob.transactions.length} {tx("sale(s) and")} {ob.payments.length} {tx("payment(s) saved on this device, not yet sent.")}</span>
        <button onClick={sync} disabled={busy || (typeof navigator !== "undefined" && !navigator.onLine)}
          title={typeof navigator !== "undefined" && !navigator.onLine ? tx("You are offline") : undefined}
          className="px-3 py-1.5 rounded-lg bg-amber-600 hover:bg-amber-500 text-white text-xs font-medium disabled:opacity-50">{busy ? tx("Syncing…") : tx("Sync now")}</button>
      </div>}
      {msg && <p role={msg.ok ? "status" : "alert"} className={msg.ok ? "text-emerald-300" : "text-red-300"}>{msg.text}</p>}
    </div>
  );
}
