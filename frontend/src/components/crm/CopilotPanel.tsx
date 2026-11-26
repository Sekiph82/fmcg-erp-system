"use client";
// M36.S04.T001 AI sales copilot: summary, follow-ups and a draft built only from evidence the user can see.
// Nothing is sent: the draft is copied for the representative to edit and send from their own mailbox.
import { useState } from "react";
import Link from "next/link";
import { crmApi, type CopilotBrief } from "@/lib/crm_pipeline";
import { tx } from "@/lib/i18n/core";

export function CopilotPanel({ customerId }: { customerId: string }) {
  const [note, setNote] = useState("");
  const [brief, setBrief] = useState<CopilotBrief | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);
  const ev = (id: string) => brief?.evidence.find((e) => e.id === id);
  const Cite = ({ ids }: { ids: string[] }) => (
    <span className="text-xs text-gray-500">
      {ids.map((id) => {
        const e = ev(id);
        return <span key={id} title={e ? `${e.date} · ${e.title}` : id} className="ml-1 px-1 rounded bg-gray-100">{e?.link ? <Link href={e.link}>{id}</Link> : id}</span>;
      })}
    </span>
  );

  async function run() {
    setBusy(true); setError(null); setCopied(false);
    try { setBrief(await crmApi.customerCopilot(customerId, note || undefined)); }
    catch { setError(tx("The brief could not be prepared. Please try again.")); }
    finally { setBusy(false); }
  }

  return (
    <section aria-label={tx("AI brief")} className="bg-white rounded-xl border p-4 space-y-3">
      <div className="flex flex-wrap gap-2 items-center">
        <h2 className="font-semibold text-gray-900 mr-auto">{tx("AI brief")}</h2>
        <input aria-label={tx("What do you need help with")} placeholder={tx("Optional: what do you need help with?")} maxLength={500} value={note}
          onChange={(e) => setNote(e.target.value)} className="text-sm border rounded-lg px-2 py-1.5 flex-1 min-w-[12rem]" />
        <button onClick={run} disabled={busy} className="px-3 py-1.5 text-sm rounded-lg bg-indigo-600 text-white disabled:opacity-50">
          {busy ? tx("Preparing…") : brief ? tx("Refresh") : tx("Prepare brief")}
        </button>
      </div>
      {error && <p role="alert" className="text-sm text-red-700">{error}</p>}
      {brief && (
        <>
          <p className="text-xs text-gray-500">
            {brief.mode === "ai" ? tx("Written by AI from the records below; check before you act.") : tx("Rule-based brief (AI not used).")}
            {brief.note ? ` ${brief.note}` : ""}
            {brief.dropped_unsupported ? tx(" {dropped_unsupported} suggestion(s) without evidence were removed.", { dropped_unsupported: brief.dropped_unsupported }) : ""}
          </p>
          <p className="text-sm text-gray-800">{brief.summary}<Cite ids={brief.summary_evidence} /></p>
          {brief.follow_ups.length > 0 && (
            <ul className="text-sm space-y-1 list-disc ml-5">
              {brief.follow_ups.map((f, i) => (
                <li key={i}>{f.due_in_days === 0 ? tx("Today") : ((f.due_in_days > 1) ? tx("In {due_in_days} days", { due_in_days: f.due_in_days }) : tx("In {due_in_days} day", { due_in_days: f.due_in_days }))}: {f.action}<Cite ids={f.evidence} /></li>
              ))}
            </ul>
          )}
          {brief.draft && (
            <div className="border rounded-lg p-3 space-y-1">
              <p className="text-xs font-semibold text-gray-500">{tx("DRAFT E-MAIL (not sent)")}</p>
              <p className="text-sm font-medium">{brief.draft.subject}</p>
              <p className="text-sm whitespace-pre-wrap text-gray-700">{brief.draft.body}</p>
              <button className="text-xs underline text-indigo-700" onClick={async () => {
                try { await navigator.clipboard.writeText(`${brief.draft!.subject}\n\n${brief.draft!.body}`); setCopied(true); } catch { setCopied(false); }
              }}>{copied ? tx("Copied") : tx("Copy to send from Communication → Email")}</button>
            </div>
          )}
          {brief.hidden_sources.length > 0 && <p className="text-xs text-gray-400">{tx("Not used (not visible to your role):")} {brief.hidden_sources.join(", ")}.</p>}
        </>
      )}
    </section>
  );
}
