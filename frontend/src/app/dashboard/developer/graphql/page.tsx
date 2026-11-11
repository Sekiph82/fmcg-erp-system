"use client";
import { useEffect, useState } from "react";
import { devPortalApi, GraphQLSchemaInfo } from "@/lib/api_portal_api";

export default function GraphQLInfoPage() {
  const [info, setInfo] = useState<GraphQLSchemaInfo | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = async () => {
    setLoading(true);
    setError(null);
    try { setInfo(await devPortalApi.getGraphQLInfo()); }
    catch (reason) { setError(reason instanceof Error ? reason.message : "GraphQL status could not be loaded."); }
    finally { setLoading(false); }
  };

  useEffect(() => { void load(); }, []);

  if (loading) return <div className="p-6 text-gray-500 text-sm">Loading…</div>;
  if (!info) return <div className="p-6 space-y-3" role="alert"><p className="text-sm text-red-700">{error ?? "GraphQL status could not be loaded."}</p><button type="button" onClick={() => void load()} className="rounded border px-3 py-1.5 text-sm">Retry</button></div>;

  const example = `curl -X POST ${info.endpoint} \\
  -H "Content-Type: application/json" --cookie "<session cookie>" \\
  -d '{"query": "{ products(limit: 5) { sku name uom } }"}'`;

  return (
    <div className="w-full min-w-0 p-6 space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">GraphQL Layer</h1>
        <p className="text-sm text-gray-500 mt-1">Read-only GraphQL endpoint and its schema.</p>
      </div>

      <div className="bg-green-50 border border-green-200 rounded-lg p-4">
        <div className="flex flex-wrap items-center gap-2 mb-1">
          <span className="text-green-700 font-semibold text-sm uppercase tracking-wide">{info.status}</span>
          <code className="bg-green-100 px-1 rounded text-xs">POST {info.endpoint}</code>
        </div>
        <p className="text-sm text-green-900">{info.note}</p>
        <p className="text-xs text-green-700 mt-2">
          REST API base: <code className="bg-green-100 px-1 rounded">{info.rest_api_base}</code> — use REST for changes.
        </p>
      </div>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <div className="bg-white border rounded-lg p-4 shadow-sm">
          <h2 className="text-sm font-semibold text-gray-700 mb-3">Types</h2>
          <ul className="space-y-1">
            {info.types.map((t) => (
              <li key={t} className="flex items-center gap-2 text-sm text-gray-700">
                <span className="text-blue-400">▸</span>
                <code className="text-gray-800">{t}</code>
              </li>
            ))}
          </ul>
        </div>
        <div className="bg-white border rounded-lg p-4 shadow-sm">
          <h2 className="text-sm font-semibold text-gray-700 mb-3">Queries</h2>
          <ul className="space-y-1">
            {info.queries.map((q) => (
              <li key={q} className="text-xs font-mono text-gray-700 bg-gray-50 rounded px-2 py-1">{q}</li>
            ))}
          </ul>
          <p className="text-xs text-gray-400 mt-3">Mutations: none — changes go through the REST API.</p>
        </div>
      </div>

      <div className="bg-white border rounded-lg p-4 shadow-sm space-y-3">
        <h2 className="text-sm font-semibold text-gray-700">Example</h2>
        <pre className="text-xs bg-gray-50 rounded p-3 overflow-x-auto whitespace-pre">{example}</pre>
        <h2 className="text-sm font-semibold text-gray-700">Schema (SDL)</h2>
        <pre className="text-xs bg-gray-50 rounded p-3 overflow-x-auto max-h-96 whitespace-pre">{info.sdl}</pre>
      </div>
    </div>
  );
}
