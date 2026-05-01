"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { getDashboard, processPending, seedEventDefinitions, WebhookDashboard, STATUS_BADGE } from "@/lib/webhooks";
import { Button } from "@/components/ui/Button";

export default function WebhooksDashboardPage() {
  const [data, setData] = useState<WebhookDashboard | null>(null);
  const [loading, setLoading] = useState(true);
  const [processing, setProcessing] = useState(false);
  const [msg, setMsg] = useState("");

  useEffect(() => { load(); }, []);

  async function load() {
    try { setData(await getDashboard()); } catch {}
    setLoading(false);
  }

  async function handleProcess() {
    setProcessing(true);
    try {
      const r = await processPending();
      setMsg(`Processed ${r.processed} pending, ${r.retried} retried`);
      await load();
    } catch { setMsg("Failed to process queue"); }
    setProcessing(false);
  }

  async function handleSeed() {
    try { await seedEventDefinitions(); setMsg("Event definitions seeded"); } catch { setMsg("Seed failed"); }
  }

  const navLinks = [
    { href: "/dashboard/webhooks/definitions", label: "Event Definitions" },
    { href: "/dashboard/webhooks/subscriptions", label: "Subscriptions" },
    { href: "/dashboard/webhooks/deliveries", label: "Deliveries" },
    { href: "/dashboard/webhooks/dead-letter", label: "Dead-Letter Queue" },
    { href: "/dashboard/webhooks/inbound", label: "Inbound Endpoints" },
    { href: "/dashboard/webhooks/reports", label: "Reports & AI" },
  ];

  if (loading) return <div className="p-8 text-gray-500">Loading...</div>;

  const kpis = data ? [
    { label: "Events (24h)", value: data.total_events_24h },
    { label: "Events (7d)", value: data.total_events_7d },
    { label: "Deliveries (24h)", value: data.total_deliveries_24h },
    { label: "Success Rate", value: `${data.delivery_success_rate_24h}%` },
    { label: "Pending", value: data.pending_deliveries, alert: data.pending_deliveries > 0 },
    { label: "Dead-Letter", value: data.dead_letter_count, alert: data.dead_letter_count > 0 },
    { label: "Active Subs", value: data.active_subscriptions },
  ] : [];

  return (
    <div className="max-w-6xl mx-auto py-8 px-4 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Webhook / Event Engine</h1>
          <p className="text-sm text-gray-500 mt-1">Event bus, outbound webhooks, and integration backbone</p>
        </div>
        <div className="flex gap-2">
          <Button variant="secondary" onClick={handleSeed}>Seed Events</Button>
          <Button onClick={handleProcess} loading={processing}>Process Queue</Button>
        </div>
      </div>

      {msg && (
        <div className="bg-blue-50 border border-blue-200 text-blue-700 text-sm rounded-lg px-4 py-2">
          {msg}
        </div>
      )}

      {/* KPI grid */}
      <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-7 gap-3">
        {kpis.map((k) => (
          <div key={k.label} className={`bg-white rounded-xl border p-4 ${(k as { alert?: boolean }).alert ? "border-amber-300" : "border-gray-200"}`}>
            <div className={`text-2xl font-bold ${(k as { alert?: boolean }).alert ? "text-amber-600" : "text-gray-900"}`}>{k.value}</div>
            <div className="text-xs text-gray-500 mt-1">{k.label}</div>
          </div>
        ))}
      </div>

      {/* Nav links */}
      <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
        {navLinks.map((l) => (
          <Link
            key={l.href}
            href={l.href}
            className="bg-white border border-gray-200 rounded-xl p-4 hover:border-indigo-300 hover:bg-indigo-50 transition-colors"
          >
            <div className="font-medium text-gray-900 text-sm">{l.label}</div>
          </Link>
        ))}
      </div>

      {/* Top events */}
      {data && data.top_events.length > 0 && (
        <div className="bg-white rounded-2xl border border-gray-200 p-6">
          <h2 className="text-sm font-semibold text-gray-700 mb-4">Top Events (24h)</h2>
          <div className="space-y-2">
            {data.top_events.map((e) => (
              <div key={e.event_code} className="flex items-center justify-between">
                <code className="text-sm text-gray-800">{e.event_code}</code>
                <span className="text-sm font-medium text-gray-900">{e.count}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Recent failures */}
      {data && data.recent_failures.length > 0 && (
        <div className="bg-white rounded-2xl border border-red-200 p-6">
          <h2 className="text-sm font-semibold text-red-700 mb-4">Recent Failures</h2>
          <div className="space-y-2">
            {data.recent_failures.map((f, i) => (
              <div key={i} className="text-sm text-gray-700 flex items-center gap-2">
                <span className={`px-2 py-0.5 rounded text-xs font-medium ${STATUS_BADGE[(f.status as string) as keyof typeof STATUS_BADGE] || ""}`}>
                  {f.status as string}
                </span>
                <code className="text-xs text-gray-500 truncate">{String(f.error || "unknown error")}</code>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
