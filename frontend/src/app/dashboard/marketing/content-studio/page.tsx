"use client";
// M46.S01.T003 content studio: brand voice rules, drafts (AI within budget or deterministic), claims review, approval.
// Nothing here publishes; an approved draft can be copied into a website page draft.
import { useCallback, useEffect, useState } from "react";
import { apiClient } from "@/lib/api";

type Evidence = { id: string; text: string; source: string };
type Profile = { id: string; name: string; voice: string; banned_terms: string[]; terminology: Record<string, string>; claim_terms: string[]; evidence: Evidence[];
  monthly_budget: number; spent_this_month: number; calls_this_month: number };
type Finding = { level: string; code: string; message: string };
type Draft = { id: string; profile_id: string; channel: string; template: string; brief: string; body: string; engine: string; cost: number; findings: Finding[];
  history: { at: string; by: string; action: string; note?: string }[]; status: string; created_by: string; approved_by: string | null; source_id: string | null };
const err = (e: unknown) => { const d = (e as { response?: { data?: { detail?: unknown } } }).response?.data?.detail; return typeof d === "string" ? d : typeof (d as { detail?: unknown })?.detail === "string" ? (d as { detail: string }).detail : "Something went wrong."; };

function ImageForm({ say }: { say: (m: string) => void }) {
  const [f, setF] = useState({ title: "", prompt: "" });
  return <section className="border rounded p-3 bg-white space-y-2 text-xs">
    <h3 className="font-semibold text-sm">AI image (draft creative)</h3>
    <p className="text-gray-500">The image lands in the asset library as a draft; it cannot be used in e-mail, social or the website until approved there.</p>
    <input aria-label="Image title" placeholder="Title, e.g. POVU AllClean counter visual" className="border rounded px-1 w-full" value={f.title} onChange={(e) => setF({ ...f, title: e.target.value })} />
    <textarea aria-label="Image prompt" rows={2} placeholder="Describe the image" className="border rounded px-1 w-full" value={f.prompt} onChange={(e) => setF({ ...f, prompt: e.target.value })} />
    <button className="border rounded px-3 py-1" onClick={() => apiClient.post("/api/v1/content-studio/images", f).then((r) => { say(`Draft creative created (document ${r.data.document_id}); approve it in the asset library.`); setF({ title: "", prompt: "" }); }).catch((e) => say(err(e)))}>Generate image</button>
  </section>;
}

function ProfileForm({ p, onSaved, say }: { p: Profile | null; onSaved: () => void; say: (m: string) => void }) {
  const [f, setF] = useState({ name: p?.name ?? "", voice: p?.voice ?? "", banned: (p?.banned_terms ?? []).join(", "), claims: (p?.claim_terms ?? []).join(", "),
    terms: Object.entries(p?.terminology ?? {}).map(([a, b]) => `${a} = ${b}`).join("\n"), evidence: (p?.evidence ?? []).map((e) => `${e.id} | ${e.text} | ${e.source}`).join("\n"),
    budget: String(p?.monthly_budget ?? 0) });
  const body = () => ({ name: f.name, voice: f.voice, banned_terms: f.banned.split(","), claim_terms: f.claims.split(","), monthly_budget: +f.budget || 0,
    terminology: Object.fromEntries(f.terms.split("\n").filter((l) => l.includes("=")).map((l) => l.split("=").map((x) => x.trim()))),
    evidence: f.evidence.split("\n").filter((l) => l.split("|").length >= 3).map((l) => { const [id, text, ...src] = l.split("|"); return { id: id.trim(), text: text.trim(), source: src.join("|").trim() }; }) });
  const save = () => (p ? apiClient.patch(`/api/v1/content-studio/profiles/${p.id}`, body()) : apiClient.post("/api/v1/content-studio/profiles", body()))
    .then(() => { say("Brand profile saved."); onSaved(); }).catch((e) => say(err(e)));
  const area = (k: keyof typeof f, label: string, rows = 3) => <label className="text-xs block">{label}<textarea aria-label={label} rows={rows} className="border rounded px-1 w-full block" value={f[k]} onChange={(e) => setF({ ...f, [k]: e.target.value })} /></label>;
  return <section className="border rounded p-3 bg-white space-y-2">
    <h3 className="font-semibold">{p ? `Brand voice: ${p.name}` : "New brand profile"}</h3>
    <div className="grid gap-2 sm:grid-cols-2">
      <label className="text-xs">Name<input aria-label="Profile name" className="border rounded px-1 w-full block" value={f.name} onChange={(e) => setF({ ...f, name: e.target.value })} /></label>
      <label className="text-xs">Monthly AI budget (USD, 0 = rules only){p && ` · used ${p.spent_this_month.toFixed(4)} in ${p.calls_this_month} calls`}
        <input aria-label="Monthly AI budget" type="number" min={0} step="0.01" className="border rounded px-1 w-full block" value={f.budget} onChange={(e) => setF({ ...f, budget: e.target.value })} /></label>
      {area("voice", "Voice and style")}{area("banned", "Banned words (comma separated)")}
      {area("terms", "Terminology (one per line: wrong = right)")}{area("claims", "Words that make a claim (comma separated)")}
    </div>
    {area("evidence", "Approved evidence — one per line: id | fact | source. Claims must cite [E:id].", 4)}
    <button className="bg-indigo-600 text-white rounded px-3 py-1 text-xs" onClick={save}>Save profile</button>
  </section>;
}

export default function ContentStudioPage() {
  const [profiles, setProfiles] = useState<Profile[]>([]);
  const [pid, setPid] = useState<string>("");
  const [drafts, setDrafts] = useState<Draft[]>([]);
  const [opts, setOpts] = useState<{ channels: Record<string, number>; templates: Record<string, string> }>({ channels: {}, templates: {} });
  const [g, setG] = useState({ channel: "web", template: "product_launch", brief: "", evidence: [] as string[] });
  const [cur, setCur] = useState<Draft | null>(null);
  const [edit, setEdit] = useState("");
  const [pageId, setPageId] = useState("");
  const [remix, setRemix] = useState<string[]>([]);
  const [msg, setMsg] = useState<string | null>(null);
  const say = useCallback((m: string) => setMsg(m), []);
  const load = useCallback(() => {
    apiClient.get("/api/v1/content-studio/profiles").then((r) => { setProfiles(r.data); setPid((p) => p || r.data[0]?.id || ""); }).catch((e) => say(err(e)));
    apiClient.get("/api/v1/content-studio/drafts").then((r) => setDrafts(r.data)).catch(() => {});
  }, [say]);
  useEffect(() => { load(); apiClient.get("/api/v1/content-studio/options").then((r) => setOpts(r.data)).catch(() => {}); }, [load]);
  const profile = profiles.find((p) => p.id === pid) ?? null;
  const pick = (d: Draft) => { setCur(d); setEdit(d.body); };
  const after = (r: { data: Draft }) => { pick(r.data); load(); };
  return (
    <div className="p-4 space-y-3 text-sm">
      <h2 className="text-lg font-semibold">Content studio</h2>
      <p className="text-xs text-gray-500">Drafts follow the brand voice. Facts must come from approved evidence; a second person approves. Nothing is published from here.</p>
      {msg && <p role="status" className="text-xs bg-amber-50 border rounded p-2">{msg}</p>}
      <div className="flex gap-2 items-center text-xs"><select aria-label="Brand profile" className="border rounded" value={pid} onChange={(e) => setPid(e.target.value)}>
        <option value="">New profile…</option>{profiles.map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}</select></div>
      <ProfileForm key={pid || "new"} p={profile} onSaved={load} say={say} />
      <ImageForm say={say} />
      {profile && <section className="border rounded p-3 bg-white space-y-2 text-xs">
        <h3 className="font-semibold text-sm">New draft</h3>
        <div className="flex flex-wrap gap-2">
          <select aria-label="Channel" className="border rounded" value={g.channel} onChange={(e) => setG({ ...g, channel: e.target.value })}>{Object.entries(opts.channels).map(([c, n]) => <option key={c} value={c}>{c} (≤{n})</option>)}</select>
          <select aria-label="Template" className="border rounded" value={g.template} onChange={(e) => setG({ ...g, template: e.target.value })}>{Object.keys(opts.templates).map((t) => <option key={t}>{t}</option>)}</select>
        </div>
        <textarea aria-label="Brief" rows={2} placeholder="Brief, e.g. Launch POVU AllClean 1 L (POVU-ALC-1L) for Nairobi shops" className="border rounded px-1 w-full" value={g.brief} onChange={(e) => setG({ ...g, brief: e.target.value })} />
        <fieldset className="flex flex-wrap gap-2"><legend>Evidence to use</legend>{profile.evidence.map((e) => <label key={e.id} className="flex gap-1"><input type="checkbox" checked={g.evidence.includes(e.id)}
          onChange={(x) => setG({ ...g, evidence: x.target.checked ? [...g.evidence, e.id] : g.evidence.filter((y) => y !== e.id) })} />{e.id}: {e.text}</label>)}</fieldset>
        <button className="bg-indigo-600 text-white rounded px-3 py-1" onClick={() => apiClient.post("/api/v1/content-studio/drafts", { profile_id: pid, channel: g.channel, template: g.template, brief: g.brief, evidence_ids: g.evidence }).then(after).catch((e) => say(err(e)))}>Write draft</button>
      </section>}
      <div className="grid gap-3 lg:grid-cols-[20rem_1fr]">
        <ul className="border rounded bg-white divide-y text-xs">{drafts.length === 0 ? <li className="p-2 text-gray-500">No drafts.</li> : drafts.map((d) =>
          <li key={d.id} onClick={() => pick(d)} className={`p-2 cursor-pointer ${cur?.id === d.id ? "bg-indigo-50" : ""}`}><b>{d.channel}</b> · {d.template} · {d.status.toLowerCase()}<div className="text-gray-500 truncate">{d.body}</div></li>)}</ul>
        {cur && <section className="border rounded p-3 bg-white space-y-2 text-xs">
          <p>Status <b>{cur.status}</b> · written by {cur.engine === "rules" ? "the rule engine (no AI cost)" : `${cur.engine} (≈ $${cur.cost.toFixed(4)})`} · {cur.created_by}{cur.source_id ? " · repurposed" : ""}</p>
          <textarea aria-label="Draft text" rows={8} className="border rounded px-1 w-full" value={edit} onChange={(e) => setEdit(e.target.value)} disabled={!["DRAFT", "REJECTED"].includes(cur.status)} />
          <p className={edit.length > (opts.channels[cur.channel] ?? 1e9) ? "text-red-600" : "text-gray-500"}>{edit.length}/{opts.channels[cur.channel]} characters</p>
          <ul>{cur.findings.map((f, i) => <li key={i} className={f.level === "error" ? "text-red-700" : "text-gray-600"}>{f.level === "error" ? "✗" : "•"} {f.message}</li>)}</ul>
          <div className="flex flex-wrap gap-2">
            {["DRAFT", "REJECTED"].includes(cur.status) && <button className="border rounded px-2 py-1" onClick={() => apiClient.patch(`/api/v1/content-studio/drafts/${cur.id}`, { body: edit }).then(after).catch((e) => say(err(e)))}>Save &amp; re-check</button>}
            {cur.status === "DRAFT" && <button className="border rounded px-2 py-1" onClick={() => apiClient.post(`/api/v1/content-studio/drafts/${cur.id}/submit`).then(after).catch((e) => say(err(e)))}>Submit for approval</button>}
            {cur.status === "IN_REVIEW" && <><button className="border rounded px-2 py-1 bg-green-50" onClick={() => apiClient.post(`/api/v1/content-studio/drafts/${cur.id}/decide`, { ok: true }).then(after).catch((e) => say(err(e)))}>Approve</button>
              <button className="border rounded px-2 py-1" onClick={() => apiClient.post(`/api/v1/content-studio/drafts/${cur.id}/decide`, { ok: false, note: "Needs changes" }).then(after).catch((e) => say(err(e)))}>Reject</button></>}
            <select aria-label="Repurpose channel" className="border rounded" onChange={(e) => e.target.value && apiClient.post("/api/v1/content-studio/drafts", { profile_id: cur.profile_id, channel: e.target.value, template: cur.template, brief: "", source_id: cur.id }).then(after).catch((x) => say(err(x)))} value="">
              <option value="">Repurpose for…</option>{Object.keys(opts.channels).filter((c) => c !== cur.channel).map((c) => <option key={c}>{c}</option>)}</select>
            <fieldset className="flex flex-wrap gap-1 items-center border rounded px-1"><legend>Remix to channels</legend>{Object.keys(opts.channels).filter((c) => c !== cur.channel).map((c) =>
              <label key={c} className="flex gap-1"><input type="checkbox" checked={remix.includes(c)} onChange={(e) => setRemix(e.target.checked ? [...remix, c] : remix.filter((x) => x !== c))} />{c}</label>)}
              <button className="border rounded px-2" disabled={remix.length === 0} onClick={() => apiClient.post(`/api/v1/content-studio/drafts/${cur.id}/remix`, { channels: remix }).then((r) => { say(`${r.data.length} drafts created (${r.data.map((d: Draft) => `${d.channel}: ${d.engine}`).join(", ")}); each needs its own approval.`); setRemix([]); load(); }).catch((e) => say(err(e)))}>Remix</button></fieldset>
            {cur.status === "APPROVED" && <><input aria-label="Website page id" placeholder="Website page id" className="border rounded px-1" value={pageId} onChange={(e) => setPageId(e.target.value)} />
              <button className="border rounded px-2 py-1" onClick={() => apiClient.post(`/api/v1/content-studio/drafts/${cur.id}/to-page`, { page_id: pageId }).then(() => say("Added to the page draft — it still needs review and publishing.")).catch((e) => say(err(e)))}>Add to page draft</button></>}
          </div>
          <details><summary>History</summary><ul>{cur.history.map((h, i) => <li key={i}>{new Date(h.at).toLocaleString()} · {h.by} · {h.action}{h.note ? ` · ${h.note}` : ""}</li>)}</ul></details>
        </section>}
      </div>
    </div>
  );
}
