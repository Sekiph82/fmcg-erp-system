"use client";
// M48.S01.T009 provider e-signature UI: provider selector with readiness, send the approved snapshot, status timeline,
// reconcile, cancel, download snapshot / signed document / evidence; admin configuration of the provider credentials.
import { useCallback, useEffect, useState } from "react";
import { providerSignApi, type ProviderEnvelope, type ProviderReadiness } from "@/lib/esign";
import { useAuth } from "@/context/AuthContext";
import { tx } from "@/lib/i18n/core";

const errText = (e: unknown) => {
  const d = (e as { response?: { data?: { detail?: unknown } } }).response?.data?.detail;
  return typeof d === "string" ? d : Array.isArray(d) ? "Check the fields: " + d.map((x: { loc?: string[] }) => x.loc?.slice(-1)[0]).join(", ") : "Something went wrong.";
};
const newKey = () => `povu-ui-${crypto.randomUUID()}`;
const tone: Record<string, string> = {
  COMPLETED: "bg-green-100 text-green-800", SENT: "bg-blue-100 text-blue-800", DELIVERED: "bg-blue-100 text-blue-800",
  CLAIMED: "bg-yellow-100 text-yellow-800", UNKNOWN: "bg-yellow-100 text-yellow-800", DECLINED: "bg-red-100 text-red-800",
  FAILED: "bg-red-100 text-red-800", INVALIDATED: "bg-red-100 text-red-800",
};

export function EnvelopeCard({ env, onChanged }: { env: ProviderEnvelope; onChanged: () => void }) {
  const { hasPermission } = useAuth();
  const [reason, setReason] = useState("");
  const [msg, setMsg] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const run = (p: Promise<unknown>, ok?: string) => {
    setBusy(true);
    p.then(() => { setMsg(ok ?? null); onChanged(); }).catch((e) => setMsg(errText(e))).finally(() => setBusy(false));
  };
  const file = (kind: "snapshot" | "signed" | "evidence") =>
    providerSignApi.download(env.id, kind, `${env.source_ref.replace(/ /g, "_")}-${kind}.pdf`)
      .then((r) => setMsg(`Downloaded ${kind} (SHA-256 ${r.sha256.slice(0, 16)}…, ${r.evidence}).`)).catch((e) => setMsg(errText(e)));
  const canReconcile = hasPermission("esign.request");
  const canCancel = hasPermission("esign.cancel");
  return (
    <div className="border rounded p-2 space-y-1" aria-label={tx("Signature request {source_ref}", { source_ref: env.source_ref })}>
      <div className="flex flex-wrap items-center gap-2">
        <b>{env.provider_label}</b>
        <span className={`px-2 rounded-full ${tone[env.status] ?? "bg-gray-100 text-gray-700"}`}>{env.status}</span>
        <span className={`px-2 rounded-full ${env.mode === "LIVE" ? "bg-purple-100 text-purple-800" : "bg-gray-100 text-gray-700"}`}>{env.mode}</span>
        <span className="text-gray-500">{env.source_ref} → {env.signer_name} &lt;{env.signer_email}&gt;</span>
      </div>
      {env.evidence_label && <p className={env.provider_certified ? "text-green-700" : "text-amber-700"}>{env.evidence_label}</p>}
      {env.erp_applied && <p>ERP: {env.erp_applied}</p>}
      {env.error && <p className="text-red-600" role="alert">{env.error}</p>}
      <p className="text-gray-500 break-all">{tx("Sent snapshot SHA-256")} {env.snapshot_sha256}{env.signed_sha256 ? tx(" · signed {signed_sha256}", { signed_sha256: env.signed_sha256 }) : ""}
        {env.evidence_sha256 ? tx(" · evidence {evidence_sha256}", { evidence_sha256: env.evidence_sha256 }) : ""}{env.provider_ref ? tx(" · provider id {provider_ref}", { provider_ref: env.provider_ref }) : ""}</p>
      <ol className="border-l pl-2">
        {env.timeline.map((t, i) => <li key={i}>{new Date(t.at).toLocaleString()} — {t.status} ({t.via}{t.provider_status ? tx(", provider: {provider_status}", { provider_status: t.provider_status }) : ""}){t.note ? `: ${t.note}` : ""}</li>)}
      </ol>
      {msg && <p role="status">{msg}</p>}
      <div className="flex flex-wrap gap-2 items-center">
        <button className="border rounded px-2" onClick={() => file("snapshot")}>{tx("Download sent snapshot")}</button>
        <button className="border rounded px-2 disabled:opacity-50" disabled={!env.signed_sha256} title={env.signed_sha256 ? "" : tx("Available once the provider completed and the signed copy was downloaded")} onClick={() => file("signed")}>{tx("Download signed document")}</button>
        <button className="border rounded px-2 disabled:opacity-50" disabled={!env.evidence_sha256} title={env.evidence_sha256 ? "" : tx("Available after completion")} onClick={() => file("evidence")}>{tx("Download evidence")}</button>
        {env.can_reconcile && <button className="border rounded px-2 disabled:opacity-50" disabled={busy || !canReconcile} title={canReconcile ? "" : tx("Needs esign.request")}
          onClick={() => run(providerSignApi.reconcile(env.id), "Status read back from the provider.")}>{tx("Refresh / reconcile")}</button>}
        {env.can_cancel && <>
          <input aria-label={tx("Cancel reason")} className="border rounded px-1" placeholder={tx("Reason to cancel")} value={reason} onChange={(e) => setReason(e.target.value)} />
          <button className="border rounded px-2 disabled:opacity-50" disabled={busy || !canCancel || reason.trim().length < 3}
            title={!canCancel ? tx("Needs esign.cancel (requester or e-signature admin)") : reason.trim().length < 3 ? tx("Give a reason") : ""}
            onClick={() => run(providerSignApi.cancel(env.id, reason.trim()), "Cancelled at the provider.")}>{tx("Cancel request")}</button></>}
      </div>
    </div>
  );
}

export function ProviderSignaturePanel({ sourceType, sourceId, sourceStatus }: { sourceType: "QUOTATION" | "CONTRACT"; sourceId: string; sourceStatus: string }) {
  const { hasPermission } = useAuth();
  const [ready, setReady] = useState<ProviderReadiness[]>([]);
  const [envs, setEnvs] = useState<ProviderEnvelope[]>([]);
  const [provider, setProvider] = useState<"DOCUSIGN" | "ADOBE_SIGN" | "">("");
  const [form, setForm] = useState({ signer_name: "", signer_email: "", expire_days: 30 });
  const [key, setKey] = useState(newKey);
  const [msg, setMsg] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const load = useCallback(() => {
    providerSignApi.readiness().then(setReady).catch(() => setReady([]));
    providerSignApi.list(sourceType, sourceId).then(setEnvs).catch(() => setEnvs([]));
  }, [sourceType, sourceId]);
  useEffect(() => { load(); }, [load]);
  if (!hasPermission("esign.view")) return null;
  const chosen = ready.find((r) => r.provider === provider);
  const open = envs.find((e) => e.can_reconcile);
  const approved = sourceType === "QUOTATION" ? sourceStatus === "SENT" : ["APPROVED", "ACTIVE"].includes(sourceStatus);
  const why = !hasPermission("esign.request") ? "You need the esign.request right to send for signature."
    : !approved ? (sourceType === "QUOTATION" ? "Only a sent (approved) quotation can go out for signature." : "Only an approved or active contract can go out for signature.")
    : open ? "Already out for signature: reconcile or cancel that request first."
    : !chosen ? "Choose a provider." : !chosen.ready ? chosen.reasons.join(" ")
    : !form.signer_name.trim() || !form.signer_email.includes("@") ? "Enter the signer's name and e-mail." : null;
  const send = () => {
    if (!provider) return;
    setBusy(true);
    providerSignApi.send({ provider, source_type: sourceType, source_id: sourceId, ...form, signer_name: form.signer_name.trim() }, key)
      .then((e) => { setMsg(e.status === "SENT" ? tx("Sent via {provider_label} ({mode}).", { provider_label: e.provider_label, mode: e.mode }) : `${e.status}: ${e.error ?? ""}`); setKey(newKey()); load(); })
      .catch((e) => setMsg(errText(e))).finally(() => setBusy(false));
  };
  return (
    <div className="border rounded p-3 bg-white space-y-2 text-xs" aria-label={tx("Provider e-signature")}>
      <h3 className="font-semibold text-sm">{tx("Signature via provider")}</h3>
      <p className="text-gray-500">{tx("The approved document is frozen as a PDF snapshot. Any change afterwards voids the request. Simulated provider signatures are evidence for testing only and never shown as certified.")}</p>
      <fieldset className="flex flex-wrap gap-3">
        <legend className="sr-only">{tx("Provider")}</legend>
        {ready.filter((r) => r.provider !== "LOCAL").map((r) => (
          <label key={r.provider} className={r.ready ? "" : "text-gray-400"} title={r.reasons.join(" ")}>
            <input type="radio" name={`prov-${sourceId}`} value={r.provider} checked={provider === r.provider}
              onChange={() => setProvider(r.provider as "DOCUSIGN" | "ADOBE_SIGN")} /> {r.label} · {r.ready ? r.mode : tx("not ready")}
          </label>))}
      </fieldset>
      {chosen && !chosen.ready && <p className="text-amber-700">{chosen.reasons.join(" ")}</p>}
      <div className="flex flex-wrap gap-2">
        <input aria-label={tx("Signer name")} className="border rounded px-1" placeholder={tx("Signer name")} value={form.signer_name} onChange={(e) => setForm({ ...form, signer_name: e.target.value })} />
        <input aria-label={tx("Signer e-mail")} type="email" className="border rounded px-1" placeholder="signer@example.com" value={form.signer_email} onChange={(e) => setForm({ ...form, signer_email: e.target.value })} />
        <label>{tx("Expires after")} <input aria-label={tx("Expiry days")} type="number" min={1} max={120} className="border rounded w-14 px-1" value={form.expire_days}
          onChange={(e) => setForm({ ...form, expire_days: Number(e.target.value) || 30 })} /> {tx("days")}</label>
        <button className="border rounded px-2 py-1 bg-blue-600 text-white disabled:opacity-50" disabled={!!why || busy} title={why ?? ""} onClick={send}>{tx("Send for signature")}</button>
      </div>
      {why && <p className="text-gray-500">{why}</p>}
      {msg && <p role="status">{msg}</p>}
      {envs.map((e) => <EnvelopeCard key={e.id} env={e} onChanged={load} />)}
    </div>
  );
}

const FIELDS: Record<string, { settings: [string, string][]; secrets: [string, string][] }> = {
  DOCUSIGN: { settings: [["integration_key", "Integration key"], ["user_id", "User ID (GUID)"], ["auth_base", "Auth server (https://account-d.docusign.com)"], ["account_id", "Account ID (optional)"]],
    secrets: [["private_key_pem", "RSA private key (PEM)"], ["connect_hmac_key", "Connect HMAC key"]] },
  ADOBE_SIGN: { settings: [["client_id", "Application (client) ID"], ["api_base", "API access point (https://api.na1.adobesign.com)"]],
    secrets: [["client_secret", "Client secret"], ["refresh_token", "Refresh token"]] },
};

function ProviderConfig({ r, onSaved }: { r: ProviderReadiness; onSaved: () => void }) {
  const [s, setS] = useState<Record<string, string>>(() => Object.fromEntries(Object.entries(r.settings).map(([k, v]) => [k, v ?? ""])));
  const [sec, setSec] = useState<Record<string, string>>({});
  const [msg, setMsg] = useState<string | null>(null);
  const f = FIELDS[r.provider];
  const save = (live?: boolean) => providerSignApi.configure(r.provider, { settings: s, secrets: sec, ...(live === undefined ? {} : { live_enabled: live }) })
    .then(() => { setSec({}); setMsg(tx("Saved. Secrets are stored encrypted and never shown again.")); onSaved(); }).catch((e) => setMsg(errText(e)));
  return (
    <div className="border rounded p-2 space-y-1">
      <div className="flex items-center gap-2"><b>{r.label}</b><span>{r.ready ? tx("ready · {mode}", { mode: r.mode }) : tx("not ready")}</span></div>
      {r.reasons.map((x) => <p key={x} className="text-amber-700">{x}</p>)}
      <div className="grid sm:grid-cols-2 gap-1">
        {f.settings.map(([k, label]) => <label key={k} className="flex flex-col">{label}
          <input className="border rounded px-1" value={s[k] ?? ""} onChange={(e) => setS({ ...s, [k]: e.target.value })} /></label>)}
        {f.secrets.map(([k, label]) => <label key={k} className="flex flex-col">{label} {r.secrets_set[k] ? tx("(set)") : tx("(not set)")}
          {k === "private_key_pem" ? <textarea className="border rounded px-1" rows={2} value={sec[k] ?? ""} onChange={(e) => setSec({ ...sec, [k]: e.target.value })} />
            : <input type="password" autoComplete="off" className="border rounded px-1" value={sec[k] ?? ""} onChange={(e) => setSec({ ...sec, [k]: e.target.value })} />}</label>)}
      </div>
      <div className="flex gap-2">
        <button className="border rounded px-2" onClick={() => save()}>{tx("Save")}</button>
        <button className="border rounded px-2" onClick={() => save(!r.live_enabled)}
          title={tx("Live sending also needs ESIGN_LIVE_ENABLED on the server and official https hosts")}>{r.live_enabled ? tx("Withdraw live activation") : tx("Record live activation")}</button>
      </div>
      {msg && <p role="status">{msg}</p>}
    </div>
  );
}

/** E-signature page tab: readiness, admin configuration, every provider request. */
export function ProviderSignaturesTab() {
  const { hasPermission } = useAuth();
  const [ready, setReady] = useState<ProviderReadiness[]>([]);
  const [envs, setEnvs] = useState<ProviderEnvelope[]>([]);
  const [err, setErr] = useState<string | null>(null);
  const load = useCallback(() => {
    providerSignApi.readiness().then(setReady).catch((e) => setErr(errText(e)));
    providerSignApi.list().then(setEnvs).catch((e) => setErr(errText(e)));
  }, []);
  useEffect(() => { load(); }, [load]);
  return (
    <div className="space-y-3 text-xs">
      {err && <p className="text-red-600" role="alert">{err}</p>}
      <div className="bg-white rounded-xl border p-3 space-y-2">
        <h2 className="text-sm font-semibold">{tx("Providers")}</h2>
        <ul>{ready.map((r) => <li key={r.provider}><b>{r.label}</b>: {r.mode === "LOCAL" ? tx("active") : r.ready ? tx("ready ({mode})", { mode: r.mode }) : tx("not ready")}
          {r.reasons.length > 0 && <span className="text-amber-700"> — {r.reasons.join(" ")}</span>}</li>)}</ul>
        {hasPermission("esign.admin") && ready.filter((r) => r.provider !== "LOCAL").map((r) => <ProviderConfig key={r.provider + (r.updated_by ?? "")} r={r} onSaved={load} />)}
      </div>
      <div className="bg-white rounded-xl border p-3 space-y-2">
        <h2 className="text-sm font-semibold">{tx("Provider signature requests")}</h2>
        {envs.length === 0 ? <p className="text-gray-500">{tx("None yet. Send one from an approved quotation.")}</p>
          : envs.map((e) => <EnvelopeCard key={e.id} env={e} onChanged={load} />)}
      </div>
    </div>
  );
}
