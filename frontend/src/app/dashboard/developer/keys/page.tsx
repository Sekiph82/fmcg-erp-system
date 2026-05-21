"use client";
import { useEffect, useState } from "react";
import { devPortalApi, ApiKeyOut, ApiKeyCreated } from "@/lib/api_portal_api";

const SCOPE_OPTS = ["read", "write", "admin", "read,write", "read,write,admin"];

interface NewKeyForm {
  key_name: string;
  scopes: string;
  rate_limit_per_min: number;
  description: string;
}

export default function ApiKeysPage() {
  const [keys, setKeys] = useState<ApiKeyOut[]>([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState<NewKeyForm>({ key_name: "", scopes: "read", rate_limit_per_min: 60, description: "" });
  const [creating, setCreating] = useState(false);
  const [newKey, setNewKey] = useState<ApiKeyCreated | null>(null);
  const [revoking, setRevoking] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  const load = () => {
    setLoading(true);
    devPortalApi.listKeys(true).then(setKeys).finally(() => setLoading(false));
  };

  useEffect(load, []);

  const create = async () => {
    setCreating(true);
    setError(null);
    try {
      const result = await devPortalApi.createKey({
        key_name: form.key_name,
        scopes: form.scopes,
        rate_limit_per_min: form.rate_limit_per_min,
        description: form.description || undefined,
      });
      setNewKey(result);
      setShowForm(false);
      load();
    } catch (e) {
      setError(String(e));
    } finally {
      setCreating(false);
    }
  };

  const revoke = async (keyId: string) => {
    if (!confirm("Revoke this API key? This cannot be undone.")) return;
    setRevoking(keyId);
    try {
      await devPortalApi.revokeKey(keyId);
      load();
    } catch (e) {
      setError(String(e));
    } finally {
      setRevoking(null);
    }
  };

  const copyKey = () => {
    if (newKey) {
      navigator.clipboard.writeText(newKey.raw_key).then(() => {
        setCopied(true);
        setTimeout(() => setCopied(false), 2000);
      });
    }
  };

  const fmtDate = (iso: string | null) => {
    if (!iso) return "—";
    return new Date(iso).toLocaleDateString("en-GB", { day: "2-digit", month: "short", year: "numeric" });
  };

  return (
    <div className="p-6 space-y-6 max-w-4xl mx-auto">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">API Keys</h1>
          <p className="text-sm text-gray-500 mt-0.5">Generate and manage your developer API keys</p>
        </div>
        <button
          onClick={() => { setShowForm(true); setNewKey(null); }}
          className="bg-blue-600 hover:bg-blue-700 text-white text-sm font-medium px-4 py-2 rounded"
        >
          + Generate Key
        </button>
      </div>

      {error && <div className="bg-red-50 border border-red-200 rounded p-3 text-sm text-red-700">{error}</div>}

      {/* Newly created key banner */}
      {newKey && (
        <div className="bg-amber-50 border border-amber-300 rounded-lg p-4 space-y-2">
          <p className="text-sm font-semibold text-amber-800">
            Key created — copy it now. It will NOT be shown again.
          </p>
          <div className="flex items-center gap-2 bg-white border border-amber-200 rounded px-3 py-2">
            <code className="font-mono text-xs text-gray-800 flex-1 break-all">{newKey.raw_key}</code>
            <button
              onClick={copyKey}
              className="text-xs text-blue-600 hover:text-blue-800 shrink-0 font-medium"
            >
              {copied ? "Copied!" : "Copy"}
            </button>
          </div>
          <button onClick={() => setNewKey(null)} className="text-xs text-gray-500 underline">Dismiss</button>
        </div>
      )}

      {/* Create form */}
      {showForm && (
        <div className="bg-white border rounded-lg p-4 shadow-sm space-y-3">
          <h2 className="text-sm font-semibold text-gray-700">New API Key</h2>
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
            <div>
              <label className="text-xs text-gray-500 block mb-1">Key Name *</label>
              <input
                type="text"
                placeholder="e.g. Production Frontend"
                value={form.key_name}
                onChange={(e) => setForm((p) => ({ ...p, key_name: e.target.value }))}
                className="w-full border border-gray-300 rounded px-3 py-1.5 text-sm focus:outline-none focus:ring-1 focus:ring-blue-500"
              />
            </div>
            <div>
              <label className="text-xs text-gray-500 block mb-1">Scopes</label>
              <select
                value={form.scopes}
                onChange={(e) => setForm((p) => ({ ...p, scopes: e.target.value }))}
                className="w-full border border-gray-300 rounded px-3 py-1.5 text-sm focus:outline-none focus:ring-1 focus:ring-blue-500"
              >
                {SCOPE_OPTS.map((s) => <option key={s} value={s}>{s}</option>)}
              </select>
            </div>
            <div>
              <label className="text-xs text-gray-500 block mb-1">Rate Limit (req/min)</label>
              <input
                type="number"
                min={1}
                max={1000}
                value={form.rate_limit_per_min}
                onChange={(e) => setForm((p) => ({ ...p, rate_limit_per_min: Number(e.target.value) }))}
                className="w-full border border-gray-300 rounded px-3 py-1.5 text-sm focus:outline-none focus:ring-1 focus:ring-blue-500"
              />
            </div>
            <div>
              <label className="text-xs text-gray-500 block mb-1">Description</label>
              <input
                type="text"
                placeholder="Optional"
                value={form.description}
                onChange={(e) => setForm((p) => ({ ...p, description: e.target.value }))}
                className="w-full border border-gray-300 rounded px-3 py-1.5 text-sm focus:outline-none focus:ring-1 focus:ring-blue-500"
              />
            </div>
          </div>
          <div className="flex gap-2">
            <button
              onClick={create}
              disabled={creating || !form.key_name}
              className="bg-blue-600 hover:bg-blue-700 text-white text-sm font-medium px-4 py-2 rounded disabled:opacity-50"
            >
              {creating ? "Generating…" : "Generate Key"}
            </button>
            <button
              onClick={() => setShowForm(false)}
              className="border border-gray-300 text-sm text-gray-600 px-4 py-2 rounded hover:bg-gray-50"
            >
              Cancel
            </button>
          </div>
        </div>
      )}

      {/* Keys table */}
      <div className="bg-white border rounded-lg shadow-sm overflow-hidden">
        <div className="px-4 py-3 border-b bg-gray-50">
          <h2 className="text-sm font-semibold text-gray-700">All API Keys</h2>
        </div>
        {loading ? (
          <div className="p-6 text-sm text-gray-400 text-center">Loading…</div>
        ) : keys.length === 0 ? (
          <div className="p-6 text-sm text-gray-400 text-center">No API keys yet.</div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-gray-50 text-xs text-gray-500">
                <tr>
                  <th className="text-left px-4 py-2">Name</th>
                  <th className="text-left px-4 py-2">Prefix</th>
                  <th className="text-left px-4 py-2">Scopes</th>
                  <th className="text-left px-4 py-2">Rate Limit</th>
                  <th className="text-left px-4 py-2">Status</th>
                  <th className="text-left px-4 py-2">Created</th>
                  <th className="text-left px-4 py-2">Last Used</th>
                  <th className="px-4 py-2"></th>
                </tr>
              </thead>
              <tbody className="divide-y">
                {keys.map((k) => (
                  <tr key={k.key_id} className={!k.is_active ? "opacity-50" : ""}>
                    <td className="px-4 py-2.5 font-medium text-gray-900">{k.key_name}</td>
                    <td className="px-4 py-2.5 font-mono text-xs text-gray-600">{k.key_prefix}…</td>
                    <td className="px-4 py-2.5">
                      {(k.scopes || "read").split(",").map((s) => (
                        <span key={s} className="inline-block bg-gray-100 text-gray-600 text-xs rounded px-1.5 py-0.5 mr-1">{s}</span>
                      ))}
                    </td>
                    <td className="px-4 py-2.5 text-gray-600">{k.rate_limit_per_min}/min</td>
                    <td className="px-4 py-2.5">
                      {k.is_active ? (
                        <span className="text-green-700 bg-green-100 text-xs rounded-full px-2 py-0.5">Active</span>
                      ) : (
                        <span className="text-gray-500 bg-gray-100 text-xs rounded-full px-2 py-0.5">Revoked</span>
                      )}
                    </td>
                    <td className="px-4 py-2.5 text-gray-500">{fmtDate(k.created_at)}</td>
                    <td className="px-4 py-2.5 text-gray-500">{fmtDate(k.last_used_at)}</td>
                    <td className="px-4 py-2.5">
                      {k.is_active && (
                        <button
                          onClick={() => revoke(k.key_id)}
                          disabled={revoking === k.key_id}
                          className="text-red-600 hover:text-red-800 text-xs disabled:opacity-50"
                        >
                          {revoking === k.key_id ? "Revoking…" : "Revoke"}
                        </button>
                      )}
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
