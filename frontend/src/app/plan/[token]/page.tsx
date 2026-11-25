"use client";
// Customer's view of a shared deal plan (M43.S01.T010): steps only; the customer ticks their own steps.
import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { API_ORIGIN } from "@/lib/api";

interface Step { id: string; title: string; owner: "us" | "customer"; due_date: string | null; done: boolean }

export default function SharedPlan() {
  const { token } = useParams<{ token: string }>();
  const base = `${API_ORIGIN}/api/v1/public/deal-plans/${encodeURIComponent(token)}`;
  const [plan, setPlan] = useState<{ title: string; steps: Step[] } | null | "missing">(null);
  useEffect(() => { fetch(base).then(async (r) => setPlan(r.ok ? await r.json() : "missing")).catch(() => setPlan("missing")); }, [base]);
  async function tick(s: Step) {
    const r = await fetch(`${base}/steps`, { method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ step_id: s.id, done: !s.done }) }).catch(() => null);
    if (r?.ok) setPlan(await r.json());
  }
  if (plan === null) return <main className="p-6 text-sm text-gray-500">Loading…</main>;
  if (plan === "missing") return <main className="p-6 text-sm text-gray-600">This plan link is not valid.</main>;
  return (
    <main className="p-4 md:p-6 max-w-xl mx-auto space-y-3">
      <h1 className="text-xl font-semibold">{plan.title}</h1>
      <ul className="space-y-2">
        {plan.steps.map((s) => (
          <li key={s.id} className="border rounded-lg p-3 flex items-start gap-2 bg-white">
            <input type="checkbox" aria-label={s.title} checked={s.done} disabled={s.owner !== "customer"} onChange={() => tick(s)} className="mt-1" />
            <div className="text-sm">
              <div className={s.done ? "line-through text-gray-500" : ""}>{s.title}</div>
              <div className="text-xs text-gray-500">{s.owner === "customer" ? "Your step" : "POVU"}{s.due_date && ` · by ${new Date(`${s.due_date}T12:00:00`).toLocaleDateString()}`}</div>
            </div>
          </li>
        ))}
      </ul>
    </main>
  );
}
