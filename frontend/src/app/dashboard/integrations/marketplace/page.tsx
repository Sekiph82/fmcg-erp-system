"use client";
import { useEffect, useState } from "react";
import Link from "next/link";

interface Connector {
  connector_id: string;
  connector_code: string;
  name: string;
  category: string;
  icon_emoji: string | null;
  auth_type: string | null;
  status: "active" | "beta" | "coming_soon" | "deprecated";
  is_configured: boolean;
  config_guide: string | null;
  docs_url: string | null;
}

interface Category {
  category: string;
  total: number;
  active: number;
}

const STATUS_COLOR: Record<string, string> = {
  active: "bg-green-100 text-green-700",
  beta: "bg-amber-100 text-amber-700",
  coming_soon: "bg-gray-100 text-gray-500",
  deprecated: "bg-red-100 text-red-600",
};

const STATUS_LABEL: Record<string, string> = {
  active: "Active",
  beta: "Beta",
  coming_soon: "Coming Soon",
  deprecated: "Deprecated",
};

const AUTH_COLOR: Record<string, string> = {
  API_KEY: "bg-blue-50 text-blue-600",
  OAUTH2: "bg-purple-50 text-purple-600",
  BASIC: "bg-gray-50 text-gray-600",
  WEBHOOK: "bg-orange-50 text-orange-600",
};

async function fetchConnectors(category?: string, status?: string): Promise<Connector[]> {
  const p = new URLSearchParams();
  if (category) p.set("category", category);
  if (status) p.set("status", status);
  const r = await fetch(`/api/v1/integrations/marketplace?${p}`);
  if (!r.ok) throw new Error(await r.text());
  return r.json();
}

async function fetchCategories(): Promise<Category[]> {
  const r = await fetch("/api/v1/integrations/marketplace/categories");
  if (!r.ok) return [];
  return r.json();
}

async function testConnector(code: string): Promise<{ result: string; message: string }> {
  const r = await fetch(`/api/v1/integrations/marketplace/${code}/test`, { method: "POST" });
  if (!r.ok) throw new Error(await r.text());
  return r.json();
}

export default function IntegrationMarketplacePage() {
  const [connectors, setConnectors] = useState<Connector[]>([]);
  const [categories, setCategories] = useState<Category[]>([]);
  const [loading, setLoading] = useState(true);
  const [filterCat, setFilterCat] = useState("");
  const [filterStatus, setFilterStatus] = useState("");
  const [search, setSearch] = useState("");
  const [testResult, setTestResult] = useState<Record<string, { result: string; message: string }>>({});
  const [testing, setTesting] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = () => {
    setLoading(true);
    Promise.all([fetchConnectors(filterCat || undefined, filterStatus || undefined), fetchCategories()])
      .then(([c, cats]) => { setConnectors(c); setCategories(cats); })
      .catch((e) => setError(String(e)))
      .finally(() => setLoading(false));
  };

  useEffect(load, [filterCat, filterStatus]);

  const handleTest = async (code: string) => {
    setTesting(code);
    try {
      const r = await testConnector(code);
      setTestResult((p) => ({ ...p, [code]: r }));
    } catch (e) {
      setTestResult((p) => ({ ...p, [code]: { result: "ERROR", message: String(e) } }));
    } finally {
      setTesting(null);
    }
  };

  const filtered = connectors.filter((c) =>
    !search || c.name.toLowerCase().includes(search.toLowerCase()) || c.category.toLowerCase().includes(search.toLowerCase())
  );

  const grouped = filtered.reduce<Record<string, Connector[]>>((acc, c) => {
    (acc[c.category] = acc[c.category] || []).push(c);
    return acc;
  }, {});

  const configuredCount = connectors.filter((c) => c.is_configured).length;
  const activeCount = connectors.filter((c) => c.status === "active").length;

  return (
    <div className="p-6 space-y-6 max-w-6xl mx-auto">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Integration Marketplace</h1>
          <p className="text-sm text-gray-500 mt-0.5">
            All available connectors — {configuredCount} configured · {activeCount} active
          </p>
        </div>
        <Link href="/dashboard/integrations"
          className="border border-gray-300 rounded px-3 py-1.5 text-sm text-gray-600 hover:bg-gray-50">
          ← Back to Overview
        </Link>
      </div>

      {error && <div className="bg-red-50 border border-red-200 rounded p-3 text-sm text-red-700">{error}</div>}

      {/* Category summary */}
      {categories.length > 0 && (
        <div className="flex flex-wrap gap-2">
          <button
            onClick={() => setFilterCat("")}
            className={`text-xs rounded-full border px-3 py-1.5 transition-colors ${!filterCat ? "bg-blue-600 text-white border-blue-600" : "bg-gray-50 text-gray-600 border-gray-300 hover:bg-gray-100"}`}
          >
            All ({connectors.length})
          </button>
          {categories.map((cat) => (
            <button
              key={cat.category}
              onClick={() => setFilterCat(filterCat === cat.category ? "" : cat.category)}
              className={`text-xs rounded-full border px-3 py-1.5 transition-colors ${filterCat === cat.category ? "bg-blue-600 text-white border-blue-600" : "bg-gray-50 text-gray-600 border-gray-300 hover:bg-gray-100"}`}
            >
              {cat.category} ({cat.total})
            </button>
          ))}
        </div>
      )}

      {/* Filters row */}
      <div className="flex flex-wrap gap-3 items-center">
        <input
          type="text"
          placeholder="Search connectors…"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="border border-gray-300 rounded px-3 py-1.5 text-sm focus:outline-none focus:ring-1 focus:ring-blue-500 w-56"
        />
        <select
          value={filterStatus}
          onChange={(e) => setFilterStatus(e.target.value)}
          className="border border-gray-300 rounded px-3 py-1.5 text-sm focus:outline-none"
        >
          <option value="">All statuses</option>
          <option value="active">Active</option>
          <option value="beta">Beta</option>
          <option value="coming_soon">Coming Soon</option>
        </select>
      </div>

      {loading ? (
        <p className="text-gray-400 text-sm">Loading marketplace…</p>
      ) : (
        <div className="space-y-8">
          {Object.entries(grouped).sort(([a], [b]) => a.localeCompare(b)).map(([cat, items]) => (
            <div key={cat}>
              <h2 className="text-sm font-bold text-gray-500 uppercase tracking-wide mb-3">{cat}</h2>
              <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
                {items.map((c) => {
                  const tr = testResult[c.connector_code];
                  return (
                    <div
                      key={c.connector_id}
                      className={`bg-white border rounded-xl p-4 shadow-sm space-y-3 ${c.status === "coming_soon" ? "opacity-70" : ""} ${c.is_configured ? "border-green-300 bg-green-50/30" : "border-gray-200"}`}
                    >
                      {/* Header */}
                      <div className="flex items-start justify-between">
                        <div className="flex items-center gap-2">
                          <span className="text-2xl">{c.icon_emoji ?? "🔌"}</span>
                          <div>
                            <p className="font-semibold text-gray-900 text-sm leading-snug">{c.name}</p>
                            {c.auth_type && (
                              <span className={`text-xs rounded px-1.5 py-0.5 font-mono ${AUTH_COLOR[c.auth_type] ?? "bg-gray-50 text-gray-500"}`}>
                                {c.auth_type}
                              </span>
                            )}
                          </div>
                        </div>
                        <div className="flex flex-col items-end gap-1">
                          <span className={`text-xs rounded-full px-2 py-0.5 font-medium ${STATUS_COLOR[c.status]}`}>
                            {STATUS_LABEL[c.status]}
                          </span>
                          {c.is_configured && (
                            <span className="text-xs text-green-600 font-medium">✓ Configured</span>
                          )}
                        </div>
                      </div>

                      {/* Config guide */}
                      {c.config_guide && (
                        <p className="text-xs text-gray-500 leading-relaxed">{c.config_guide}</p>
                      )}

                      {/* Test result */}
                      {tr && (
                        <div className={`text-xs rounded p-2 ${tr.result === "OK" ? "bg-green-50 text-green-700" : tr.result === "NOT_AVAILABLE" ? "bg-gray-50 text-gray-500" : "bg-amber-50 text-amber-700"}`}>
                          <span className="font-medium">{tr.result}:</span> {tr.message}
                        </div>
                      )}

                      {/* Actions */}
                      <div className="flex gap-2">
                        {c.status !== "coming_soon" && (
                          <button
                            onClick={() => handleTest(c.connector_code)}
                            disabled={testing === c.connector_code}
                            className="flex-1 text-xs border border-gray-300 rounded py-1 text-gray-600 hover:bg-gray-50 disabled:opacity-50"
                          >
                            {testing === c.connector_code ? "Testing…" : "Test"}
                          </button>
                        )}
                        <Link
                          href="/dashboard/integrations"
                          className="flex-1 text-xs border border-blue-300 bg-blue-50 rounded py-1 text-blue-700 hover:bg-blue-100 text-center"
                        >
                          Configure
                        </Link>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
