"use client";

// M43.S01.T001–T004: the signed-in user's own Google / Microsoft mailbox and calendar connections (delegated OAuth).
// "Waiting for setup" until an administrator enters the OAuth app keys (Integrations → Provider keys); a connection
// is shown as connected only after the provider actually issued tokens.
import { useEffect, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiClient } from "@/lib/api";
import { tx, lx } from "@/lib/i18n/core";

interface Provider { provider: "google" | "microsoft"; purposes: string[]; configured: boolean }
interface Connection {
  id: string; provider: string; purpose: string; status: string; account_email: string | null;
  last_error: string | null; last_sync_at: string | null;
}

const LABEL: Record<string, string> = { google: "Google", microsoft: "Microsoft 365" };
const PURPOSE: Record<string, string> = { mail: "Mail", calendar: "Calendar" };
const REASON: Record<string, string> = lx(() => ({
  consent_refused: tx("Permission was not given at the provider; nothing was connected."),
  scope_missing: tx("Not every requested permission was allowed; connect again and allow all of them."),
  state_expired: tx("The sign-in took too long; start again."),
  bad_state: tx("That sign-in link was already used; start again."),
  not_configured: tx("This provider is not set up yet."),
}));

export function ConnectedAccounts({ purposes }: { purposes: ("mail" | "calendar")[] }) {
  const qc = useQueryClient();
  const [notice, setNotice] = useState<{ ok: boolean; text: string } | null>(null);
  const { data: providers = [] } = useQuery<Provider[]>({
    queryKey: ["oauth-providers"],
    queryFn: async () => (await apiClient.get("/api/v1/integrations/oauth/providers")).data,
  });
  const { data: conns = [] } = useQuery<Connection[]>({
    queryKey: ["oauth-connections"],
    queryFn: async () => (await apiClient.get("/api/v1/integrations/oauth/connections")).data,
  });

  useEffect(() => {   // result of the provider round trip (?oauth=connected|error&reason=…)
    const q = new URLSearchParams(window.location.search);
    if (q.get("oauth") === "connected") setNotice({ ok: true, text: tx("{LABEL} {PURPOSE} connected.", { LABEL: LABEL[q.get("provider") ?? ""] ?? "Account", PURPOSE: PURPOSE[q.get("purpose") ?? ""] ?? "" }) });
    if (q.get("oauth") === "error") setNotice({ ok: false, text: REASON[q.get("reason") ?? ""] ?? tx("The connection failed; nothing was connected.") });
  }, []);

  const start = useMutation({
    mutationFn: async ({ provider, purpose }: { provider: string; purpose: string }) =>
      (await apiClient.post(`/api/v1/integrations/oauth/${provider}/${purpose}/start`)).data as { authorize_url: string },
    onSuccess: (d) => { window.location.assign(d.authorize_url); },
    onError: () => setNotice({ ok: false, text: tx("Could not start the connection.") }),
  });
  const disconnect = useMutation({
    mutationFn: async (id: string) => apiClient.delete(`/api/v1/integrations/oauth/connections/${id}`),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["oauth-connections"] }); qc.invalidateQueries({ queryKey: ["email-accounts"] }); },
  });

  return (
    <div className="border rounded-lg bg-white p-3 space-y-2">
      <div className="text-sm font-semibold text-gray-800">{tx("Connected accounts")}</div>
      {notice && (
        <div className={`text-xs rounded px-2 py-1 ${notice.ok ? "bg-green-50 text-green-700" : "bg-red-50 text-red-700"}`}>{notice.text}</div>
      )}
      <div className="grid sm:grid-cols-2 gap-2">
        {providers.flatMap((p) => purposes.map((purpose) => {
          const c = conns.find((x) => x.provider === p.provider && x.purpose === purpose);
          const live = c?.status === "CONNECTED";
          return (
            <div key={`${p.provider}-${purpose}`} className="border rounded p-2 text-xs space-y-1">
              <div className="flex items-center justify-between gap-2">
                <span className="font-medium">{LABEL[p.provider]} {PURPOSE[purpose]}</span>
                <span className={`px-1.5 py-0.5 rounded ${live ? "bg-green-100 text-green-700" : !p.configured ? "bg-gray-100 text-gray-600" : c?.status === "ERROR" ? "bg-red-100 text-red-700" : "bg-amber-100 text-amber-800"}`}>
                  {live ? tx("Connected") : !p.configured ? tx("Waiting for setup") : c?.status === "ERROR" ? tx("Reconnect needed") : tx("Not connected")}
                </span>
              </div>
              {c?.account_email && <div className="text-gray-600 break-all">{c.account_email}</div>}
              {c?.last_error && <div className="text-red-600">{c.last_error}</div>}
              {!p.configured && <div className="text-gray-500">{tx("An administrator enters the")} {LABEL[p.provider]} {tx("app keys under Integrations → Provider keys.")}</div>}
              <div className="flex gap-2">
                {p.configured && !live && (
                  <button className="text-indigo-600 hover:underline disabled:opacity-50" disabled={start.isPending}
                          onClick={() => start.mutate({ provider: p.provider, purpose })}>{tx("Connect")}</button>
                )}
                {c && c.status !== "REVOKED" && (
                  <button className="text-red-600 hover:underline" onClick={() => { if (confirm(tx("Disconnect this account? The ERP stops reading and sending through it."))) disconnect.mutate(c.id); }}>{tx("Disconnect")}</button>
                )}
              </div>
            </div>
          );
        }))}
      </div>
    </div>
  );
}
