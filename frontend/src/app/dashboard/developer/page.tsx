"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import { devPortalApi, DevPortalDashboard, DevResources } from "@/lib/api_portal_api";

export default function DeveloperPortalPage() {
  const [dash, setDash] = useState<DevPortalDashboard | null>(null);
  const [res, setRes] = useState<DevResources | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([devPortalApi.getDashboard(), devPortalApi.getResources()])
      .then(([d, r]) => { setDash(d); setRes(r); })
      .finally(() => setLoading(false));
  }, []);

  const links = [
    { href: "/dashboard/developer/keys", label: "API Keys", desc: "Generate and manage API keys" },
    { href: "/dashboard/developer/graphql", label: "GraphQL Layer", desc: "GraphQL schema info and status" },
    { href: "/docs", label: "OpenAPI Docs", desc: "Interactive Swagger UI", external: true },
    { href: "/redoc", label: "ReDoc", desc: "Alternative API documentation", external: true },
    { href: "/dashboard/webhooks", label: "Webhooks", desc: "Event subscriptions and deliveries" },
    { href: "/dashboard/integrations", label: "Integrations Hub", desc: "Connector marketplace overview" },
  ];

  return (
    <div className="p-6 space-y-6 max-w-5xl mx-auto">
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
          {/* KPI strip */}
          {dash && (
            <div className="grid grid-cols-2 gap-4 sm:grid-cols-5">
              {[
                { label: "Total Keys", value: dash.total_keys, color: "text-gray-800" },
                { label: "Active Keys", value: dash.active_keys, color: "text-blue-600" },
                { label: "Total API Calls", value: dash.total_api_calls, color: "text-gray-800" },
                { label: "Success", value: dash.success_calls, color: "text-green-600" },
                { label: "Errors", value: dash.error_calls, color: "text-red-600" },
              ].map((k) => (
                <div key={k.label} className="bg-white border rounded-lg p-4 shadow-sm">
                  <p className="text-xs text-gray-500">{k.label}</p>
                  <p className={`text-2xl font-bold mt-1 ${k.color}`}>{k.value}</p>
                </div>
              ))}
            </div>
          )}

          {/* Scopes & rate limit info */}
          {dash && (
            <div className="bg-white border rounded-lg p-4 shadow-sm flex flex-wrap gap-6">
              <div>
                <p className="text-xs text-gray-500 mb-1">Available Scopes</p>
                <div className="flex gap-2">
                  {dash.available_scopes.map((s) => (
                    <span key={s} className="bg-blue-100 text-blue-700 text-xs font-medium rounded-full px-3 py-1">{s}</span>
                  ))}
                </div>
              </div>
              <div>
                <p className="text-xs text-gray-500 mb-1">Default Rate Limit</p>
                <span className="text-sm font-semibold text-gray-700">{dash.default_rate_limit} req/min</span>
              </div>
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
