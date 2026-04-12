"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  integrationsApi,
  CrmCustomerMapping,
  EcommerceOrderMapping,
  MachineStatusRow,
  SyncStatus,
} from "@/lib/integrations";

const SYNC_STATUS_CFG: Record<SyncStatus, string> = {
  SYNCED: "bg-emerald-100 text-emerald-800",
  PENDING: "bg-amber-100 text-amber-800",
  FAILED: "bg-red-100 text-red-800",
  CONFLICT: "bg-orange-100 text-orange-700",
};

function SyncBadge({ status }: { status: SyncStatus }) {
  return (
    <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${SYNC_STATUS_CFG[status]}`}>
      {status}
    </span>
  );
}

function CrmSection() {
  const qc = useQueryClient();
  const [direction, setDirection] = useState<"PUSH" | "PULL">("PUSH");
  const [provider, setProvider] = useState("generic");
  const [result, setResult] = useState<{ total: number; synced: number; errors: string[] } | null>(null);

  const { data: mappings = [], isLoading } = useQuery({
    queryKey: ["crm-mappings"],
    queryFn: integrationsApi.listCrmMappings,
  });

  const syncMut = useMutation({
    mutationFn: () => integrationsApi.syncCrm({ direction, crm_provider: provider }),
    onSuccess: (data) => {
      setResult(data);
      qc.invalidateQueries({ queryKey: ["crm-mappings"] });
    },
  });

  return (
    <div className="space-y-4">
      <div className="bg-white border border-gray-200 rounded-xl p-5 space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="font-semibold text-gray-900">👥 CRM Sync</h2>
          <span className="text-xs text-gray-500">{mappings.length} mapped customers</span>
        </div>

        <div className="flex flex-wrap gap-3 items-end">
          <div>
            <label className="block text-xs text-gray-500 mb-1">Direction</label>
            <select
              value={direction}
              onChange={(e) => setDirection(e.target.value as "PUSH" | "PULL")}
              className="border border-gray-300 rounded-lg px-3 py-1.5 text-sm"
            >
              <option value="PUSH">Push to CRM</option>
              <option value="PULL">Pull from CRM</option>
            </select>
          </div>
          <div>
            <label className="block text-xs text-gray-500 mb-1">CRM Provider</label>
            <select
              value={provider}
              onChange={(e) => setProvider(e.target.value)}
              className="border border-gray-300 rounded-lg px-3 py-1.5 text-sm"
            >
              {["generic", "hubspot", "salesforce", "zoho"].map((p) => (
                <option key={p} value={p}>{p}</option>
              ))}
            </select>
          </div>
          <button
            onClick={() => syncMut.mutate()}
            disabled={syncMut.isPending}
            className="px-4 py-1.5 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700 disabled:opacity-50"
          >
            {syncMut.isPending ? "Syncing..." : "🔄 Sync Now"}
          </button>
        </div>

        {result && (
          <div className={`rounded-lg p-3 text-sm ${result.errors.length > 0 ? "bg-amber-50 border border-amber-200" : "bg-emerald-50 border border-emerald-200"}`}>
            <p className="font-medium">{result.errors.length === 0 ? "✅ Sync complete" : "⚠️ Sync with errors"}</p>
            <p className="text-xs mt-1">
              {result.synced}/{result.total} synced
              {result.errors.length > 0 && ` · ${result.errors.length} errors`}
            </p>
            {result.errors.slice(0, 3).map((e, i) => (
              <p key={i} className="text-xs text-red-600 mt-0.5">{e}</p>
            ))}
          </div>
        )}
      </div>

      {/* Mappings table */}
      <div className="bg-white border border-gray-200 rounded-xl overflow-hidden">
        <div className="px-4 py-3 border-b border-gray-100">
          <h3 className="text-sm font-semibold text-gray-700">Customer Mappings</h3>
        </div>
        {isLoading ? (
          <div className="p-6 text-center text-gray-400 text-sm">Loading...</div>
        ) : mappings.length === 0 ? (
          <div className="p-6 text-center text-gray-400 text-sm">No mappings yet — run a sync to create them</div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-gray-50">
                <tr>
                  {["External CRM ID", "Provider", "Direction", "Status", "Last Synced"].map((h) => (
                    <th key={h} className="px-4 py-2 text-left text-xs font-semibold text-gray-500">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {mappings.map((m: CrmCustomerMapping) => (
                  <tr key={m.id} className="hover:bg-gray-50">
                    <td className="px-4 py-2 text-xs font-mono text-indigo-700">{m.external_crm_id}</td>
                    <td className="px-4 py-2 text-xs text-gray-700">{m.crm_provider}</td>
                    <td className="px-4 py-2 text-xs text-gray-600">{m.sync_direction}</td>
                    <td className="px-4 py-2"><SyncBadge status={m.sync_status} /></td>
                    <td className="px-4 py-2 text-xs text-gray-500">
                      {m.last_sync_at ? new Date(m.last_sync_at).toLocaleString() : "—"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}

function EcommerceSection() {
  const qc = useQueryClient();
  const [platform, setPlatform] = useState("shopify");
  const [importResult, setImportResult] = useState<{ imported: number; mapped: number; errors: string[] } | null>(null);
  const [syncResult, setSyncResult] = useState<Record<string, unknown> | null>(null);

  const { data: orders = [], isLoading } = useQuery({
    queryKey: ["ecommerce-orders"],
    queryFn: integrationsApi.listEcommerceOrders,
  });

  const importMut = useMutation({
    mutationFn: () => integrationsApi.importOrders({ platform, limit: 50 }),
    onSuccess: (data) => {
      setImportResult(data);
      qc.invalidateQueries({ queryKey: ["ecommerce-orders"] });
    },
  });

  const syncMut = useMutation({
    mutationFn: () => integrationsApi.syncInventory(platform),
    onSuccess: (data) => setSyncResult(data),
  });

  return (
    <div className="space-y-4">
      <div className="bg-white border border-gray-200 rounded-xl p-5 space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="font-semibold text-gray-900">🛒 E-commerce Sync</h2>
          <span className="text-xs text-gray-500">{orders.length} order mappings</span>
        </div>

        <div className="flex flex-wrap gap-3 items-end">
          <div>
            <label className="block text-xs text-gray-500 mb-1">Platform</label>
            <select
              value={platform}
              onChange={(e) => setPlatform(e.target.value)}
              className="border border-gray-300 rounded-lg px-3 py-1.5 text-sm"
            >
              {["shopify", "woocommerce"].map((p) => (
                <option key={p} value={p}>{p}</option>
              ))}
            </select>
          </div>
          <button
            onClick={() => importMut.mutate()}
            disabled={importMut.isPending}
            className="px-4 py-1.5 bg-indigo-600 text-white rounded-lg text-sm font-medium hover:bg-indigo-700 disabled:opacity-50"
          >
            {importMut.isPending ? "Importing..." : "⬇️ Import Orders"}
          </button>
          <button
            onClick={() => syncMut.mutate()}
            disabled={syncMut.isPending}
            className="px-4 py-1.5 bg-emerald-600 text-white rounded-lg text-sm font-medium hover:bg-emerald-700 disabled:opacity-50"
          >
            {syncMut.isPending ? "Syncing..." : "📦 Sync Inventory"}
          </button>
        </div>

        {importResult && (
          <div className="rounded-lg p-3 text-sm bg-blue-50 border border-blue-200">
            <p className="font-medium">Import result: {importResult.imported} new orders</p>
            {importResult.errors.length > 0 && (
              <p className="text-xs text-red-600 mt-1">{importResult.errors.length} errors</p>
            )}
          </div>
        )}
        {syncResult && (
          <div className="rounded-lg p-3 text-sm bg-emerald-50 border border-emerald-200">
            <p className="font-medium">Inventory sync complete</p>
            <pre className="text-xs mt-1 text-gray-600">{JSON.stringify(syncResult, null, 2)}</pre>
          </div>
        )}
      </div>

      {/* Orders table */}
      <div className="bg-white border border-gray-200 rounded-xl overflow-hidden">
        <div className="px-4 py-3 border-b border-gray-100">
          <h3 className="text-sm font-semibold text-gray-700">Order Mappings</h3>
        </div>
        {isLoading ? (
          <div className="p-6 text-center text-gray-400 text-sm">Loading...</div>
        ) : orders.length === 0 ? (
          <div className="p-6 text-center text-gray-400 text-sm">No order mappings — import orders first</div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-gray-50">
                <tr>
                  {["Platform", "External Order", "Order No", "Status", "Last Synced"].map((h) => (
                    <th key={h} className="px-4 py-2 text-left text-xs font-semibold text-gray-500">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {orders.map((o: EcommerceOrderMapping) => (
                  <tr key={o.id} className="hover:bg-gray-50">
                    <td className="px-4 py-2 text-xs font-medium text-gray-700">{o.source_platform}</td>
                    <td className="px-4 py-2 text-xs font-mono text-indigo-700">{o.external_order_id}</td>
                    <td className="px-4 py-2 text-xs text-gray-700">{o.external_order_no ?? "—"}</td>
                    <td className="px-4 py-2"><SyncBadge status={o.sync_status} /></td>
                    <td className="px-4 py-2 text-xs text-gray-500">
                      {o.last_sync_at ? new Date(o.last_sync_at).toLocaleString() : "—"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}

function IotSection() {
  const { data: machines = [], isLoading } = useQuery({
    queryKey: ["iot-machines"],
    queryFn: integrationsApi.getMachineStatus,
    refetchInterval: 30_000,
  });

  return (
    <div className="space-y-4">
      <div className="bg-white border border-gray-200 rounded-xl overflow-hidden">
        <div className="px-4 py-3 border-b border-gray-100 flex items-center justify-between">
          <h2 className="text-sm font-semibold text-gray-700">🏭 Machine / IoT Status</h2>
          <span className="text-xs text-gray-500">{machines.length} machines (24h)</span>
        </div>
        {isLoading ? (
          <div className="p-6 text-center text-gray-400 text-sm">Loading...</div>
        ) : machines.length === 0 ? (
          <div className="p-6 text-center text-gray-400 text-sm">No machine events in the last 24h</div>
        ) : (
          <div className="divide-y divide-gray-100">
            {machines.map((m: MachineStatusRow) => (
              <div key={m.machine_id} className="px-4 py-3 flex items-center justify-between">
                <div>
                  <p className="font-medium text-gray-900 text-sm">{m.machine_name ?? m.machine_id}</p>
                  <p className="text-xs text-gray-500">ID: {m.machine_id}</p>
                </div>
                <div className="text-right">
                  <p className="text-xs font-medium text-gray-700">
                    {m.last_event_type}: <span className="text-indigo-700">{m.last_value ?? "—"}</span>
                  </p>
                  <p className="text-xs text-gray-500">
                    {m.event_count_24h} events · {new Date(m.last_seen).toLocaleString()}
                  </p>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

export default function SyncStatusPage() {
  const [activeTab, setActiveTab] = useState<"crm" | "ecommerce" | "iot">("crm");

  return (
    <div className="max-w-4xl mx-auto px-4 py-6 space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">🔄 Sync Status</h1>
        <p className="text-gray-500 text-sm mt-0.5">CRM, e-commerce, and IoT machine sync</p>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 bg-gray-100 rounded-xl p-1 w-fit">
        {(["crm", "ecommerce", "iot"] as const).map((tab) => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
              activeTab === tab
                ? "bg-white text-gray-900 shadow-sm"
                : "text-gray-600 hover:text-gray-900"
            }`}
          >
            {tab === "crm" ? "👥 CRM" : tab === "ecommerce" ? "🛒 E-commerce" : "🏭 IoT"}
          </button>
        ))}
      </div>

      {activeTab === "crm" && <CrmSection />}
      {activeTab === "ecommerce" && <EcommerceSection />}
      {activeTab === "iot" && <IotSection />}
    </div>
  );
}
