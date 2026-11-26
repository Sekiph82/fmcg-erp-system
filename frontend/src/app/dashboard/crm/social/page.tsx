"use client";
// M44.S01.T006–T008 social: channels, composer + calendar with approval/versions, listening inbox.
// M48.S01.T005 asynchronous publish states (submitted is not live), TikTok creator options + consent, submit/refresh/cancel.
import { useCallback, useEffect, useMemo, useState } from "react";
import { apiClient } from "@/lib/api";

interface Channel { id: string; network: string; name: string; external_id: string; time_zone: string; listen_enabled: boolean; publishing: string; mode: string; tiktok_audited?: boolean; options: Record<string, string | boolean> }
interface Post { id: string; channel_id: string; network: string; channel: string; text: string; media: { url: string; kind: string; alt_text?: string; thumbnail_url?: string }[]; format: string | null; flow_phase: string | null;
  link: string | null; campaign_tag: string | null; scheduled_at: string | null; time_zone: string; status: string; version: number;
  approved: boolean; approved_by: string | null; error: string | null; route: string; problems: string[]; conflicts: string[];
  history: { at: string; event: string; version: number; detail: string }[]; external_post_id: string | null; provider_ref: string | null;
  provider_status: string | null; fail_reason: string | null; publish_mode: string | null; published_at: string | null;
  publish_options: TikTokOpts | null }
interface TikTokOpts { privacy_level: string; disable_comment: boolean; disable_duet: boolean; disable_stitch: boolean; source: string; consent: boolean; consent_by?: string }
interface CreatorInfo { creator_nickname: string | null; privacy_level_options: string[]; provider_privacy_level_options: string[]; audited: boolean;
  comment_disabled: boolean; duet_disabled: boolean; stitch_disabled: boolean; max_video_post_duration_sec: number | null; mode: string }
interface Item { id: string; network: string; kind: string; author: string | null; text: string | null; occurred_at: string; source: string;
  sentiment: string | null; topics: string[]; evidence: { positive?: string[]; negative?: string[]; source?: { network: string; external_id: string; via: string } }; status: string; assigned_to: string | null; reply_draft: string | null;
  reply_status: string | null; reply_requested_by: string | null; reply_approved_by: string | null; reply_external_id: string | null; reply_error: string | null; provider_state: string | null;
  ops: Record<"reply" | "hide" | "delete", { available: boolean; reason: string }> }

const NETS = ["facebook", "instagram", "linkedin", "tiktok", "x", "youtube"];
const err = (e: unknown) => { const d = (e as { response?: { data?: { detail?: unknown } } }).response?.data?.detail; return typeof d === "string" ? d : "Request failed."; };
const newKey = () => (typeof crypto !== "undefined" && crypto.randomUUID ? crypto.randomUUID() : `${Date.now()}-${Math.random().toString(36).slice(2)}`);
const IN_FLIGHT = ["SUBMITTING", "SUBMITTED", "PROCESSING", "UNKNOWN"];
const STATE_TEXT: Record<string, string> = { EXPORTED: "exported / delivered as a draft — not published", SUBMITTING: "submitting…", SUBMITTED: "submitted — not live yet", PROCESSING: "processing at the network — not live yet",
  UNKNOWN: "outcome unknown — reconciling", PUBLISHED: "published (confirmed by the network)", FAILED: "failed / rejected" };
const STATE_CLS: Record<string, string> = { PUBLISHED: "bg-emerald-100 text-emerald-800", FAILED: "bg-red-100 text-red-800", UNKNOWN: "bg-amber-100 text-amber-800",
  SUBMITTED: "bg-sky-100 text-sky-800", PROCESSING: "bg-sky-100 text-sky-800", SUBMITTING: "bg-sky-100 text-sky-800" };
const PRIVACY: Record<string, string> = { PUBLIC_TO_EVERYONE: "Everyone", MUTUAL_FOLLOW_FRIENDS: "Friends", FOLLOWER_OF_CREATOR: "Followers", SELF_ONLY: "Only me (private)" };

function TikTokOptions({ post, run }: { post: Post; run: (fn: () => Promise<unknown>, ok: string) => Promise<void> }) {
  const [info, setInfo] = useState<CreatorInfo | null>(null);
  const [loadErr, setLoadErr] = useState<string | null>(null);
  const cur = post.publish_options;
  // TikTok requires an explicit choice: no privacy is pre-selected and consent starts unticked
  const [o, setO] = useState({ privacy_level: "", disable_comment: cur?.disable_comment ?? false, disable_duet: cur?.disable_duet ?? false,
    disable_stitch: cur?.disable_stitch ?? false, source: cur?.source ?? "PULL_FROM_URL", consent: false });
  const load = () => { setLoadErr(null); apiClient.get(`/api/v1/social/channels/${post.channel_id}/tiktok/creator-info`)
    .then((r) => { const d: CreatorInfo = r.data; setInfo(d); setO((x) => ({ ...x, disable_comment: x.disable_comment || d.comment_disabled,
      disable_duet: x.disable_duet || d.duet_disabled, disable_stitch: x.disable_stitch || d.stitch_disabled })); })
    .catch((e) => setLoadErr(err(e))); };
  const why = !info ? "Load the creator's options first." : !o.privacy_level ? "Choose who can see the post." : !o.consent ? "Tick the consent box." : null;
  return (
    <details className="border rounded p-2 bg-gray-50"><summary className="cursor-pointer">TikTok options {cur ? `· ${PRIVACY[cur.privacy_level] ?? cur.privacy_level} · consent by ${cur.consent_by ?? "?"}` : "· not set (required)"}</summary>
      <div className="space-y-1 mt-1">
        <button type="button" className="underline" onClick={load}>Load creator options from TikTok</button>
        {loadErr && <p className="text-red-600">{loadErr}</p>}
        {info && <>
          <p className="text-gray-600">Posting as {info.creator_nickname ?? "creator"}{info.max_video_post_duration_sec ? ` · videos up to ${info.max_video_post_duration_sec}s` : ""}.
            {!info.audited && " This app is not audited by TikTok yet, so posts can only be private (Only me)."}</p>
          <label className="flex gap-1 items-center">Who can see it
            <select aria-label="TikTok privacy" className="border rounded px-1" value={o.privacy_level} onChange={(e) => setO({ ...o, privacy_level: e.target.value })}>
              <option value="">Choose…</option>{info.privacy_level_options.map((v) => <option key={v} value={v}>{PRIVACY[v] ?? v}</option>)}</select></label>
          <div className="flex flex-wrap gap-3">
            <label><input type="checkbox" checked={!o.disable_comment} disabled={info.comment_disabled} onChange={(e) => setO({ ...o, disable_comment: !e.target.checked })} /> Allow comments{info.comment_disabled && " (off in the creator's settings)"}</label>
            <label><input type="checkbox" checked={!o.disable_duet} disabled={info.duet_disabled} onChange={(e) => setO({ ...o, disable_duet: !e.target.checked })} /> Allow Duet{info.duet_disabled && " (off)"}</label>
            <label><input type="checkbox" checked={!o.disable_stitch} disabled={info.stitch_disabled} onChange={(e) => setO({ ...o, disable_stitch: !e.target.checked })} /> Allow Stitch{info.stitch_disabled && " (off)"}</label>
          </div>
          <label className="flex gap-1 items-center">Video source
            <select aria-label="TikTok video source" className="border rounded px-1" value={o.source} onChange={(e) => setO({ ...o, source: e.target.value })}>
              <option value="PULL_FROM_URL">TikTok pulls the URL (verified domain)</option><option value="FILE_UPLOAD">Upload the file in chunks</option></select></label>
          <label className="flex gap-1 items-start"><input type="checkbox" aria-label="TikTok consent" checked={o.consent} onChange={(e) => setO({ ...o, consent: e.target.checked })} />
            <span>I consent to this video being posted to the TikTok account above with these settings, and agree to TikTok&apos;s Music Usage Confirmation.</span></label>
          <button type="button" disabled={!!why} title={why ?? ""} className="border rounded px-2 py-0.5 disabled:opacity-50"
            onClick={() => run(() => apiClient.put(`/api/v1/social/posts/${post.id}/tiktok-options`, o), "TikTok options saved.")}>Save TikTok options</button>
          {why && <span className="ml-2 text-gray-500">{why}</span>}
        </>}
      </div>
    </details>);
}

// M49.S01.T007-T010: format-aware composer (only what each network's API offers, disabled with the exact reason), capability
// matrix, per-post metrics read from the network, listening/moderation inbox (assign, approved reply, hide/delete where allowed).
interface Fmt { key: string; label: string; available: boolean; reason: string | null; verified: boolean; note: string | null; schedule: string;
  media_min: number; media_max: number; kinds: string[]; alt_text: boolean; link: string; max_text: number }
interface Cap { network: string; formats: Fmt[]; scheduling: string; notes: string[]; publishing: string; mode: string;
  insights: { available: boolean; note: string }; moderation: Record<string, { available: boolean; note: string; verified: boolean }> }
interface MediaRow { url: string; kind: string; alt_text: string; thumbnail_url: string }
interface Metric { metric: string; value: number; source: string; fetched_at: string }
type FieldDef = { key: string; label: string; type: "text" | "bool" | "number" | "select" | "datetime" | "tags"; nets: string; fmts?: string[]; options?: string[]; hint?: string };

const FIELDS: FieldDef[] = [
  { key: "native_schedule", label: "Use Facebook's own scheduler (needs a time 10 min to 30 days ahead)", type: "bool", nets: "facebook", fmts: ["text", "link", "photo", "photos", "video", "reel"] },
  { key: "title", label: "Video title", type: "text", nets: "facebook", fmts: ["video", "reel"] },
  { key: "share_to_feed", label: "Also show the Reel in the feed", type: "bool", nets: "instagram", fmts: ["reel"] },
  { key: "cover_url", label: "Reel cover image URL (https)", type: "text", nets: "instagram", fmts: ["reel"] },
  { key: "resumable", label: "Resumable upload (only on the Facebook Login path)", type: "bool", nets: "instagram", fmts: ["video", "reel"] },
  { key: "article_title", label: "Article title (required, LinkedIn does not read the page)", type: "text", nets: "linkedin", fmts: ["link"] },
  { key: "article_description", label: "Article description", type: "text", nets: "linkedin", fmts: ["link"] },
  { key: "article_thumbnail_url", label: "Article thumbnail image URL", type: "text", nets: "linkedin", fmts: ["link"] },
  { key: "video_title", label: "Video title", type: "text", nets: "linkedin", fmts: ["video"] },
  { key: "title", label: "YouTube title (1-100 characters)", type: "text", nets: "youtube" },
  { key: "made_for_kids", label: "Made for kids?", type: "select", nets: "youtube", options: ["", "no", "yes"], hint: "YouTube requires this declaration." },
  { key: "privacy_status", label: "Visibility", type: "select", nets: "youtube", options: ["private", "unlisted", "public"] },
  { key: "publish_at", label: "Release time (YouTube publishAt; video stays private until then)", type: "datetime", nets: "youtube" },
  { key: "tags", label: "Tags (comma separated)", type: "tags", nets: "youtube" },
  { key: "thumbnail_url", label: "Custom thumbnail URL", type: "text", nets: "youtube" },
  { key: "playlist_id", label: "Add to playlist id", type: "text", nets: "youtube" },
  { key: "description", label: "Description", type: "text", nets: "tiktok", fmts: ["photo", "photo_inbox"] },
  { key: "photo_cover_index", label: "Cover photo number (0 = first)", type: "number", nets: "tiktok", fmts: ["photo", "photo_inbox"] },
  { key: "video_cover_timestamp_ms", label: "Cover frame (ms)", type: "number", nets: "tiktok", fmts: ["video"] },
  { key: "is_aigc", label: "AI-generated content", type: "bool", nets: "tiktok", fmts: ["video"] },
  { key: "brand_content_toggle", label: "Paid partnership (brand content)", type: "bool", nets: "tiktok", fmts: ["video"] },
];
const EMPTY = { channel_id: "", format: "", text: "", media: [] as MediaRow[], link: "", campaign_tag: "", when: "", key: newKey(), fopts: {} as Record<string, string | boolean> };
const OPS = ["reply", "hide", "delete"] as const;

function buildFopts(net: string, fmt: string, f: Record<string, string | boolean>) {
  const out: Record<string, unknown> = {};
  for (const d of FIELDS) {
    if (d.nets !== net || (d.fmts && !d.fmts.includes(fmt))) continue;
    const v = f[d.key];
    if (v === undefined || v === "" || v === false) continue;
    out[d.key] = d.type === "number" ? Number(v) : d.type === "tags" ? String(v).split(",").map((t) => t.trim()).filter(Boolean)
      : d.key === "made_for_kids" ? v === "yes" : d.type === "datetime" ? new Date(String(v)).toISOString() : v;
  }
  if (net === "youtube" && f.made_for_kids === "no") out.made_for_kids = false;
  return out;
}

function Insights({ post }: { post: Post }) {
  const [m, setM] = useState<Metric[] | null>(null);
  const [e, setE] = useState<string | null>(null);
  const ok = post.status === "PUBLISHED" && !!post.external_post_id;
  const call = (path: "get" | "post") => (path === "get" ? apiClient.get(`/api/v1/social/posts/${post.id}/insights`) : apiClient.post(`/api/v1/social/posts/${post.id}/insights/refresh`))
    .then((r) => { setM(r.data.metrics); setE(null); }).catch((x) => setE(err(x)));
  return (
    <details className="border rounded p-1" onToggle={(ev) => { if ((ev.target as HTMLDetailsElement).open && m === null && ok) call("get"); }}>
      <summary className="cursor-pointer">Metrics</summary>
      <button type="button" disabled={!ok} title={ok ? "" : "Only a post confirmed as published (with a network post id) has metrics."} className="underline disabled:opacity-50 disabled:no-underline" onClick={() => call("post")}>Read from the network</button>
      {!ok && <span className="ml-2 text-gray-500">Not published yet: nothing to read, and none is estimated.</span>}
      {e && <p className="text-red-600">{e}</p>}
      {m && (m.length === 0 ? <p className="text-gray-500">No metrics stored yet.</p> : <ul>{m.map((x) => <li key={x.metric}>{x.metric}: <b>{x.value}</b> <span className="text-gray-400">({x.source}, {new Date(x.fetched_at).toLocaleString()})</span></li>)}</ul>)}
    </details>);
}

function CapabilityTable({ caps }: { caps: Cap[] }) {
  return (
    <section className="space-y-3">
      <p className="text-xs text-gray-500">What each network&apos;s official API allows (M48 capability matrix, checked 2026-11-26). Unavailable means the API has no such operation, not that we forgot it. Manual export is the only fallback, and only for what the API cannot do.</p>
      {caps.map((c) => (
        <div key={c.network} className="border rounded bg-white p-2 text-xs space-y-1">
          <h3 className="font-semibold capitalize">{c.network} <span className="font-normal text-gray-500">· {c.publishing === "API" ? `publishes by API (${c.mode})` : "publishing not enabled here"}</span></h3>
          {c.notes.map((n, i) => <p key={i} className="text-amber-700">⚠ {n}</p>)}
          <p className="text-gray-600">Scheduling: {c.scheduling}. Metrics: {c.insights.note}.</p>
          <table className="w-full"><tbody>{c.formats.map((f) => (
            <tr key={f.key} className="border-t align-top"><td className="pr-2 w-44">{f.available ? "✓" : "✗"} {f.label}</td>
              <td className={f.available ? "text-gray-600" : "text-red-700"}>{f.available ? [f.note, f.media_max ? `${f.media_min === f.media_max ? f.media_max : `${f.media_min}-${f.media_max}`} media` : "no media", f.alt_text ? "alt text" : null, !f.verified ? "UNVERIFIED in the matrix" : null].filter(Boolean).join(" · ") : f.reason}</td></tr>))}</tbody></table>
          <p className="text-gray-600">Comments: {Object.entries(c.moderation).map(([op, v]) => `${op} ${v.available ? "yes" : "NO"}`).join(" · ")}</p>
          {Object.entries(c.moderation).filter(([, v]) => !v.available).map(([op, v]) => <p key={op} className="text-red-700">{op}: {v.note}</p>)}
        </div>))}
    </section>);
}

export default function SocialPage() {
  const [tab, setTab] = useState<"calendar" | "inbox" | "channels" | "capabilities">("calendar");
  const [channels, setChannels] = useState<Channel[]>([]);
  const [caps, setCaps] = useState<Cap[]>([]);
  const [posts, setPosts] = useState<Post[]>([]);
  const [items, setItems] = useState<Item[]>([]);
  const [note, setNote] = useState("");
  const [msg, setMsg] = useState<string | null>(null);
  const [draft, setDraft] = useState(EMPTY);
  const [editing, setEditing] = useState<string | null>(null);
  const [nc, setNc] = useState({ network: "facebook", external_id: "", name: "", time_zone: "Africa/Nairobi" });
  const [csv, setCsv] = useState("");
  const [fNet, setFNet] = useState("");
  const [fWho, setFWho] = useState("");
  const load = useCallback(() => Promise.all([
    apiClient.get("/api/v1/social/channels").then((r) => setChannels(r.data)),
    apiClient.get("/api/v1/social/capabilities").then((r) => setCaps(Object.values(r.data.networks) as Cap[])),
    apiClient.get("/api/v1/social/posts").then((r) => setPosts(r.data)),
    apiClient.get("/api/v1/social/inbox", { params: { ...(fNet ? { network: fNet } : {}), ...(fWho ? { assigned_to: fWho } : {}) } }).then((r) => { setItems(r.data.items); setNote(r.data.note); }),
  ]).catch((e) => setMsg(err(e))), [fNet, fWho]);
  useEffect(() => { load(); }, [load]);
  const run = async (fn: () => Promise<unknown>, ok: string) => { setMsg(null); try { await fn(); setMsg(ok); } catch (e) { setMsg(err(e)); } load(); };
  const ch = channels.find((c) => c.id === draft.channel_id);
  const tz = ch?.time_zone ?? "Africa/Nairobi";
  const cap = caps.find((c) => c.network === ch?.network);
  const fmt = cap?.formats.find((f) => f.key === draft.format);
  const why = !ch ? "Choose a channel." : !fmt ? "Choose a format." : !fmt.available ? fmt.reason : null;
  const payload = () => ({ channel_id: draft.channel_id, idempotency_key: draft.key, text: draft.text, link: draft.link || null, format: draft.format || null,
    format_options: buildFopts(ch?.network ?? "", draft.format, draft.fopts), campaign_tag: draft.campaign_tag || null,
    media: draft.media.filter((m) => m.url).map((m) => ({ url: m.url, kind: m.kind, ...(m.alt_text ? { alt_text: m.alt_text } : {}), ...(m.thumbnail_url ? { thumbnail_url: m.thumbnail_url } : {}) })),
    scheduled_at: draft.when || null, time_zone: tz });
  const byDay = useMemo(() => {
    const g: Record<string, Post[]> = {};
    for (const p of posts) { const k = p.scheduled_at ? new Date(p.scheduled_at).toLocaleDateString() : "Not scheduled"; (g[k] ||= []).push(p); }
    return Object.entries(g);
  }, [posts]);
  const input = "border rounded px-2 py-1 text-xs";
  const modeOf = (p: Post) => p.publish_mode ?? (p.route === "API" ? channels.find((c) => c.id === p.channel_id)?.mode ?? null : null);
  const act = (p: Post, a: string, ok: string) => run(() => apiClient.post(`/api/v1/social/posts/${p.id}/${a}`), ok);
  const setMedia = (i: number, patch: Partial<MediaRow>) => setDraft({ ...draft, media: draft.media.map((m, j) => (j === i ? { ...m, ...patch } : m)) });
  const visibleFields = FIELDS.filter((d) => d.nets === ch?.network && (!d.fmts || d.fmts.includes(draft.format)) && !(d.key === "resumable" && ch?.options.ig_login !== "facebook"));
  const itemAct = (i: Item, path: string, body: unknown, ok: string) => run(() => apiClient.post(`/api/v1/social/inbox/${i.id}/${path}`, body), ok);
  return (
    <div className="p-4 space-y-3 text-sm">
      <div className="flex flex-wrap gap-2 items-center"><h2 className="text-lg font-semibold mr-2">Social</h2>
        {(["calendar", "inbox", "channels", "capabilities"] as const).map((t) => <button key={t} onClick={() => setTab(t)} className={`text-xs px-2 py-1 rounded border ${tab === t ? "bg-indigo-600 text-white" : "bg-white"}`}>{t === "inbox" ? "Listening inbox" : t === "capabilities" ? "What each network allows" : t[0].toUpperCase() + t.slice(1)}</button>)}</div>
      {msg && <p role="status" className="text-xs border rounded p-2 bg-gray-50">{msg}</p>}

      {tab === "capabilities" && <CapabilityTable caps={caps} />}

      {tab === "channels" && <section className="border rounded p-3 bg-white space-y-2">
        <p className="text-xs text-gray-500">Publishing runs by API on Facebook, Instagram, LinkedIn, TikTok, YouTube and X only when the owner has enabled it and the token is set; everything else is exported and posted by hand. Listening stores comments only for channels you opt in, read through each network&apos;s official API (no scraping).</p>
        <form className="flex flex-wrap gap-2" onSubmit={(e) => { e.preventDefault(); run(() => apiClient.post("/api/v1/social/channels", nc), "Channel added."); }}>
          <select aria-label="Network" className={input} value={nc.network} onChange={(e) => setNc({ ...nc, network: e.target.value })}>{NETS.map((n) => <option key={n}>{n}</option>)}</select>
          <input aria-label="Channel id" required placeholder="Page / account id" className={input} value={nc.external_id} onChange={(e) => setNc({ ...nc, external_id: e.target.value })} />
          <input aria-label="Channel name" required placeholder="Name" className={input} value={nc.name} onChange={(e) => setNc({ ...nc, name: e.target.value })} />
          <input aria-label="Channel time zone" className={input} value={nc.time_zone} onChange={(e) => setNc({ ...nc, time_zone: e.target.value })} />
          <button className="border rounded px-3 py-1 text-xs">Add</button></form>
        <ul className="text-xs space-y-1">{channels.map((c) => { const rd = caps.find((x) => x.network === c.network)?.moderation.read; return (
          <li key={c.id} className="flex flex-wrap gap-2 items-center border-t pt-1"><b>{c.name}</b><span>{c.network} · {c.time_zone} · {c.publishing === "API" ? "publishes by API" : "manual export"}</span>
            <label className="flex items-center gap-1"><input type="checkbox" checked={c.listen_enabled} onChange={(e) => run(() => apiClient.patch(`/api/v1/social/channels/${c.id}/listening`, null, { params: { enabled: e.target.checked } }), "Listening updated.")} /> listen</label>
            <button className="underline disabled:opacity-50 disabled:no-underline" disabled={!c.listen_enabled || !rd?.available} title={!c.listen_enabled ? "Turn listening on first (opt-in)." : rd?.available ? "" : rd?.note}
              onClick={() => run(async () => { const r = await apiClient.post(`/api/v1/social/channels/${c.id}/poll`); setMsg(r.data.reason ?? `Read ${r.data.stored} new item(s).`); }, "Polled.")}>Poll now</button>
            {rd && !rd.available && <span className="text-red-700">{rd.note}</span>}
            {c.network === "x" && <select aria-label="X tier" className={input} value={String(c.options.x_tier ?? "")} onChange={(e) => e.target.value && run(() => apiClient.patch(`/api/v1/social/channels/${c.id}/options`, { x_tier: e.target.value }), "Saved.")}><option value="">X access tier…</option>{["pay_per_use", "basic", "pro", "enterprise"].map((t) => <option key={t}>{t}</option>)}</select>}
            {c.network === "instagram" && <select aria-label="Instagram login path" className={input} value={String(c.options.ig_login ?? "instagram")} onChange={(e) => run(() => apiClient.patch(`/api/v1/social/channels/${c.id}/options`, { ig_login: e.target.value }), "Saved.")}><option value="instagram">Instagram Login</option><option value="facebook">Facebook Login (resumable upload)</option></select>}
            {c.network === "youtube" && <label className="flex items-center gap-1"><input type="checkbox" checked={!!c.options.youtube_project_verified} onChange={(e) => run(() => apiClient.patch(`/api/v1/social/channels/${c.id}/options`, { youtube_project_verified: e.target.checked }), "Saved.")} /> API project verified by Google</label>}
          </li>); })}</ul>
      </section>}

      {tab === "calendar" && <>
        <form className="border rounded p-3 bg-white space-y-2" onSubmit={(e) => { e.preventDefault();
          run(() => (editing ? apiClient.put(`/api/v1/social/posts/${editing}`, payload()) : apiClient.post("/api/v1/social/posts", payload())).then(() => { setDraft({ ...EMPTY, key: newKey() }); setEditing(null); }), editing ? "Post updated." : "Draft saved."); }}>
          <h3 className="font-semibold">{editing ? "Edit post" : "New post"}</h3>
          <div className="flex flex-wrap gap-2">
            <select aria-label="Post channel" required className={input} value={draft.channel_id} onChange={(e) => { const n = channels.find((c) => c.id === e.target.value)?.network; const first = caps.find((c) => c.network === n)?.formats.find((f) => f.available);
              setDraft({ ...draft, channel_id: e.target.value, format: first?.key ?? "", fopts: {} }); }}>
              <option value="">Channel…</option>{channels.map((c) => <option key={c.id} value={c.id}>{c.network} · {c.name}</option>)}</select>
            <select aria-label="Post format" required className={input} value={draft.format} disabled={!cap} onChange={(e) => setDraft({ ...draft, format: e.target.value, fopts: {} })}>
              <option value="">Format…</option>{cap?.formats.map((f) => <option key={f.key} value={f.key} disabled={!f.available} title={f.reason ?? ""}>{f.label}{f.available ? "" : " — unavailable"}</option>)}</select>
            <input aria-label="Publish time" type="datetime-local" className={input} value={draft.when} onChange={(e) => setDraft({ ...draft, when: e.target.value })} />
            <span className="text-xs text-gray-500 self-center">({tz})</span>
            <input aria-label="Campaign tag" placeholder="Campaign tag" className={input} value={draft.campaign_tag} onChange={(e) => setDraft({ ...draft, campaign_tag: e.target.value })} />
          </div>
          {cap && <ul className="text-xs space-y-0.5">{cap.formats.filter((f) => !f.available).map((f) => <li key={f.key} className="text-red-700">✗ {f.label}: {f.reason}</li>)}
            {cap.notes.map((n, i) => <li key={i} className="text-amber-700">⚠ {n}</li>)}<li className="text-gray-500">Scheduling: {cap.scheduling}.</li></ul>}
          {fmt?.available && <p className="text-xs text-gray-600">{fmt.note ?? ""} {fmt.media_max ? `Media: ${fmt.media_min === fmt.media_max ? fmt.media_max : `${fmt.media_min}-${fmt.media_max}`} (${fmt.kinds.join("/")}).` : "This format takes no media."} Text up to {fmt.max_text}.{!fmt.verified ? " UNVERIFIED in the capability matrix." : ""}</p>}
          <textarea aria-label="Post text" required rows={3} className={`${input} w-full`} value={draft.text} onChange={(e) => setDraft({ ...draft, text: e.target.value })} />
          {fmt?.available && fmt.media_max > 0 && <div className="space-y-1">
            {draft.media.map((m, i) => (
              <div key={i} className="flex flex-wrap gap-2">
                <input aria-label={`Media ${i + 1} URL`} placeholder="https://… public media URL" className={`${input} flex-1 min-w-0`} value={m.url} onChange={(e) => setMedia(i, { url: e.target.value })} />
                <select aria-label={`Media ${i + 1} kind`} className={input} value={m.kind} onChange={(e) => setMedia(i, { kind: e.target.value })}>{fmt.kinds.map((k) => <option key={k}>{k}</option>)}</select>
                {fmt.alt_text && <input aria-label={`Media ${i + 1} alt text`} placeholder="Alt text (max 1000)" maxLength={1000} className={`${input} flex-1 min-w-0`} value={m.alt_text} onChange={(e) => setMedia(i, { alt_text: e.target.value })} />}
                {ch?.network === "linkedin" && m.kind === "video" && <input aria-label={`Media ${i + 1} thumbnail URL`} placeholder="Thumbnail URL" className={`${input} flex-1 min-w-0`} value={m.thumbnail_url} onChange={(e) => setMedia(i, { thumbnail_url: e.target.value })} />}
                <button type="button" className="underline" onClick={() => setDraft({ ...draft, media: draft.media.filter((_, j) => j !== i) })}>Remove</button>
              </div>))}
            <button type="button" className="underline text-xs disabled:opacity-50 disabled:no-underline" disabled={draft.media.length >= fmt.media_max} title={draft.media.length >= fmt.media_max ? `This format takes at most ${fmt.media_max}.` : ""}
              onClick={() => setDraft({ ...draft, media: [...draft.media, { url: "", kind: fmt.kinds[0], alt_text: "", thumbnail_url: "" }] })}>Add media ({draft.media.length}/{fmt.media_max})</button>
          </div>}
          {fmt?.available && fmt.link !== "no" && <input aria-label="Link" placeholder={fmt.link === "required" ? "Link (required)" : "Link (optional)"} className={`${input} w-full`} value={draft.link} onChange={(e) => setDraft({ ...draft, link: e.target.value })} />}
          {fmt?.available && visibleFields.length > 0 && <div className="flex flex-wrap gap-3 border rounded p-2 bg-gray-50">{visibleFields.map((d) => (
            <label key={d.key} className="flex flex-col gap-0.5 text-xs">{d.type === "bool" ? <span className="flex gap-1 items-center"><input type="checkbox" checked={!!draft.fopts[d.key]} onChange={(e) => setDraft({ ...draft, fopts: { ...draft.fopts, [d.key]: e.target.checked } })} /> {d.label}</span> : <>
              <span>{d.label}</span>{d.type === "select" ? <select aria-label={d.label} className={input} value={String(draft.fopts[d.key] ?? "")} onChange={(e) => setDraft({ ...draft, fopts: { ...draft.fopts, [d.key]: e.target.value } })}>{d.options!.map((o) => <option key={o} value={o}>{o || "choose…"}</option>)}</select>
                : <input aria-label={d.label} type={d.type === "number" ? "number" : d.type === "datetime" ? "datetime-local" : "text"} className={input} value={String(draft.fopts[d.key] ?? "")} onChange={(e) => setDraft({ ...draft, fopts: { ...draft.fopts, [d.key]: e.target.value } })} />}</>}
              {d.hint && <span className="text-gray-500">{d.hint}</span>}</label>))}</div>}
          <div className="flex gap-2 items-center"><button disabled={!!why} title={why ?? ""} className="bg-indigo-600 text-white rounded px-3 py-1 text-xs disabled:opacity-50">{editing ? "Save changes" : "Save draft"}</button>
            {why && <span className="text-xs text-gray-500">{why}</span>}
            {editing && <button type="button" className="text-xs underline" onClick={() => { setEditing(null); setDraft({ ...EMPTY, key: newKey() }); }}>Cancel edit</button>}</div>
          <p className="text-xs text-gray-500">Changing the text, media, format or link after approval creates a new version that needs approval again; changing only the time keeps the approval. Every draft is checked against the network&apos;s documented limits before it can be approved.</p>
        </form>
        {byDay.length === 0 && <p className="text-xs text-gray-500">No posts yet.</p>}
        {byDay.map(([day, ps]) => (
          <section key={day} className="border rounded bg-white p-2"><h3 className="text-xs font-semibold text-gray-600 mb-1">{day}</h3>
            <ul className="space-y-2">{ps.map((p) => (
              <li key={p.id} className="text-xs border-t pt-1 space-y-0.5">
                <div className="flex flex-wrap gap-2 items-center"><b>{p.channel}</b><span className="text-gray-500">{p.network}{p.format ? ` · ${p.format}` : ""}</span>
                  {p.scheduled_at && <span>{new Date(p.scheduled_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}</span>}
                  <span className={`px-1 rounded ${STATE_CLS[p.status] ?? "bg-gray-100"}`} title={p.provider_status ?? ""}>{p.provider_status === "SCHEDULED" ? "scheduled at the network — not live yet" : (STATE_TEXT[p.status] ?? p.status.toLowerCase())} · v{p.version}{p.approved ? " · approved" : ""}</span>
                  {modeOf(p) && <span className={`px-1 rounded border ${modeOf(p) === "LIVE" ? "border-red-500 text-red-700" : "border-gray-400 text-gray-600"}`}>{modeOf(p)}</span>}
                  {p.campaign_tag && <span className="text-indigo-700">#{p.campaign_tag}</span>}<span className="text-gray-500">{p.route === "API" ? "API" : "manual"}</span>
                  {p.flow_phase && IN_FLIGHT.includes(p.status) && <span className="text-gray-500">step: {p.flow_phase}</span>}</div>
                <p className="whitespace-pre-wrap">{p.text}</p>
                {p.media.length > 0 && <p className="text-gray-500">{p.media.length} media: {p.media.map((m) => m.kind).join(", ")}</p>}
                {p.problems.map((x, i) => <p key={i} className="text-amber-700">⚠ {x}</p>)}
                {p.conflicts.map((x, i) => <p key={i} className="text-amber-700">⏱ {x}</p>)}
                {p.error && <p className="text-red-600">{p.error}{p.fail_reason ? ` (${p.fail_reason})` : ""}</p>}
                {p.provider_ref && <p className="text-gray-500">Network reference {p.provider_ref}{p.provider_status ? ` · ${p.provider_status}` : ""}{p.status !== "PUBLISHED" ? " — a submission, not yet a live post" : ""}</p>}
                {p.status === "PUBLISHED" && <p className="text-emerald-700">{modeOf(p) === "SIMULATED" ? "Simulated (local simulator only, not on the real network)" : "Live"}{p.external_post_id ? ` · post ${p.external_post_id}` : " (the network gave no public post id, e.g. a private post)"}{p.published_at ? ` · ${new Date(p.published_at).toLocaleString()}` : ""}</p>}
                {p.status === "EXPORTED" && p.provider_status === "SEND_TO_USER_INBOX" && <p className="text-gray-700">Delivered to the creator&apos;s TikTok inbox as a draft. It is not a post until the creator publishes it in the TikTok app.</p>}
                {p.network === "tiktok" && ["DRAFT", "PENDING", "APPROVED", "FAILED"].includes(p.status) && <TikTokOptions post={p} run={run} />}
                {p.status === "PUBLISHED" && <Insights post={p} />}
                <div className="flex flex-wrap gap-2">
                  {["DRAFT", "PENDING", "APPROVED", "FAILED"].includes(p.status) && <button className="underline" onClick={() => { setEditing(p.id); setTab("calendar");
                    setDraft({ channel_id: p.channel_id, format: p.format ?? "", text: p.text, media: p.media.map((m) => ({ url: m.url, kind: m.kind, alt_text: m.alt_text ?? "", thumbnail_url: m.thumbnail_url ?? "" })), link: p.link ?? "", campaign_tag: p.campaign_tag ?? "",
                      when: p.scheduled_at ? new Date(p.scheduled_at).toLocaleString("sv-SE", { timeZone: p.time_zone }).slice(0, 16).replace(" ", "T") : "", key: newKey(), fopts: {} }); }}>Edit</button>}
                  {p.status === "DRAFT" && <button className="underline" onClick={() => act(p, "request", "Sent for approval.")}>Request approval</button>}
                  {p.status === "PENDING" && <><button className="underline" onClick={() => act(p, "approve", "Approved.")}>Approve</button><button className="underline" onClick={() => act(p, "reject", "Rejected.")}>Reject</button></>}
                  {p.status === "APPROVED" && p.approved && <button className="underline disabled:opacity-50 disabled:no-underline" disabled={p.route !== "API" || p.problems.length > 0}
                    title={p.route !== "API" ? "Publishing by API is not enabled for this network" : p.problems.join(" ")}
                    onClick={() => act(p, "submit", "Submitted — the network is processing it; it is not live until confirmed.")}>Submit now</button>}
                  {["SUBMITTED", "PROCESSING", "UNKNOWN"].includes(p.status) && p.provider_ref && <button className="underline" onClick={() => act(p, "refresh", "Status refreshed.")}>Refresh status</button>}
                  {p.status === "UNKNOWN" && (!p.provider_ref || p.provider_ref.startsWith("lookup:")) && <button className="underline" onClick={() => { if (window.confirm("Did you check the channel and the post is NOT there?")) act(p, "release", "Released: it can be submitted again."); }}>Checked: not posted</button>}
                  {p.status === "FAILED" && p.approved && <button className="underline" onClick={() => act(p, "retry", "Will retry.")}>Retry</button>}
                  {p.approved && p.route !== "API" && !["PUBLISHED", "EXPORTED", "CANCELLED"].includes(p.status) && <button className="underline" onClick={() => run(async () => { const r = await apiClient.post(`/api/v1/social/posts/${p.id}/export`); await navigator.clipboard?.writeText(r.data.text).catch(() => undefined); }, "Exported; text copied for manual posting.")}>Export for manual posting</button>}
                  {!["PUBLISHED", "SUBMITTING", "UNKNOWN", "CANCELLED"].includes(p.status) && <button className="underline text-red-600"
                    onClick={() => act(p, "cancel", IN_FLIGHT.includes(p.status) ? "Cancel requested at the network." : "Cancelled.")}>Cancel</button>}
                </div>
                <details><summary className="cursor-pointer text-gray-500">History</summary><ul>{p.history.map((h, i) => <li key={i}>{new Date(h.at).toLocaleString()} · {h.event} · v{h.version} {h.detail}</li>)}</ul></details>
              </li>))}</ul></section>))}
      </>}

      {tab === "inbox" && <section className="space-y-2">
        <p className="text-xs text-gray-500">{note}</p>
        <div className="flex flex-wrap gap-2 items-center text-xs">
          <select aria-label="Filter network" className={input} value={fNet} onChange={(e) => setFNet(e.target.value)}><option value="">All networks</option>{NETS.map((n) => <option key={n}>{n}</option>)}</select>
          <input aria-label="Filter assignee" placeholder="Assigned to" className={input} value={fWho} onChange={(e) => setFWho(e.target.value)} />
          <button className="underline" onClick={() => run(async () => { const r = await apiClient.post("/api/v1/social/inbox/retention-sweep"); setMsg(`Erased personal content of ${r.data.erased} item(s) older than ${r.data.retention_days} days.`); }, "Retention applied.")}>Apply retention now</button>
        </div>
        <details className="border rounded p-2 bg-white"><summary className="text-xs cursor-pointer">Import comments (CSV)</summary>
          <textarea aria-label="CSV" rows={4} className={`${input} w-full mt-1`} placeholder="network,kind,external_id,author,text,url,occurred_at" value={csv} onChange={(e) => setCsv(e.target.value)} />
          <button className="border rounded px-3 py-1 text-xs" onClick={() => run(async () => { const r = await apiClient.post("/api/v1/social/inbox/import", { csv }); setMsg(`Imported ${r.data.stored}, duplicates ${r.data.duplicates}, rejected ${r.data.rejected}.`); }, "Imported.")}>Import</button></details>
        {items.length === 0 && <p className="text-xs text-gray-500">Nothing in the inbox.</p>}
        <ul className="space-y-2">{items.map((i) => (
          <li key={i.id} className="border rounded p-2 bg-white text-xs space-y-1">
            <div className="flex flex-wrap gap-2"><b>{i.author ?? "—"}</b><span className="text-gray-500">{i.network} {i.kind.toLowerCase()} · {new Date(i.occurred_at).toLocaleString()} · {i.source.toLowerCase()}</span>
              {i.sentiment && <span className={i.sentiment === "NEGATIVE" ? "text-red-700" : i.sentiment === "POSITIVE" ? "text-emerald-700" : "text-gray-600"}>{i.sentiment.toLowerCase()}</span>}
              {i.topics.map((t) => <span key={t} className="px-1 bg-gray-100 rounded">{t}</span>)}
              {i.provider_state && <span className="px-1 border rounded">{i.provider_state.toLowerCase()} on the network</span>}<span className="ml-auto">{i.status.toLowerCase()}{i.assigned_to ? ` · ${i.assigned_to}` : ""}</span></div>
            <p>{i.text ?? <i>Deleted (by the author, the network, retention or opt-out).</i>}</p>
            {(i.evidence.positive?.length || i.evidence.negative?.length) ? <p className="text-gray-500">Because of the words: {[...(i.evidence.positive ?? []), ...(i.evidence.negative ?? [])].join(", ")}{i.evidence.source ? ` · source ${i.evidence.source.network} ${i.evidence.source.external_id} via ${i.evidence.source.via.toLowerCase()}` : ""}. Keyword tags are an aid, not a verdict.</p> : null}
            {i.status !== "DELETED" && <>
              <div className="flex gap-2 items-center"><input aria-label="Assign to" placeholder="Assign to (username)" className={input} defaultValue={i.assigned_to ?? ""} onBlur={(e) => e.target.value !== (i.assigned_to ?? "") && run(() => apiClient.patch(`/api/v1/social/inbox/${i.id}`, { assigned_to: e.target.value || null }), "Assigned.")} />
                <button className="underline" onClick={() => { if (window.confirm(`Erase this author's items on ${i.network} and never store them again?`) && i.author) run(() => apiClient.post("/api/v1/social/inbox/optout", { network: i.network, author: i.author, reason: "author opt-out" }), "Author opted out."); }}>Opt this author out</button></div>
              <textarea aria-label="Reply draft" rows={2} className={`${input} w-full`} defaultValue={i.reply_draft ?? ""} disabled={!i.ops.reply.available || ["SENT", "SENDING"].includes(i.reply_status ?? "")}
                onBlur={(e) => e.target.value !== (i.reply_draft ?? "") && run(() => apiClient.patch(`/api/v1/social/inbox/${i.id}`, { reply_draft: e.target.value }), "Draft saved.")} />
              <p className="text-gray-500">Reply: {i.reply_status ? i.reply_status.toLowerCase() : "no draft"}{i.reply_requested_by ? ` · requested by ${i.reply_requested_by}` : ""}{i.reply_approved_by ? ` · approved by ${i.reply_approved_by}` : ""}{i.reply_external_id ? ` · network reply ${i.reply_external_id}` : ""}</p>
              {i.reply_error && <p className="text-red-600">{i.reply_error}</p>}
              <div className="flex flex-wrap gap-2">
                <button className="underline" onClick={() => run(async () => { const r = await apiClient.post(`/api/v1/social/inbox/${i.id}/suggest-reply`); await apiClient.patch(`/api/v1/social/inbox/${i.id}`, { reply_draft: r.data.reply_draft }); }, "Suggested a draft — edit it, then request approval.")}>Suggest reply</button>
                <button className="underline disabled:opacity-50 disabled:no-underline" disabled={!i.ops.reply.available || !i.reply_draft || !["DRAFT", "FAILED"].includes(i.reply_status ?? "")} title={i.ops.reply.available ? "" : i.ops.reply.reason} onClick={() => itemAct(i, "reply/request", null, "Reply sent for approval.")}>Request reply approval</button>
                {i.reply_status === "PENDING" && <><button className="underline" onClick={() => itemAct(i, "reply/approve", null, "Reply approved (a second person is required).")}>Approve reply</button><button className="underline" onClick={() => itemAct(i, "reply/reject", null, "Reply sent back to draft.")}>Reject reply</button></>}
                {i.reply_status === "APPROVED" && <button className="underline" onClick={() => itemAct(i, "reply/send", null, "Reply sent.")}>Send approved reply</button>}
                {(["ASSIGNED", "REPLIED", "DONE"] as const).map((s) => <button key={s} className="underline" onClick={() => run(() => apiClient.patch(`/api/v1/social/inbox/${i.id}`, { status: s }), "Updated.")}>{s === "REPLIED" ? "mark replied by hand" : s.toLowerCase()}</button>)}
                {(["hide", "delete"] as const).map((op) => <button key={op} className="underline text-red-700 disabled:opacity-50 disabled:no-underline disabled:text-gray-500" disabled={!i.ops[op].available || (op === "hide" && i.provider_state === "HIDDEN")} title={i.ops[op].available ? "" : i.ops[op].reason}
                  onClick={() => { const reason = window.prompt(`Why ${op} this comment on ${i.network}? ${op === "delete" ? "This cannot be undone." : ""}`); if (reason && reason.length >= 3) itemAct(i, `moderate/${op}`, { confirm: true, reason }, op === "hide" ? "Hidden on the network." : "Deleted on the network."); }}>{op} on {i.network}</button>)}
              </div>
              {OPS.filter((op) => !i.ops[op].available).map((op) => <p key={op} className="text-red-700">✗ {op}: {i.ops[op].reason}</p>)}
            </>}
          </li>))}</ul>
      </section>}
    </div>
  );
}
