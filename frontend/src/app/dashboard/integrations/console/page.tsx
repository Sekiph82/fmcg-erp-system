"use client";
// Integration console (M36.S05.T003): evidence-based health per connector — never a fake "synced".
import { useCallback, useEffect, useState } from "react";
import { apiClient } from "@/lib/api";
import { tx } from "@/lib/i18n/core";

interface Row {
  provider: string; label: string; capability: string; health: string; credentials: "SET" | "NOT_SET" | null;
  last_success_at: string | null; last_failure_at: string | null; last_error: string | null;
  consecutive_failures: number; next_retry_at: string | null; can_sync: boolean; screen: string | null; notes: string;
}
interface Console { connectors: Row[]; mappings: Record<string, Record<string, unknown>>; generated_at: string }

const HEALTH: Record<string, [string, string]> = {
  HEALTHY: ["Working", "bg-emerald-100 text-emerald-800"],
  FAILING: ["Failing", "bg-red-100 text-red-700"],
  NO_DATA: ["No runs yet", "bg-gray-100 text-gray-700"],
  NOT_CONNECTED: ["Not connected", "bg-amber-100 text-amber-800"],
  STUB_ONLY: ["Not available", "bg-gray-100 text-gray-500"],
  SIMULATED: ["Simulation only", "bg-blue-50 text-blue-700"],
};
const when = (v: string | null) => (v ? new Date(v).toLocaleString() : "—");

export default function IntegrationConsolePage() {
  const [data, setData] = useState<Console | null>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const [msg, setMsg] = useState<{ ok: boolean; text: string } | null>(null);

  const load = useCallback(async () => {
    try { setData((await apiClient.get<Console>("/api/v1/integrations/console")).data); }
    catch { setMsg({ ok: false, text: tx("Could not load the integration console.") }); }
  }, []);
  useEffect(() => { load(); }, [load]);

  const sync = async (r: Row) => {
    setBusy(r.provider); setMsg(null);
    try {
      const res = (await apiClient.post(`/api/v1/integrations/console/${r.provider}/sync`)).data as { status: string; result: Record<string, number>; error: string | null };
      const detail = Object.entries(res.result ?? {}).map(([k, v]) => `${k} ${v}`).join(", ");
      setMsg({ ok: res.status === "SUCCESS", text: res.status === "SUCCESS" ? `${r.label}: done${detail ? ` (${detail})` : ""}.` : `${r.label} failed: ${res.error ?? "see the log"}` });
    } catch (e: unknown) {
      const d = (e as { response?: { data?: { detail?: unknown; retry_at?: string } } })?.response?.data;
      const text = typeof d?.detail === "string" ? d.detail : (d?.detail as { detail?: string })?.detail ?? "Sync was refused.";
      setMsg({ ok: false, text: d?.retry_at ? `${text} Next try after ${when(d.retry_at)}.` : text });
    } finally { setBusy(null); await load(); }
  };

  const m = data?.mappings;
  const tally = (o?: Record<string, unknown>) => o && Object.keys(o).length ? Object.entries(o).map(([k, v]) => `${k} ${v}`).join(" · ") : "none";
  return (
    <div className="space-y-4">
      <div>
        <h2 className="text-lg font-semibold text-gray-900">{tx("Integration console")}</h2>
        <p className="text-xs text-gray-500">{tx("Health comes only from recorded runs. Secrets are never shown — only whether they are set.")}</p>
      </div>
      {msg && <p role="status" className={`text-sm rounded px-3 py-2 ${msg.ok ? "bg-emerald-50 text-emerald-800" : "bg-red-50 text-red-700"}`}>{msg.text}</p>}
      {!data ? <p className="text-sm text-gray-500">{tx("Loading…")}</p> : (
        <>
          <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
            {data.connectors.map((r) => {
              const [label, cls] = HEALTH[r.health] ?? [r.health, "bg-gray-100 text-gray-700"];
              return (
                <div key={r.provider} className="bg-white border rounded-xl p-4 space-y-2" data-testid={`connector-${r.provider}`}>
                  <div className="flex items-start justify-between gap-2">
                    <p className="font-medium text-gray-900 text-sm">{r.label}</p>
                    <span className={`shrink-0 text-xs rounded-full px-2 py-0.5 ${cls}`}>{label}</span>
                  </div>
                  <dl className="text-xs text-gray-600 grid grid-cols-2 gap-x-2 gap-y-1">
                    <dt>{tx("Credentials")}</dt><dd>{r.credentials === null ? tx("not needed") : r.credentials === "SET" ? tx("set") : tx("not set")}</dd>
                    <dt>{tx("Last success")}</dt><dd>{when(r.last_success_at)}</dd>
                    {r.consecutive_failures > 0 && <><dt>{tx("Failures in a row")}</dt><dd>{r.consecutive_failures}</dd></>}
                    {r.next_retry_at && <><dt>{tx("Next retry")}</dt><dd>{when(r.next_retry_at)}</dd></>}
                  </dl>
                  {r.last_error && <p className="text-xs text-red-700 break-words">{r.last_error}</p>}
                  <div className="flex flex-wrap gap-2 pt-1">
                    {r.can_sync && (
                      <button onClick={() => sync(r)} disabled={busy !== null || !!r.next_retry_at}
                        className="text-xs rounded bg-blue-600 text-white px-3 py-1.5 disabled:opacity-50">
                        {busy === r.provider ? tx("Syncing…") : tx("Sync now")}
                      </button>
                    )}
                    {r.screen && <a href={r.screen} className="text-xs rounded border px-3 py-1.5 text-gray-700">{tx("Open")}</a>}
                  </div>
                </div>
              );
            })}
          </div>
          <div className="bg-white border rounded-xl p-4 text-xs text-gray-700 space-y-1">
            <p className="font-semibold text-gray-900 text-sm mb-1">{tx("Mapping health")}</p>
            <p>{tx("Shop orders:")} {tally(m?.ecommerce_orders)}</p>
            <p>{tx("Shop products:")} {tally(m?.ecommerce_products)}</p>
            <p>{tx("External CRM customers:")} {tally(m?.crm_customers)}</p>
            <p>{tx("Mailboxes:")} {String(m?.mailboxes?.connected ?? 0)} {tx("connected,")} {String(m?.mailboxes?.with_errors ?? 0)} {tx("with errors")}</p>
            <p>{tx("Webhook deliveries:")} {tally(m?.webhooks?.by_status as Record<string, unknown>)}</p>
          </div>
        </>
      )}
    </div>
  );
}
