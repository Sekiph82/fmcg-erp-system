"use client";
import { useCallback, useEffect, useState } from "react";
import { crmApi, type EmailCampaign } from "@/lib/crm_pipeline";
import { companyApi, getActiveCompanyId, type Company } from "@/lib/company";

function errorText(e: unknown) {
  const detail = (e as { response?: { data?: { detail?: unknown } } }).response?.data?.detail;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) return detail.map((d) => (d as { msg?: string }).msg).join("; ");
  if (detail && typeof detail === "object" && "detail" in detail) return String((detail as { detail: unknown }).detail);
  return "Request failed.";
}

const EMPTY = { name: "", subject: "", body: "", segment_id: "", company_id: "" };

export default function CRMEmailCampaignsPage() {
  const [items, setItems] = useState<EmailCampaign[]>([]);
  const [segments, setSegments] = useState<{ id: string; name: string; members: number }[]>([]);
  const [companies, setCompanies] = useState<Company[]>([]);
  const [draft, setDraft] = useState({ ...EMPTY, company_id: getActiveCompanyId() ?? "" });
  const [preview, setPreview] = useState<Record<string, { customers: number; addresses: number; with_consent: number }>>({});
  const [error, setError] = useState<string | null>(null);
  const [info, setInfo] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      const [c, s] = await Promise.all([crmApi.getEmailCampaigns(), crmApi.getCampaignSegments()]);
      setItems(c);
      setSegments(s);
    } catch (e) { setError(errorText(e)); }
  }, []);
  useEffect(() => { load(); companyApi.list().then(setCompanies).catch(() => setCompanies([])); }, [load]);

  async function act(fn: () => Promise<unknown>, msg: string) {
    setError(null);
    try { await fn(); setInfo(msg); await load(); } catch (e) { setError(errorText(e)); }
  }

  const input = "text-sm border rounded-lg px-2 py-1.5";
  const segName = (id: string) => segments.find((s) => s.id === id)?.name ?? "—";
  return (
    <div className="p-6 space-y-6">
      <div>
        <h1 className="text-xl font-bold text-gray-900">E-mail Campaigns</h1>
        <p className="text-sm text-gray-500">Segment campaigns go through the outbox: only addresses with recorded consent receive them, one e-mail per address. Conversions = recipients who ordered within 30 days.</p>
      </div>
      {error && <p role="alert" className="rounded-lg p-3 text-sm bg-red-50 border border-red-200 text-red-700">{error}</p>}
      {info && !error && <p role="status" className="rounded-lg p-3 text-sm bg-emerald-50 border border-emerald-200 text-emerald-800">{info}</p>}

      <form aria-label="New campaign" className="bg-white rounded-xl border shadow-sm p-4 grid md:grid-cols-2 gap-2"
        onSubmit={(e) => { e.preventDefault(); act(() => crmApi.createEmailCampaign(draft), "Draft campaign created."); setDraft({ ...EMPTY, company_id: draft.company_id }); }}>
        <h2 className="font-semibold text-gray-800 md:col-span-2">New campaign</h2>
        <input aria-label="Campaign name" required placeholder="Name" value={draft.name} onChange={(e) => setDraft({ ...draft, name: e.target.value })} className={input} />
        <select aria-label="Segment" required value={draft.segment_id} onChange={(e) => setDraft({ ...draft, segment_id: e.target.value })} className={input}>
          <option value="">Choose a segment…</option>
          {segments.map((s) => <option key={s.id} value={s.id}>{s.name} ({s.members})</option>)}
        </select>
        <select aria-label="Company" required value={draft.company_id} onChange={(e) => setDraft({ ...draft, company_id: e.target.value })} className={input}>
          <option value="">Choose the sending company…</option>
          {companies.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
        </select>
        <input aria-label="Campaign subject" required placeholder="Subject — {company_name} allowed" value={draft.subject} onChange={(e) => setDraft({ ...draft, subject: e.target.value })} className={`${input} md:col-span-2`} />
        <textarea aria-label="Campaign body" required rows={4} placeholder="Message — {contact_name} {company_name}" value={draft.body} onChange={(e) => setDraft({ ...draft, body: e.target.value })} className={`${input} md:col-span-2`} />
        <button type="submit" className="px-3 py-1.5 text-sm bg-blue-600 text-white rounded-lg md:col-start-2">Save draft</button>
      </form>

      <div className="bg-white rounded-xl border shadow-sm p-4 overflow-x-auto">
        <h2 className="font-semibold text-gray-800 mb-2">Campaigns</h2>
        {items.length === 0 ? <p className="text-sm text-gray-400">No campaigns yet.</p> : (
          <table className="w-full text-sm">
            <thead><tr className="text-left text-xs text-gray-500"><th className="py-1">Name</th><th>Segment</th><th>Status</th><th>Audience</th><th>Results</th><th /></tr></thead>
            <tbody>{items.map((c) => {
              const p = preview[c.id];
              const st = c.stats.by_status;
              return (
                <tr key={c.id} className="border-t align-top">
                  <td className="py-1.5">{c.name}<div className="text-xs text-gray-500">{c.subject}</div></td>
                  <td>{segName(c.segment_id)}</td>
                  <td>{c.status}{c.scheduled_at && c.status === "SCHEDULED" ? ` · ${new Date(c.scheduled_at).toLocaleString()}` : ""}</td>
                  <td className="text-xs">{c.audience_size != null ? `${c.audience_size} addresses` : p ? `${p.addresses} addresses, ${p.with_consent} with consent` :
                    <button className="underline" onClick={async () => setPreview({ ...preview, [c.id]: await crmApi.previewEmailCampaign(c.id) })}>Preview audience</button>}</td>
                  <td className="text-xs">{Object.keys(st).length ? Object.entries(st).map(([k, v]) => `${k} ${v}`).join(" · ") : "—"}
                    {c.queued_at && <div>Converted: {c.stats.converted_customers}</div>}</td>
                  <td className="text-right space-x-2 whitespace-nowrap">
                    {(c.status === "DRAFT" || c.status === "FAILED") && <button className="text-xs underline" onClick={() => act(() => crmApi.scheduleEmailCampaign(c.id), "Campaign scheduled; the worker queues it within a minute.")}>Send now</button>}
                    {c.status !== "CANCELLED" && <button className="text-xs underline" onClick={() => act(() => crmApi.cancelEmailCampaign(c.id), "Campaign cancelled.")}>Cancel</button>}
                  </td>
                </tr>
              );
            })}</tbody>
          </table>
        )}
      </div>
    </div>
  );
}
