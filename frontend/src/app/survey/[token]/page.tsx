"use client";
// Public CSAT / CES / post-chat survey (M45.S01.T019): one answer per link, no login.
import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { API_ORIGIN } from "@/lib/api";
import { useI18n } from "@/lib/i18n";
import LanguageSwitcher from "@/components/LanguageSwitcher";

type S = { kind: string; question: string; min: number; max: number; answered: boolean };

export default function SurveyPage() {
  const { t } = useI18n();
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
        <div className="flex flex-wrap items-center justify-between gap-2"><h1 className="text-lg font-semibold break-words min-w-0">{t("public.survey.title")}</h1><LanguageSwitcher /></div>
        {state === "invalid" ? <p className="text-red-600">{t("public.survey.invalid")}</p> : state === "done" ? <p className="text-green-700">{t("public.survey.thanks")}</p> : !s ? <p className="text-gray-500">{t("common.loading")}</p> : <>
          <p className="break-words">{s.question}</p>
          <div className="flex flex-wrap gap-2">{Array.from({ length: s.max - s.min + 1 }, (_, i) => s.min + i).map((n) =>
            <button key={n} aria-label={t("public.survey.score", { n })} className={`w-10 h-10 rounded border ${score === n ? "bg-indigo-600 text-white" : ""}`} onClick={() => setScore(n)}>{n}</button>)}</div>
          <p className="text-xs text-gray-500">{s.min} = {s.kind === "CES" ? t("public.survey.veryHard") : t("public.survey.veryUnhappy")}, {s.max} = {s.kind === "CES" ? t("public.survey.veryEasy") : t("public.survey.veryHappy")}</p>
          <textarea aria-label={t("public.survey.comment")} className="border rounded w-full px-2 py-1" rows={3} placeholder={t("public.survey.commentPlaceholder")} value={comment} onChange={(e) => setComment(e.target.value)} />
          <button className="w-full bg-indigo-600 text-white rounded py-2 disabled:opacity-50" disabled={score === null} onClick={send}>{t("common.send")}</button>
        </>}
      </div>
    </main>
  );
}
