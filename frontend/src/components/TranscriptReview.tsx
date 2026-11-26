"use client";
// M49.S01.T005: start a transcription (EN/SW/TR/auto, optional speaker labels), review and correct it, approve into
// coaching, withdraw, or type it by hand when no engine works. Shows provider signals only - never an accuracy figure.
import { useCallback, useEffect, useState } from "react";
import { apiClient } from "@/lib/api";
import { tx } from "@/lib/i18n/core";

interface Seg { start: number | null; end: number | null; speaker: string | null; text: string; edited: boolean }
interface Job { id: string; engine: string; status: string; review_status: string; language_requested: string; language_detected: string | null;
  error_code: string | null; error: string | null; warnings: string[] | null; redacted_segments: number; segments?: Seg[];
  quality: { flags: string[]; speakers: string[]; provider_signals: { mean_avg_logprob: number | null; max_no_speech_prob: number | null }; note: string } | null }
interface Engine { key: string; label: string; state: string; note: string | null }

const detail = (e: unknown, fb: string) => {
  const d = (e as { response?: { data?: { detail?: unknown } } }).response?.data?.detail;
  return typeof d === "string" ? d : fb;
};
const BASE = "/api/v1/calls/transcripts";

export function TranscriptReview({ callId, hasConsentedRecording }: { callId: string; hasConsentedRecording: boolean }) {
  const [engines, setEngines] = useState<Engine[]>([]);
  const [job, setJob] = useState<Job | null>(null);
  const [lang, setLang] = useState("auto");
  const [diarize, setDiarize] = useState(false);
  const [msg, setMsg] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [manual, setManual] = useState("");
  const [drafts, setDrafts] = useState<Record<number, { text: string; speaker: string }>>({});

  const load = useCallback(async () => {
    apiClient.get(`${BASE}/engines`).then((r) => setEngines(r.data.engines)).catch(() => setEngines([]));
    try {
      const list = (await apiClient.get(BASE, { params: { source_type: "call", source_id: callId } })).data as Job[];
      const cur = list.find((j) => j.status !== "WITHDRAWN") ?? null;
      setJob(cur ? (await apiClient.get(`${BASE}/${cur.id}`)).data : null);
    } catch { setJob(null); }
  }, [callId]);
  useEffect(() => { load(); }, [load]);

  async function act(fn: () => Promise<unknown>, ok: string) {
    setBusy(true);
    try { await fn(); setMsg(ok); setDrafts({}); await load(); } catch (e) { setMsg(detail(e, tx("That did not work."))); } finally { setBusy(false); }
  }
  const available = engines.some((e) => e.state === "AVAILABLE");
  const startReason = !hasConsentedRecording ? tx("Needs a consented https recording.") : !available ? tx("No engine is available (see below).") : undefined;
  const btn = "rounded border px-2 py-1 text-xs disabled:opacity-40 disabled:cursor-not-allowed";

  return (
    <div className="text-xs space-y-2 border rounded p-2 bg-white" aria-label={tx("Transcription review")}>
      <div className="flex flex-wrap gap-2 items-center">
        <label>{tx("Language")} <select className="border rounded px-1" value={lang} onChange={(e) => setLang(e.target.value)}>
          <option value="auto">{tx("Auto-detect")}</option><option value="en">{tx("English")}</option><option value="sw">{tx("Kiswahili")}</option><option value="tr">{tx("Turkce")}</option></select></label>
        <label title={tx("Speaker labels come from the diarization model; sw/tr quality is not verified.")}><input type="checkbox" checked={diarize} onChange={(e) => setDiarize(e.target.checked)} /> {tx("Speaker labels")}</label>
        <button className={btn} disabled={busy || !!startReason || (!!job && job.status !== "FAILED")} title={startReason}
          onClick={() => act(() => apiClient.post(BASE, { source_type: "call", source_id: callId, language: lang, diarize }), tx("Transcription finished; review it before approving."))}>{tx("Start transcription")}</button>
        {startReason && <span className="text-gray-500">{startReason}</span>}
      </div>
      <ul className="text-gray-600">
        {engines.map((e) => <li key={e.key}><b>{e.label}</b>: {e.state}{e.note ? ` - ${e.note}` : ""}</li>)}
      </ul>
      {msg && <p role="status">{msg}</p>}
      {job && (
        <div className="space-y-1">
          <div>{tx("Status")} <b>{job.status}</b> {tx("· review")} <b>{job.review_status}</b> {tx("· engine")} {job.engine}
            {job.language_detected && tx(" · language {language_detected}", { language_detected: job.language_detected })}{job.redacted_segments > 0 && tx(" · personal data masked in {redacted_segments} segment(s)", { redacted_segments: job.redacted_segments })}</div>
          {job.status === "FAILED" && <p className="text-red-600">{tx("Failed (")}{job.error_code}): {job.error}</p>}
          {job.quality && (
            <p className="text-gray-600">{tx("Provider signals only (not an accuracy score): mean log-prob")} {job.quality.provider_signals.mean_avg_logprob ?? tx("n/a")}{tx(", max no-speech")} {job.quality.provider_signals.max_no_speech_prob ?? tx("n/a")}
              {job.quality.flags.length > 0 && <span className="text-amber-700"> {tx("· flags:")} {job.quality.flags.join(", ")}</span>}</p>
          )}
          {job.warnings?.map((w) => <p key={w} className="text-amber-700">{w}</p>)}
          {job.status === "DONE" && job.segments?.map((s, i) => {
            const d = drafts[i] ?? { text: s.text, speaker: s.speaker ?? "" };
            return (
              <div key={i} className="flex gap-1 items-start">
                <span className="w-12 text-gray-400">{s.start !== null ? `${s.start.toFixed(1)}s` : ""}</span>
                <input className="border rounded px-1 w-20" aria-label={tx("Speaker {i}", { i: i + 1 })} value={d.speaker} placeholder={tx("speaker")} maxLength={20} onChange={(e) => setDrafts({ ...drafts, [i]: { ...d, speaker: e.target.value } })} />
                <textarea className="border rounded px-1 flex-1" aria-label={tx("Segment {i}", { i: i + 1 })} rows={2} maxLength={4000} value={d.text} onChange={(e) => setDrafts({ ...drafts, [i]: { ...d, text: e.target.value } })} />
                <button className={btn} disabled={busy || !drafts[i] || (d.text === s.text && d.speaker === (s.speaker ?? ""))}
                  onClick={() => act(() => apiClient.patch(`${BASE}/${job.id}/segments/${i}`, { text: d.text, speaker: d.speaker }), tx("Segment saved."))}>{s.edited ? tx("Saved*") : tx("Save")}</button>
              </div>
            );
          })}
          <div className="flex gap-2">
            <button className={btn} disabled={busy || job.status !== "DONE" || job.review_status === "REVIEWED"} title={job.status !== "DONE" ? tx("Only a finished transcript can be approved.") : undefined}
              onClick={() => act(() => apiClient.post(`${BASE}/${job.id}/approve`), tx("Approved: coaching can now use this transcript."))}>{tx("Approve for coaching")}</button>
            {job.status === "FAILED" && <button className={btn} disabled={busy} onClick={() => act(() => apiClient.post(`${BASE}/${job.id}/retry`), "Retried.")}>{tx("Retry")}</button>}
            <button className="rounded border border-red-300 text-red-700 px-2 py-1 text-xs disabled:opacity-40" disabled={busy || job.status === "WITHDRAWN"}
              onClick={() => { if (confirm(tx("Withdraw this transcript? The text, edits and coaching notes quoted from it are deleted."))) act(() => apiClient.post(`${BASE}/${job.id}/withdraw`), tx("Transcript withdrawn.")); }}>{tx("Withdraw")}</button>
          </div>
          {job.status === "FAILED" && (
            <div className="space-y-1">
              <p className="text-gray-600">{tx("Fallback: type or paste the transcript yourself (one line per segment).")}</p>
              <textarea className="border rounded w-full px-1" rows={3} aria-label={tx("Manual transcript")} value={manual} onChange={(e) => setManual(e.target.value)} />
              <button className={btn} disabled={busy || manual.trim().length < 3} onClick={() => act(() => apiClient.put(`${BASE}/${job.id}/manual`, { text: manual }), tx("Manual transcript saved."))}>{tx("Use typed transcript")}</button>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
