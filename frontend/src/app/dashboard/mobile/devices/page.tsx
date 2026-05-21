"use client";
import { useEffect, useState } from "react";
import { mobileApi, DeviceOut } from "@/lib/mobile_api";

const PLATFORM_COLOR: Record<string, string> = {
  ios: "bg-gray-100 text-gray-700",
  android: "bg-green-100 text-green-700",
  web: "bg-blue-100 text-blue-700",
};

const PLATFORM_ICON: Record<string, string> = {
  ios: "🍎",
  android: "🤖",
  web: "🌐",
};

export default function DeviceManagerPage() {
  const [devices, setDevices] = useState<DeviceOut[]>([]);
  const [loading, setLoading] = useState(true);
  const [removing, setRemoving] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [testMsg, setTestMsg] = useState({ title: "Test Push", body: "Hello from ERP!" });
  const [sending, setSending] = useState(false);
  const [sendResult, setSendResult] = useState<string | null>(null);

  const load = () => {
    setLoading(true);
    mobileApi.listDevices()
      .then(setDevices)
      .catch((e) => setError(String(e)))
      .finally(() => setLoading(false));
  };

  useEffect(load, []);

  const remove = async (tokenId: string) => {
    setRemoving(tokenId);
    try {
      await mobileApi.deactivateDevice(tokenId);
      setDevices((prev) => prev.filter((d) => d.push_token_id !== tokenId));
    } catch (e) {
      setError(String(e));
    } finally {
      setRemoving(null);
    }
  };

  const sendTest = async () => {
    setSending(true);
    setSendResult(null);
    try {
      const r = await mobileApi.sendPush({
        user_ids: ["__all__"],
        title: testMsg.title,
        body: testMsg.body,
      });
      setSendResult(`Queued for ${r.queued} device(s). ${r.note}`);
    } catch (e) {
      setSendResult(`Error: ${String(e)}`);
    } finally {
      setSending(false);
    }
  };

  const fmtDate = (iso: string) => {
    if (!iso) return "—";
    return new Date(iso).toLocaleString("en-GB", {
      day: "2-digit", month: "short", year: "numeric", hour: "2-digit", minute: "2-digit",
    });
  };

  return (
    <div className="p-6 space-y-6 max-w-3xl mx-auto">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Device Manager</h1>
          <p className="text-sm text-gray-500 mt-0.5">Manage registered push token devices</p>
        </div>
        <button onClick={load} disabled={loading}
          className="border border-gray-300 rounded px-3 py-1.5 text-sm text-gray-600 hover:bg-gray-50 disabled:opacity-50">
          Refresh
        </button>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 rounded p-3 text-sm text-red-700">{error}</div>
      )}

      {/* Device list */}
      <div className="bg-white border rounded-lg shadow-sm overflow-hidden">
        <div className="px-4 py-3 border-b bg-gray-50">
          <h2 className="text-sm font-semibold text-gray-700">
            My Registered Devices
            <span className="ml-2 font-normal text-gray-400">{devices.length} active</span>
          </h2>
        </div>

        {loading ? (
          <div className="p-6 text-sm text-gray-400 text-center">Loading…</div>
        ) : devices.length === 0 ? (
          <div className="p-6 text-sm text-gray-400 text-center">
            No devices registered. Register via{" "}
            <code className="bg-gray-100 px-1 rounded">POST /api/v1/mobile/devices</code> from your native app.
          </div>
        ) : (
          <div className="divide-y">
            {devices.map((d) => (
              <div key={d.push_token_id} className="px-4 py-3 flex items-center gap-4">
                <span className="text-2xl">{PLATFORM_ICON[d.platform] ?? "📱"}</span>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className="font-medium text-sm text-gray-900 truncate">
                      {d.device_name || d.device_id}
                    </span>
                    <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${PLATFORM_COLOR[d.platform] ?? "bg-gray-100 text-gray-600"}`}>
                      {d.platform.toUpperCase()}
                    </span>
                    {d.app_version && (
                      <span className="text-xs text-gray-400">v{d.app_version}</span>
                    )}
                  </div>
                  <p className="text-xs text-gray-400 mt-0.5 truncate">Last seen: {fmtDate(d.last_seen_at)}</p>
                  <p className="text-xs text-gray-300 font-mono truncate mt-0.5">{d.token.slice(0, 40)}…</p>
                </div>
                <button
                  onClick={() => remove(d.push_token_id)}
                  disabled={removing === d.push_token_id}
                  className="text-sm text-red-600 hover:text-red-800 disabled:opacity-50 shrink-0"
                >
                  {removing === d.push_token_id ? "Removing…" : "Remove"}
                </button>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Test push notification */}
      <div className="bg-white border rounded-lg p-4 shadow-sm space-y-3">
        <h2 className="text-sm font-semibold text-gray-700">Test Push Notification (Stub)</h2>
        <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
          <div>
            <label className="text-xs text-gray-500 block mb-1">Title</label>
            <input
              type="text"
              value={testMsg.title}
              onChange={(e) => setTestMsg((p) => ({ ...p, title: e.target.value }))}
              className="w-full border border-gray-300 rounded px-3 py-1.5 text-sm focus:outline-none focus:ring-1 focus:ring-blue-500"
            />
          </div>
          <div>
            <label className="text-xs text-gray-500 block mb-1">Body</label>
            <input
              type="text"
              value={testMsg.body}
              onChange={(e) => setTestMsg((p) => ({ ...p, body: e.target.value }))}
              className="w-full border border-gray-300 rounded px-3 py-1.5 text-sm focus:outline-none focus:ring-1 focus:ring-blue-500"
            />
          </div>
        </div>
        <button
          onClick={sendTest}
          disabled={sending}
          className="bg-blue-600 hover:bg-blue-700 text-white text-sm font-medium px-4 py-2 rounded disabled:opacity-50"
        >
          {sending ? "Sending…" : "Send Test Push"}
        </button>
        {sendResult && (
          <p className="text-xs text-gray-600 bg-gray-50 rounded p-2">{sendResult}</p>
        )}
        <p className="text-xs text-gray-400">
          Note: push delivery is a stub. Wire FCM / APNs SDK in the backend to enable real delivery.
        </p>
      </div>
    </div>
  );
}
