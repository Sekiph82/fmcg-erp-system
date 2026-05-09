"use client";
import { useEffect, useState } from "react";

interface RepDayLog {
  id: string;
  rep_name: string | null;
  rep_user_id: string | null;
  log_date: string;
  start_time: string | null;
  start_gps_lat: number | null;
  start_gps_lng: number | null;
  end_time: string | null;
  end_gps_lat: number | null;
  end_gps_lng: number | null;
  total_visits: number | null;
  total_km_est: number | null;
  total_sales: number | null;
  start_photo_url: string | null;
  end_photo_url: string | null;
  notes: string | null;
  created_at: string;
}

interface LogForm {
  rep_name: string;
  rep_user_id: string;
  log_date: string;
  start_gps_lat: string;
  start_gps_lng: string;
  end_gps_lat: string;
  end_gps_lng: string;
  total_visits: string;
  total_km_est: string;
  total_sales: string;
  start_photo_url: string;
  end_photo_url: string;
  notes: string;
}

const EMPTY_FORM: LogForm = {
  rep_name: "", rep_user_id: "",
  log_date: new Date().toISOString().split("T")[0],
  start_gps_lat: "", start_gps_lng: "",
  end_gps_lat: "", end_gps_lng: "",
  total_visits: "", total_km_est: "",
  total_sales: "", start_photo_url: "",
  end_photo_url: "", notes: "",
};

export default function FieldRepDayLogPage() {
  const [logs, setLogs] = useState<RepDayLog[]>([]);
  const [loading, setLoading] = useState(true);
  const [form, setForm] = useState<LogForm>(EMPTY_FORM);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [gpsLoading, setGpsLoading] = useState(false);

  const load = () => {
    setLoading(true);
    fetch("/api/v1/van-sales/rep-day-log?limit=50")
      .then((r) => r.json())
      .then(setLogs)
      .catch((e) => setError(String(e)))
      .finally(() => setLoading(false));
  };

  useEffect(load, []);

  const captureGPS = (type: "start" | "end") => {
    if (!navigator.geolocation) {
      setError("Geolocation not available in this browser.");
      return;
    }
    setGpsLoading(true);
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        setForm((p) => ({
          ...p,
          [`${type}_gps_lat`]: String(pos.coords.latitude),
          [`${type}_gps_lng`]: String(pos.coords.longitude),
        }));
        setGpsLoading(false);
      },
      (err) => {
        setError(`GPS error: ${err.message}`);
        setGpsLoading(false);
      }
    );
  };

  const submit = async () => {
    setSaving(true);
    setError(null);
    setSuccess(null);
    try {
      const body: Record<string, unknown> = {
        log_date: form.log_date,
        rep_name: form.rep_name || undefined,
        rep_user_id: form.rep_user_id || undefined,
        start_gps_lat: form.start_gps_lat ? Number(form.start_gps_lat) : undefined,
        start_gps_lng: form.start_gps_lng ? Number(form.start_gps_lng) : undefined,
        end_gps_lat: form.end_gps_lat ? Number(form.end_gps_lat) : undefined,
        end_gps_lng: form.end_gps_lng ? Number(form.end_gps_lng) : undefined,
        total_visits: form.total_visits ? Number(form.total_visits) : undefined,
        total_km_est: form.total_km_est ? Number(form.total_km_est) : undefined,
        total_sales: form.total_sales ? Number(form.total_sales) : undefined,
        start_photo_url: form.start_photo_url || undefined,
        end_photo_url: form.end_photo_url || undefined,
        notes: form.notes || undefined,
      };
      const r = await fetch("/api/v1/van-sales/rep-day-log", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      if (!r.ok) throw new Error(await r.text());
      const res = await r.json();
      setSuccess(`Log ${res.action} — ID: ${res.id.slice(0, 8)}`);
      setForm(EMPTY_FORM);
      load();
    } catch (e) {
      setError(String(e));
    } finally {
      setSaving(false);
    }
  };

  const fmtDt = (iso: string | null) =>
    iso ? new Date(iso).toLocaleString("en-GB", { hour: "2-digit", minute: "2-digit" }) : "—";

  return (
    <div className="p-6 space-y-6 max-w-4xl mx-auto">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Field Rep Daily Log</h1>
        <p className="text-sm text-gray-500 mt-0.5">GPS check-in/out, daily summary, photo capture</p>
      </div>

      {error && <div className="bg-red-50 border border-red-200 rounded p-3 text-sm text-red-700">{error}</div>}
      {success && <div className="bg-green-50 border border-green-200 rounded p-3 text-sm text-green-700">{success}</div>}

      {/* Log form */}
      <div className="bg-white border rounded-lg p-5 shadow-sm space-y-4">
        <h2 className="text-sm font-semibold text-gray-700">Submit / Update Day Log</h2>

        <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
          <div>
            <label className="text-xs text-gray-500 block mb-1">Rep Name</label>
            <input type="text" value={form.rep_name}
              onChange={(e) => setForm((p) => ({ ...p, rep_name: e.target.value }))}
              placeholder="e.g. John Kamau"
              className="w-full border border-gray-300 rounded px-3 py-1.5 text-sm focus:outline-none focus:ring-1 focus:ring-blue-500" />
          </div>
          <div>
            <label className="text-xs text-gray-500 block mb-1">Date *</label>
            <input type="date" value={form.log_date}
              onChange={(e) => setForm((p) => ({ ...p, log_date: e.target.value }))}
              className="w-full border border-gray-300 rounded px-3 py-1.5 text-sm focus:outline-none focus:ring-1 focus:ring-blue-500" />
          </div>
          <div>
            <label className="text-xs text-gray-500 block mb-1">Total Visits</label>
            <input type="number" min={0} value={form.total_visits}
              onChange={(e) => setForm((p) => ({ ...p, total_visits: e.target.value }))}
              placeholder="e.g. 12"
              className="w-full border border-gray-300 rounded px-3 py-1.5 text-sm focus:outline-none focus:ring-1 focus:ring-blue-500" />
          </div>
        </div>

        {/* GPS capture */}
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <div className="bg-blue-50 rounded-lg p-3 space-y-2">
            <div className="flex items-center justify-between">
              <p className="text-xs font-medium text-blue-700">Start Location</p>
              <button onClick={() => captureGPS("start")} disabled={gpsLoading}
                className="text-xs text-blue-600 hover:text-blue-800 underline disabled:opacity-50">
                {gpsLoading ? "Locating…" : "Capture GPS"}
              </button>
            </div>
            <div className="grid grid-cols-2 gap-2">
              <input type="number" step="any" value={form.start_gps_lat}
                onChange={(e) => setForm((p) => ({ ...p, start_gps_lat: e.target.value }))}
                placeholder="Latitude"
                className="border border-blue-200 rounded px-2 py-1 text-xs focus:outline-none" />
              <input type="number" step="any" value={form.start_gps_lng}
                onChange={(e) => setForm((p) => ({ ...p, start_gps_lng: e.target.value }))}
                placeholder="Longitude"
                className="border border-blue-200 rounded px-2 py-1 text-xs focus:outline-none" />
            </div>
            <input type="text" value={form.start_photo_url}
              onChange={(e) => setForm((p) => ({ ...p, start_photo_url: e.target.value }))}
              placeholder="Start photo URL"
              className="w-full border border-blue-200 rounded px-2 py-1 text-xs focus:outline-none" />
          </div>

          <div className="bg-green-50 rounded-lg p-3 space-y-2">
            <div className="flex items-center justify-between">
              <p className="text-xs font-medium text-green-700">End Location</p>
              <button onClick={() => captureGPS("end")} disabled={gpsLoading}
                className="text-xs text-green-600 hover:text-green-800 underline disabled:opacity-50">
                {gpsLoading ? "Locating…" : "Capture GPS"}
              </button>
            </div>
            <div className="grid grid-cols-2 gap-2">
              <input type="number" step="any" value={form.end_gps_lat}
                onChange={(e) => setForm((p) => ({ ...p, end_gps_lat: e.target.value }))}
                placeholder="Latitude"
                className="border border-green-200 rounded px-2 py-1 text-xs focus:outline-none" />
              <input type="number" step="any" value={form.end_gps_lng}
                onChange={(e) => setForm((p) => ({ ...p, end_gps_lng: e.target.value }))}
                placeholder="Longitude"
                className="border border-green-200 rounded px-2 py-1 text-xs focus:outline-none" />
            </div>
            <input type="text" value={form.end_photo_url}
              onChange={(e) => setForm((p) => ({ ...p, end_photo_url: e.target.value }))}
              placeholder="End photo URL"
              className="w-full border border-green-200 rounded px-2 py-1 text-xs focus:outline-none" />
          </div>
        </div>

        <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
          <div>
            <label className="text-xs text-gray-500 block mb-1">Total KM (est.)</label>
            <input type="number" step="0.1" value={form.total_km_est}
              onChange={(e) => setForm((p) => ({ ...p, total_km_est: e.target.value }))}
              placeholder="e.g. 85.5"
              className="w-full border border-gray-300 rounded px-3 py-1.5 text-sm focus:outline-none focus:ring-1 focus:ring-blue-500" />
          </div>
          <div>
            <label className="text-xs text-gray-500 block mb-1">Total Sales (KES)</label>
            <input type="number" step="0.01" value={form.total_sales}
              onChange={(e) => setForm((p) => ({ ...p, total_sales: e.target.value }))}
              placeholder="e.g. 145000"
              className="w-full border border-gray-300 rounded px-3 py-1.5 text-sm focus:outline-none focus:ring-1 focus:ring-blue-500" />
          </div>
          <div>
            <label className="text-xs text-gray-500 block mb-1">Notes</label>
            <input type="text" value={form.notes}
              onChange={(e) => setForm((p) => ({ ...p, notes: e.target.value }))}
              placeholder="Optional notes"
              className="w-full border border-gray-300 rounded px-3 py-1.5 text-sm focus:outline-none focus:ring-1 focus:ring-blue-500" />
          </div>
        </div>

        <button onClick={submit} disabled={saving || !form.log_date}
          className="bg-blue-600 hover:bg-blue-700 text-white text-sm font-medium px-5 py-2 rounded disabled:opacity-50">
          {saving ? "Submitting…" : "Submit Day Log"}
        </button>
      </div>

      {/* Log history */}
      <div className="bg-white border rounded-lg shadow-sm overflow-hidden">
        <div className="px-4 py-3 border-b bg-gray-50 flex items-center justify-between">
          <h2 className="text-sm font-semibold text-gray-700">
            Recent Day Logs
            <span className="ml-2 font-normal text-gray-400">{logs.length} records</span>
          </h2>
          <button onClick={load} disabled={loading}
            className="text-xs text-blue-600 hover:text-blue-800 disabled:opacity-50">Refresh</button>
        </div>

        {loading ? (
          <div className="p-6 text-sm text-gray-400 text-center">Loading…</div>
        ) : logs.length === 0 ? (
          <div className="p-6 text-sm text-gray-400 text-center">No day logs yet.</div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-gray-50 text-xs text-gray-500">
                <tr>
                  <th className="text-left px-4 py-2">Date</th>
                  <th className="text-left px-4 py-2">Rep</th>
                  <th className="text-left px-4 py-2">Start</th>
                  <th className="text-left px-4 py-2">End</th>
                  <th className="text-left px-4 py-2">Visits</th>
                  <th className="text-left px-4 py-2">KM</th>
                  <th className="text-left px-4 py-2">Sales (KES)</th>
                </tr>
              </thead>
              <tbody className="divide-y">
                {logs.map((lg) => (
                  <tr key={lg.id} className="hover:bg-gray-50">
                    <td className="px-4 py-2.5 font-medium text-gray-800">{lg.log_date}</td>
                    <td className="px-4 py-2.5 text-gray-600">{lg.rep_name ?? "—"}</td>
                    <td className="px-4 py-2.5 text-xs text-gray-500">
                      {fmtDt(lg.start_time)}
                      {lg.start_gps_lat && (
                        <a href={`https://maps.google.com/?q=${lg.start_gps_lat},${lg.start_gps_lng}`}
                          target="_blank" rel="noopener noreferrer"
                          className="ml-1 text-blue-400 hover:text-blue-600">📍</a>
                      )}
                    </td>
                    <td className="px-4 py-2.5 text-xs text-gray-500">
                      {fmtDt(lg.end_time)}
                      {lg.end_gps_lat && (
                        <a href={`https://maps.google.com/?q=${lg.end_gps_lat},${lg.end_gps_lng}`}
                          target="_blank" rel="noopener noreferrer"
                          className="ml-1 text-blue-400 hover:text-blue-600">📍</a>
                      )}
                    </td>
                    <td className="px-4 py-2.5 text-gray-700">{lg.total_visits ?? "—"}</td>
                    <td className="px-4 py-2.5 text-gray-600">{lg.total_km_est?.toFixed(1) ?? "—"}</td>
                    <td className="px-4 py-2.5 text-gray-700 font-medium">
                      {lg.total_sales ? lg.total_sales.toLocaleString() : "—"}
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
