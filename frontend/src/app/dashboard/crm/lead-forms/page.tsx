"use client";
import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { crmApi, type LeadForm, type LeadSubmissionRow } from "@/lib/crm_pipeline";

function errorText(e: unknown) {
  const detail = (e as { response?: { data?: { detail?: unknown } } }).response?.data?.detail;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) return detail.map((d) => (d as { msg?: string }).msg).join("; ");
  if (detail && typeof detail === "object" && "detail" in detail) return String((detail as { detail: unknown }).detail);
  return "Request failed.";
}

const EMPTY = { slug: "", name: "", title: "", intro: "", consent_text: "I agree to be contacted about products and offers.", require_consent: true, assigned_rep_id: "" };

export default function LeadFormsPage() {
  const [forms, setForms] = useState<LeadForm[]>([]);
  const [selected, setSelected] = useState<LeadForm | null>(null);
  const [subs, setSubs] = useState<LeadSubmissionRow[]>([]);
  const [draft, setDraft] = useState(EMPTY);
  const [error, setError] = useState<string | null>(null);
  const origin = typeof window !== "undefined" ? window.location.origin : "";

  const load = useCallback(async () => {
    try { setForms(await crmApi.listLeadForms()); } catch (e) { setError(errorText(e)); }
  }, []);
  useEffect(() => { load(); }, [load]);
  useEffect(() => {
    if (selected) crmApi.listLeadSubmissions(selected.id).then(setSubs).catch((e) => setError(errorText(e)));
  }, [selected]);

  async function create(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    try {
      await crmApi.createLeadForm({ ...draft, assigned_rep_id: draft.assigned_rep_id || null, intro: draft.intro || null });
      setDraft(EMPTY);
      await load();
    } catch (err) { setError(errorText(err)); }
  }

  return (
    <div className="p-6 space-y-6">
      <div>
        <h1 className="text-xl font-bold text-gray-900">Website Lead Forms</h1>
        <p className="text-sm text-gray-500">Public forms create leads in the CRM with source and campaign attribution. Spam-trapped, rate-limited, consent recorded.</p>
      </div>
      {error && <p role="alert" className="rounded-lg p-3 text-sm bg-red-50 border border-red-200 text-red-700">{error}</p>}
      <div className="bg-white rounded-xl border shadow-sm p-4 overflow-x-auto">
        {forms.length === 0 ? <p className="text-sm text-gray-400">No forms yet.</p> : (
          <table className="w-full text-sm">
            <thead><tr className="text-left text-xs text-gray-500"><th className="py-1">Form</th><th>Public link</th><th>Owner</th><th>Status</th><th /></tr></thead>
            <tbody>
              {forms.map((f) => (
                <tr key={f.id} className="border-t">
                  <td className="py-1.5"><button className="text-indigo-700 underline" onClick={() => setSelected(f)}>{f.name}</button></td>
                  <td className="font-mono text-xs"><a href={`/forms/${f.slug}`} target="_blank" rel="noreferrer" className="underline">/forms/{f.slug}</a></td>
                  <td>{f.assigned_rep_id ?? "—"}</td>
                  <td>{f.active_flag ? "Active" : "Inactive"}</td>
                  <td className="text-right">
                    <button className="text-xs underline" onClick={async () => { try { await crmApi.updateLeadForm(f.id, { active_flag: !f.active_flag }); await load(); } catch (e) { setError(errorText(e)); } }}>
                      {f.active_flag ? "Deactivate" : "Activate"}
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
        <form aria-label="New lead form" onSubmit={create} className="grid md:grid-cols-3 gap-2 mt-4">
          <input aria-label="Slug" required placeholder="slug (e.g. contact-sales)" value={draft.slug} onChange={(e) => setDraft({ ...draft, slug: e.target.value })} className="text-sm border rounded-lg px-2 py-1.5" />
          <input aria-label="Name" required placeholder="Internal name" value={draft.name} onChange={(e) => setDraft({ ...draft, name: e.target.value })} className="text-sm border rounded-lg px-2 py-1.5" />
          <input aria-label="Title" required placeholder="Title shown to visitors" value={draft.title} onChange={(e) => setDraft({ ...draft, title: e.target.value })} className="text-sm border rounded-lg px-2 py-1.5" />
          <input aria-label="Intro" placeholder="Intro text" value={draft.intro} onChange={(e) => setDraft({ ...draft, intro: e.target.value })} className="text-sm border rounded-lg px-2 py-1.5 md:col-span-2" />
          <input aria-label="Owner" placeholder="Owner rep id" value={draft.assigned_rep_id} onChange={(e) => setDraft({ ...draft, assigned_rep_id: e.target.value })} className="text-sm border rounded-lg px-2 py-1.5" />
          <input aria-label="Consent text" placeholder="Consent statement" value={draft.consent_text} onChange={(e) => setDraft({ ...draft, consent_text: e.target.value })} className="text-sm border rounded-lg px-2 py-1.5 md:col-span-2" />
          <button type="submit" className="px-3 py-1.5 text-sm bg-blue-600 text-white rounded-lg">Create form</button>
        </form>
      </div>
      {selected && (
        <div className="bg-white rounded-xl border shadow-sm p-4 space-y-3 overflow-x-auto">
          <h2 className="font-semibold text-gray-800">{selected.name}: embed and submissions</h2>
          <pre className="text-xs bg-gray-50 border rounded p-2 whitespace-pre-wrap">{`<iframe src="${origin}/forms/${selected.slug}?page=YOUR_PAGE_URL" width="100%" height="640" style="border:0"></iframe>`}</pre>
          {subs.length === 0 ? <p className="text-sm text-gray-400">No submissions yet.</p> : (
            <table className="w-full text-sm">
              <thead><tr className="text-left text-xs text-gray-500"><th className="py-1">Received</th><th>Status</th><th>E-mail</th><th>Consent</th><th>Campaign</th><th>Lead</th></tr></thead>
              <tbody>
                {subs.map((s) => (
                  <tr key={s.id} className="border-t">
                    <td className="py-1.5">{new Date(s.received_at).toLocaleString()}</td><td>{s.status}</td><td>{s.contact_email ?? "—"}</td>
                    <td>{s.consent_given ? "Yes" : "No"}</td>
                    <td className="text-xs">{[s.utm_source, s.utm_medium, s.utm_campaign].filter(Boolean).join(" / ") || "—"}</td>
                    <td>{s.crm_record_id ? <Link className="underline" href={`/dashboard/crm/records/${s.crm_record_id}`}>Open</Link> : "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      )}
    </div>
  );
}
