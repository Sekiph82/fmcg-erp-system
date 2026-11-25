"use client";
// Public CSAT / CES / post-chat survey (M45.S01.T019): one answer per link, no login.
import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { API_ORIGIN } from "@/lib/api";

type S = { kind: string; question: string; min: number; max: number; answered: boolean };

export default function SurveyPage() {
  const { token } = useParams<{ token: string }>();
  const url = `${API_ORIGIN}/api/v1/public/survey/${encodeURIComponent(token)}`;
  const [s, setS] = useState<S | null>(null);
  const [state, setState] = useState<"loading" | "open" | "done" | "invalid">("loading");
  const [score, setScore] = useState<number | null>(null);
  const [comment, setComment] = useState("");
  useEffect(() => {
    fetch(url).then(async (r) => { if (!r.ok) return setState("invalid"); const j: S = await r.json(); setS(j); setState(j.answered ? "done" : "open"); })
      .catch(() => setState("invalid"));
  }, [url]);
  const send = async () => {
    if (score === null) return;
    const r = await fetch(url, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ score, comment: comment || null }) }).catch(() => null);
    if (r?.ok || r?.status === 409) setState("done");
  };
  return (
    <main className="min-h-screen bg-gray-50 flex items-start justify-center p-4">
      <div className="w-full max-w-md bg-white rounded-xl border shadow-sm p-5 space-y-3 text-sm">
        <h1 className="text-lg font-semibold">POVU feedback</h1>
        {state === "invalid" ? <p className="text-red-600">This link is not valid.</p> : state === "done" ? <p className="text-green-700">Thank you for your answer.</p> : !s ? <p className="text-gray-500">Loading…</p> : <>
          <p>{s.question}</p>
          <div className="flex flex-wrap gap-2">{Array.from({ length: s.max - s.min + 1 }, (_, i) => s.min + i).map((n) =>
            <button key={n} aria-label={`Score ${n}`} className={`w-10 h-10 rounded border ${score === n ? "bg-indigo-600 text-white" : ""}`} onClick={() => setScore(n)}>{n}</button>)}</div>
          <p className="text-xs text-gray-500">{s.min} = {s.kind === "CES" ? "very hard" : "very unhappy"}, {s.max} = {s.kind === "CES" ? "very easy" : "very happy"}</p>
          <textarea aria-label="Comment" className="border rounded w-full px-2 py-1" rows={3} placeholder="Anything to add? (optional)" value={comment} onChange={(e) => setComment(e.target.value)} />
          <button className="w-full bg-indigo-600 text-white rounded py-2 disabled:opacity-50" disabled={score === null} onClick={send}>Send</button>
        </>}
      </div>
    </main>
  );
}
