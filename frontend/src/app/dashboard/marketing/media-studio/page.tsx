"use client";
// M51.S01.T006/T007/T010 media studio: AI image drafts, narration/caption/poster/trim/transcode jobs, large resumable uploads.
// Everything produced here is a DRAFT until a second person approves it; nothing is published from this page.
import { useCallback, useEffect, useRef, useState } from "react";
import { apiClient } from "@/lib/api";
import { tx } from "@/lib/i18n/core";

const B = "/api/v1/media-studio";
type Finding = { level: string; code: string; message: string };
type ImageJob = { id: string; status: string; mode: string; provider: string; model: string | null; title: string; prompt: string; size: string; document_id: string | null;
  findings: Finding[]; provenance: Record<string, string | null>; cost_estimate: number; error: string | null; created_by: string; reviewed_by: string | null };
type Job = { id: string; kind: string; status: string; progress: number; error: string | null; output_object_id: string | null; source_object_id: string | null; has_captions: boolean; result: Record<string, unknown> };
type Obj = { id: string; backend: string; file_name: string; mime: string; size: number; status: string; scan_status: string; approval: string; sha256: string | null };
type Status = { images: { status: string; detail?: string; mode?: string; provider?: string; budget_usd: number; spent_this_month: number; calls_this_month: number };
  tools: { ffmpeg: { status: string; detail: string | null }; presets: Record<string, { available: boolean }>; tts: { status: string; engine?: string; detail?: string; voices: Record<string, { supported: boolean; note: string | null }> } };
  storage: { backend: string; status: string; used_bytes: number; quota_bytes: number; scanner: string; require_scan: boolean } };
const err = (e: unknown) => { const d = (e as { response?: { data?: { detail?: unknown } } }).response?.data?.detail; return typeof d === "string" ? d : d && typeof d === "object" ? JSON.stringify(d).slice(0, 200) : "Something went wrong."; };
const mb = (n: number) => `${(n / 1048576).toFixed(n < 1048576 ? 2 : 1)} MiB`;
const badge = (s: string) => ({ GENERATED: "bg-amber-100", APPROVED: "bg-green-100", SUCCEEDED: "bg-green-100", READY: "bg-green-100", REJECTED: "bg-red-100", FAILED: "bg-red-100", TIMEOUT: "bg-red-100", UNAVAILABLE: "bg-gray-200", QUARANTINED: "bg-red-100" } as Record<string, string>)[s] ?? "bg-gray-100";

export default function MediaStudioPage() {
  const [st, setSt] = useState<Status | null>(null);
  const [images, setImages] = useState<ImageJob[]>([]);
  const [jobs, setJobs] = useState<Job[]>([]);
  const [objs, setObjs] = useState<Obj[]>([]);
  const [msg, setMsg] = useState<string | null>(null);
  const [img, setImg] = useState({ title: "", prompt: "", overlay: "", size: "1024x1024", skus: "" });
  const [job, setJob] = useState({ kind: "NARRATION", source: "", text: "", locale: "en", start: "0", end: "5", at: "1", preset: "WAV" });
  const [up, setUp] = useState<{ name: string; done: number; total: number; session?: string; file?: File } | null>(null);
  const [preview, setPreview] = useState<{ url: string; mime: string } | null>(null);
  const [busy, setBusy] = useState(false);
  const fileRef = useRef<HTMLInputElement>(null);
  const say = (m: string) => setMsg(m);

  const load = useCallback(() => Promise.all([apiClient.get(`${B}/status`), apiClient.get(`${B}/images`), apiClient.get(`${B}/jobs`), apiClient.get(`${B}/storage/objects`)])
    .then(([s, i, j, o]) => { setSt(s.data); setImages(i.data); setJobs(j.data); setObjs(o.data); }).catch((e) => say(err(e))), []);
  useEffect(() => { void load(); }, [load]);
  const active = jobs.some((j) => j.status === "QUEUED" || j.status === "RUNNING");
  useEffect(() => { if (!active) return; const t = setInterval(() => void load(), 1500); return () => clearInterval(t); }, [active, load]);

  const act = (p: Promise<unknown>, ok: string) => p.then(() => { say(ok); return load(); }).catch((e) => say(err(e)));

  const makeImage = async () => {
    setBusy(true);
    try {
      const r = await apiClient.post(`${B}/images`, { title: img.title, prompt: img.prompt, size: img.size, overlay_text: img.overlay || null, product_skus: img.skus.split(",").map((s) => s.trim()).filter(Boolean) });
      say(r.data.status === "GENERATED" ? "Image created as a draft. A second person must approve it." : `${r.data.status}: ${r.data.error ?? ""}`);
      await load();
    } catch (e) { say(err(e)); } finally { setBusy(false); }
  };

  const makeJob = () => {
    const k = job.kind;
    const params = k === "NARRATION" ? { text: job.text, locale: job.locale } : k === "CAPTIONS" ? { text: job.text, locale: job.locale }
      : k === "TRIM" ? { start: +job.start, end: +job.end, reencode: true } : k === "POSTER" ? { at: +job.at } : { preset: job.preset };
    return act(apiClient.post(`${B}/jobs`, { kind: k, source_object_id: k === "NARRATION" ? null : job.source || null, params }), "Job queued.");
  };

  // Resumable multipart upload: ask the server which parts it really holds, send only the missing ones.
  const upload = async (file: File, resume?: string) => {
    try {
      let sid = resume;
      if (!sid) {
        const r = await apiClient.post(`${B}/storage/uploads`, { file_name: file.name, total_size: file.size });
        sid = r.data.id as string;
      }
      const s = (await apiClient.get(`${B}/storage/uploads/${sid}`)).data;
      const have = new Set<number>(s.received_parts);
      setUp({ name: file.name, done: have.size, total: s.parts_total, session: sid, file });
      for (let n = 1; n <= s.parts_total; n++) {
        if (have.has(n)) continue;
        await apiClient.put(`${B}/storage/uploads/${sid}/parts/${n}`, file.slice((n - 1) * s.part_size, n * s.part_size), { headers: { "Content-Type": "application/octet-stream" } });
        have.add(n);
        setUp({ name: file.name, done: have.size, total: s.parts_total, session: sid, file });
      }
      await apiClient.post(`${B}/storage/uploads/${sid}/complete`);
      setUp(null);
      say("Upload complete: scanned and stored.");
      await load();
    } catch (e) { say(`${err(e)} ${up ? "You can resume the upload." : ""}`); }
  };

  // captions need the signed-in session, so fetch them and hand the browser a file
  const save = async (id: string, format: string) => {
    try {
      const r = await apiClient.get(`${B}/jobs/${id}/captions?format=${format}`, { responseType: "blob" });
      const a = document.createElement("a");
      a.href = URL.createObjectURL(r.data as Blob); a.download = `captions.${format}`; a.click(); URL.revokeObjectURL(a.href);
    } catch (e) { say(err(e)); }
  };

  const play = async (o: Obj) => {
    try { const r = await apiClient.post(`${B}/storage/objects/${o.id}/access-url`, { ttl_seconds: 300 }); setPreview({ url: r.data.url, mime: o.mime }); }
    catch (e) { say(err(e)); }
  };

  return <main className="p-4 space-y-6 max-w-5xl">
    <h1 className="text-xl font-semibold">{tx("Media studio")}</h1>
    <p className="text-xs text-gray-500">{tx("AI images, narration, captions, posters, trims and large uploads. Everything created here is a draft until a second person approves it.")}</p>
    {msg && <div role="status" className="border rounded p-2 text-sm bg-blue-50">{msg} <button className="underline text-xs" onClick={() => setMsg(null)}>{tx("dismiss")}</button></div>}
    {st && <section className="grid gap-2 sm:grid-cols-3 text-xs" aria-label={tx("Tool status")}>
      <div className="border rounded p-2"><b>{tx("Images")}</b>: {st.images.status}{st.images.mode ? tx(" ({mode}, {provider})", { mode: st.images.mode, provider: st.images.provider }) : ""}<br />{tx("Budget $")}{st.images.budget_usd.toFixed(2)}{tx(", used $")}{st.images.spent_this_month.toFixed(2)} {tx("in")} {st.images.calls_this_month} {tx("calls")}{st.images.detail && <><br />{st.images.detail}</>}</div>
      <div className="border rounded p-2"><b>{tx("ffmpeg")}</b>: {st.tools.ffmpeg.status}{st.tools.ffmpeg.detail && <><br />{st.tools.ffmpeg.detail}</>}<br /><b>{tx("Narration")}</b>: {st.tools.tts.status}{st.tools.tts.engine ? ` (${st.tools.tts.engine})` : ""}<br />
        {Object.entries(st.tools.tts.voices).map(([l, v]) => <span key={l} className="mr-2">{l.toUpperCase()}: {v.supported ? tx("yes") : tx("no")}</span>)}</div>
      <div className="border rounded p-2"><b>{tx("Storage")}</b>: {st.storage.backend} {st.storage.status}<br />{mb(st.storage.used_bytes)} {tx("of")} {mb(st.storage.quota_bytes)}<br />{tx("Virus scan:")} {st.storage.scanner}{st.storage.scanner !== "clamav" && tx(" (files stay quarantined until a scanner is configured)")}</div>
    </section>}

    <section className="border rounded p-3 bg-white space-y-2 text-xs" aria-label={tx("AI image")}>
      <h2 className="font-semibold text-sm">{tx("AI image (draft)")}</h2>
      <input aria-label={tx("Image title")} placeholder={tx("Title, e.g. POVU AllClean counter visual")} className="border rounded px-1 w-full" value={img.title} onChange={(e) => setImg({ ...img, title: e.target.value })} />
      <textarea aria-label={tx("Image prompt")} rows={2} placeholder={tx("Describe the image (at least 10 characters)")} className="border rounded px-1 w-full" value={img.prompt} onChange={(e) => setImg({ ...img, prompt: e.target.value })} />
      <div className="grid gap-2 sm:grid-cols-3">
        <input aria-label={tx("Text on the image")} placeholder={tx("Text on the image (claims need approved evidence)")} className="border rounded px-1" value={img.overlay} onChange={(e) => setImg({ ...img, overlay: e.target.value })} />
        <input aria-label={tx("Product SKUs")} placeholder={tx("Product SKUs, comma separated")} className="border rounded px-1" value={img.skus} onChange={(e) => setImg({ ...img, skus: e.target.value })} />
        <select aria-label={tx("Image size")} className="border rounded px-1" value={img.size} onChange={(e) => setImg({ ...img, size: e.target.value })}><option>{tx("1024x1024")}</option><option>{tx("1536x1024")}</option><option>{tx("1024x1536")}</option></select>
      </div>
      <button className="bg-indigo-600 text-white rounded px-3 py-1 disabled:opacity-50" disabled={busy || img.title.length < 1 || img.prompt.length < 10 || st?.images.status !== "AVAILABLE"} onClick={() => void makeImage()}>{tx("Generate image")}</button>
      {st?.images.status !== "AVAILABLE" && <span className="ml-2 text-gray-500">{tx("Disabled:")} {st?.images.detail ?? tx("no image provider")}</span>}
      <ul className="space-y-2 pt-2">{images.map((i) => <li key={i.id} className="border rounded p-2">
        <span className={`px-1 rounded ${badge(i.status)}`}>{i.status}</span> <b>{i.title}</b> · {i.mode} · {i.provider}{i.model ? `/${i.model}` : ""} · {i.size} · ${i.cost_estimate.toFixed(2)}
        {i.error && <div className="text-red-700">{i.error}</div>}
        {i.findings.map((f, n) => <div key={n} className="text-red-700">{f.message}</div>)}
        {i.provenance.prompt_sha256 && <div className="text-gray-500">{tx("Provenance: prompt hash")} {i.provenance.prompt_sha256.slice(0, 12)}…, {i.provenance.generated_at}</div>}
        {i.document_id && <div>{tx("Asset library document")} {i.document_id}</div>}
        {i.status === "GENERATED" && <div className="space-x-2 pt-1">
          <button className="border rounded px-2" onClick={() => void act(apiClient.post(`${B}/images/${i.id}/review`, { approve: true }), "Approved: usable in e-mail, social, CMS and ads.")}>{tx("Approve")}</button>
          <button className="border rounded px-2" onClick={() => void act(apiClient.post(`${B}/images/${i.id}/review`, { approve: false }), "Discarded.")}>{tx("Discard")}</button></div>}
      </li>)}</ul>
    </section>

    <section className="border rounded p-3 bg-white space-y-2 text-xs" aria-label={tx("Media jobs")}>
      <h2 className="font-semibold text-sm">{tx("Narration, captions and video tools")}</h2>
      <div className="grid gap-2 sm:grid-cols-4">
        <select aria-label={tx("Job kind")} className="border rounded px-1" value={job.kind} onChange={(e) => setJob({ ...job, kind: e.target.value })}>{["NARRATION", "CAPTIONS", "POSTER", "TRIM", "TRANSCODE"].map((k) => <option key={k}>{k}</option>)}</select>
        {job.kind !== "NARRATION" && <select aria-label={tx("Source media")} className="border rounded px-1 sm:col-span-2" value={job.source} onChange={(e) => setJob({ ...job, source: e.target.value })}><option value="">{tx("Pick a ready media file")}</option>
          {objs.filter((o) => o.status === "READY" && (o.mime.startsWith("video/") || o.mime.startsWith("audio/"))).map((o) => <option key={o.id} value={o.id}>{o.file_name} ({mb(o.size)})</option>)}</select>}
        {(job.kind === "NARRATION" || job.kind === "CAPTIONS") && <select aria-label={tx("Language")} className="border rounded px-1" value={job.locale} onChange={(e) => setJob({ ...job, locale: e.target.value })}>
          {[tx("en"), tx("sw"), tx("tr")].map((l) => <option key={l} value={l}>{l.toUpperCase()}{job.kind === "NARRATION" && st && !st.tools.tts.voices[l]?.supported ? tx(" (no voice)") : ""}</option>)}</select>}
        {job.kind === "TRIM" && <><input aria-label={tx("Start seconds")} type="number" min={0} className="border rounded px-1" value={job.start} onChange={(e) => setJob({ ...job, start: e.target.value })} /><input aria-label={tx("End seconds")} type="number" min={0} className="border rounded px-1" value={job.end} onChange={(e) => setJob({ ...job, end: e.target.value })} /></>}
        {job.kind === "POSTER" && <input aria-label={tx("Poster time seconds")} type="number" min={0} className="border rounded px-1" value={job.at} onChange={(e) => setJob({ ...job, at: e.target.value })} />}
        {job.kind === "TRANSCODE" && <select aria-label={tx("Preset")} className="border rounded px-1" value={job.preset} onChange={(e) => setJob({ ...job, preset: e.target.value })}>{Object.entries(st?.tools.presets ?? { WAV: { available: true } }).map(([k, v]) => <option key={k} value={k} disabled={!v.available}>{k}{v.available ? "" : tx(" (encoder missing)")}</option>)}</select>}
      </div>
      {(job.kind === "NARRATION" || job.kind === "CAPTIONS") && <textarea aria-label={tx("Script")} rows={3} placeholder={job.kind === "CAPTIONS" ? tx("Script of the media; cue times are estimated from sentence length") : tx("Text to read aloud")} className="border rounded px-1 w-full" value={job.text} onChange={(e) => setJob({ ...job, text: e.target.value })} />}
      <button className="bg-indigo-600 text-white rounded px-3 py-1 disabled:opacity-50" disabled={(job.kind !== "NARRATION" && !job.source) || ((job.kind === "NARRATION" || job.kind === "CAPTIONS") && job.text.trim().length < 3)} onClick={() => void makeJob()}>{tx("Create job")}</button>
      <ul className="space-y-1 pt-2">{jobs.map((j) => <li key={j.id} className="border rounded p-2">
        <span className={`px-1 rounded ${badge(j.status)}`}>{j.status}</span> <b>{j.kind}</b>
        {(j.status === "RUNNING" || j.status === "QUEUED") && <progress aria-label={tx("Progress")} className="ml-2 align-middle" max={1} value={j.progress} />} {Math.round(j.progress * 100)}%
        {j.error && <div className="text-red-700">{j.error}</div>}
        {j.result?.timing != null && <div className="text-gray-500">{String(j.result.cues)} {tx("cues ·")} {String(j.result.timing)}</div>}
        <span className="space-x-2 ml-2">
          {j.has_captions && [tx("vtt"), tx("srt")].map((f) => <button key={f} className="underline" onClick={() => void save(j.id, f)}>{f.toUpperCase()}</button>)}
          {(j.status === "QUEUED" || j.status === "RUNNING") && <button className="border rounded px-2" onClick={() => void act(apiClient.post(`${B}/jobs/${j.id}/cancel`), "Cancelled.")}>{tx("Cancel")}</button>}</span>
      </li>)}</ul>
    </section>

    <section className="border rounded p-3 bg-white space-y-2 text-xs" aria-label={tx("Storage")}>
      <h2 className="font-semibold text-sm">{tx("Media files")}</h2>
      <div className="space-x-2"><input ref={fileRef} aria-label={tx("Choose media file")} type="file" accept=".mp4,.m4v,.webm,.m4a,.mp3,.ogg,.wav,.png,.jpg,.jpeg,.webp" onChange={(e) => { const f = e.target.files?.[0]; if (f) void upload(f); }} />
        {up && <span>{up.name}: {up.done}/{up.total} {tx("parts")} <progress aria-label={tx("Upload progress")} max={up.total} value={up.done} /> {up.session && up.file && <button className="border rounded px-2" onClick={() => void upload(up.file!, up.session)}>{tx("Resume")}</button>}
          {up.session && <button className="border rounded px-2" onClick={() => void act(apiClient.delete(`${B}/storage/uploads/${up.session}`).then(() => setUp(null)), "Upload cancelled and cleaned up.")}>{tx("Cancel upload")}</button>}</span>}</div>
      {preview && <div className="border rounded p-2">{preview.mime.startsWith("video/") ? <video controls className="max-h-64" src={preview.url} /> : preview.mime.startsWith("audio/") ? <audio controls src={preview.url} /> : <img alt={tx("Preview")} className="max-h-64" src={preview.url} />}
        <button className="underline ml-2" onClick={() => setPreview(null)}>{tx("Close preview")}</button></div>}
      <ul className="space-y-1">{objs.map((o) => <li key={o.id} className="border rounded p-2">
        <span className={`px-1 rounded ${badge(o.status)}`}>{o.status}</span> <b>{o.file_name}</b> · {mb(o.size)} {tx("· scan")} {o.scan_status} · {o.approval} · {o.backend}
        <span className="space-x-2 ml-2">
          <button className="border rounded px-2 disabled:opacity-40" disabled={o.status !== "READY"} title={o.status !== "READY" ? tx("Only clean, ready files can be played") : ""} onClick={() => void play(o)}>{tx("Play")}</button>
          {o.approval === "DRAFT" && o.status === "READY" && <button className="border rounded px-2" onClick={() => void act(apiClient.post(`${B}/storage/objects/${o.id}/approve`), "Approved.")}>{tx("Approve")}</button>}
          <button className="border rounded px-2" onClick={() => void act(apiClient.post(`${B}/storage/objects/${o.id}/revoke`), "All issued links revoked.")}>{tx("Revoke links")}</button>
          <button className="border rounded px-2" onClick={() => { if (confirm(tx("Delete {file_name}? This removes the stored file.", { file_name: o.file_name }))) void act(apiClient.delete(`${B}/storage/objects/${o.id}`), "Deleted."); }}>{tx("Delete")}</button></span>
      </li>)}</ul>
      <div className="space-x-2 pt-1">
        <button className="border rounded px-2" onClick={() => void act(apiClient.post(`${B}/storage/backups`), "Backup finished.")}>{tx("Back up now")}</button>
        <button className="border rounded px-2" onClick={() => void act(apiClient.post(`${B}/storage/cleanup`).then((r) => say(`Cleanup: ${JSON.stringify(r.data)}`)), "Cleanup done.")}>{tx("Clean up expired uploads")}</button></div>
    </section>
  </main>;
}
