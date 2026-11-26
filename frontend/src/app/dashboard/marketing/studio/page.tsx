"use client";
// M49.S01.T012 Integrated Marketing Studio: one workspace per campaign. It LINKS records that other modules own
// (assets, designs, posts, ad trees, audiences) and shows their live state; each channel is still approved and
// submitted in its own module. Analytics come only from stored data ("No data" otherwise).
import { useCallback, useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { apiClient } from "@/lib/api";
import { useAuth } from "@/context/AuthContext";
import { RequirePermission } from "@/components/PermissionGuard";

type Item = { link_id?: string; kind: string; ref_id: string; label: string; status?: string; version?: number; linked_version?: number | null; usable?: boolean;
  outdated?: boolean; submitted?: boolean; approved?: boolean; approval?: string; mode?: string; via?: string; members?: number; provider?: string; audience_size?: number | null; missing?: boolean };
type Req = { id: string; amount: string; cap: string; status: string; note: string | null; requested_by: string; decided_by: string | null };
type Studio = {
  campaign: { id: string; code: string; name: string; status: string; approval_status: string; objective: string | null; start_date: string; end_date: string; budget: string | null };
  brief: { data: Partial<BriefForm> & { channels?: string[]; product_skus?: string[] }; version: number; history: { version: number; by: string }[]; updated_by: string | null };
  creative: Item[]; audience: Item[]; missing: Item[];
  channels: Record<"email" | "social" | "ads", { items: Item[]; submitted: boolean }>;
  budget: { amount: string | null; cap: string; pending: Req | null; requests: Req[] };
  checklist: { step: string; done: boolean; reason: string | null }[];
  user: { can_write: boolean; can_finance_approve: boolean };
};
type BriefForm = { summary: string; key_message: string; audience_notes: string; kpi: string };
type Analytics = {
  attribution: { orders: number; revenue: Record<string, string>; leads: number; leads_by_source: Record<string, number>; has_data: boolean; basis: string[] };
  channels: { ads: { has_data: boolean; by_platform: Record<string, { rows: number; impressions: number; clicks: number; conversions: number; spend: string }> };
    social: { has_data: boolean; by_network: Record<string, Record<string, string>> }; email: { note: string } };
  spend: { approved_brand_spend: Record<string, string>; roas: Record<string, string>; note: string };
  no_data: boolean;
};
type Cands = Record<string, { ref_id: string; label: string; version?: number; status?: string; members?: number }[]>;
type Row = { id: string; code: string; name: string; status: string; approval_status: string; budget: string | null; has_brief: boolean };

const API = "/api/v1/marketing-studio";
const CH = ["email", "social", "ads"] as const;
const KIND_NAME: Record<string, string> = { DAM_ASSET: "Approved asset (library)", BRAND_ASSET: "Brand asset", EMAIL_DESIGN: "E-mail design", SOCIAL_POST: "Social post",
  AD_TREE: "Ad campaign", AUDIENCE_SYNC: "Audience sync", AUDIENCE: "Audience", EMAIL_CAMPAIGN: "E-mail campaign" };
const err = (e: unknown) => { const d = (e as { response?: { data?: { detail?: unknown } } }).response?.data?.detail; return typeof d === "string" ? d : "Something went wrong."; };

function Badge({ children, tone }: { children: React.ReactNode; tone: "ok" | "warn" | "bad" | "idle" }) {
  const c = { ok: "bg-emerald-100 text-emerald-800", warn: "bg-amber-100 text-amber-800", bad: "bg-red-100 text-red-800", idle: "bg-gray-100 text-gray-700" }[tone];
  return <span className={`inline-block rounded px-1.5 py-0.5 text-[11px] ${c}`}>{children}</span>;
}

function ItemRow({ it, onRemove, canWrite }: { it: Item; onRemove?: (id: string) => void; canWrite: boolean }) {
  return <li className="flex flex-wrap items-center gap-2 border rounded px-2 py-1 text-xs bg-white">
    <span className="font-medium break-all">{it.label}</span>
    <Badge tone="idle">{KIND_NAME[it.kind] ?? it.kind}</Badge>
    {it.status && <Badge tone={it.submitted || it.usable ? "ok" : "warn"}>{it.status}</Badge>}
    {it.approval && <Badge tone={it.approval === "APPROVED" ? "ok" : "warn"}>approval {it.approval}</Badge>}
    {it.approved === false && <Badge tone="warn">not approved</Badge>}
    {it.mode && <Badge tone="idle">{it.mode === "SIMULATED" ? "local / simulated" : it.mode}</Badge>}
    {it.outdated && <Badge tone="warn">newer version exists (linked v{it.linked_version})</Badge>}
    {it.via === "campaign_tag" && <Badge tone="idle">via campaign tag</Badge>}
    {it.members !== undefined && <Badge tone="idle">{it.members} members</Badge>}
    {it.link_id && onRemove && <button className="ml-auto border rounded px-2 py-0.5 disabled:opacity-50" disabled={!canWrite} title={canWrite ? "" : "Marketing editors only"}
      onClick={() => onRemove(it.link_id!)}>Unlink</button>}
  </li>;
}

function Picker({ kinds, cands, canWrite, onLink }: { kinds: string[]; cands: Cands | null; canWrite: boolean; onLink: (kind: string, ref: string) => void }) {
  const opts = kinds.flatMap((k) => (cands?.[k] ?? []).map((c) => ({ ...c, kind: k })));
  const [sel, setSel] = useState("");
  const [kind, ref] = sel.split("|");
  const reason = !canWrite ? "Marketing editors only" : !opts.length ? "Nothing approved and available to link yet" : !sel ? "Choose a record first" : "";
  return <div className="flex flex-wrap gap-2 items-center text-xs">
    <select aria-label="Record to link" className="border rounded px-1 py-1 max-w-full" value={sel} onChange={(e) => setSel(e.target.value)}>
      <option value="">Choose a record to link…</option>
      {opts.map((o) => <option key={o.kind + o.ref_id} value={`${o.kind}|${o.ref_id}`}>{KIND_NAME[o.kind]}: {o.label}{o.version ? ` (v${o.version})` : ""}</option>)}
    </select>
    <button className="border rounded px-3 py-1 bg-white disabled:opacity-50" disabled={!!reason} onClick={() => { onLink(kind, ref); setSel(""); }}>Link</button>
    {reason && <span className="text-gray-500">{reason}</span>}
  </div>;
}

function BriefCard({ s, say, reload }: { s: Studio; say: (m: string) => void; reload: () => void }) {
  const d = s.brief.data;
  const [f, setF] = useState({ summary: d.summary ?? "", key_message: d.key_message ?? "", audience_notes: d.audience_notes ?? "", kpi: d.kpi ?? "",
    channels: d.channels ?? [], skus: (d.product_skus ?? []).join(", ") });
  const reason = !s.user.can_write ? "Marketing editors only" : !f.summary.trim() || !f.key_message.trim() ? "Summary and key message are required" : "";
  const save = () => apiClient.put(`${API}/campaigns/${s.campaign.id}/brief`, { summary: f.summary, key_message: f.key_message, audience_notes: f.audience_notes, kpi: f.kpi,
    channels: f.channels, product_skus: f.skus.split(",").map((x) => x.trim()).filter(Boolean) }).then(() => { say("Brief saved."); reload(); }).catch((e) => say(err(e)));
  const t = (k: "summary" | "key_message" | "audience_notes" | "kpi", label: string, rows = 2) => <label className="text-xs block">{label}
    <textarea aria-label={label} rows={rows} className="border rounded px-1 w-full block" value={f[k]} onChange={(e) => setF({ ...f, [k]: e.target.value })} /></label>;
  return <div className="space-y-2">
    <div className="grid gap-2 sm:grid-cols-2">{t("summary", "Summary", 3)}{t("key_message", "Key message", 3)}{t("audience_notes", "Audience notes")}{t("kpi", "KPI")}</div>
    <label className="text-xs block">Product SKUs (comma separated, e.g. POVU-ALC-1L)
      <input aria-label="Product SKUs" className="border rounded px-1 w-full block" value={f.skus} onChange={(e) => setF({ ...f, skus: e.target.value })} /></label>
    <div className="flex flex-wrap gap-3 text-xs" role="group" aria-label="Channels">Channels:
      {CH.map((c) => <label key={c} className="flex items-center gap-1"><input type="checkbox" checked={f.channels.includes(c)}
        onChange={(e) => setF({ ...f, channels: e.target.checked ? [...f.channels, c] : f.channels.filter((x) => x !== c) })} />{c}</label>)}</div>
    <div className="flex flex-wrap items-center gap-2 text-xs">
      <button className="bg-indigo-600 text-white rounded px-3 py-1 disabled:opacity-50" disabled={!!reason} onClick={save}>Save brief</button>
      {reason && <span className="text-gray-500">{reason}</span>}
      <span className="text-gray-500">Version {s.brief.version || "none yet"}{s.brief.updated_by ? ` · by ${s.brief.updated_by}` : ""}</span>
    </div>
  </div>;
}

function BudgetCard({ s, say, reload, canFinance }: { s: Studio; say: (m: string) => void; reload: () => void; canFinance: boolean }) {
  const [amount, setAmount] = useState("");
  const [note, setNote] = useState("");
  const b = s.budget, n = Number(amount), over = n > Number(b.cap);
  const reason = !s.user.can_write ? "Marketing editors only" : b.pending ? "A request is already waiting for finance" : !(n > 0) ? "Enter an amount above 0" : "";
  const post = (p: Promise<unknown>, ok: string) => p.then(() => { say(ok); setAmount(""); setNote(""); reload(); }).catch((e) => say(err(e)));
  return <div className="space-y-2 text-xs">
    <p>Current budget: <b>{b.amount ?? "not set"}</b> · finance cap <b>{b.cap}</b>. Above the cap, a finance approver other than you must approve.</p>
    <div className="flex flex-wrap gap-2 items-end">
      <label>Amount<input aria-label="Budget amount" type="number" min={0} step="0.01" className="border rounded px-1 block" value={amount} onChange={(e) => setAmount(e.target.value)} /></label>
      <label className="grow">Note<input aria-label="Budget note" maxLength={300} className="border rounded px-1 w-full block" value={note} onChange={(e) => setNote(e.target.value)} /></label>
      <button className="bg-indigo-600 text-white rounded px-3 py-1 disabled:opacity-50" disabled={!!reason}
        onClick={() => post(apiClient.post(`${API}/campaigns/${s.campaign.id}/budget`, { amount: n, note: note || null }), over ? "Sent to finance for approval." : "Budget applied.")}>
        {over ? "Request finance approval" : "Set budget"}</button>
    </div>
    {reason && <p className="text-gray-500">{reason}</p>}
    {b.pending && <div className="border rounded p-2 bg-amber-50 space-y-1">
      <p>Waiting for finance: <b>{b.pending.amount}</b> (asked by {b.pending.requested_by}{b.pending.note ? ` — ${b.pending.note}` : ""})</p>
      <div className="flex flex-wrap items-center gap-2">
        <button className="border rounded px-3 py-1 bg-white disabled:opacity-50" disabled={!canFinance} onClick={() => post(apiClient.post(`${API}/budget-requests/${b.pending!.id}/decide`, { ok: true }), "Budget approved.")}>Approve</button>
        <button className="border rounded px-3 py-1 bg-white disabled:opacity-50" disabled={!canFinance} onClick={() => post(apiClient.post(`${API}/budget-requests/${b.pending!.id}/decide`, { ok: false }), "Budget rejected.")}>Reject</button>
        {!canFinance && <span className="text-gray-500">Finance approvers only (finance.approve). The requester can never approve their own request.</span>}
      </div></div>}
    {b.requests.length > 0 && <details><summary className="cursor-pointer">History ({b.requests.length})</summary><ul className="mt-1 space-y-0.5">
      {b.requests.map((r) => <li key={r.id}>{r.amount} · {r.status} · {r.requested_by}{r.decided_by ? ` → ${r.decided_by}` : ""}</li>)}</ul></details>}
  </div>;
}

function AnalyticsCard({ a }: { a: Analytics | null }) {
  if (!a) return <p className="text-xs text-gray-500">Loading…</p>;
  const at = a.attribution;
  return <div className="space-y-2 text-xs">
    {a.no_data && <p className="border rounded p-2 bg-gray-50">No data yet: no attributed orders, leads, ad rows or social metrics are stored for this campaign. Nothing is estimated.</p>}
    <div className="grid gap-2 sm:grid-cols-3">
      <div className="border rounded p-2 bg-white"><p className="text-gray-500">ERP orders attributed</p><p className="text-lg font-semibold">{at.orders || "No data"}</p>
        {Object.entries(at.revenue).map(([c, v]) => <p key={c}>{c} {v}</p>)}</div>
      <div className="border rounded p-2 bg-white"><p className="text-gray-500">Website leads (UTM)</p><p className="text-lg font-semibold">{at.leads || "No data"}</p>
        {Object.entries(at.leads_by_source).map(([k, v]) => <p key={k}>{k}: {v}</p>)}</div>
      <div className="border rounded p-2 bg-white"><p className="text-gray-500">Approved brand spend</p>
        {Object.keys(a.spend.approved_brand_spend).length ? Object.entries(a.spend.approved_brand_spend).map(([c, v]) => <p key={c}>{c} {v}{a.spend.roas[c] ? ` · ROAS ${a.spend.roas[c]}` : ""}</p>) : <p className="text-lg font-semibold">No data</p>}</div>
    </div>
    <div className="grid gap-2 sm:grid-cols-2">
      <div className="border rounded p-2 bg-white"><p className="font-medium">Ads (stored performance rows)</p>
        {a.channels.ads.has_data ? Object.entries(a.channels.ads.by_platform).map(([p, v]) => <p key={p}>{p}: {v.impressions} impr · {v.clicks} clicks · {v.conversions} conv · spend {v.spend}</p>) : <p className="text-gray-500">No data</p>}</div>
      <div className="border rounded p-2 bg-white"><p className="font-medium">Social (metrics as returned by the network)</p>
        {a.channels.social.has_data ? Object.entries(a.channels.social.by_network).map(([n, m]) => <p key={n}>{n}: {Object.entries(m).map(([k, v]) => `${k} ${v}`).join(" · ")}</p>) : <p className="text-gray-500">No data</p>}</div>
    </div>
    <p className="text-gray-500">E-mail: {a.channels.email.note}</p>
    <details><summary className="cursor-pointer">How attribution works</summary><ul className="list-disc pl-4">{at.basis.map((b) => <li key={b}>{b}</li>)}</ul></details>
  </div>;
}

function Card({ n, title, children }: { n: number; title: string; children: React.ReactNode }) {
  return <section className="border rounded p-3 bg-white space-y-2"><h2 className="font-semibold text-sm"><span className="text-indigo-600">{n}.</span> {title}</h2>{children}</section>;
}

function StudioWorkspace() {
  const { hasPermission } = useAuth();
  const [rows, setRows] = useState<Row[]>([]);
  const [cid, setCid] = useState("");
  const [s, setS] = useState<Studio | null>(null);
  const [cands, setCands] = useState<Cands | null>(null);
  const [an, setAn] = useState<Analytics | null>(null);
  const [msg, setMsg] = useState("");
  const [nc, setNc] = useState({ code: "", name: "", start: "", end: "" });

  const list = useCallback(() => apiClient.get(`${API}/campaigns`).then((r) => setRows(r.data)).catch((e) => setMsg(err(e))), []);
  const load = useCallback((id: string) => {
    if (!id) { setS(null); return Promise.resolve(); }
    return Promise.all([apiClient.get(`${API}/campaigns/${id}`), apiClient.get(`${API}/campaigns/${id}/candidates`), apiClient.get(`${API}/campaigns/${id}/analytics`)])
      .then(([a, b, c]) => { setS(a.data); setCands(b.data); setAn(c.data); }).catch((e) => setMsg(err(e)));
  }, []);
  useEffect(() => { list(); }, [list]);
  useEffect(() => { setS(null); setAn(null); setMsg(""); load(cid); }, [cid, load]);

  const reload = () => { load(cid); list(); };
  const link = (kind: string, ref_id: string) => apiClient.post(`${API}/campaigns/${cid}/links`, { kind, ref_id }).then(() => { setMsg("Linked."); reload(); }).catch((e) => setMsg(err(e)));
  const unlink = (lid: string) => apiClient.delete(`${API}/campaigns/${cid}/links/${lid}`).then(() => { setMsg("Unlinked."); reload(); }).catch((e) => setMsg(err(e)));
  const createReason = !hasPermission("campaigns.create") ? "Needs campaigns.create" : !nc.code.trim() || !nc.name.trim() || !nc.start || !nc.end ? "Code, name and both dates are required" : nc.end < nc.start ? "End date is before the start date" : "";
  const create = () => apiClient.post("/api/v1/marketing/campaigns", { campaign_code: nc.code.trim(), campaign_name: nc.name.trim(), campaign_type: "DIGITAL", start_date: nc.start, end_date: nc.end })
    .then((r) => { setNc({ code: "", name: "", start: "", end: "" }); setMsg("Campaign created."); list().then(() => setCid(r.data.id)); }).catch((e) => setMsg(err(e)));
  const approveReason = !hasPermission("campaigns.approve") ? "Needs campaigns.approve" : s?.campaign.approval_status === "APPROVED" ? "Already approved" : "";
  const sel = useMemo(() => rows.find((r) => r.id === cid), [rows, cid]);

  return <div className="p-3 sm:p-6 space-y-3 max-w-6xl mx-auto">
    <header className="flex flex-wrap items-center gap-2 justify-between">
      <div><h1 className="text-xl font-bold">Marketing Studio</h1>
        <p className="text-xs text-gray-500">Brief → creative → audience → channels → budget → analytics. Each channel is approved and submitted in its own module; this page links and tracks it.</p></div>
      <label className="text-xs">Campaign
        <select aria-label="Campaign" className="border rounded px-2 py-1 block min-w-[14rem]" value={cid} onChange={(e) => setCid(e.target.value)}>
          <option value="">Choose a campaign…</option>
          {rows.map((r) => <option key={r.id} value={r.id}>{r.code} · {r.name}</option>)}</select></label>
    </header>
    {msg && <p role="status" className="text-xs border rounded px-2 py-1 bg-indigo-50">{msg}</p>}

    {!s && <section className="border rounded p-3 bg-white space-y-2 text-xs">
      <h2 className="font-semibold text-sm">{cid ? "Loading…" : "Start a campaign"}</h2>
      {!cid && <><p className="text-gray-500">Pick a campaign above, or create one here (same record as Marketing → Campaigns).</p>
        <div className="grid gap-2 sm:grid-cols-4">
          <input aria-label="Campaign code" placeholder="Code, e.g. POVU-SPRING" className="border rounded px-1 py-1" value={nc.code} onChange={(e) => setNc({ ...nc, code: e.target.value })} />
          <input aria-label="Campaign name" placeholder="Name, e.g. POVU AllClean spring" className="border rounded px-1 py-1" value={nc.name} onChange={(e) => setNc({ ...nc, name: e.target.value })} />
          <input aria-label="Start date" type="date" className="border rounded px-1 py-1" value={nc.start} onChange={(e) => setNc({ ...nc, start: e.target.value })} />
          <input aria-label="End date" type="date" className="border rounded px-1 py-1" value={nc.end} onChange={(e) => setNc({ ...nc, end: e.target.value })} /></div>
        <div className="flex items-center gap-2"><button className="bg-indigo-600 text-white rounded px-3 py-1 disabled:opacity-50" disabled={!!createReason} onClick={create}>Create campaign</button>
          {createReason && <span className="text-gray-500">{createReason}</span>}</div></>}
    </section>}

    {s && <>
      <section className="border rounded p-3 bg-white space-y-2">
        <div className="flex flex-wrap items-center gap-2 text-xs">
          <b className="text-sm">{s.campaign.name}</b><Badge tone="idle">{s.campaign.code}</Badge><Badge tone="idle">{s.campaign.status}</Badge>
          <Badge tone={s.campaign.approval_status === "APPROVED" ? "ok" : "warn"}>campaign approval {s.campaign.approval_status}</Badge>
          <span className="text-gray-500">{s.campaign.start_date} → {s.campaign.end_date}</span>
          <button className="ml-auto border rounded px-3 py-1 disabled:opacity-50" disabled={!!approveReason} title={approveReason}
            onClick={() => apiClient.post(`/api/v1/marketing/campaigns/${cid}/approve`).then(() => { setMsg("Campaign approved."); reload(); }).catch((e) => setMsg(err(e)))}>Approve campaign</button>
          {approveReason && <span className="text-gray-500">{approveReason}</span>}
          {sel && <Link className="underline" href={`/dashboard/marketing/campaigns/${cid}`}>Open campaign record</Link>}
        </div>
        <ol className="flex flex-wrap gap-1.5 text-[11px]" aria-label="Progress">
          {s.checklist.map((c) => <li key={c.step} title={c.reason ?? "Done"}><Badge tone={c.done ? "ok" : "warn"}>{c.done ? "✓" : "○"} {c.step}{c.done ? "" : ` — ${c.reason}`}</Badge></li>)}</ol>
      </section>

      <div className="grid gap-3 lg:grid-cols-2">
        <Card n={1} title="Brief"><BriefCard key={s.brief.version} s={s} say={setMsg} reload={reload} /></Card>
        <Card n={2} title="Creative (approved assets and published designs only)">
          <ul className="space-y-1">{s.creative.map((i) => <ItemRow key={i.link_id} it={i} canWrite={s.user.can_write} onRemove={unlink} />)}</ul>
          {!s.creative.length && <p className="text-xs text-gray-500">Nothing linked. Assets must be APPROVED in the library; create drafts in <Link className="underline" href="/dashboard/marketing/content-studio">Content Studio</Link> or <Link className="underline" href="/dashboard/crm/email-designer">E-mail designer</Link>.</p>}
          <Picker kinds={["DAM_ASSET", "BRAND_ASSET", "EMAIL_DESIGN"]} cands={cands} canWrite={s.user.can_write} onLink={link} />
        </Card>
        <Card n={3} title="Audience">
          <ul className="space-y-1">{s.audience.map((i) => <ItemRow key={i.link_id} it={i} canWrite={s.user.can_write} onRemove={unlink} />)}</ul>
          {!s.audience.length && <p className="text-xs text-gray-500">Build segments in <Link className="underline" href="/dashboard/crm/audiences">Audiences</Link>; platform uploads are approved in <Link className="underline" href="/dashboard/crm/audiences/sync">Audience sync</Link>. Only consented members are ever uploaded.</p>}
          <Picker kinds={["AUDIENCE", "AUDIENCE_SYNC"]} cands={cands} canWrite={s.user.can_write} onLink={link} />
        </Card>
        <Card n={5} title="Budget and finance cap"><BudgetCard s={s} say={setMsg} reload={reload} canFinance={s.user.can_finance_approve} /></Card>
      </div>

      <Card n={4} title="Channels (submitted through their own approval flows)">
        <div className="grid gap-3 md:grid-cols-3">
          {CH.map((c) => {
            const href = { email: "/dashboard/crm/email-campaigns", social: "/dashboard/marketing/social-media", ads: "/dashboard/marketing/ads/lifecycle" }[c];
            const wanted = s.brief.data.channels?.includes(c);
            return <div key={c} className="border rounded p-2 space-y-1 bg-gray-50">
              <div className="flex items-center gap-2 text-xs"><b className="capitalize">{c}</b>
                {wanted === false || !s.brief.data.channels?.length ? null : <Badge tone="idle">in brief</Badge>}
                <Badge tone={s.channels[c].submitted ? "ok" : "warn"}>{s.channels[c].submitted ? "submitted (local)" : "not submitted"}</Badge>
                <Link className="ml-auto underline text-xs" href={href}>Open {c} module</Link></div>
              <ul className="space-y-1">{s.channels[c].items.map((i) => <ItemRow key={i.kind + i.ref_id} it={i} canWrite={s.user.can_write} onRemove={unlink} />)}</ul>
              {!s.channels[c].items.length && <p className="text-xs text-gray-500">{c === "email" ? "Link a published design above, or create a segment campaign with this campaign selected." : "Nothing linked yet."}</p>}
              {c !== "email" && <Picker kinds={[c === "social" ? "SOCIAL_POST" : "AD_TREE"]} cands={cands} canWrite={s.user.can_write} onLink={link} />}
            </div>;
          })}
        </div>
        <p className="text-[11px] text-gray-500">&quot;Submitted (local)&quot; means a simulated submission or a manual export. Live publishing needs the owner&apos;s activation in each module.</p>
      </Card>

      <Card n={6} title="Analytics and ERP attribution"><AnalyticsCard a={an} /></Card>
    </>}
  </div>;
}

export default function StudioPage() {
  return <RequirePermission permission="marketing.view"><StudioWorkspace /></RequirePermission>;
}
