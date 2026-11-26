"use client";
import { useCallback, useEffect, useState } from "react";
import { crmApi, type ConsentRow, type OutboxMessage } from "@/lib/crm_pipeline";
import { useAuth } from "@/context/AuthContext";
import { tx } from "@/lib/i18n/core";

function errorText(e: unknown) {
  const detail = (e as { response?: { data?: { detail?: unknown } } }).response?.data?.detail;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) return detail.map((d) => (d as { msg?: string }).msg).join("; ");
  if (detail && typeof detail === "object" && "detail" in detail) return String((detail as { detail: unknown }).detail);
  return "Request failed.";
}

const STATUS_STYLE: Record<string, string> = {
  SENT: "text-emerald-700", QUEUED: "text-amber-700", SENDING: "text-amber-700", SUPPRESSED: "text-gray-500",
  FAILED: "text-red-700", CANCELLED: "text-gray-500",
};

export default function CRMOutboxPage() {
  const [messages, setMessages] = useState<OutboxMessage[]>([]);
  const [enabled, setEnabled] = useState<boolean | null>(null);
  const [consents, setConsents] = useState<ConsentRow[]>([]);
  const [mail, setMail] = useState({ to_email: "", subject: "", body: "", track_engagement: false });
  const [block, setBlock] = useState({ email: "", status: "UNSUBSCRIBED" });
  const [error, setError] = useState<string | null>(null);
  const [info, setInfo] = useState<string | null>(null);

  const { hasPermission } = useAuth();
  const canConfig = hasPermission("crm.edit_all");
  const load = useCallback(async () => {
    try {
      const o = await crmApi.getOutbox();
      setMessages(o.messages);
      setEnabled(o.delivery_enabled);
      if (canConfig) setConsents(await crmApi.getConsents().catch(() => []));  // consent register: company-wide CRM editors only
    } catch (e) { setError(errorText(e)); }
  }, [canConfig]);
  useEffect(() => { load(); }, [load]);

  async function act(fn: () => Promise<unknown>, msg: string) {
    setError(null);
    try { await fn(); setInfo(msg); await load(); } catch (e) { setError(errorText(e)); }
  }

  const input = "text-sm border rounded-lg px-2 py-1.5";
  return (
    <div className="p-6 space-y-6">
      <div>
        <h1 className="text-xl font-bold text-gray-900">{tx("E-mail Outbox & Consent")}</h1>
        <p className="text-sm text-gray-500">{tx("Every CRM e-mail is queued here first. Sequence and campaign mail needs recorded consent; unsubscribed or bounced addresses are never mailed.")}</p>
      </div>
      {enabled === false && (
        <p role="status" className="rounded-lg p-3 text-sm bg-amber-50 border border-amber-200 text-amber-800">
          {tx("Outbound e-mail is not enabled on this server (CRM_OUTBOUND_EMAIL_ENABLED / SMTP). Messages stay queued; nothing is reported as sent.")}
        </p>
      )}
      {error && <p role="alert" className="rounded-lg p-3 text-sm bg-red-50 border border-red-200 text-red-700">{error}</p>}
      {info && !error && <p className="rounded-lg p-3 text-sm bg-emerald-50 border border-emerald-200 text-emerald-800">{info}</p>}

      <form aria-label={tx("Compose e-mail")} className="bg-white rounded-xl border shadow-sm p-4 grid md:grid-cols-3 gap-2"
        onSubmit={(e) => { e.preventDefault(); act(() => crmApi.queueEmail(mail), "E-mail queued."); setMail({ to_email: "", subject: "", body: "", track_engagement: false }); }}>
        <h2 className="font-semibold text-gray-800 md:col-span-3">{tx("Compose one-to-one e-mail")}</h2>
        <input aria-label={tx("To")} required type="email" placeholder="to@example.com" value={mail.to_email} onChange={(e) => setMail({ ...mail, to_email: e.target.value })} className={input} />
        <input aria-label={tx("Subject")} required placeholder={tx("Subject")} value={mail.subject} onChange={(e) => setMail({ ...mail, subject: e.target.value })} className={`${input} md:col-span-2`} />
        <textarea aria-label={tx("Message")} required rows={3} placeholder={tx("Message")} value={mail.body} onChange={(e) => setMail({ ...mail, body: e.target.value })} className={`${input} md:col-span-3`} />
        <label className="flex items-center gap-2 text-xs text-gray-600 md:col-span-3"><input type="checkbox" checked={mail.track_engagement} onChange={(e) => setMail({ ...mail, track_engagement: e.target.checked })} /> {tx("Track opens and clicks (opt-in; indicator only)")}</label>
        <button type="submit" className="px-3 py-1.5 text-sm bg-blue-600 text-white rounded-lg md:col-start-3">{tx("Queue e-mail")}</button>
      </form>

      <div className="bg-white rounded-xl border shadow-sm p-4 overflow-x-auto">
        <h2 className="font-semibold text-gray-800 mb-2">{tx("Outbox")}</h2>
        {messages.length === 0 ? <p className="text-sm text-gray-400">{tx("No e-mails yet.")}</p> : (
          <table className="w-full text-sm">
            <thead><tr className="text-left text-xs text-gray-500"><th className="py-1">{tx("Queued")}</th><th>{tx("To")}</th><th>{tx("Subject")}</th><th>{tx("Purpose")}</th><th>{tx("Status")}</th><th /></tr></thead>
            <tbody>
              {messages.map((m) => (
                <tr key={m.id} className="border-t">
                  <td className="py-1.5">{new Date(m.created_at).toLocaleString()}</td><td>{m.to_email}</td><td>{m.subject}</td><td>{m.purpose}</td>
                  <td className={STATUS_STYLE[m.status] ?? ""} title={m.status_reason ?? undefined}>{m.status}{m.status_reason ? ` — ${m.status_reason}` : ""}</td>
                  <td>{m.status === "QUEUED" && <button className="text-xs underline" onClick={() => act(() => crmApi.cancelEmail(m.id), "Cancelled.")}>{tx("Cancel")}</button>}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {canConfig && <div className="bg-white rounded-xl border shadow-sm p-4 overflow-x-auto">
        <h2 className="font-semibold text-gray-800 mb-2">{tx("Consent register")}</h2>
        <form aria-label={tx("Record consent")} className="flex flex-wrap gap-2 mb-3"
          onSubmit={(e) => { e.preventDefault(); act(() => crmApi.setConsent(block), "Consent recorded."); setBlock({ ...block, email: "" }); }}>
          <input aria-label={tx("E-mail address")} required type="email" placeholder={tx("address")} value={block.email} onChange={(e) => setBlock({ ...block, email: e.target.value })} className={input} />
          <select aria-label={tx("Consent status")} value={block.status} onChange={(e) => setBlock({ ...block, status: e.target.value })} className={input}>
            {["UNSUBSCRIBED", "BOUNCED", "COMPLAINED", "SUBSCRIBED"].map((s) => <option key={s} value={s}>{s}</option>)}
          </select>
          <button type="submit" className="px-3 py-1.5 text-sm border rounded-lg">{tx("Record")}</button>
        </form>
        {consents.length === 0 ? <p className="text-sm text-gray-400">{tx("No consent events yet.")}</p> : (
          <table className="w-full text-sm">
            <thead><tr className="text-left text-xs text-gray-500"><th className="py-1">{tx("Address")}</th><th>{tx("Status")}</th><th>{tx("Source")}</th><th>{tx("Updated")}</th></tr></thead>
            <tbody>{consents.map((c) => (
              <tr key={c.email} className="border-t"><td className="py-1.5">{c.email}</td><td>{c.status}</td><td>{c.source ?? "—"}</td>
                <td>{c.updated_at ? new Date(c.updated_at).toLocaleString() : "—"}</td></tr>
            ))}</tbody>
          </table>
        )}
      </div>}
    </div>
  );
}
