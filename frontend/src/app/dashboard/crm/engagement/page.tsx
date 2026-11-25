"use client";
// M43.S01.T006 e-mail engagement and sales activity: per sender and per message, machine events excluded.
import { useEffect, useState } from "react";
import { apiClient } from "@/lib/api";
import { DeliverabilityPanel } from "@/components/DeliverabilityPanel";

interface Sender { sender: string; sent: number; tracked: number; opened: number; clicked: number; machine_only: number;
  open_rate: number | null; click_rate: number | null }
interface Msg { id: string; to: string; subject: string; purpose: string; sent_at: string; tracked: boolean;
  human_opens: number; machine_opens: number; clicks: number; first_open: string | null }
interface Data { senders: Sender[]; messages: Msg[]; unsubscribes: number; note: string }

const pct = (v: number | null) => (v === null ? "—" : `${Math.round(v * 100)}%`);

export default function CRMEngagementPage() {
  const [days, setDays] = useState(30);
  const [data, setData] = useState<Data | null>(null);
  const [error, setError] = useState(false);
  useEffect(() => {
    setData(null); setError(false);
    apiClient.get(`/api/v1/crm-engagement?days=${days}`).then((r) => setData(r.data)).catch(() => setError(true));
  }, [days]);
  return (
    <div className="p-4 space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h2 className="text-lg font-semibold">E-mail engagement</h2>
        <select aria-label="Period" className="border rounded px-2 py-1 text-sm" value={days} onChange={(e) => setDays(+e.target.value)}>
          {[7, 30, 90, 365].map((d) => <option key={d} value={d}>Last {d} days</option>)}
        </select>
      </div>
      <DeliverabilityPanel />
      {error && <p className="text-sm text-red-600">Could not load engagement data.</p>}
      {!data && !error && <p className="text-sm text-gray-500">Loading…</p>}
      {data && (
        <>
          <p className="text-xs text-gray-500">{data.note} Unsubscribes in the period: {data.unsubscribes}.</p>
          <div className="overflow-x-auto">
            <table className="min-w-full text-sm">
              <thead><tr className="text-left text-gray-500"><th className="py-1 pr-3">Sender</th><th>Sent</th><th>Tracked</th>
                <th>Opened</th><th>Clicked</th><th>Open rate</th><th>Click rate</th><th>Machine only</th></tr></thead>
              <tbody>{data.senders.map((s) => (
                <tr key={s.sender} className="border-t"><td className="py-1 pr-3">{s.sender}</td><td>{s.sent}</td><td>{s.tracked}</td>
                  <td>{s.opened}</td><td>{s.clicked}</td><td>{pct(s.open_rate)}</td><td>{pct(s.click_rate)}</td><td>{s.machine_only}</td></tr>
              ))}</tbody>
            </table>
            {data.senders.length === 0 && <p className="text-sm text-gray-500 mt-2">No e-mails sent in this period.</p>}
          </div>
          <div className="overflow-x-auto">
            <table className="min-w-full text-xs">
              <thead><tr className="text-left text-gray-500"><th className="py-1 pr-3">Sent</th><th>To</th><th>Subject</th>
                <th>Opens</th><th>Proxy/scanner</th><th>Clicks</th><th>First open</th></tr></thead>
              <tbody>{data.messages.map((m) => (
                <tr key={m.id} className="border-t"><td className="py-1 pr-3 whitespace-nowrap">{new Date(m.sent_at).toLocaleString()}</td>
                  <td>{m.to}</td><td>{m.subject}</td>
                  <td>{m.tracked ? m.human_opens : "not tracked"}</td><td>{m.tracked ? m.machine_opens : "—"}</td>
                  <td>{m.tracked ? m.clicks : "—"}</td><td>{m.first_open ? new Date(m.first_open).toLocaleString() : "—"}</td></tr>
              ))}</tbody>
            </table>
          </div>
        </>
      )}
    </div>
  );
}
