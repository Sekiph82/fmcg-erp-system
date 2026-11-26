"use client";
// M47.S01.T010 CRM platform settings: lead-form shortening ("skip if known"), smart contact properties, Slack routing
// per event type and linking your own Slack user for Approve / Reject buttons.
import { useCallback, useEffect, useState } from "react";
import { apiClient } from "@/lib/api";

type Form = { id: string; name: string; slug: string };
type Route = { id: string; event_type: string; channel_label: string; active: boolean; webhook: string };
const SKIPPABLE = ["company_name", "contact_person_name"];   // e-mail and phone are always typed (M47 review)
const EVENTS = ["DEAL", "TICKET", "APPROVAL", "APPROVE"];
const err = (e: unknown) => { const d = (e as { response?: { data?: { detail?: unknown } } }).response?.data?.detail; return typeof d === "string" ? d : "Request failed."; };

export default function CrmPlatformDepthPage() {
  const [msg, setMsg] = useState<string | null>(null);
  const [forms, setForms] = useState<Form[]>([]);
  const [formId, setFormId] = useState("");
  const [skip, setSkip] = useState<string[]>([]);
  const [routes, setRoutes] = useState<{ signing_secret_configured: boolean; routes: Route[] } | null>(null);
  const [route, setRoute] = useState({ event_type: "APPROVE", channel_label: "", webhook_url: "", active: true });
  const [link, setLink] = useState("");
  const [mine, setMine] = useState<string | null>(null);
  const run = (p: Promise<unknown>, ok: string) => p.then(() => setMsg(ok)).catch((e) => setMsg(err(e)));
  const loadRoutes = useCallback(() => apiClient.get("/api/v1/platform-depth/slack/routes").then((r) => setRoutes(r.data)).catch(() => setRoutes(null)), []);
  useEffect(() => {
    apiClient.get("/api/v1/crm/lead-forms").then((r) => setForms(r.data)).catch(() => setForms([]));
    apiClient.get("/api/v1/platform-depth/slack/link").then((r) => setMine(r.data.slack_user_id)).catch(() => setMine(null));
    loadRoutes();
  }, [loadRoutes]);
  const pickForm = (id: string) => {
    setFormId(id);
    if (id) apiClient.get(`/api/v1/platform-depth/lead-forms/${id}/skip-if-known`).then((r) => setSkip(r.data.fields)).catch((e) => setMsg(err(e)));
  };
  return (
    <div className="p-4 space-y-4 text-sm max-w-3xl">
      <h2 className="text-lg font-semibold">CRM platform settings</h2>
      {msg && <p role="status" className="text-xs">{msg}</p>}

      <section className="border rounded p-3 bg-white space-y-2"><h3 className="font-semibold">Form shortening</h3>
        <p className="text-xs text-gray-500">For a visitor who allowed marketing cookies and is linked to a contact, the public form leaves out the ticked fields we already know (the values are never shown back).</p>
        <select aria-label="Lead form" className="border rounded px-1 text-xs" value={formId} onChange={(e) => pickForm(e.target.value)}>
          <option value="">choose a form…</option>{forms.map((f) => <option key={f.id} value={f.id}>{f.name} ({f.slug})</option>)}</select>
        {formId && <div className="flex flex-wrap gap-3 text-xs">{SKIPPABLE.map((k) => (
          <label key={k} className="flex items-center gap-1"><input type="checkbox" checked={skip.includes(k)}
            onChange={(e) => setSkip(e.target.checked ? [...skip, k] : skip.filter((x) => x !== k))} />skip {k} if known</label>))}
          <button className="border rounded px-2" onClick={() => run(apiClient.put(`/api/v1/platform-depth/lead-forms/${formId}/skip-if-known`, { fields: skip }), "Saved.")}>Save</button></div>}
      </section>

      <section className="border rounded p-3 bg-white space-y-2"><h3 className="font-semibold">Smart contact properties</h3>
        <p className="text-xs text-gray-500">last_order_date, preferred_channel and last_objection (from notes tagged #objection) are filled from activity every day.</p>
        <button className="border rounded px-2 text-xs" onClick={() => apiClient.post("/api/v1/platform-depth/smart-properties/recompute").then((r) => setMsg(`${r.data.changed} value(s) updated.`)).catch((e) => setMsg(err(e)))}>Recompute now</button>
      </section>

      <section className="border rounded p-3 bg-white space-y-2"><h3 className="font-semibold">Slack</h3>
        {routes && <p className="text-xs text-gray-500">Approve / Reject buttons: {routes.signing_secret_configured ? "signing secret configured" : "NOT CONFIGURED (no SLACK_SIGNING_SECRET)"}.</p>}
        {routes && <table className="text-xs w-full"><tbody>{routes.routes.map((r) => <tr key={r.id} className="border-t"><td className="p-1">{r.event_type}</td><td>{r.channel_label}</td><td>{r.webhook}</td><td>{r.active ? "on" : "off"}</td>
          <td><button className="underline text-red-600" onClick={() => run(apiClient.delete(`/api/v1/platform-depth/slack/routes/${r.event_type}`).then(loadRoutes), "Removed.")}>Remove</button></td></tr>)}</tbody></table>}
        {routes && <form className="flex flex-wrap gap-2 text-xs" onSubmit={(e) => { e.preventDefault(); run(apiClient.put("/api/v1/platform-depth/slack/routes", route).then(loadRoutes), "Route saved."); }}>
          <select aria-label="Event" className="border rounded px-1" value={route.event_type} onChange={(e) => setRoute({ ...route, event_type: e.target.value })}>{EVENTS.map((x) => <option key={x}>{x}</option>)}</select>
          <input aria-label="Channel" className="border rounded px-1 w-28" required placeholder="#approvals" value={route.channel_label} onChange={(e) => setRoute({ ...route, channel_label: e.target.value })} />
          <input aria-label="Webhook URL" className="border rounded px-1 w-72" required type="url" placeholder="https://hooks.slack.com/services/…" value={route.webhook_url} onChange={(e) => setRoute({ ...route, webhook_url: e.target.value })} />
          <button className="border rounded px-2">Save route</button></form>}
        <div className="flex flex-wrap gap-2 text-xs items-center"><span>My Slack user: {mine ?? "not linked"}</span>
          <input aria-label="Slack user id" className="border rounded px-1 w-32" placeholder="U0123ABC" value={link} onChange={(e) => setLink(e.target.value.trim())} />
          <button className="border rounded px-2" onClick={() => run(apiClient.put("/api/v1/platform-depth/slack/link", { slack_user_id: link }).then(() => setMine(link)), "Linked.")}>Link</button>
          {mine && <button className="underline" onClick={() => run(apiClient.delete("/api/v1/platform-depth/slack/link").then(() => setMine(null)), "Unlinked.")}>Unlink</button>}</div>
      </section>
    </div>
  );
}
