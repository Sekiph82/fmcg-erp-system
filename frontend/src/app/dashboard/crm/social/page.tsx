"use client";
// M44.S01.T006–T008 social: channels, composer + calendar with approval/versions, listening inbox.
// M48.S01.T005 asynchronous publish states (submitted is not live), TikTok creator options + consent, submit/refresh/cancel.
import { useCallback, useEffect, useMemo, useState } from "react";
import { apiClient } from "@/lib/api";

interface Channel { id: string; network: string; name: string; external_id: string; time_zone: string; listen_enabled: boolean; publishing: string; mode: string; tiktok_audited?: boolean }
interface Post { id: string; channel_id: string; network: string; channel: string; text: string; media: { url: string; kind: string }[];
  link: string | null; campaign_tag: string | null; scheduled_at: string | null; time_zone: string; status: string; version: number;
  approved: boolean; approved_by: string | null; error: string | null; route: string; problems: string[]; conflicts: string[];
  history: { at: string; event: string; version: number; detail: string }[]; external_post_id: string | null; provider_ref: string | null;
  provider_status: string | null; fail_reason: string | null; publish_mode: string | null; published_at: string | null;
  publish_options: TikTokOpts | null }
interface TikTokOpts { privacy_level: string; disable_comment: boolean; disable_duet: boolean; disable_stitch: boolean; source: string; consent: boolean; consent_by?: string }
interface CreatorInfo { creator_nickname: string | null; privacy_level_options: string[]; provider_privacy_level_options: string[]; audited: boolean;
  comment_disabled: boolean; duet_disabled: boolean; stitch_disabled: boolean; max_video_post_duration_sec: number | null; mode: string }
interface Item { id: string; network: string; kind: string; author: string | null; text: string | null; occurred_at: string; source: string;
  sentiment: string | null; topics: string[]; evidence: { positive?: string[]; negative?: string[] }; status: string; assigned_to: string | null; reply_draft: string | null }

const NETS = ["facebook", "instagram", "linkedin", "tiktok", "x", "youtube"];
const err = (e: unknown) => { const d = (e as { response?: { data?: { detail?: unknown } } }).response?.data?.detail; return typeof d === "string" ? d : "Request failed."; };
const newKey = () => (typeof crypto !== "undefined" && crypto.randomUUID ? crypto.randomUUID() : `${Date.now()}-${Math.random().toString(36).slice(2)}`);
const IN_FLIGHT = ["SUBMITTING", "SUBMITTED", "PROCESSING", "UNKNOWN"];
const STATE_TEXT: Record<string, string> = { SUBMITTING: "submitting…", SUBMITTED: "submitted — not live yet", PROCESSING: "processing at the network — not live yet",
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

const EMPTY = { channel_id: "", text: "", media_url: "", media_kind: "image", link: "", campaign_tag: "", when: "", key: newKey() };

export default function SocialPage() {
  const [tab, setTab] = useState<"calendar" | "inbox" | "channels">("calendar");
  const [channels, setChannels] = useState<Channel[]>([]);
  const [posts, setPosts] = useState<Post[]>([]);
  const [items, setItems] = useState<Item[]>([]);
  const [note, setNote] = useState("");
  const [msg, setMsg] = useState<string | null>(null);
  const [draft, setDraft] = useState(EMPTY);
  const [editing, setEditing] = useState<string | null>(null);
  const [nc, setNc] = useState({ network: "facebook", external_id: "", name: "", time_zone: "Africa/Nairobi" });
  const [csv, setCsv] = useState("");
  const load = useCallback(() => Promise.all([
    apiClient.get("/api/v1/social/channels").then((r) => setChannels(r.data)),
    apiClient.get("/api/v1/social/posts").then((r) => setPosts(r.data)),
    apiClient.get("/api/v1/social/inbox").then((r) => { setItems(r.data.items); setNote(r.data.note); }),
  ]).catch((e) => setMsg(err(e))), []);
  useEffect(() => { load(); }, [load]);
  const run = async (fn: () => Promise<unknown>, ok: string) => { setMsg(null); try { await fn(); setMsg(ok); } catch (e) { setMsg(err(e)); } load(); };
  const tz = channels.find((c) => c.id === draft.channel_id)?.time_zone ?? "Africa/Nairobi";
  const payload = () => ({ channel_id: draft.channel_id, idempotency_key: draft.key, text: draft.text, link: draft.link || null,
    campaign_tag: draft.campaign_tag || null, media: draft.media_url ? [{ url: draft.media_url, kind: draft.media_kind }] : [],
    scheduled_at: draft.when || null, time_zone: tz });
  const byDay = useMemo(() => {
    const g: Record<string, Post[]> = {};
    for (const p of posts) { const k = p.scheduled_at ? new Date(p.scheduled_at).toLocaleDateString() : "Not scheduled"; (g[k] ||= []).push(p); }
    return Object.entries(g);
  }, [posts]);
  const input = "border rounded px-2 py-1 text-xs";
  const modeOf = (p: Post) => p.publish_mode ?? (p.route === "API" ? channels.find((c) => c.id === p.channel_id)?.mode ?? null : null);
  const act = (p: Post, a: string, ok: string) => run(() => apiClient.post(`/api/v1/social/posts/${p.id}/${a}`), ok);
  return (
    <div className="p-4 space-y-3 text-sm">
      <div className="flex flex-wrap gap-2 items-center"><h2 className="text-lg font-semibold mr-2">Social</h2>
        {(["calendar", "inbox", "channels"] as const).map((t) => <button key={t} onClick={() => setTab(t)} className={`text-xs px-2 py-1 rounded border ${tab === t ? "bg-indigo-600 text-white" : "bg-white"}`}>{t === "inbox" ? "Listening inbox" : t[0].toUpperCase() + t.slice(1)}</button>)}</div>
      {msg && <p role="status" className="text-xs border rounded p-2 bg-gray-50">{msg}</p>}

      {tab === "channels" && <section className="border rounded p-3 bg-white space-y-2">
        <p className="text-xs text-gray-500">Publishing runs by API only on Facebook, Instagram, LinkedIn and TikTok when the owner has enabled it and the token is set; everything else is exported and posted by hand. Listening stores comments only for channels you opt in.</p>
        <form className="flex flex-wrap gap-2" onSubmit={(e) => { e.preventDefault(); run(() => apiClient.post("/api/v1/social/channels", nc), "Channel added."); }}>
          <select aria-label="Network" className={input} value={nc.network} onChange={(e) => setNc({ ...nc, network: e.target.value })}>{NETS.map((n) => <option key={n}>{n}</option>)}</select>
          <input aria-label="Channel id" required placeholder="Page / account id" className={input} value={nc.external_id} onChange={(e) => setNc({ ...nc, external_id: e.target.value })} />
          <input aria-label="Channel name" required placeholder="Name" className={input} value={nc.name} onChange={(e) => setNc({ ...nc, name: e.target.value })} />
          <input aria-label="Channel time zone" className={input} value={nc.time_zone} onChange={(e) => setNc({ ...nc, time_zone: e.target.value })} />
          <button className="border rounded px-3 py-1 text-xs">Add</button></form>
        <ul className="text-xs space-y-1">{channels.map((c) => <li key={c.id} className="flex flex-wrap gap-2 items-center border-t pt-1"><b>{c.name}</b><span>{c.network} · {c.time_zone} · {c.publishing === "API" ? "publishes by API" : "manual export"}</span>
          <label className="flex items-center gap-1"><input type="checkbox" checked={c.listen_enabled} onChange={(e) => run(() => apiClient.patch(`/api/v1/social/channels/${c.id}/listening`, null, { params: { enabled: e.target.checked } }), "Listening updated.")} /> listen</label></li>)}</ul>
      </section>}

      {tab === "calendar" && <>
        <form className="border rounded p-3 bg-white space-y-2" onSubmit={(e) => { e.preventDefault();
          run(() => (editing ? apiClient.put(`/api/v1/social/posts/${editing}`, payload()) : apiClient.post("/api/v1/social/posts", payload())).then(() => { setDraft({ ...EMPTY, key: newKey() }); setEditing(null); }), editing ? "Post updated." : "Draft saved."); }}>
          <h3 className="font-semibold">{editing ? "Edit post" : "New post"}</h3>
          <div className="flex flex-wrap gap-2">
            <select aria-label="Post channel" required className={input} value={draft.channel_id} onChange={(e) => setDraft({ ...draft, channel_id: e.target.value })}>
              <option value="">Channel…</option>{channels.map((c) => <option key={c.id} value={c.id}>{c.network} · {c.name}</option>)}</select>
            <input aria-label="Publish time" type="datetime-local" className={input} value={draft.when} onChange={(e) => setDraft({ ...draft, when: e.target.value })} />
            <span className="text-xs text-gray-500 self-center">({tz})</span>
            <input aria-label="Campaign tag" placeholder="Campaign tag" className={input} value={draft.campaign_tag} onChange={(e) => setDraft({ ...draft, campaign_tag: e.target.value })} />
          </div>
          <textarea aria-label="Post text" required rows={3} className={`${input} w-full`} value={draft.text} onChange={(e) => setDraft({ ...draft, text: e.target.value })} />
          <div className="flex flex-wrap gap-2">
            <input aria-label="Media URL" placeholder="https://… image or video" className={`${input} flex-1 min-w-0`} value={draft.media_url} onChange={(e) => setDraft({ ...draft, media_url: e.target.value })} />
            <select aria-label="Media kind" className={input} value={draft.media_kind} onChange={(e) => setDraft({ ...draft, media_kind: e.target.value })}><option>image</option><option>video</option></select>
            <input aria-label="Link" placeholder="Link (optional)" className={`${input} flex-1 min-w-0`} value={draft.link} onChange={(e) => setDraft({ ...draft, link: e.target.value })} />
          </div>
          <div className="flex gap-2"><button className="bg-indigo-600 text-white rounded px-3 py-1 text-xs">{editing ? "Save changes" : "Save draft"}</button>
            {editing && <button type="button" className="text-xs underline" onClick={() => { setEditing(null); setDraft({ ...EMPTY, key: newKey() }); }}>Cancel edit</button>}</div>
          <p className="text-xs text-gray-500">Changing the text, media or link after approval creates a new version that needs approval again; changing only the time keeps the approval.</p>
        </form>
        {byDay.length === 0 && <p className="text-xs text-gray-500">No posts yet.</p>}
        {byDay.map(([day, ps]) => (
          <section key={day} className="border rounded bg-white p-2"><h3 className="text-xs font-semibold text-gray-600 mb-1">{day}</h3>
            <ul className="space-y-2">{ps.map((p) => (
              <li key={p.id} className="text-xs border-t pt-1 space-y-0.5">
                <div className="flex flex-wrap gap-2 items-center"><b>{p.channel}</b><span className="text-gray-500">{p.network}</span>
                  {p.scheduled_at && <span>{new Date(p.scheduled_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}</span>}
                  <span className={`px-1 rounded ${STATE_CLS[p.status] ?? "bg-gray-100"}`} title={p.provider_status ?? ""}>{STATE_TEXT[p.status] ?? p.status.toLowerCase()} · v{p.version}{p.approved ? " · approved" : ""}</span>
                  {modeOf(p) && <span className={`px-1 rounded border ${modeOf(p) === "LIVE" ? "border-red-500 text-red-700" : "border-gray-400 text-gray-600"}`}>{modeOf(p)}</span>}
                  {p.campaign_tag && <span className="text-indigo-700">#{p.campaign_tag}</span>}<span className="text-gray-500">{p.route === "API" ? "API" : "manual"}</span></div>
                <p className="whitespace-pre-wrap">{p.text}</p>
                {p.problems.map((x, i) => <p key={i} className="text-amber-700">⚠ {x}</p>)}
                {p.conflicts.map((x, i) => <p key={i} className="text-amber-700">⏱ {x}</p>)}
                {p.error && <p className="text-red-600">{p.error}{p.fail_reason ? ` (${p.fail_reason})` : ""}</p>}
                {p.provider_ref && <p className="text-gray-500">Network reference {p.provider_ref}{p.provider_status ? ` · ${p.provider_status}` : ""}{p.status !== "PUBLISHED" ? " — a submission, not yet a live post" : ""}</p>}
                {p.status === "PUBLISHED" && <p className="text-emerald-700">Live{p.external_post_id ? ` · post ${p.external_post_id}` : " (the network gave no public post id, e.g. a private post)"}{p.published_at ? ` · ${new Date(p.published_at).toLocaleString()}` : ""}</p>}
                {p.network === "tiktok" && ["DRAFT", "PENDING", "APPROVED", "FAILED"].includes(p.status) && <TikTokOptions post={p} run={run} />}
                <div className="flex flex-wrap gap-2">
                  {["DRAFT", "PENDING", "APPROVED", "FAILED"].includes(p.status) && <button className="underline" onClick={() => { setEditing(p.id); setTab("calendar");
                    setDraft({ channel_id: p.channel_id, text: p.text, media_url: p.media[0]?.url ?? "", media_kind: p.media[0]?.kind ?? "image", link: p.link ?? "", campaign_tag: p.campaign_tag ?? "",
                      when: p.scheduled_at ? new Date(p.scheduled_at).toLocaleString("sv-SE", { timeZone: p.time_zone }).slice(0, 16).replace(" ", "T") : "", key: newKey() }); }}>Edit</button>}
                  {p.status === "DRAFT" && <button className="underline" onClick={() => act(p, "request", "Sent for approval.")}>Request approval</button>}
                  {p.status === "PENDING" && <><button className="underline" onClick={() => act(p, "approve", "Approved.")}>Approve</button><button className="underline" onClick={() => act(p, "reject", "Rejected.")}>Reject</button></>}
                  {p.status === "APPROVED" && p.approved && <button className="underline disabled:opacity-50 disabled:no-underline" disabled={p.route !== "API" || p.problems.length > 0}
                    title={p.route !== "API" ? "Publishing by API is not enabled for this network" : p.problems.join(" ")}
                    onClick={() => act(p, "submit", "Submitted — the network is processing it; it is not live until confirmed.")}>Submit now</button>}
                  {["SUBMITTED", "PROCESSING", "UNKNOWN"].includes(p.status) && p.provider_ref && <button className="underline" onClick={() => act(p, "refresh", "Status refreshed.")}>Refresh status</button>}
                  {p.status === "UNKNOWN" && !p.provider_ref && <button className="underline" onClick={() => { if (window.confirm("Did you check the channel and the post is NOT there?")) act(p, "release", "Released: it can be submitted again."); }}>Checked: not posted</button>}
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
        <details className="border rounded p-2 bg-white"><summary className="text-xs cursor-pointer">Import comments (CSV)</summary>
          <textarea aria-label="CSV" rows={4} className={`${input} w-full mt-1`} placeholder="network,kind,external_id,author,text,url,occurred_at" value={csv} onChange={(e) => setCsv(e.target.value)} />
          <button className="border rounded px-3 py-1 text-xs" onClick={() => run(async () => { const r = await apiClient.post("/api/v1/social/inbox/import", { csv }); setMsg(`Imported ${r.data.stored}, duplicates ${r.data.duplicates}, rejected ${r.data.rejected}.`); }, "Imported.")}>Import</button></details>
        {items.length === 0 && <p className="text-xs text-gray-500">Nothing in the inbox.</p>}
        <ul className="space-y-2">{items.map((i) => (
          <li key={i.id} className="border rounded p-2 bg-white text-xs space-y-1">
            <div className="flex flex-wrap gap-2"><b>{i.author ?? "—"}</b><span className="text-gray-500">{i.network} {i.kind.toLowerCase()} · {new Date(i.occurred_at).toLocaleString()} · {i.source.toLowerCase()}</span>
              {i.sentiment && <span className={i.sentiment === "NEGATIVE" ? "text-red-700" : i.sentiment === "POSITIVE" ? "text-emerald-700" : "text-gray-600"}>{i.sentiment.toLowerCase()}</span>}
              {i.topics.map((t) => <span key={t} className="px-1 bg-gray-100 rounded">{t}</span>)}<span className="ml-auto">{i.status.toLowerCase()}</span></div>
            <p>{i.text ?? <i>Deleted by the author.</i>}</p>
            {(i.evidence.positive?.length || i.evidence.negative?.length) ? <p className="text-gray-500">Because of: {[...(i.evidence.positive ?? []), ...(i.evidence.negative ?? [])].join(", ")}</p> : null}
            {i.status !== "DELETED" && <>
              <textarea aria-label="Reply draft" rows={2} className={`${input} w-full`} defaultValue={i.reply_draft ?? ""} onBlur={(e) => e.target.value !== (i.reply_draft ?? "") && run(() => apiClient.patch(`/api/v1/social/inbox/${i.id}`, { reply_draft: e.target.value }), "Draft saved.")} />
              <div className="flex flex-wrap gap-2">
                <button className="underline" onClick={() => run(async () => { const r = await apiClient.post(`/api/v1/social/inbox/${i.id}/suggest-reply`); await apiClient.patch(`/api/v1/social/inbox/${i.id}`, { reply_draft: r.data.reply_draft }); }, "Suggested a draft — edit before replying on the network.")}>Suggest reply</button>
                {(["ASSIGNED", "REPLIED", "HIDDEN", "DONE"] as const).map((s) => <button key={s} className="underline" onClick={() => run(() => apiClient.patch(`/api/v1/social/inbox/${i.id}`, { status: s }), "Updated.")}>{s.toLowerCase()}</button>)}
              </div></>}
          </li>))}</ul>
      </section>}
    </div>
  );
}
