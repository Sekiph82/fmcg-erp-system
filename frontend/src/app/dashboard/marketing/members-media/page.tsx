"use client";
// M46.S01.T006 members and media: access lists of portal accounts (with revocation), video/audio library with
// WebVTT captions, podcast shows, and who watched (member plays also appear on the customer timeline).
import { useCallback, useEffect, useState } from "react";
import { apiClient } from "@/lib/api";

type Acl = { id: string; name: string; account_ids: string[]; account_types: string[]; revoked_ids: string[] };
type Account = { id: string; code: string; name: string | null; type: string; status: string };
type Media = { id: string; kind: string; title: string; mime: string; size: number; captions: string[]; podcast: string | null; public: boolean; access_list_id: string | null; views: number;
  page_id: string | null; poster: boolean };
const err = (e: unknown) => { const d = (e as { response?: { data?: { detail?: unknown } } }).response?.data?.detail; return typeof d === "string" ? d : typeof (d as { detail?: unknown })?.detail === "string" ? (d as { detail: string }).detail : "Something went wrong."; };

export default function MembersMediaPage() {
  const [acls, setAcls] = useState<Acl[]>([]);
  const [accounts, setAccounts] = useState<Account[]>([]);
  const [media, setMedia] = useState<Media[]>([]);
  const [cur, setCur] = useState<Acl | null>(null);
  const [name, setName] = useState("");
  const [up, setUp] = useState<{ file: File | null; title: string; podcast: string; access: string }>({ file: null, title: "", podcast: "", access: "" });
  const [cap, setCap] = useState<{ id: string; locale: string; vtt: string } | null>(null);
  const [views, setViews] = useState<{ id: string; rows: { at: string; account: string | null; seconds: number }[] } | null>(null);
  const [msg, setMsg] = useState<string | null>(null);
  const [cut, setCut] = useState<{ id: string; at: string; start: string; end: string } | null>(null);
  const load = useCallback(() => {
    apiClient.get("/api/v1/cms/access-lists").then((r) => { setAcls(r.data); setCur((c) => r.data.find((a: Acl) => a.id === c?.id) ?? null); }).catch((e) => setMsg(err(e)));
    apiClient.get("/api/v1/cms/media").then((r) => setMedia(r.data)).catch(() => {});
  }, []);
  useEffect(() => { load(); apiClient.get("/api/v1/cms/portal-accounts").then((r) => setAccounts(r.data)).catch(() => {}); }, [load]);
  const saveAcl = (a: Acl, patch: Partial<Acl>) => apiClient.patch(`/api/v1/cms/access-lists/${a.id}`, patch).then(load).catch((e) => setMsg(err(e)));
  const upload = () => {
    if (!up.file) return;
    const fd = new FormData();
    fd.append("file", up.file); fd.append("title", up.title || up.file.name);
    if (up.podcast) fd.append("podcast", up.podcast);
    if (up.access === "PUBLIC") fd.append("public", "true"); else if (up.access) fd.append("access_list_id", up.access);
    apiClient.post("/api/v1/cms/media", fd).then(() => { setMsg("Uploaded."); setUp({ file: null, title: "", podcast: "", access: "" }); load(); }).catch((e) => setMsg(err(e)));
  };
  return (
    <div className="p-4 space-y-3 text-sm">
      <h2 className="text-lg font-semibold">Members &amp; media</h2>
      <p className="text-xs text-gray-500">Members sign in through the customer portal. A page, video or help article on an access list is shown only to listed accounts; removing or revoking an account takes effect at once.</p>
      {msg && <p role="status" className="text-xs bg-amber-50 border rounded p-2">{msg}</p>}
      <section className="border rounded p-3 bg-white space-y-2 text-xs">
        <h3 className="font-semibold text-sm">Access lists</h3>
        <div className="flex gap-2"><input aria-label="New access list" placeholder="e.g. Gold distributors" className="border rounded px-1" value={name} onChange={(e) => setName(e.target.value)} />
          <button className="border rounded px-2" onClick={() => apiClient.post("/api/v1/cms/access-lists", { name }).then(() => { setName(""); load(); }).catch((e) => setMsg(err(e)))}>Create</button></div>
        <ul className="flex flex-wrap gap-2">{acls.map((a) => <li key={a.id}><button className={`border rounded px-2 ${cur?.id === a.id ? "bg-indigo-50 font-bold" : ""}`} onClick={() => setCur(a)}>{a.name} ({a.account_ids.length})</button></li>)}</ul>
        {cur && <div className="space-y-1">
          <fieldset className="flex gap-3"><legend>Whole account types</legend>{["CUSTOMER", "DISTRIBUTOR"].map((t) => <label key={t} className="flex gap-1"><input type="checkbox" checked={cur.account_types.includes(t)}
            onChange={(e) => saveAcl(cur, { account_types: e.target.checked ? [...cur.account_types, t] : cur.account_types.filter((x) => x !== t) })} />{t.toLowerCase()}</label>)}</fieldset>
          <table className="w-full"><thead><tr><th className="text-left">Portal account</th><th>Type</th><th>Member</th><th>Revoked</th></tr></thead><tbody>{accounts.map((a) =>
            <tr key={a.id} className="border-t"><td>{a.code}{a.name ? ` · ${a.name}` : ""}</td><td className="text-center">{a.type.toLowerCase()}</td>
              <td className="text-center"><input type="checkbox" aria-label={`Member ${a.code}`} checked={cur.account_ids.includes(a.id)} onChange={(e) => saveAcl(cur, { account_ids: e.target.checked ? [...cur.account_ids, a.id] : cur.account_ids.filter((x) => x !== a.id) })} /></td>
              <td className="text-center"><input type="checkbox" aria-label={`Revoke ${a.code}`} checked={cur.revoked_ids.includes(a.id)} onChange={(e) => saveAcl(cur, { revoked_ids: e.target.checked ? [...cur.revoked_ids, a.id] : cur.revoked_ids.filter((x) => x !== a.id) })} /></td></tr>)}</tbody></table>
          <p className="text-gray-500">To gate a help article, set its access list in Knowledge base (field access_list_id) — members read it at /kb/members.</p>
        </div>}
      </section>
      <section className="border rounded p-3 bg-white space-y-2 text-xs">
        <h3 className="font-semibold text-sm">Video &amp; audio</h3>
        <div className="flex flex-wrap gap-2 items-center">
          <input aria-label="Media file" type="file" accept=".mp4,.m4v,.webm,.m4a,.mp3,.ogg,.wav" onChange={(e) => setUp({ ...up, file: e.target.files?.[0] ?? null })} />
          <input aria-label="Media title" placeholder="Title" className="border rounded px-1" value={up.title} onChange={(e) => setUp({ ...up, title: e.target.value })} />
          <input aria-label="Podcast show" placeholder="Podcast show (optional)" className="border rounded px-1" value={up.podcast} onChange={(e) => setUp({ ...up, podcast: e.target.value })} />
          <select aria-label="Media access" className="border rounded" value={up.access} onChange={(e) => setUp({ ...up, access: e.target.value })}>
            <option value="">Staff only (not shown)</option><option value="PUBLIC">Public</option>{acls.map((a) => <option key={a.id} value={a.id}>Members: {a.name}</option>)}</select>
          <button className="bg-indigo-600 text-white rounded px-3 py-1" onClick={upload} disabled={!up.file}>Upload</button></div>
        <ul className="divide-y">{media.length === 0 ? <li className="py-1 text-gray-500">No media yet.</li> : media.map((m) => <li key={m.id} className="py-1 space-y-1">
          <div className="flex flex-wrap justify-between gap-2"><span><b>{m.title}</b> · {m.kind.toLowerCase()} · {(m.size / 1048576).toFixed(1)} MB · {m.public ? "public" : m.access_list_id ? `members: ${acls.find((a) => a.id === m.access_list_id)?.name ?? "list"}` : "staff only"}
            {m.podcast ? ` · podcast ${m.podcast}` : ""}{m.page_id ? " · page narration" : ""}{m.poster ? " · poster set" : ""} · captions {m.captions.join(", ") || "none"} · {m.views} plays · id <code className="select-all">{m.id}</code></span>
            <span className="flex gap-2"><button className="underline" onClick={() => setCap({ id: m.id, locale: "en", vtt: "WEBVTT\n\n00:00.000 --> 00:03.000\n" })}>Captions</button>
              <button className="underline" onClick={() => setCut(cut?.id === m.id ? null : { id: m.id, at: "0", start: "0", end: "10" })}>Poster / Trim</button>
              <button className="underline" onClick={() => apiClient.get(`/api/v1/cms/media/${m.id}/views`).then((r) => setViews({ id: m.id, rows: r.data }))}>Plays</button></span></div>
          {cap?.id === m.id && <div className="space-y-1"><select aria-label="Caption language" className="border rounded" value={cap.locale} onChange={(e) => setCap({ ...cap, locale: e.target.value })}>{["en", "sw", "tr"].map((l) => <option key={l}>{l}</option>)}</select>
            <textarea aria-label="WebVTT captions" rows={5} className="border rounded w-full font-mono" value={cap.vtt} onChange={(e) => setCap({ ...cap, vtt: e.target.value })} />
            <button className="border rounded px-2" onClick={() => apiClient.put(`/api/v1/cms/media/${m.id}/captions/${cap.locale}`, { vtt: cap.vtt }).then(() => { setCap(null); load(); }).catch((e) => setMsg(err(e)))}>Save captions</button></div>}
          {cut?.id === m.id && <div className="flex flex-wrap gap-2 items-center">
            {m.kind === "VIDEO" && <><label>Poster at (s)<input aria-label="Poster time" type="number" min={0} step="0.1" className="border rounded px-1 w-16 ml-1" value={cut.at} onChange={(e) => setCut({ ...cut, at: e.target.value })} /></label>
              <button className="border rounded px-2" onClick={() => apiClient.post(`/api/v1/cms/media/${m.id}/poster`, { t: +cut.at || 0 }).then(() => { setMsg("Poster frame saved; it is shown with the same access as the video."); load(); }).catch((e) => setMsg(err(e)))}>Make poster</button></>}
            <label>Trim from (s)<input aria-label="Trim start" type="number" min={0} step="0.1" className="border rounded px-1 w-16 ml-1" value={cut.start} onChange={(e) => setCut({ ...cut, start: e.target.value })} /></label>
            <label>to (s)<input aria-label="Trim end" type="number" min={0} step="0.1" className="border rounded px-1 w-16 ml-1" value={cut.end} onChange={(e) => setCut({ ...cut, end: e.target.value })} /></label>
            <button className="border rounded px-2" onClick={() => apiClient.post(`/api/v1/cms/media/${m.id}/trim`, { start: +cut.start, end: +cut.end }).then(() => { setMsg("Trimmed copy saved as a new staff-only item; the original is unchanged."); setCut(null); load(); }).catch((e) => setMsg(err(e)))}>Save trimmed copy</button></div>}
          {views?.id === m.id &&<ul className="pl-3">{views.rows.length === 0 ? <li>No plays yet.</li> : views.rows.map((v, i) => <li key={i}>{new Date(v.at).toLocaleString()} · {v.account ?? "anonymous"} · {v.seconds} s</li>)}</ul>}
        </li>)}</ul>
      </section>
    </div>
  );
}
