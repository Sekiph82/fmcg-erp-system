"use client";
import { useEffect, useState } from "react";
import { devPortalApi, GraphQLSchemaInfo } from "@/lib/api_portal_api";

export default function GraphQLInfoPage() {
  const [info, setInfo] = useState<GraphQLSchemaInfo | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    devPortalApi.getGraphQLInfo().then(setInfo).finally(() => setLoading(false));
  }, []);

  if (loading) return <div className="p-6 text-gray-500 text-sm">Loading…</div>;
  if (!info) return null;

  return (
    <div className="p-6 space-y-6 max-w-3xl mx-auto">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">GraphQL Layer</h1>
        <p className="text-sm text-gray-500 mt-1">GraphQL endpoint status and planned schema.</p>
      </div>

      {/* Status banner */}
      <div className="bg-amber-50 border border-amber-200 rounded-lg p-4">
        <div className="flex items-center gap-2 mb-1">
          <span className="text-amber-600 font-semibold text-sm uppercase tracking-wide">{info.status}</span>
        </div>
        <p className="text-sm text-amber-800">{info.note}</p>
        <p className="text-xs text-amber-600 mt-2">
          REST API base: <code className="bg-amber-100 px-1 rounded">{info.rest_api_base}</code> — all features available via REST.
        </p>
      </div>

      {/* Planned schema */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
        <div className="bg-white border rounded-lg p-4 shadow-sm">
          <h2 className="text-sm font-semibold text-gray-700 mb-3">Planned Types</h2>
          <ul className="space-y-1">
            {info.planned_types.map((t) => (
              <li key={t} className="flex items-center gap-2 text-sm text-gray-700">
                <span className="text-blue-400">▸</span>
                <code className="text-gray-800">{t}</code>
              </li>
            ))}
          </ul>
        </div>
        <div className="bg-white border rounded-lg p-4 shadow-sm">
          <h2 className="text-sm font-semibold text-gray-700 mb-3">Planned Queries</h2>
          <ul className="space-y-1">
            {info.planned_queries.map((q) => (
              <li key={q} className="text-xs font-mono text-gray-700 bg-gray-50 rounded px-2 py-1">{q}</li>
            ))}
          </ul>
        </div>
        <div className="bg-white border rounded-lg p-4 shadow-sm">
          <h2 className="text-sm font-semibold text-gray-700 mb-3">Planned Mutations</h2>
          <ul className="space-y-1">
            {info.planned_mutations.map((m) => (
              <li key={m} className="text-xs font-mono text-gray-700 bg-gray-50 rounded px-2 py-1">{m}</li>
            ))}
          </ul>
        </div>
      </div>

      {/* Integration guide */}
      <div className="bg-white border rounded-lg p-4 shadow-sm space-y-3">
        <h2 className="text-sm font-semibold text-gray-700">Enable GraphQL — Integration Steps</h2>
        <ol className="list-decimal list-inside space-y-2 text-sm text-gray-700">
          <li>
            Install: <code className="bg-gray-100 px-1 rounded text-xs">pip install strawberry-graphql[fastapi]</code>
          </li>
          <li>Define types and resolvers in <code className="bg-gray-100 px-1 rounded text-xs">backend/app/graphql/schema.py</code></li>
          <li>
            Mount in main.py: <code className="bg-gray-100 px-1 rounded text-xs">app.include_router(strawberry.fastapi.GraphQLRouter(schema), prefix="/graphql")</code>
          </li>
          <li>Reuse existing SQLAlchemy models and service functions as resolvers.</li>
          <li>Add authentication middleware: validate Bearer token from HTTP headers inside context.</li>
        </ol>
        <p className="text-xs text-gray-400">
          Until GraphQL is wired, use the REST API at{" "}
          <code className="bg-gray-100 px-1 rounded">/api/v1</code> — all ERP functionality is fully available there.
        </p>
      </div>
    </div>
  );
}
