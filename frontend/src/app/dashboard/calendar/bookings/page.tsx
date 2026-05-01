"use client";
import { useEffect, useState } from "react";
import { calendarApi, ResourceBooking, CalendarResource, BookingStatus } from "@/lib/calendar";

const STATUS_COLOR: Record<BookingStatus, string> = {
  reserved: "bg-yellow-100 text-yellow-700",
  confirmed: "bg-green-100 text-green-700",
  cancelled: "bg-gray-100 text-gray-500",
};

export default function BookingsPage() {
  const [bookings, setBookings] = useState<ResourceBooking[]>([]);
  const [resources, setResources] = useState<CalendarResource[]>([]);
  const [loading, setLoading] = useState(true);
  const [filterResource, setFilterResource] = useState("");
  const [filterStatus, setFilterStatus] = useState("");
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({
    resource_id: "", start_datetime: "", end_datetime: "", notes: "", booked_by: "",
  });
  const [checking, setChecking] = useState<{ available?: boolean; checked?: boolean } | null>(null);

  const load = () =>
    Promise.all([
      calendarApi.listBookings({
        resource_id: filterResource || undefined,
        status: filterStatus || undefined,
      }),
      calendarApi.listResources(),
    ]).then(([b, r]) => { setBookings(b); setResources(r); }).finally(() => setLoading(false));

  useEffect(() => { load(); }, [filterResource, filterStatus]);

  const resourceName = (id: string) => resources.find(r => r.resource_id === id)?.name ?? id;

  const checkAvail = async () => {
    if (!form.resource_id || !form.start_datetime || !form.end_datetime) return;
    const result = await calendarApi.checkAvailability({
      resource_id: form.resource_id,
      start_datetime: new Date(form.start_datetime).toISOString(),
      end_datetime: new Date(form.end_datetime).toISOString(),
    });
    setChecking({ available: result.available, checked: true });
  };

  const create = async () => {
    await calendarApi.createBooking({
      ...form,
      start_datetime: new Date(form.start_datetime).toISOString(),
      end_datetime: new Date(form.end_datetime).toISOString(),
    });
    setShowForm(false);
    setChecking(null);
    load();
  };

  const confirm = async (id: string) => {
    await calendarApi.confirmBooking(id);
    load();
  };

  const cancel = async (id: string) => {
    if (!confirm("Cancel this booking?")) return;
    await calendarApi.cancelBooking(id);
    load();
  };

  return (
    <div className="p-6 space-y-4">
      <div className="flex items-center justify-between flex-wrap gap-2">
        <h1 className="text-xl font-bold text-gray-900">Resource Bookings</h1>
        <button onClick={() => setShowForm(true)}
          className="rounded bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700">
          + New Booking
        </button>
      </div>

      <div className="flex gap-3 flex-wrap">
        <select className="border rounded px-2 py-1 text-sm" value={filterResource}
          onChange={e => setFilterResource(e.target.value)}>
          <option value="">All Resources</option>
          {resources.map(r => <option key={r.resource_id} value={r.resource_id}>{r.name}</option>)}
        </select>
        <select className="border rounded px-2 py-1 text-sm" value={filterStatus}
          onChange={e => setFilterStatus(e.target.value)}>
          <option value="">All Statuses</option>
          {(["reserved", "confirmed", "cancelled"] as BookingStatus[]).map(s => (
            <option key={s} value={s} className="capitalize">{s}</option>
          ))}
        </select>
      </div>

      {showForm && (
        <div className="bg-white border rounded-lg p-5 shadow-sm space-y-4">
          <h2 className="font-semibold text-gray-800">New Booking</h2>
          <div className="grid grid-cols-2 gap-3">
            <div className="col-span-2"><label className="text-xs text-gray-500">Resource *</label>
              <select className="w-full border rounded px-2 py-1.5 text-sm mt-1" value={form.resource_id}
                onChange={e => { setForm({ ...form, resource_id: e.target.value }); setChecking(null); }}>
                <option value="">Select resource…</option>
                {resources.filter(r => r.status === "active").map(r => (
                  <option key={r.resource_id} value={r.resource_id}>{r.name}</option>
                ))}
              </select></div>
            <div><label className="text-xs text-gray-500">Start *</label>
              <input type="datetime-local" className="w-full border rounded px-2 py-1.5 text-sm mt-1"
                value={form.start_datetime} onChange={e => { setForm({ ...form, start_datetime: e.target.value }); setChecking(null); }} /></div>
            <div><label className="text-xs text-gray-500">End *</label>
              <input type="datetime-local" className="w-full border rounded px-2 py-1.5 text-sm mt-1"
                value={form.end_datetime} onChange={e => { setForm({ ...form, end_datetime: e.target.value }); setChecking(null); }} /></div>
            <div><label className="text-xs text-gray-500">Booked By</label>
              <input className="w-full border rounded px-2 py-1.5 text-sm mt-1"
                value={form.booked_by} onChange={e => setForm({ ...form, booked_by: e.target.value })} /></div>
            <div><label className="text-xs text-gray-500">Notes</label>
              <input className="w-full border rounded px-2 py-1.5 text-sm mt-1"
                value={form.notes} onChange={e => setForm({ ...form, notes: e.target.value })} /></div>
          </div>
          {checking?.checked && (
            <p className={`text-sm font-medium ${checking.available ? "text-green-600" : "text-red-600"}`}>
              {checking.available ? "✓ Resource is available for this slot" : "✗ Conflict detected — resource not available"}
            </p>
          )}
          <div className="flex gap-2">
            <button onClick={checkAvail} className="rounded border border-blue-300 px-3 py-1.5 text-sm text-blue-600 hover:bg-blue-50">Check Availability</button>
            <button onClick={create} disabled={checking?.available === false}
              className="rounded bg-blue-600 px-4 py-1.5 text-sm text-white hover:bg-blue-700 disabled:opacity-50">Book</button>
            <button onClick={() => { setShowForm(false); setChecking(null); }}
              className="rounded border px-4 py-1.5 text-sm text-gray-600 hover:bg-gray-50">Cancel</button>
          </div>
        </div>
      )}

      {loading ? <p className="text-sm text-gray-500">Loading…</p> : (
        <div className="bg-white border rounded-lg shadow-sm overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 border-b">
              <tr>
                {["Resource", "Start", "End", "Booked By", "Notes", "Status", "Actions"].map(h => (
                  <th key={h} className="px-4 py-2 text-left text-xs font-semibold text-gray-600">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y">
              {bookings.map(b => (
                <tr key={b.booking_id} className="hover:bg-gray-50">
                  <td className="px-4 py-2 font-medium text-gray-800">{resourceName(b.resource_id)}</td>
                  <td className="px-4 py-2 text-gray-600 text-xs">{new Date(b.start_datetime).toLocaleString()}</td>
                  <td className="px-4 py-2 text-gray-600 text-xs">{new Date(b.end_datetime).toLocaleString()}</td>
                  <td className="px-4 py-2 text-gray-500 text-xs">{b.booked_by ?? "—"}</td>
                  <td className="px-4 py-2 text-gray-500 text-xs max-w-[120px] truncate">{b.notes ?? "—"}</td>
                  <td className="px-4 py-2">
                    <span className={`rounded-full px-2 py-0.5 text-xs ${STATUS_COLOR[b.status]}`}>{b.status}</span>
                  </td>
                  <td className="px-4 py-2 flex gap-2">
                    {b.status === "reserved" && (
                      <button onClick={() => confirm(b.booking_id)} className="text-xs text-green-600 hover:underline">Confirm</button>
                    )}
                    {b.status !== "cancelled" && (
                      <button onClick={() => cancel(b.booking_id)} className="text-xs text-red-500 hover:underline">Cancel</button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          {bookings.length === 0 && <p className="text-center text-gray-400 py-8 text-sm">No bookings found.</p>}
        </div>
      )}
    </div>
  );
}
