"use client";
// M50.S01.T011 consent page for the Gmail / Outlook CRM add-ins. Opened by the add-in (Outlook: Office dialog, Gmail: a
// browser tab). A signed-in ERP user approves what the add-in may do; the one-time code goes back to the add-in only:
// Outlook: Office.context.ui.messageParent (or window.opener.postMessage to the exact origin that asked, local harness);
// Gmail: shown on this page to type into the add-on card (60 seconds, useless without the add-on's verifier). Never in a URL.
import { useEffect, useMemo, useState } from "react";
import { API_ORIGIN, apiClient } from "@/lib/api";

declare global { interface Window { Office?: { onReady: (cb: () => void) => void; context: { ui: { messageParent: (m: string) => void } } } } }
const HOSTS = ["outlook", "gmail"] as const;

export default function AddinAuthorize() {
  const p = useMemo(() => (typeof window === "undefined" ? new URLSearchParams() : new URLSearchParams(window.location.search)), []);
  const host = p.get("host") ?? "", challenge = p.get("challenge") ?? "", state = p.get("state") ?? "", origin = p.get("origin") ?? "";
  const valid = (HOSTS as readonly string[]).includes(host) && /^[A-Za-z0-9_-]{43}$/.test(challenge) && /^[A-Za-z0-9_-]{8,64}$/.test(state);
  const [me, setMe] = useState<{ full_name?: string; username?: string } | null | undefined>(undefined);
  const [write, setWrite] = useState(true);
  const [code, setCode] = useState<string | null>(null);
  const [msg, setMsg] = useState<string | null>(null);
  useEffect(() => {
    if (host === "outlook" && !window.Office) { const s = document.createElement("script"); s.src = "https://appsforoffice.microsoft.com/lib/1/hosted/office.js"; document.head.appendChild(s); }
    fetch(`${API_ORIGIN}/api/v1/auth/me`, { credentials: "include" }).then((r) => (r.ok ? r.json() : null)).then(setMe).catch(() => setMe(null));
  }, [host]);

  const approve = async () => {
    try {
      const r = await apiClient.post("/api/v1/public/crm-addin/auth/authorize", { host, code_challenge: challenge, origin: host === "gmail" ? "gmail-addon" : origin, scopes: write ? ["addin.read", "addin.write"] : ["addin.read"] });
      const payload = JSON.stringify({ type: "povu-addin-code", code: r.data.code, state, api: API_ORIGIN });
      if (host === "gmail") { setCode(r.data.code); return; }
      if (window.Office?.context?.ui?.messageParent) { window.Office.context.ui.messageParent(payload); setMsg("Signed in. You can close this window."); }
      else if (window.opener && origin) { window.opener.postMessage(payload, origin); setMsg("Signed in. You can close this window."); window.close(); }
      else setMsg("This page must be opened by the add-in.");
    } catch (e) {
      const d = (e as { response?: { data?: { detail?: unknown } } }).response?.data?.detail;
      setMsg(typeof d === "string" ? d : "Could not sign the add-in in.");
    }
  };

  if (!valid) return <main className="p-6 text-sm">This sign-in link is not valid. Open it from the add-in.</main>;
  return (
    <main className="p-6 text-sm max-w-md space-y-3">
      <h1 className="text-lg font-semibold">POVU CRM add-in</h1>
      {me === undefined && <p>Checking your ERP session…</p>}
      {me === null && <p>Sign in to the ERP first (<a className="underline" href="/login" target="_blank" rel="noreferrer">open the login page</a>), then reload this window.</p>}
      {me && !code && <>
        <p>Allow the {host === "gmail" ? "Gmail add-on" : "Outlook add-in"} to act as <b>{me.full_name ?? me.username}</b> in the CRM? It can look up the sender, and log e-mails, notes and tasks on the deals you may already see. It cannot see anything else. You can revoke it any time under CRM → Add-in sign-ins.</p>
        {host === "gmail" && <div role="alert" className="border border-amber-400 bg-amber-50 rounded p-2 text-xs space-y-1">
          <p><b>Only continue if you just started this from your own Gmail add-on card.</b> Someone could send you this link to get access to your CRM.</p>
          <p>Check code on this page: <b className="font-mono text-base" data-testid="addin-state">{state}</b>. The add-on card must show the same check code; if it does not, or you did not open this from the card, press Cancel.</p></div>}
        <label className="flex gap-2 items-center text-xs"><input type="checkbox" checked={write} onChange={(e) => setWrite(e.target.checked)} /> Also allow logging e-mails, notes and tasks (untick for look-up only)</label>
        <button className="bg-indigo-600 text-white rounded px-3 py-1" onClick={approve}>Allow</button>
        <button className="border rounded px-3 py-1 ml-2" onClick={() => { setMsg("Cancelled. You can close this window."); window.Office?.context?.ui?.messageParent?.(JSON.stringify({ type: "povu-addin-denied", state })); }}>Cancel</button>
      </>}
      {code && <div className="space-y-2"><p>Check code <b className="font-mono">{state}</b> must match your add-on card. Type this code into the Gmail add-on within a minute. It works once and only with that add-on.</p>
        <p className="font-mono text-base break-all select-all border rounded p-2" data-testid="addin-code">{code}</p></div>}
      {msg && <p role="status" className="text-xs">{msg}</p>}
    </main>
  );
}
