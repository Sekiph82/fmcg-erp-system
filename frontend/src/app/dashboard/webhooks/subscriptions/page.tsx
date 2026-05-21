"use client";

import { useEffect, useState } from "react";
import {
  listSubscriptions, createSubscription, updateSubscription, deleteSubscription,
  testSubscription, Subscription, SubscriptionCreate, AuthType,
} from "@/lib/webhooks";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";

export default function SubscriptionsPage() {
  const [subs, setSubs] = useState<Subscription[]>([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [testResults, setTestResults] = useState<Record<string, string>>({});
  const [form, setForm] = useState<SubscriptionCreate>({
    name: "",
    endpoint_url: "",
    http_method: "POST",
    auth_type: "none",
    max_retries: 5,
    timeout_seconds: 30,
  });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => { load(); }, []);
  async function load() {
    try { setSubs(await listSubscriptions()); } catch {}
    setLoading(false);
  }

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault();
    setError(""); setSaving(true);
    try {
      await createSubscription(form);
      setShowForm(false);
      setForm({ name: "", endpoint_url: "", http_method: "POST", auth_type: "none", max_retries: 5, timeout_seconds: 30 });
      await load();
    } catch (err: unknown) {
      const e2 = err as { response?: { data?: { detail?: string } } };
      setError(e2?.response?.data?.detail || "Failed to create subscription");
    }
    setSaving(false);
  }

  async function handleToggle(sub: Subscription) {
    await updateSubscription(sub.id, { active_flag: !sub.active_flag });
    await load();
  }

  async function handleDelete(id: string) {
    if (!confirm("Delete this subscription?")) return;
    await deleteSubscription(id);
    await load();
  }

  async function handleTest(id: string) {
    setTestResults((prev) => ({ ...prev, [id]: "Testing..." }));
    try {
      const r = await testSubscription(id);
      setTestResults((prev) => ({
        ...prev,
        [id]: r.success ? `OK ${r.status_code}` : `FAIL: ${r.error || r.status_code}`,
      }));
    } catch {
      setTestResults((prev) => ({ ...prev, [id]: "Request failed" }));
    }
  }

  if (loading) return <div className="p-8 text-gray-500">Loading...</div>;

  return (
    <div className="max-w-5xl mx-auto py-8 px-4 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Webhook Subscriptions</h1>
          <p className="text-sm text-gray-500 mt-1">{subs.length} subscription(s)</p>
        </div>
        <Button onClick={() => setShowForm(!showForm)}>
          {showForm ? "Cancel" : "New Subscription"}
        </Button>
      </div>

      {showForm && (
        <div className="bg-white rounded-2xl border border-gray-200 p-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">New Subscription</h2>
          <form onSubmit={handleCreate} className="grid grid-cols-2 gap-4">
            <Input id="name" label="Name" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} required />
            <Input id="url" label="Endpoint URL" value={form.endpoint_url} onChange={(e) => setForm({ ...form, endpoint_url: e.target.value })} required placeholder="https://..." />
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">HTTP Method</label>
              <select className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" value={form.http_method} onChange={(e) => setForm({ ...form, http_method: e.target.value as "POST" | "PUT" })}>
                <option value="POST">POST</option>
                <option value="PUT">PUT</option>
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Auth Type</label>
              <select className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" value={form.auth_type} onChange={(e) => setForm({ ...form, auth_type: e.target.value as AuthType })}>
                <option value="none">None</option>
                <option value="bearer">Bearer Token</option>
                <option value="basic">Basic Auth</option>
                <option value="hmac">HMAC Signature</option>
              </select>
            </div>
            {form.auth_type !== "none" && (
              <Input id="secret" label="Secret / Token" value={form.secret_key || ""} onChange={(e) => setForm({ ...form, secret_key: e.target.value })} type="password" />
            )}
            {form.auth_type === "basic" && (
              <Input id="user" label="Username" value={form.auth_user || ""} onChange={(e) => setForm({ ...form, auth_user: e.target.value })} />
            )}
            <Input id="retries" label="Max Retries" type="number" value={String(form.max_retries)} onChange={(e) => setForm({ ...form, max_retries: Number(e.target.value) })} />
            <Input id="timeout" label="Timeout (s)" type="number" value={String(form.timeout_seconds)} onChange={(e) => setForm({ ...form, timeout_seconds: Number(e.target.value) })} />
            {error && <div className="col-span-2 text-sm text-red-600 bg-red-50 border border-red-200 rounded px-3 py-2">{error}</div>}
            <div className="col-span-2 flex justify-end gap-3">
              <Button variant="secondary" type="button" onClick={() => setShowForm(false)}>Cancel</Button>
              <Button type="submit" loading={saving}>Create</Button>
            </div>
          </form>
        </div>
      )}

      <div className="space-y-3">
        {subs.map((sub) => (
          <div key={sub.id} className="bg-white rounded-2xl border border-gray-200 p-5">
            <div className="flex items-start justify-between">
              <div className="space-y-1">
                <div className="flex items-center gap-2">
                  <span className="font-semibold text-gray-900">{sub.name}</span>
                  <span className={`text-xs px-2 py-0.5 rounded font-medium ${sub.active_flag ? "bg-green-100 text-green-700" : "bg-gray-100 text-gray-500"}`}>
                    {sub.active_flag ? "Active" : "Paused"}
                  </span>
                  <span className="text-xs bg-gray-100 text-gray-600 px-2 py-0.5 rounded">{sub.auth_type}</span>
                </div>
                <code className="text-xs text-gray-600">{sub.http_method} {sub.endpoint_url}</code>
                {sub.event_codes && sub.event_codes.length > 0 && (
                  <div className="flex gap-1 flex-wrap mt-1">
                    {sub.event_codes.map((c) => (
                      <span key={c} className="text-xs bg-indigo-50 text-indigo-700 px-2 py-0.5 rounded-full">{c}</span>
                    ))}
                  </div>
                )}
                <div className="text-xs text-gray-400">Retries: {sub.max_retries} · Timeout: {sub.timeout_seconds}s</div>
              </div>
              <div className="flex gap-2 flex-col items-end">
                <div className="flex gap-2">
                  <button onClick={() => handleTest(sub.id)} className="text-xs text-indigo-600 hover:underline">Test</button>
                  <button onClick={() => handleToggle(sub)} className="text-xs text-amber-600 hover:underline">
                    {sub.active_flag ? "Pause" : "Enable"}
                  </button>
                  <button onClick={() => handleDelete(sub.id)} className="text-xs text-red-600 hover:underline">Delete</button>
                </div>
                {testResults[sub.id] && (
                  <span className={`text-xs px-2 py-0.5 rounded ${testResults[sub.id].startsWith("OK") ? "bg-green-100 text-green-700" : "bg-red-100 text-red-700"}`}>
                    {testResults[sub.id]}
                  </span>
                )}
              </div>
            </div>
          </div>
        ))}
        {subs.length === 0 && (
          <div className="text-center py-12 text-gray-400">No subscriptions yet. Create one to start receiving webhooks.</div>
        )}
      </div>
    </div>
  );
}
