"use client";
// M45.S01.T016 single sign-on configuration (superusers): OIDC provider, role mapping, enforcement with break-glass.
import { useEffect, useState } from "react";
import { apiClient } from "@/lib/api";
import { tx } from "@/lib/i18n/core";

type Cfg = { name: string; issuer: string; client_id: string; client_secret?: string; scopes: string; role_mapping: Record<string, string>; enforced: boolean; break_glass: string[]; active: boolean; has_secret?: boolean; redirect_uri?: string };
const EMPTY: Cfg = { name: "Company IdP", issuer: "https://", client_id: "", scopes: "openid email profile groups", role_mapping: {}, enforced: false, break_glass: [], active: false };
const err = (e: unknown) => { const d = (e as { response?: { data?: { detail?: unknown } } }).response?.data?.detail; return typeof d === "string" ? d : tx("Something went wrong."); };
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
    apiClient.put("/api/v1/sso/config", { ...cfg, role_mapping, client_secret: cfg.client_secret || undefined }).then(() => setMsg(tx("Saved."))).catch((e) => setMsg(err(e)));
  };
  const field = (k: keyof Cfg, label: string, type = "text") => <label className="text-xs block">{label}<input aria-label={label} type={type} className={inp} value={String(cfg[k] ?? "")} onChange={(e) => setCfg({ ...cfg, [k]: e.target.value })} /></label>;
  return (
    <div className="p-4 space-y-3 text-sm max-w-2xl">
      <h2 className="text-lg font-semibold">{tx("Single sign-on")}</h2>
      {status && <p className="text-xs text-gray-500">{tx("OpenID Connect:")} {status.oidc.toLowerCase().replace("_", " ")}{tx(". SAML:")} {status.saml.toLowerCase().replace("_", " ")} ({status.saml_note})</p>}
      {msg && <p role="status" className="text-xs">{msg}</p>}
      {field("name", tx("Name shown on the login page"))}
      {field("issuer", "Issuer URL")}
      {field("client_id", "Client ID")}
      <label className="text-xs block">{tx("Client secret")} {cfg.has_secret ? tx("(stored; leave empty to keep)") : ""}<input aria-label={tx("Client secret")} type="password" className={inp} value={cfg.client_secret ?? ""} onChange={(e) => setCfg({ ...cfg, client_secret: e.target.value })} /></label>
      {field("scopes", "Scopes")}
      {cfg.redirect_uri && <p className="text-xs">{tx("Redirect URI to register at the provider:")} <code>{cfg.redirect_uri}</code></p>}
      <label className="text-xs block">{tx("Role mapping (one per line: idp-group=ERP role name)")}<textarea aria-label={tx("Role mapping")} className={inp} rows={3} value={mapping} onChange={(e) => setMapping(e.target.value)} /></label>
      <label className="text-xs block">{tx("Break-glass usernames (may still use a password), comma separated")}
        <input aria-label={tx("Break-glass usernames")} className={inp} value={cfg.break_glass.join(", ")} onChange={(e) => setCfg({ ...cfg, break_glass: e.target.value.split(",").map((x) => x.trim()).filter(Boolean) })} /></label>
      <label className="text-xs flex gap-2 items-center"><input type="checkbox" checked={cfg.active} onChange={(e) => setCfg({ ...cfg, active: e.target.checked })} /> {tx("Active")}</label>
      <label className="text-xs flex gap-2 items-center"><input type="checkbox" checked={cfg.enforced} onChange={(e) => setCfg({ ...cfg, enforced: e.target.checked })} /> {tx("Enforce: block password login except break-glass")}</label>
      <p className="text-xs text-gray-500">{tx("Only users that already exist in the ERP (same e-mail) can sign in; disabled users are refused.")}</p>
      <button className="bg-indigo-600 text-white rounded px-3 py-1 text-xs" onClick={save}>{tx("Save")}</button>
      <SamlSection />
    </div>
  );
}

// M50.S01.T010 SAML 2.0 (python3-saml + xmlsec): IdP details, signing certificate, role mapping; SP metadata for the IdP admin.
type Saml = { name: string; idp_entity_id: string; idp_sso_url: string; idp_x509_cert: string; sp_entity_id: string; email_attribute: string; groups_attribute: string; clock_skew_seconds: number; active: boolean };
type SamlOut = { library: { available: boolean; detail: string }; config: (Saml & { role_mapping: Record<string, string>; acs_url: string; metadata_url: string; certificate: { subject: string; not_after: string; expired: boolean; sha256: string } }) | null; defaults: { sp_entity_id: string; acs_url: string } };
function SamlSection() {
  const [o, setO] = useState<SamlOut | null>(null);
  const [f, setF] = useState<Saml>({ name: "Company SAML IdP", idp_entity_id: "", idp_sso_url: "https://", idp_x509_cert: "", sp_entity_id: "", email_attribute: "email", groups_attribute: "groups", clock_skew_seconds: 60, active: false });
  const [map, setMap] = useState("");
  const [m, setM] = useState<string | null>(null);
  useEffect(() => {
    apiClient.get("/api/v1/sso/saml/config").then((r) => {
      setO(r.data);
      if (r.data.config) { const { role_mapping, certificate: _c, acs_url: _a, metadata_url: _m, id: _i, ...rest } = r.data.config; setF({ ...rest, idp_x509_cert: "" }); setMap(Object.entries(role_mapping ?? {}).map(([k, v]) => `${k}=${v}`).join("\n")); }
      else setF((x) => ({ ...x, sp_entity_id: r.data.defaults.sp_entity_id }));
    }).catch((e) => setM(err(e)));
  }, []);
  const save = () => {
    const role_mapping = Object.fromEntries(map.split("\n").map((l) => l.split("=").map((x) => x.trim())).filter((x) => x.length === 2 && x[0] && x[1]));
    apiClient.put("/api/v1/sso/saml/config", { ...f, idp_x509_cert: f.idp_x509_cert || undefined, role_mapping }).then((r) => { setM(tx("SAML saved.")); setO({ ...o!, config: r.data }); }).catch((e) => setM(err(e)));
  };
  const t = (k: keyof Saml, label: string) => <label className="text-xs block">{label}<input aria-label={label} className={inp} value={String(f[k] ?? "")} onChange={(e) => setF({ ...f, [k]: k === "clock_skew_seconds" ? Number(e.target.value) : e.target.value })} /></label>;
  return (
    <section className="border-t pt-4 mt-4 space-y-3" aria-label={tx("SAML 2.0")}>
      <h3 className="font-semibold">{tx("SAML 2.0")}</h3>
      {o && !o.library.available && <p className="text-xs text-red-600">{tx("SAML library not available on this server:")} {o.library.detail}</p>}
      {o && o.library.available && <p className="text-xs text-gray-500">{tx("Library:")} {o.library.detail}{tx(". Sign-in is service-provider initiated; the assertion must be signed by the certificate below.")}</p>}
      {m && <p role="status" className="text-xs">{m}</p>}
      {o?.config && <div className="text-xs border rounded p-2 bg-gray-50 space-y-1">
        <div>{tx("Give the IdP administrator: SP entity ID")} <code>{o.config.sp_entity_id}</code>{tx(", ACS URL")} <code>{o.config.acs_url}</code> {tx("(HTTP-POST), or the metadata:")} <a className="underline" href={o.config.metadata_url} target="_blank" rel="noreferrer">{o.config.metadata_url}</a></div>
        <div>{tx("IdP certificate:")} {o.config.certificate.subject}{tx(", valid until")} {new Date(o.config.certificate.not_after).toLocaleDateString()}{o.config.certificate.expired ? tx(" (EXPIRED)") : ""}{tx(", SHA-256")} {o.config.certificate.sha256.slice(0, 16)}…</div></div>}
      {t("name", tx("SAML name shown on the login page"))}
      {t("idp_entity_id", tx("IdP entity ID"))}
      {t("idp_sso_url", tx("IdP single sign-on URL (HTTP-Redirect)"))}
      <label className="text-xs block">{tx("IdP signing certificate (PEM, public part only)")}{o?.config ? tx(" — paste again only to replace it") : ""}<textarea aria-label={tx("IdP certificate")} className={`${inp} font-mono`} rows={4} value={f.idp_x509_cert} onChange={(e) => setF({ ...f, idp_x509_cert: e.target.value })} /></label>
      {t("sp_entity_id", tx("SP entity ID"))}
      {t("email_attribute", tx("E-mail attribute name"))}
      {t("groups_attribute", tx("Groups attribute name"))}
      {t("clock_skew_seconds", tx("Allowed clock skew (seconds, max 120)"))}
      <label className="text-xs block">{tx("Role mapping (idp-group=ERP role name, one per line)")}<textarea aria-label={tx("SAML role mapping")} className={inp} rows={3} value={map} onChange={(e) => setMap(e.target.value)} /></label>
      <label className="text-xs flex gap-2 items-center"><input type="checkbox" checked={f.active} onChange={(e) => setF({ ...f, active: e.target.checked })} /> {tx("Active (shows the SAML button on the login page)")}</label>
      <p className="text-xs text-gray-500">{tx("Only users that already exist in the ERP (same e-mail) can sign in; privileged accounts keep password + authenticator app.")}</p>
      <button className="bg-indigo-600 text-white rounded px-3 py-1 text-xs disabled:opacity-50" disabled={!o?.library.available || (!o?.config && !f.idp_x509_cert)} onClick={save}>{tx("Save SAML")}</button>
    </section>
  );
}
