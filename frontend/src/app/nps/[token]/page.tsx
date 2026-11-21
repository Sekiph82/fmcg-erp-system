"use client";
// Public one-time survey link (M40.S01.T001): no login; the token in the link is the only credential.
import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { API_ORIGIN } from "@/lib/api";

interface Survey { question: string; follow_up: string | null; order_no: string | null; answered: boolean }

export default function PublicSurvey() {
  const { token } = useParams<{ token: string }>();
  const url = `${API_ORIGIN}/api/v1/public/nps/${encodeURIComponent(token)}`;
  const [s, setS] = useState<Survey | null>(null);
  const [state, setState] = useState<"loading" | "open" | "done" | "invalid">("loading");
  const [score, setScore] = useState<number | null>(null);
  const [comment, setComment] = useState("");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetch(url).then(async (r) => {
      if (!r.ok) { setState("invalid"); return; }
      const j: Survey = await r.json(); setS(j); setState(j.answered ? "done" : "open");
    }).catch(() => setState("invalid"));
  }, [url]);

  async function send() {
    if (score === null) return;
    setError(null);
    const r = await fetch(url, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ score, comment: comment || null }) }).catch(() => null);
    if (r?.ok || r?.status === 409) setState("done"); else setError("Could not send; please try again.");
  }

  return (
    <main className="min-h-screen bg-gray-50 text-gray-900 flex items-start justify-center p-4">
      <div className="w-full max-w-md bg-white rounded-xl border p-5 space-y-3 mt-8">
        <p className="font-semibold text-indigo-700">POVU</p>
        {state === "loading" && <p className="text-sm text-gray-500">Loading…</p>}
        {state === "invalid" && <p className="text-sm text-gray-600">This survey link is not valid or has expired.</p>}
        {state === "done" && <p className="text-sm text-emerald-700">Thank you — your answer has been received.</p>}
        {state === "open" && s && (<>
          <p className="font-medium">{s.question}</p>
          {s.order_no && <p className="text-xs text-gray-500">Order {s.order_no}</p>}
          <div role="radiogroup" aria-label="Score from 0 to 10" className="grid grid-cols-11 gap-1">
            {Array.from({ length: 11 }, (_, n) => (
              <button key={n} type="button" role="radio" aria-checked={score === n} onClick={() => setScore(n)}
                className={`py-2 rounded text-sm border ${score === n ? "bg-indigo-600 text-white border-indigo-600" : "bg-white"}`}>{n}</button>
            ))}
          </div>
          <textarea aria-label="Comment (optional)" maxLength={2000} rows={3} placeholder={s.follow_up ?? "Anything we should know? (optional)"}
            value={comment} onChange={(e) => setComment(e.target.value)} className="w-full border rounded-lg px-3 py-2 text-sm" />
          {error && <p role="alert" className="text-xs text-red-700">{error}</p>}
          <button onClick={send} disabled={score === null} className="w-full py-2.5 rounded-lg bg-indigo-600 text-white text-sm disabled:opacity-50">Send</button>
        </>)}
      </div>
    </main>
  );
}
