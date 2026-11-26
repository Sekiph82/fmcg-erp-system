"use client";
// M45.S01.T018 configuration sandbox: export a bundle from staging, dry-run and apply it here.
import { useState } from "react";
import { apiClient } from "@/lib/api";
import { tx } from "@/lib/i18n/core";

type Step = { table: string; key: string; action: string; changed?: string[]; detail?: string };
const err = (e: unknown) => { const d = (e as { response?: { data?: { detail?: unknown } } }).response?.data?.detail; return typeof d === "string" ? d : "Something went wrong."; };

export default function ConfigSandboxPage() {
  const [bundle, setBundle] = useState<Record<string, unknown> | null>(null);
  const [mode, setMode] = useState<"overwrite" | "skip_existing">("overwrite");
  const [plan, setPlan] = useState<{ steps: Step[]; summary: Record<string, number> } | null>(null);
  const [msg, setMsg] = useState<string | null>(null);
  const [cms, setCms] = useState(false);                     // M47.S01.T007 include website content
  const [siteMap, setSiteMap] = useState("");                // "source-key=target-key, ..."
  const siteKeys = () => Object.fromEntries(siteMap.split(",").map((p) => p.split("=").map((x) => x.trim())).filter((p) => p.length === 2 && p[0] && p[1]));
  const download = () => apiClient.get(`/api/v1/config-bundles/export${cms ? "?include_cms=true" : ""}`).then((r) => {
    const a = document.createElement("a");
    a.href = URL.createObjectURL(new Blob([JSON.stringify(r.data, null, 2)], { type: "application/json" }));
    a.download = `config-${String(r.data.sha256).slice(0, 8)}.json`; a.click();
  }).catch((e) => setMsg(err(e)));
  const load = (f: File | undefined) => f && f.text().then((t) => { try { setBundle(JSON.parse(t)); setPlan(null); setMsg(null); } catch { setMsg(tx("Not a JSON file.")); } });
  const dry = () => bundle && apiClient.post("/api/v1/config-bundles/plan", { bundle, mode, site_keys: siteKeys() }).then((r) => setPlan(r.data)).catch((e) => setMsg(err(e)));
  const apply = () => bundle && apiClient.post("/api/v1/config-bundles/apply", { bundle, mode, site_keys: siteKeys() }).then((r) => { setMsg(tx("Applied: {created} created, {updated} updated. Workflows arrive as drafts: publish them.", { created: r.data.created, updated: r.data.updated })); setPlan(null); }).catch((e) => setMsg(err(e)));
  return (
    <div className="p-4 space-y-3 text-sm max-w-4xl">
      <h2 className="text-lg font-semibold">{tx("Configuration sandbox")}</h2>
      <div className="flex flex-wrap gap-3 items-center text-xs">
        <label className="flex items-center gap-1"><input type="checkbox" checked={cms} onChange={(e) => setCms(e.target.checked)} />{tx("Include website content (live public pages as drafts, tables, redirects, CTAs; media by reference)")}</label>
        <label>{tx("Site key mapping")}<input aria-label={tx("Site key mapping")} className="border rounded px-1 ml-1" placeholder={tx("povu=povu-staging")} value={siteMap} onChange={(e) => setSiteMap(e.target.value)} /></label>
      </div>
      <p className="text-xs text-gray-500">{tx("Try configuration changes on a staging copy, export them here, then dry-run and apply them in production. Bundles contain pipelines, custom fields and objects, templates, sequences, forms, scoring and routing rules and workflows: never customer or transaction data.")}</p>
      {msg && <p role="status" className="text-xs">{msg}</p>}
      <button className="border rounded px-3 py-1 text-xs" onClick={download}>{tx("Export this system's configuration")}</button>
      <div className="border rounded p-3 bg-white space-y-2">
        <input aria-label={tx("Bundle file")} type="file" accept="application/json" onChange={(e) => load(e.target.files?.[0])} />
        <select aria-label={tx("When a setting already exists")} className="border rounded px-1 text-xs" value={mode} onChange={(e) => setMode(e.target.value as "overwrite" | "skip_existing")}>
          <option value="overwrite">{tx("Update existing settings")}</option><option value="skip_existing">{tx("Keep existing settings")}</option></select>
        <div className="flex gap-2"><button className="border rounded px-3 py-1 text-xs" disabled={!bundle} onClick={dry}>{tx("Dry run")}</button>
          <button className="bg-indigo-600 text-white rounded px-3 py-1 text-xs" disabled={!plan || (plan.summary.error ?? 0) > 0} onClick={apply}>{tx("Apply")}</button></div>
        {plan && <><p className="text-xs">{Object.entries(plan.summary).map(([k, v]) => `${v} ${k}`).join(" · ")}</p>
          <table className="text-xs w-full"><tbody>{plan.steps.filter((s) => s.action !== "unchanged").map((s, i) => <tr key={i} className="border-t">
            <td className="p-1">{s.table}</td><td>{s.key}</td><td className={s.action === "error" ? "text-red-600" : ""}>{s.action}</td><td>{s.changed?.join(", ") ?? s.detail ?? ""}</td></tr>)}</tbody></table></>}
      </div>
    </div>
  );
}
