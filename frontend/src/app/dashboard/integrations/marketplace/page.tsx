"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import {
  integrationsApi,
  MarketplaceCategory,
  MarketplaceConnector,
  PluginLifecycleEvent,
  PluginLifecycleAction,
} from "@/lib/integrations";

const STATUS_COLOR: Record<string, string> = {
  active: "bg-green-100 text-green-700",
  beta: "bg-amber-100 text-amber-700",
  coming_soon: "bg-gray-100 text-gray-500",
  deprecated: "bg-red-100 text-red-600",
};

const INSTALL_COLOR: Record<string, string> = {
  installed: "bg-green-100 text-green-700",
  disabled: "bg-gray-100 text-gray-600",
  update_available: "bg-blue-100 text-blue-700",
  uninstalled: "bg-gray-100 text-gray-500",
  error: "bg-red-100 text-red-700",
};

const AUTH_COLOR: Record<string, string> = {
  API_KEY: "bg-blue-50 text-blue-600",
  OAUTH2: "bg-purple-50 text-purple-600",
  BASIC: "bg-gray-50 text-gray-600",
  WEBHOOK: "bg-orange-50 text-orange-600",
};

export default function IntegrationMarketplacePage() {
  const [connectors, setConnectors] = useState<MarketplaceConnector[]>([]);
  const [categories, setCategories] = useState<MarketplaceCategory[]>([]);
  const [events, setEvents] = useState<PluginLifecycleEvent[]>([]);
  const [loading, setLoading] = useState(true);
  const [filterCat, setFilterCat] = useState("");
  const [filterStatus, setFilterStatus] = useState("");
  const [tenantKey, setTenantKey] = useState("default");
  const [search, setSearch] = useState("");
  const [busy, setBusy] = useState<string | null>(null);
  const [testResult, setTestResult] = useState<Record<string, { result: string; message: string }>>({});
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [items, cats, audit] = await Promise.all([
        integrationsApi.listMarketplace({
          category: filterCat || undefined,
          status: filterStatus || undefined,
          tenant_key: tenantKey,
        }),
        integrationsApi.listMarketplaceCategories(),
        integrationsApi.listPluginEvents({ tenant_key: tenantKey, limit: 12 }),
      ]);
      setConnectors(items);
      setCategories(cats);
      setEvents(audit);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setLoading(false);
    }
  }, [filterCat, filterStatus, tenantKey]);

  useEffect(() => { load(); }, [load]);

  const runAction = async (connector: MarketplaceConnector, action: "install" | PluginLifecycleAction) => {
    setBusy(`${connector.connector_code}:${action}`);
    setError(null);
    try {
      if (action === "install") {
        await integrationsApi.installPlugin(connector.connector_code, {
          tenant_key: tenantKey,
          environment: "sandbox",
          config: {},
          notes: "Installed from marketplace",
        });
      } else {
        await integrationsApi.transitionPlugin(connector.connector_code, action, tenantKey);
      }
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(null);
    }
  };

  const handleTest = async (code: string) => {
    setBusy(`${code}:test`);
    try {
      const result = await integrationsApi.testMarketplaceConnector(code, tenantKey);
      setTestResult((prev) => ({ ...prev, [code]: result }));
    } catch (e) {
      setTestResult((prev) => ({
        ...prev,
        [code]: { result: "ERROR", message: e instanceof Error ? e.message : String(e) },
      }));
    } finally {
      setBusy(null);
    }
  };

  const filtered = connectors.filter((connector) => {
    const haystack = `${connector.name} ${connector.category} ${connector.connector_code}`.toLowerCase();
    return !search || haystack.includes(search.toLowerCase());
  });

  const grouped = filtered.reduce<Record<string, MarketplaceConnector[]>>((acc, connector) => {
    (acc[connector.category] = acc[connector.category] || []).push(connector);
    return acc;
  }, {});

  const installedCount = connectors.filter((c) => c.installation_status === "installed" || c.installation_status === "update_available").length;
  const disabledCount = connectors.filter((c) => c.installation_status === "disabled").length;
  const installableCount = connectors.filter((c) => c.status === "active" || c.status === "beta").length;

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Integration Marketplace</h1>
          <p className="text-sm text-gray-500 mt-1">Governed connector catalog, tenant install state, lifecycle audit, and dependency controls</p>
        </div>
        <Link href="/dashboard/integrations" className="border rounded-lg px-3 py-2 text-sm text-gray-600 hover:bg-gray-50">
          Back to Overview
        </Link>
      </div>

      {error && <div className="bg-red-50 border border-red-200 rounded-lg p-3 text-sm text-red-700">{error}</div>}

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {[
          ["Installable", installableCount, "Active or beta connectors"],
          ["Installed", installedCount, `Tenant ${tenantKey}`],
          ["Disabled", disabledCount, "Installed but inactive"],
          ["Audit Events", events.length, "Latest lifecycle changes"],
        ].map(([label, value, sub]) => (
          <div key={label as string} className="bg-white rounded-lg border p-4">
            <p className="text-xs text-gray-500">{label}</p>
            <p className="text-xl font-bold text-gray-900 mt-1">{value}</p>
            <p className="text-xs text-gray-400 mt-0.5">{sub}</p>
          </div>
        ))}
      </div>

      <div className="bg-white rounded-lg border p-4 flex flex-wrap items-end gap-3">
        <div>
          <label className="block text-xs text-gray-500 mb-1">Tenant</label>
          <input value={tenantKey} onChange={(e) => setTenantKey(e.target.value || "default")} className="border rounded-lg px-3 py-2 text-sm w-36" />
        </div>
        <div>
          <label className="block text-xs text-gray-500 mb-1">Search</label>
          <input value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Connector name" className="border rounded-lg px-3 py-2 text-sm w-56" />
        </div>
        <div>
          <label className="block text-xs text-gray-500 mb-1">Status</label>
          <select value={filterStatus} onChange={(e) => setFilterStatus(e.target.value)} className="border rounded-lg px-3 py-2 text-sm">
            <option value="">All statuses</option>
            <option value="active">Active</option>
            <option value="beta">Beta</option>
            <option value="coming_soon">Coming Soon</option>
            <option value="deprecated">Deprecated</option>
          </select>
        </div>
        <button onClick={load} disabled={loading} className="px-4 py-2 text-sm bg-gray-900 text-white rounded-lg hover:bg-gray-800 disabled:opacity-50">
          {loading ? "Loading..." : "Refresh"}
        </button>
      </div>

      <div className="flex flex-wrap gap-2">
        <button
          onClick={() => setFilterCat("")}
          className={`text-xs rounded-full border px-3 py-1.5 ${!filterCat ? "bg-blue-600 text-white border-blue-600" : "bg-gray-50 text-gray-600 border-gray-300 hover:bg-gray-100"}`}
        >
          All ({connectors.length})
        </button>
        {categories.map((cat) => (
          <button
            key={cat.category}
            onClick={() => setFilterCat(filterCat === cat.category ? "" : cat.category)}
            className={`text-xs rounded-full border px-3 py-1.5 ${filterCat === cat.category ? "bg-blue-600 text-white border-blue-600" : "bg-gray-50 text-gray-600 border-gray-300 hover:bg-gray-100"}`}
          >
            {cat.category} ({cat.total})
          </button>
        ))}
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-4 gap-6">
        <div className="xl:col-span-3 space-y-8">
          {loading ? (
            <p className="text-gray-400 text-sm">Loading marketplace...</p>
          ) : Object.entries(grouped).length === 0 ? (
            <div className="bg-white rounded-lg border p-8 text-center text-gray-500">No connectors match the current filters.</div>
          ) : (
            Object.entries(grouped).sort(([a], [b]) => a.localeCompare(b)).map(([category, items]) => (
              <div key={category}>
                <h2 className="text-sm font-bold text-gray-500 uppercase mb-3">{category}</h2>
                <div className="grid grid-cols-1 md:grid-cols-2 2xl:grid-cols-3 gap-4">
                  {items.map((connector) => {
                    const result = testResult[connector.connector_code];
                    const installable = connector.status === "active" || connector.status === "beta";
                    const installed = connector.installation_status === "installed" || connector.installation_status === "update_available";
                    const disabled = connector.installation_status === "disabled";
                    return (
                      <div key={connector.connector_id} className={`bg-white border rounded-lg p-4 space-y-3 ${connector.status === "coming_soon" ? "opacity-70" : ""}`}>
                        <div className="flex items-start justify-between gap-3">
                          <div className="flex items-center gap-2">
                            <span className="text-2xl">{connector.icon_emoji ?? ">"}</span>
                            <div>
                              <p className="font-semibold text-gray-900 text-sm">{connector.name}</p>
                              <p className="text-xs text-gray-500">{connector.connector_code} · v{connector.current_version}</p>
                            </div>
                          </div>
                          <div className="flex flex-col items-end gap-1">
                            <span className={`text-xs rounded-full px-2 py-0.5 ${STATUS_COLOR[connector.status]}`}>{connector.status.replace("_", " ")}</span>
                            {connector.installation_status && (
                              <span className={`text-xs rounded-full px-2 py-0.5 ${INSTALL_COLOR[connector.installation_status]}`}>
                                {connector.installation_status.replace("_", " ")}
                              </span>
                            )}
                          </div>
                        </div>

                        <div className="flex flex-wrap gap-1">
                          {connector.auth_type && <span className={`text-xs rounded px-1.5 py-0.5 font-mono ${AUTH_COLOR[connector.auth_type] ?? "bg-gray-50 text-gray-500"}`}>{connector.auth_type}</span>}
                          {connector.required_permissions.map((permission) => (
                            <span key={permission} className="text-xs rounded px-1.5 py-0.5 bg-gray-50 text-gray-500">{permission}</span>
                          ))}
                        </div>

                        {connector.dependency_codes.length > 0 && (
                          <p className="text-xs text-gray-500">Requires: {connector.dependency_codes.join(", ")}</p>
                        )}
                        {connector.config_guide && <p className="text-xs text-gray-500 leading-relaxed">{connector.config_guide}</p>}

                        {result && (
                          <div className={`text-xs rounded p-2 ${result.result === "OK" ? "bg-green-50 text-green-700" : result.result === "NOT_AVAILABLE" ? "bg-gray-50 text-gray-500" : "bg-amber-50 text-amber-700"}`}>
                            <span className="font-medium">{result.result}:</span> {result.message}
                          </div>
                        )}

                        <div className="flex flex-wrap gap-2">
                          {!installed && !disabled && installable && (
                            <button onClick={() => runAction(connector, "install")} disabled={busy === `${connector.connector_code}:install`} className="text-xs border rounded px-3 py-1.5 text-green-700 border-green-300 bg-green-50 hover:bg-green-100 disabled:opacity-50">Install</button>
                          )}
                          {disabled && (
                            <button onClick={() => runAction(connector, "enable")} disabled={busy === `${connector.connector_code}:enable`} className="text-xs border rounded px-3 py-1.5 text-green-700 border-green-300 bg-green-50 hover:bg-green-100 disabled:opacity-50">Enable</button>
                          )}
                          {installed && (
                            <button onClick={() => runAction(connector, "disable")} disabled={busy === `${connector.connector_code}:disable`} className="text-xs border rounded px-3 py-1.5 text-gray-700 border-gray-300 hover:bg-gray-50 disabled:opacity-50">Disable</button>
                          )}
                          {(installed || disabled) && (
                            <button onClick={() => runAction(connector, "uninstall")} disabled={busy === `${connector.connector_code}:uninstall`} className="text-xs border rounded px-3 py-1.5 text-red-700 border-red-300 bg-red-50 hover:bg-red-100 disabled:opacity-50">Uninstall</button>
                          )}
                          {connector.status !== "coming_soon" && (
                            <button onClick={() => handleTest(connector.connector_code)} disabled={busy === `${connector.connector_code}:test`} className="text-xs border rounded px-3 py-1.5 text-gray-600 border-gray-300 hover:bg-gray-50 disabled:opacity-50">Test</button>
                          )}
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            ))
          )}
        </div>

        <div className="bg-white rounded-lg border overflow-hidden self-start">
          <div className="px-4 py-3 border-b">
            <h2 className="font-semibold text-gray-800">Lifecycle Audit</h2>
          </div>
          <div className="divide-y divide-gray-100">
            {events.map((event) => (
              <div key={event.id} className="p-4">
                <p className="text-sm font-medium text-gray-900">{event.connector_code}</p>
                <p className="text-xs text-gray-500 mt-0.5">{event.action} · {event.previous_status || "-"} to {event.new_status || "-"}</p>
                {event.message && <p className="text-xs text-gray-600 mt-2">{event.message}</p>}
              </div>
            ))}
            {!loading && events.length === 0 && (
              <p className="p-4 text-sm text-gray-500">No lifecycle events yet.</p>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
