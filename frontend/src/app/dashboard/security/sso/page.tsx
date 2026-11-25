"use client";
// M45.S01.T016 single sign-on configuration (superusers): OIDC provider, role mapping, enforcement with break-glass.
import { useEffect, useState } from "react";
import { apiClient } from "@/lib/api";

type Cfg = { name: string; issuer: string; client_id: string; client_secret?: string; scopes: string; role_mapping: Record<string, string>; enforced: boolean; break_glass: string[]; active: boolean; has_secret?: boolean; redirect_uri?: string };
const EMPTY: Cfg = { name: "Company IdP", issuer: "https://", client_id: "", scopes: "openid email profile groups", role_mapping: {}, enforced: false, break_glass: [], active: false };
const err = (e: unknown) => { const d = (e as { response?: { data?: { detail?: unknown } } }).response?.data?.detail; return typeof d === "string" ? d : "Something went wrong."; };
const inp = "border rounded px-2 py-1 w-full text-xs";

export default function SSOPage() {
  const [cfg, setCfg] = useState<Cfg>(EMPTY);
  const [mapping, setMapping] = useState("");
  const [status, setStatus] = useState<{ oidc: string; saml: string; saml_note: string } | null>(null);
  const [msg, setMsg] = useState<string | null>(null);
  useEffect(() => {
    apiClient.get("/api/v1/sso/config").then((r) => { if (r.data) { setCfg(r.data); setMapping(Object.entries(r.data.role_mapping ?? {}).map(([k, v]) => `${k}=${v}`).join("\n")); } }).catch((e) => setMsg(err(e)));
    apiClient.get("/api/v1/sso/status").then((r) => setStatus(r.data)).catch(() => setStatus(null));
  }, []);
  const save = () => {
    const role_mapping = Object.fromEntries(mapping.split("\n").map((l) => l.split("=").map((x) => x.trim())).filter((x) => x.length === 2 && x[0] && x[1]));
    apiClient.put("/api/v1/sso/config", { ...cfg, role_mapping, client_secret: cfg.client_secret || undefined }).then(() => setMsg("Saved.")).catch((e) => setMsg(err(e)));
  };
  const field = (k: keyof Cfg, label: string, type = "text") => <label className="text-xs block">{label}<input aria-label={label} type={type} className={inp} value={String(cfg[k] ?? "")} onChange={(e) => setCfg({ ...cfg, [k]: e.target.value })} /></label>;
  return (
    <div className="p-4 space-y-3 text-sm max-w-2xl">
      <h2 className="text-lg font-semibold">Single sign-on</h2>
      {status && <p className="text-xs text-gray-500">OpenID Connect: {status.oidc.toLowerCase().replace("_", " ")}. SAML: {status.saml.toLowerCase().replace("_", " ")} ({status.saml_note})</p>}
      {msg && <p role="status" className="text-xs">{msg}</p>}
      {field("name", "Name shown on the login page")}
      {field("issuer", "Issuer URL")}
      {field("client_id", "Client ID")}
      <label className="text-xs block">Client secret {cfg.has_secret ? "(stored; leave empty to keep)" : ""}<input aria-label="Client secret" type="password" className={inp} value={cfg.client_secret ?? ""} onChange={(e) => setCfg({ ...cfg, client_secret: e.target.value })} /></label>
      {field("scopes", "Scopes")}
      {cfg.redirect_uri && <p className="text-xs">Redirect URI to register at the provider: <code>{cfg.redirect_uri}</code></p>}
      <label className="text-xs block">Role mapping (one per line: idp-group=ERP role name)<textarea aria-label="Role mapping" className={inp} rows={3} value={mapping} onChange={(e) => setMapping(e.target.value)} /></label>
      <label className="text-xs block">Break-glass usernames (may still use a password), comma separated
        <input aria-label="Break-glass usernames" className={inp} value={cfg.break_glass.join(", ")} onChange={(e) => setCfg({ ...cfg, break_glass: e.target.value.split(",").map((x) => x.trim()).filter(Boolean) })} /></label>
      <label className="text-xs flex gap-2 items-center"><input type="checkbox" checked={cfg.active} onChange={(e) => setCfg({ ...cfg, active: e.target.checked })} /> Active</label>
      <label className="text-xs flex gap-2 items-center"><input type="checkbox" checked={cfg.enforced} onChange={(e) => setCfg({ ...cfg, enforced: e.target.checked })} /> Enforce: block password login except break-glass</label>
      <p className="text-xs text-gray-500">Only users that already exist in the ERP (same e-mail) can sign in; disabled users are refused.</p>
      <button className="bg-indigo-600 text-white rounded px-3 py-1 text-xs" onClick={save}>Save</button>
    </div>
  );
}
