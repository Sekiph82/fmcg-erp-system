"use client";

import { useEffect, useState } from "react";
import { listInboundEndpoints, createInboundEndpoint, InboundEndpoint, AuthType } from "@/lib/webhooks";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";

export default function InboundEndpointsPage() {
  const [endpoints, setEndpoints] = useState<InboundEndpoint[]>([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [saving, setSaving] = useState(false);
  const [form, setForm] = useState({ name: "", endpoint_path: "", auth_type: "none" as AuthType, handler_module: "", description: "" });
  const [error, setError] = useState("");

  useEffect(() => { load(); }, []);
  async function load() {
    try { setEndpoints(await listInboundEndpoints()); } catch {}
    setLoading(false);
  }

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault();
    setError(""); setSaving(true);
    try {
      await createInboundEndpoint(form);
      setShowForm(false);
      await load();
    } catch (err: unknown) {
      const e2 = err as { response?: { data?: { detail?: string } } };
      setError(e2?.response?.data?.detail || "Failed to create endpoint");
    }
    setSaving(false);
  }

  const apiBase = typeof window !== "undefined" ? `${window.location.protocol}//${window.location.hostname}:8000` : "http://localhost:8000";

  if (loading) return <div className="p-8 text-gray-500">Loading...</div>;

  return (
    <div className="max-w-4xl mx-auto py-8 px-4 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Inbound Endpoints</h1>
          <p className="text-sm text-gray-500 mt-1">Receive webhooks from external systems</p>
        </div>
        <Button onClick={() => setShowForm(!showForm)}>
          {showForm ? "Cancel" : "New Endpoint"}
        </Button>
      </div>

      {showForm && (
        <div className="bg-white rounded-2xl border border-gray-200 p-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">Register Inbound Endpoint</h2>
          <form onSubmit={handleCreate} className="grid grid-cols-2 gap-4">
            <Input id="name" label="Name" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} required />
            <Input id="path" label="Path Slug" value={form.endpoint_path} onChange={(e) => setForm({ ...form, endpoint_path: e.target.value })} required placeholder="payment-callback" />
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Auth Type</label>
              <select className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" value={form.auth_type} onChange={(e) => setForm({ ...form, auth_type: e.target.value as AuthType })}>
                <option value="none">None</option>
                <option value="hmac">HMAC Signature</option>
                <option value="bearer">Bearer Token</option>
              </select>
            </div>
            <Input id="handler" label="Handler Module (tag)" value={form.handler_module} onChange={(e) => setForm({ ...form, handler_module: e.target.value })} placeholder="payment_confirmation" />
            <div className="col-span-2">
              <Input id="desc" label="Description" value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} />
            </div>
            {error && <div className="col-span-2 text-sm text-red-600 bg-red-50 border border-red-200 rounded px-3 py-2">{error}</div>}
            <div className="col-span-2 flex justify-end gap-3">
              <Button variant="secondary" type="button" onClick={() => setShowForm(false)}>Cancel</Button>
              <Button type="submit" loading={saving}>Create</Button>
            </div>
          </form>
        </div>
      )}

      <div className="space-y-3">
        {endpoints.map((ep) => (
          <div key={ep.id} className="bg-white rounded-2xl border border-gray-200 p-5">
            <div className="flex items-start justify-between">
              <div className="space-y-2">
                <div className="flex items-center gap-2">
                  <span className="font-semibold text-gray-900">{ep.name}</span>
                  <span className={`text-xs px-2 py-0.5 rounded font-medium ${ep.active_flag ? "bg-green-100 text-green-700" : "bg-gray-100 text-gray-500"}`}>
                    {ep.active_flag ? "Active" : "Inactive"}
                  </span>
                </div>
                <div className="text-xs bg-gray-900 text-green-400 font-mono px-3 py-2 rounded-lg">
                  POST {apiBase}/api/v1/webhooks/inbound/{ep.endpoint_path}
                </div>
                <div className="flex gap-4 text-xs text-gray-500">
                  <span>Auth: {ep.auth_type}</span>
                  {ep.handler_module && <span>Handler: {ep.handler_module}</span>}
                  <span>Received: {ep.receive_count}</span>
                  {ep.last_received_at && <span>Last: {new Date(ep.last_received_at).toLocaleString()}</span>}
                </div>
              </div>
            </div>
          </div>
        ))}
        {endpoints.length === 0 && (
          <div className="text-center py-12 text-gray-400">No inbound endpoints configured.</div>
        )}
      </div>
    </div>
  );
}
