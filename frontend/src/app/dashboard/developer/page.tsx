"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import {
  devPortalApi,
  DevPortalDashboard,
  DevPortalRequestError,
  DevResources,
  PartnerAuditEvent,
  PartnerUsageAnalytics,
} from "@/lib/api_portal_api";

export default function DeveloperPortalPage() {
  const [dash, setDash] = useState<DevPortalDashboard | null>(null);
  const [res, setRes] = useState<DevResources | null>(null);
  const [audit, setAudit] = useState<PartnerAuditEvent[]>([]);
  const [usage, setUsage] = useState<PartnerUsageAnalytics | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [sessionExpired, setSessionExpired] = useState(false);

  const load = async () => {
    setLoading(true);
    setError(null);
    setSessionExpired(false);
    const results = await Promise.allSettled([
      devPortalApi.getDashboard(),
      devPortalApi.getResources(),
      devPortalApi.getPartnerAudit(20),
      devPortalApi.getUsageAnalytics(30),
    ]);
    if (results[0].status === "fulfilled") setDash(results[0].value);
    if (results[1].status === "fulfilled") setRes(results[1].value);
    if (results[2].status === "fulfilled") setAudit(results[2].value);
    if (results[3].status === "fulfilled") setUsage(results[3].value);
    const failure = results.find((result) => result.status === "rejected");
    if (failure?.status === "rejected") {
      const reason = failure.reason;
      setError(reason instanceof Error ? reason.message : "Developer Portal could not be loaded.");
      const status = typeof reason === "object" && reason !== null && "status" in reason
        ? (reason as { status?: unknown }).status
        : undefined;
      setSessionExpired(status === 401);
    }
    setLoading(false);
  };

  useEffect(() => { void load(); }, []);

  const links = [
    { href: "/dashboard/developer/applications", label: "API Applications", desc: "Register and manage API client applications" },
    { href: "/dashboard/developer/keys", label: "API Keys", desc: "Generate and manage API keys" },
    { href: "/dashboard/developer/graphql", label: "GraphQL Layer", desc: "GraphQL schema info and status" },
    { href: "/docs", label: "OpenAPI Docs", desc: "Interactive Swagger UI", external: true },
    { href: "/redoc", label: "ReDoc", desc: "Alternative API documentation", external: true },
    { href: "/dashboard/webhooks", label: "Webhooks", desc: "Event subscriptions and deliveries" },
    { href: "/dashboard/integrations", label: "Integrations Hub", desc: "Connector marketplace overview" },
  ];

  return (
    <div className="w-full min-w-0 p-6 space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Developer Portal</h1>
        <p className="text-sm text-gray-500 mt-1">
          API key management, GraphQL layer, SDK resources, and developer tools.
        </p>
      </div>

      {loading ? (
        <p className="text-gray-500 text-sm">Loading…</p>
      ) : (
        <>
          {error && (
            <div role="alert" className="flex flex-wrap items-center justify-between gap-3 rounded-lg border border-amber-200 bg-amber-50 p-4 text-sm text-amber-900">
              <span>{error}</span>
              <div className="flex items-center gap-2">
                {sessionExpired && <Link href="/login" className="rounded border border-amber-300 px-3 py-1.5 font-medium hover:bg-amber-100">Sign in</Link>}
                {!sessionExpired && <button type="button" onClick={() => void load()} className="rounded border border-amber-300 px-3 py-1.5 font-medium hover:bg-amber-100">Retry</button>}
              </div>
            </div>
          )}
          {/* KPI strip */}
          {dash && usage && (
            <div className="grid grid-cols-2 gap-4 sm:grid-cols-5">
              {[
                { label: "Total Keys", value: dash.total_keys, color: "text-gray-800" },
                { label: "Active Keys", value: dash.active_keys, color: "text-blue-600" },
                { label: "Recorded calls (30d)", value: usage.total_calls, color: "text-gray-800" },
                { label: "Success (30d)", value: usage.success_calls, color: "text-green-600" },
                { label: "Errors (30d)", value: usage.error_calls, color: "text-red-600" },
              ].map((k) => (
                <div key={k.label} className="bg-white border rounded-lg p-4 shadow-sm">
                  <p className="text-xs text-gray-500">{k.label}</p>
                  <p className={`text-2xl font-bold mt-1 ${k.color}`}>{k.value}</p>
                </div>
              ))}
            </div>
          )}

          {usage && (
            <section aria-labelledby="partner-usage-heading" className="bg-white border rounded-lg p-4 shadow-sm space-y-3">
              <div className="flex flex-wrap items-start justify-between gap-2">
                <div>
                  <h2 id="partner-usage-heading" className="text-sm font-semibold text-gray-800">Partner usage analytics</h2>
                  <p className="text-xs text-gray-500">Recorded usage-log rows from the last {usage.days} days</p>
                </div>
                <p className="text-xs text-gray-600">
                  Average response: {usage.average_response_ms === null ? "—" : `${Math.round(usage.average_response_ms)} ms`}
                </p>
              </div>
              <p className="text-xs text-amber-800 bg-amber-50 border border-amber-200 rounded p-2">{usage.collection_note}</p>
              {usage.daily_usage.length ? (
                <div className="overflow-x-auto">
                  <table className="w-full text-xs">
                    <thead className="text-left text-gray-500 border-b">
                      <tr>
                        <th className="py-2 pr-3">Date (UTC)</th>
                        <th className="py-2 pr-3">Recorded</th>
                        <th className="py-2 pr-3">Successful</th>
                        <th className="py-2">Errors</th>
                      </tr>
                    </thead>
                    <tbody>
                      {usage.daily_usage.map((day) => (
                        <tr key={day.date} className="border-b last:border-0 text-gray-700">
                          <td className="py-2 pr-3">{day.date}</td>
                          <td className="py-2 pr-3">{day.total_calls}</td>
                          <td className="py-2 pr-3">{day.success_calls}</td>
                          <td className="py-2">{day.error_calls}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ) : (
                <p className="text-sm text-gray-500">No usage-log rows were recorded in this window.</p>
              )}
              {usage.unclassified_calls > 0 && (
                <p className="text-xs text-gray-500">{usage.unclassified_calls} rows have no classifiable HTTP status.</p>
              )}
            </section>
          )}

          <section aria-labelledby="partner-audit-heading" className="bg-white border rounded-lg p-4 shadow-sm space-y-3">
            <div>
              <h2 id="partner-audit-heading" className="text-sm font-semibold text-gray-800">Partner credential audit</h2>
              <p className="text-xs text-gray-500">Recent application and credential changes performed by your account</p>
            </div>
            {audit.length ? (
              <ul className="divide-y">
                {audit.map((event) => (
                  <li key={event.id} className="py-2 flex flex-wrap justify-between gap-x-4 gap-y-1 text-xs">
                    <span className="text-gray-800">
                      {event.event_type.replace(/_/g, " ").toLowerCase()}
                      {event.target_name ? ` · ${event.target_name}` : ""}
                    </span>
                    <time className="text-gray-500" dateTime={event.created_at}>
                      {new Date(event.created_at).toLocaleString()}
                    </time>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="text-sm text-gray-500">No partner application or credential changes have been recorded.</p>
            )}
          </section>

          {/* Scopes & rate limit policy */}
          {dash && res && (
            <div className="bg-white border rounded-lg p-4 shadow-sm space-y-4">
              <div className="flex flex-wrap gap-6">
                <div>
                  <p className="text-xs text-gray-500 mb-1">Available Scope Policies</p>
                  <div className="flex gap-2">
                    {dash.available_scopes.map((scope) => (
                      <span key={scope} className="bg-blue-100 text-blue-700 text-xs font-medium rounded-full px-3 py-1">{scope}</span>
                    ))}
                  </div>
                </div>
                <div>
                  <p className="text-xs text-gray-500 mb-1">Per-key Rate Policy</p>
                  <span className="text-sm font-semibold text-gray-700">
                    {dash.default_rate_limit} req/min default · {res.rate_limits.minimum}–{res.rate_limits.maximum} allowed
                  </span>
                </div>
              </div>
              <ul className="space-y-1 text-xs text-gray-600">
                {Object.entries(res.api_key_scopes).map(([scope, description]) => (
                  <li key={scope}><span className="font-semibold">{scope}:</span> {description}</li>
                ))}
              </ul>
              <p className="text-xs text-amber-800 bg-amber-50 border border-amber-200 rounded p-2">
                These are stored credential policies. API-key request authentication is not enabled, so scopes and rate limits are not currently enforced.
              </p>
            </div>
          )}

          {/* Auth info */}
          {res && (
            <div className="bg-white border rounded-lg p-4 shadow-sm space-y-2">
              <h2 className="text-sm font-semibold text-gray-700">Authentication</h2>
              <div className="text-sm text-gray-600 space-y-1">
                {Object.entries(res.authentication).map(([k, v]) => (
                  <div key={k} className="flex gap-2">
                    <span className="text-gray-400 capitalize shrink-0">{k.replace(/_/g, " ")}:</span>
                    <span className="font-mono text-gray-700 text-xs">{v}</span>
                  </div>
                ))}
              </div>
              <p className="text-xs text-gray-400 mt-2">{res.sdk_note}</p>
            </div>
          )}
        </>
      )}

      {/* Navigation */}
      <div className="bg-white border rounded-lg p-4 shadow-sm">
        <h2 className="text-sm font-semibold text-gray-700 mb-3">Developer Tools</h2>
        <div className="grid grid-cols-1 gap-2 sm:grid-cols-2 lg:grid-cols-3">
          {links.map((l) => (
            <Link
              key={l.href}
              href={l.href}
              target={l.external ? "_blank" : undefined}
              rel={l.external ? "noopener noreferrer" : undefined}
              className="flex flex-col rounded border border-blue-200 bg-blue-50 px-4 py-3 hover:bg-blue-100"
            >
              <span className="text-sm font-semibold text-blue-700">
                {l.label}
                {l.external && <span className="ml-1 text-xs text-blue-400">↗</span>}
              </span>
              <span className="text-xs text-blue-500 mt-0.5">{l.desc}</span>
            </Link>
          ))}
        </div>
      </div>
    </div>
  );
}
