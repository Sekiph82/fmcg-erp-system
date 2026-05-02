"use client";

import { useState } from "react";
import { getReport, getHealthMonitor, getPayloadAdvisor, getAnomalyDetector, WebhookReport } from "@/lib/webhooks";
import { Button } from "@/components/ui/Button";

export default function WebhookReportsPage() {
  const [days, setDays] = useState(7);
  const [report, setReport] = useState<WebhookReport | null>(null);
  const [health, setHealth] = useState<unknown>(null);
  const [advisor, setAdvisor] = useState<unknown>(null);
  const [anomaly, setAnomaly] = useState<unknown>(null);
  const [loading, setLoading] = useState(false);

  async function loadReport() {
    setLoading(true);
    try {
      const [r, h, a, an] = await Promise.all([
        getReport(days),
        getHealthMonitor(),
        getPayloadAdvisor(),
        getAnomalyDetector(),
      ]);
      setReport(r); setHealth(h); setAdvisor(a); setAnomaly(an);
    } catch {}
    setLoading(false);
  }

  return (
    <div className="max-w-5xl mx-auto py-8 px-4 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Reports & AI</h1>
          <p className="text-sm text-gray-500 mt-1">Delivery analytics and AI insights</p>
        </div>
        <div className="flex items-center gap-3">
          <select className="border border-gray-300 rounded-lg px-3 py-2 text-sm" value={days} onChange={(e) => setDays(Number(e.target.value))}>
            <option value={1}>Last 24h</option>
            <option value={7}>Last 7 days</option>
            <option value={30}>Last 30 days</option>
          </select>
          <Button onClick={loadReport} loading={loading}>Load Reports</Button>
        </div>
      </div>

      {report && (
        <div className="space-y-4">
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            {[
              { label: "Success Rate", value: `${report.delivery_success_rate}%`, color: report.delivery_success_rate > 95 ? "text-green-700" : "text-amber-600" },
              { label: "Delivered", value: report.total_delivered, color: "text-gray-900" },
              { label: "Failed", value: report.total_failed, color: "text-red-600" },
              { label: "Dead-Letter", value: report.total_dead_letter, color: "text-gray-600" },
              { label: "Avg Retry", value: `${report.avg_retry_count}x`, color: "text-gray-900" },
            ].map((k) => (
              <div key={k.label} className="bg-white rounded-xl border border-gray-200 p-4">
                <div className={`text-2xl font-bold ${k.color}`}>{k.value}</div>
                <div className="text-xs text-gray-500 mt-1">{k.label}</div>
              </div>
            ))}
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div className="bg-white rounded-2xl border border-gray-200 p-5">
              <h3 className="font-semibold text-gray-700 mb-3 text-sm">Top Event Producers</h3>
              <div className="space-y-2">
                {report.top_event_producers.map((e) => (
                  <div key={e.module} className="flex justify-between text-sm">
                    <span className="text-gray-700">{e.module}</span>
                    <span className="font-medium">{e.count}</span>
                  </div>
                ))}
              </div>
            </div>
            <div className="bg-white rounded-2xl border border-gray-200 p-5">
              <h3 className="font-semibold text-gray-700 mb-3 text-sm">Failure Reasons (HTTP Status)</h3>
              <div className="space-y-2">
                {report.failure_reasons.map((e) => (
                  <div key={e.http_status} className="flex justify-between text-sm">
                    <span className="font-mono text-red-700">{e.http_status}</span>
                    <span className="font-medium">{e.count}</span>
                  </div>
                ))}
                {report.failure_reasons.length === 0 && <div className="text-gray-400 text-sm">No failures</div>}
              </div>
            </div>
          </div>
        </div>
      )}

      {!!health && (
        <div className="bg-white rounded-2xl border border-gray-200 p-6">
          <h2 className="font-semibold text-gray-900 mb-3">AI: Integration Health Monitor</h2>
          <pre className="text-xs bg-gray-900 text-green-300 rounded-lg p-4 overflow-auto max-h-64">
            {JSON.stringify(health, null, 2)}
          </pre>
        </div>
      )}

      {!!advisor && (
        <div className="bg-white rounded-2xl border border-gray-200 p-6">
          <h2 className="font-semibold text-gray-900 mb-3">AI: Payload Advisor</h2>
          <pre className="text-xs bg-gray-900 text-blue-300 rounded-lg p-4 overflow-auto max-h-64">
            {JSON.stringify(advisor, null, 2)}
          </pre>
        </div>
      )}

      {!!anomaly && (
        <div className="bg-white rounded-2xl border border-gray-200 p-6">
          <h2 className="font-semibold text-gray-900 mb-3">AI: Anomaly Detector</h2>
          <pre className="text-xs bg-gray-900 text-amber-300 rounded-lg p-4 overflow-auto max-h-64">
            {JSON.stringify(anomaly, null, 2)}
          </pre>
        </div>
      )}

      {!report && !loading && (
        <div className="text-center py-16 text-gray-400">Click "Load Reports" to fetch analytics and AI insights.</div>
      )}
    </div>
  );
}
