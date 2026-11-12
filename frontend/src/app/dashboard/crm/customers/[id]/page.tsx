"use client";
import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { crmApi, type CustomerTimeline, type TimelineEvent } from "@/lib/crm_pipeline";

const TYPE_LABELS: Record<string, string> = {
  crm_record: "CRM", crm_activity: "Activity", interaction: "Interaction", visit: "Visit", field_visit: "Field visit",
  call: "Call", meeting: "Meeting", quote: "Quote", order: "Order", invoice: "Invoice", payment: "Payment",
  ticket: "Ticket", email: "E-mail",
};
const SOURCE_LABELS: Record<string, string> = {
  crm: "CRM records", interactions: "interactions", calls_meetings: "calls and meetings", sales: "quotes, orders, invoices and payments",
  tickets: "support tickets", email: "e-mail",
};

function errorText(e: unknown) {
  const detail = (e as { response?: { data?: { detail?: unknown } } }).response?.data?.detail;
  if (typeof detail === "string") return detail;
  if (detail && typeof detail === "object" && "detail" in detail) return String((detail as { detail: unknown }).detail);
  return "Could not load the timeline.";
}

export default function CustomerTimelinePage() {
  const { id } = useParams<{ id: string }>();
  const [data, setData] = useState<CustomerTimeline | null>(null);
  const [events, setEvents] = useState<TimelineEvent[]>([]);
  const [type, setType] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async (before?: string) => {
    setLoading(true);
    setError(null);
    try {
      const page = await crmApi.getCustomerTimeline(id, { limit: 25, before, types: type || undefined });
      setData(page);
      setEvents((prev) => (before ? [...prev, ...page.events] : page.events));
    } catch (e) {
      setError(errorText(e));
    }
    setLoading(false);
  }, [id, type]);
  useEffect(() => { load(); }, [load]);

  return (
    <div className="p-6 space-y-4 max-w-4xl">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <Link href="/dashboard/sales/customers" className="text-xs text-indigo-600">← Customers</Link>
          <h1 className="text-xl font-bold text-gray-900">{data ? `${data.customer.name} · ${data.customer.code}` : "Customer timeline"}</h1>
          <p className="text-sm text-gray-500">Everything that touched this customer, newest first.</p>
        </div>
        <label className="text-xs text-gray-500">Show
          <select aria-label="Event type" value={type} onChange={(e) => setType(e.target.value)} className="block text-sm border rounded-lg px-2 py-1.5">
            <option value="">All events</option>
            {Object.entries(TYPE_LABELS).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
          </select>
        </label>
      </div>
      {error && <p role="alert" className="rounded-lg p-3 text-sm bg-red-50 border border-red-200 text-red-700">{error}</p>}
      {data && data.hidden_sources.length > 0 && (
        <p className="text-xs text-gray-500">Not shown for your role: {data.hidden_sources.map((s) => SOURCE_LABELS[s] ?? s).join(", ")}.</p>
      )}
      <ol className="relative border-l border-gray-200 ml-2">
        {events.map((e) => (
          <li key={e.key} className="ml-4 pb-4">
            <span className="absolute -left-1.5 mt-1.5 h-3 w-3 rounded-full bg-indigo-500" aria-hidden />
            <div className="text-xs text-gray-500">
              {new Date(e.at).toLocaleString()} · <span className="font-medium">{TYPE_LABELS[e.type] ?? e.type}</span>
              {e.status && <> · {e.status}</>}
            </div>
            <div className="text-sm text-gray-900">
              {e.link ? <Link href={e.link} className="hover:underline">{e.title}</Link> : e.title}
            </div>
            {e.detail && <p className="text-xs text-gray-600 mt-0.5">{e.detail}</p>}
          </li>
        ))}
      </ol>
      {!loading && events.length === 0 && !error && <p className="text-sm text-gray-400">No events for this customer yet.</p>}
      {loading && <p className="text-sm text-gray-400">Loading…</p>}
      {data?.next && !loading && (
        <button className="px-3 py-1.5 text-sm border rounded-lg" onClick={() => load(data.next!)}>Load older events</button>
      )}
    </div>
  );
}
