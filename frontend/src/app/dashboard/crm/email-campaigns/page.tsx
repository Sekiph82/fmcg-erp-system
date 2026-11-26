"use client";
import { useCallback, useEffect, useState } from "react";
import { apiClient } from "@/lib/api";
import { crmApi, type EmailCampaign } from "@/lib/crm_pipeline";
import { getActiveCompanyId } from "@/lib/company";
import { emailApi, type EmailTemplate } from "@/lib/email";
import { useAuth } from "@/context/AuthContext";
import { tx } from "@/lib/i18n/core";

function errorText(e: unknown) {
  const detail = (e as { response?: { data?: { detail?: unknown } } }).response?.data?.detail;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) return detail.map((d) => (d as { msg?: string }).msg).join("; ");
  if (detail && typeof detail === "object" && "detail" in detail) return String((detail as { detail: unknown }).detail);
  return "Request failed.";
}

const EMPTY = { name: "", subject: "", body: "", segment_id: "", company_id: "", track_engagement: false, design_id: "", ab_split_pct: 0, variant_b_subject: "", send_time_optimize: false };

export default function CRMEmailCampaignsPage() {
  const [items, setItems] = useState<EmailCampaign[]>([]);
  const [segments, setSegments] = useState<{ id: string; name: string; members: number }[]>([]);
  const { hasPermission } = useAuth();
  const canAuthor = hasPermission("crm.edit_all");  // creating a campaign is company-wide CRM configuration
  const [companies, setCompanies] = useState<{ id: string; name: string }[]>([]);
  const [draft, setDraft] = useState({ ...EMPTY, company_id: getActiveCompanyId() ?? "" });
  const [preview, setPreview] = useState<Record<string, { customers: number; addresses: number; with_consent: number }>>({});
  const [error, setError] = useState<string | null>(null);
  const [info, setInfo] = useState<string | null>(null);
  const [templates, setTemplates] = useState<EmailTemplate[]>([]);
  const [designs, setDesigns] = useState<{ id: string; name: string; version: number; status: string }[]>([]);
  useEffect(() => { apiClient.get("/api/v1/email-designs").then((r) => setDesigns(r.data.filter((d: { status: string }) => d.status === "PUBLISHED"))).catch(() => setDesigns([])); }, []);
  const loadTemplates = useCallback(() => emailApi.listTemplates("crm_campaign").then(setTemplates).catch(() => setTemplates([])), []);

  const load = useCallback(async () => {
    try {
      const [c, s] = await Promise.all([crmApi.getEmailCampaigns(), crmApi.getCampaignSegments()]);
      setItems(c);
      setSegments(s);
    } catch (e) { setError(errorText(e)); }
  }, []);
  useEffect(() => {
    load();
    if (canAuthor) {
      crmApi.getCampaignCompanies().then(setCompanies).catch(() => setCompanies([]));
      loadTemplates();
    }
  }, [load, canAuthor, loadTemplates]);

  async function act(fn: () => Promise<unknown>, msg: string) {
    setError(null);
    try { await fn(); setInfo(msg); await load(); } catch (e) { setError(errorText(e)); }
  }

  const input = "text-sm border rounded-lg px-2 py-1.5";
  const segName = (id: string) => segments.find((s) => s.id === id)?.name ?? "—";
  return (
    <div className="p-6 space-y-6">
      <div>
        <h1 className="text-xl font-bold text-gray-900">{tx("E-mail Campaigns")}</h1>
        <p className="text-sm text-gray-500">{tx("Segment campaigns go through the outbox: only addresses with recorded consent receive them, one e-mail per address. Conversions = recipients who ordered within 30 days.")}</p>
      </div>
      {error && <p role="alert" className="rounded-lg p-3 text-sm bg-red-50 border border-red-200 text-red-700">{error}</p>}
      {info && !error && <p role="status" className="rounded-lg p-3 text-sm bg-emerald-50 border border-emerald-200 text-emerald-800">{info}</p>}

      {canAuthor && <form aria-label={tx("New campaign")} className="bg-white rounded-xl border shadow-sm p-4 grid md:grid-cols-2 gap-2"
        onSubmit={(e) => { e.preventDefault(); act(() => crmApi.createEmailCampaign({ ...draft, design_id: draft.design_id || undefined, variant_b_subject: draft.variant_b_subject || undefined }), "Draft campaign created."); setDraft({ ...EMPTY, company_id: draft.company_id }); }}>
        <h2 className="font-semibold text-gray-800 md:col-span-2">{tx("New campaign")}</h2>
        <div className="md:col-span-2 flex flex-wrap gap-2 items-center">
          <select aria-label={tx("Start from template")} value="" className={input}
            onChange={(e) => {
              const t = templates.find((x) => x.id === e.target.value);
              if (t) setDraft({ ...draft, subject: t.subject_template, body: t.body_template, name: draft.name || t.name });
            }}>
            <option value="">{templates.length ? tx("Start from a saved template…") : tx("No saved templates yet")}</option>
            {templates.map((t) => <option key={t.id} value={t.id}>{t.name}</option>)}
          </select>
          <button type="button" className="px-3 py-1.5 text-sm border rounded-lg" disabled={!draft.subject || !draft.body}
            onClick={() => {
              const name = prompt(tx("Template name"), draft.name || draft.subject);
              if (name) act(() => emailApi.createTemplate({ name, module: "crm_campaign", subject_template: draft.subject, body_template: draft.body }).then(loadTemplates), "Template saved.");
            }}>{tx("Save as template")}</button>
        </div>
        <input aria-label={tx("Campaign name")} required placeholder={tx("Name")} value={draft.name} onChange={(e) => setDraft({ ...draft, name: e.target.value })} className={input} />
        <select aria-label={tx("Segment")} required value={draft.segment_id} onChange={(e) => setDraft({ ...draft, segment_id: e.target.value })} className={input}>
          <option value="">{tx("Choose a segment…")}</option>
          {segments.map((s) => <option key={s.id} value={s.id}>{s.name} ({s.members})</option>)}
        </select>
        <select aria-label={tx("Company")} required value={draft.company_id} onChange={(e) => setDraft({ ...draft, company_id: e.target.value })} className={input}>
          <option value="">{tx("Choose the sending company…")}</option>
          {companies.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
        </select>
        <input aria-label={tx("Campaign subject")} required placeholder={tx("Subject — {company_name} allowed")} value={draft.subject} onChange={(e) => setDraft({ ...draft, subject: e.target.value })} className={`${input} md:col-span-2`} />
        <textarea aria-label={tx("Campaign body")} required rows={4} placeholder={tx("Message — {contact_name} {company_name}")} value={draft.body} onChange={(e) => setDraft({ ...draft, body: e.target.value })} className={`${input} md:col-span-2`} />
        <select aria-label={tx("E-mail design")} className={`${input} md:col-span-2`} value={draft.design_id} onChange={(e) => setDraft({ ...draft, design_id: e.target.value })}>
          <option value="">{tx("Plain text e-mail (no design)")}</option>{designs.map((d) => <option key={d.id} value={d.id}>{d.name} {tx("v")}{d.version}</option>)}</select>
        <div className="md:col-span-2"><label className="flex items-center gap-2 text-xs text-gray-600"><input type="checkbox" checked={draft.track_engagement} onChange={(e) => setDraft({ ...draft, track_engagement: e.target.checked })} /> {tx("Track opens and clicks (only if tracking is switched on for the company; recipients can opt out; opens are an indicator, not proof of reading)")}</label></div>
        <fieldset className="md:col-span-2 border rounded-lg p-2 grid md:grid-cols-3 gap-2 items-center">
          <legend className="text-xs text-gray-600 px-1">{tx("A/B test (optional)")}</legend>
          <label className="text-xs text-gray-600">{tx("Share getting variant B (0–50%)")}
            <input aria-label={tx("Variant B share")} type="number" min={0} max={50} value={draft.ab_split_pct} onChange={(e) => setDraft({ ...draft, ab_split_pct: Math.max(0, Math.min(50, +e.target.value || 0)) })} className={`${input} w-20 ml-2`} /></label>
          <input aria-label={tx("Variant B subject")} placeholder={tx("Variant B subject")} disabled={!draft.ab_split_pct} value={draft.variant_b_subject} onChange={(e) => setDraft({ ...draft, variant_b_subject: e.target.value })} className={`${input} md:col-span-2`} />
          <p className="text-xs text-gray-500 md:col-span-3">{tx("A winner is shown only with at least 100 sent per variant and a significant click difference (p<0.05); otherwise “no winner”.")}</p>
        </fieldset>
        <div className="md:col-span-2"><label className="flex items-center gap-2 text-xs text-gray-600"><input type="checkbox" checked={draft.send_time_optimize} onChange={(e) => setDraft({ ...draft, send_time_optimize: e.target.checked })} /> {tx("Send at each person's usual opening hour (only where we have at least 3 recorded opens; others get it at the scheduled time)")}</label></div>
        <button type="submit" className="px-3 py-1.5 text-sm bg-blue-600 text-white rounded-lg md:col-start-2">{tx("Save draft")}</button>
      </form>}

      <div className="bg-white rounded-xl border shadow-sm p-4 overflow-x-auto">
        <h2 className="font-semibold text-gray-800 mb-2">{tx("Campaigns")}</h2>
        {items.length === 0 ? <p className="text-sm text-gray-400">{tx("No campaigns yet.")}</p> : (
          <table className="w-full text-sm">
            <thead><tr className="text-left text-xs text-gray-500"><th className="py-1">{tx("Name")}</th><th>{tx("Segment")}</th><th>{tx("Status")}</th><th>{tx("Audience")}</th><th>{tx("Results")}</th><th /></tr></thead>
            <tbody>{items.map((c) => {
              const p = preview[c.id];
              const st = c.stats.by_status;
              return (
                <tr key={c.id} className="border-t align-top">
                  <td className="py-1.5">{c.name}<div className="text-xs text-gray-500">{c.subject}</div></td>
                  <td>{segName(c.segment_id)}</td>
                  <td>{c.status}{c.approval_status !== "NONE" && <div className="text-xs text-gray-500">{tx("Approval:")} {c.approval_status.toLowerCase()}</div>}{c.scheduled_at && c.status === "SCHEDULED" ? ` · ${new Date(c.scheduled_at).toLocaleString()}` : ""}</td>
                  <td className="text-xs">{c.audience_size != null ? tx("{audience_size} addresses", { audience_size: c.audience_size }) : p ? tx("{addresses} addresses, {with_consent} with consent", { addresses: p.addresses, with_consent: p.with_consent }) :
                    <button className="underline" onClick={async () => setPreview({ ...preview, [c.id]: await crmApi.previewEmailCampaign(c.id) })}>{tx("Preview audience")}</button>}</td>
                  <td className="text-xs">{Object.keys(st).length ? Object.entries(st).map(([k, v]) => `${k} ${v}`).join(" · ") : "—"}
                    {c.queued_at && <div>{tx("Converted:")} {c.stats.converted_customers}</div>}</td>
                  <td className="text-right space-x-2 whitespace-nowrap">
                    {(c.status === "DRAFT" || c.status === "FAILED") && <button className="text-xs underline" onClick={() => act(() => crmApi.scheduleEmailCampaign(c.id), "Campaign scheduled; the worker queues it within a minute.")}>{tx("Send now")}</button>}
                    {canAuthor && c.status === "DRAFT" && c.approval_status !== "PENDING" && c.approval_status !== "APPROVED" && <button className="text-xs underline" onClick={() => act(() => crmApi.campaignApproval(c.id, "request"), "Sent for approval; another editor must approve it.")}>{tx("Request approval")}</button>}
                    {canAuthor && c.approval_status === "PENDING" && <><button className="text-xs underline" onClick={() => act(() => crmApi.campaignApproval(c.id, "approve"), "Campaign approved.")}>{tx("Approve")}</button>
                      <button className="text-xs underline" onClick={() => act(() => crmApi.campaignApproval(c.id, "reject"), "Campaign rejected.")}>{tx("Reject")}</button></>}
                    {c.ab_split_pct > 0 && c.queued_at && <button className="text-xs underline" onClick={async () => { setError(null); try { const r = await crmApi.campaignAbResult(c.id); setInfo(`A/B: ${r.verdict}. A ${r.arms.A.clicked}/${r.arms.A.sent}, B ${r.arms.B.clicked}/${r.arms.B.sent}${r.p_value != null ? `, p=${r.p_value}` : ""}.`); } catch (e) { setError(errorText(e)); } }}>{tx("A/B result")}</button>}
                    {c.status !== "CANCELLED" && <button className="text-xs underline" onClick={() => act(() => crmApi.cancelEmailCampaign(c.id), "Campaign cancelled.")}>{tx("Cancel")}</button>}
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
