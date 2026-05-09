"use client";
import { useEffect, useState } from "react";

interface Shift {
  shift_id: string;
  user_id: string;
  user_name: string | null;
  department: string | null;
  shift_date: string;
  shift_type: string;
  shift_start: string;
  shift_end: string;
  location: string | null;
  approved_flag: boolean;
  approved_by: string | null;
  notes: string | null;
  created_at: string;
}

interface ShiftForm {
  user_id: string;
  user_name: string;
  department: string;
  shift_date: string;
  shift_type: string;
  shift_start: string;
  shift_end: string;
  location: string;
  notes: string;
}

const SHIFT_PRESETS: Record<string, { start: string; end: string; label: string }> = {
  morning: { start: "06:00", end: "14:00", label: "Morning (06:00–14:00)" },
  afternoon: { start: "14:00", end: "22:00", label: "Afternoon (14:00–22:00)" },
  night: { start: "22:00", end: "06:00", label: "Night (22:00–06:00)" },
  custom: { start: "", end: "", label: "Custom" },
};

const SHIFT_COLOR: Record<string, string> = {
  morning: "bg-amber-100 text-amber-700",
  afternoon: "bg-blue-100 text-blue-700",
  night: "bg-purple-100 text-purple-700",
  custom: "bg-gray-100 text-gray-600",
};

const EMPTY_FORM: ShiftForm = {
  user_id: "", user_name: "", department: "",
  shift_date: new Date().toISOString().split("T")[0],
  shift_type: "morning", shift_start: "06:00", shift_end: "14:00",
  location: "", notes: "",
};

export default function ShiftSchedulePage() {
  const [shifts, setShifts] = useState<Shift[]>([]);
  const [loading, setLoading] = useState(true);
  const [form, setForm] = useState<ShiftForm>(EMPTY_FORM);
  const [saving, setSaving] = useState(false);
  const [filterDept, setFilterDept] = useState("");
  const [filterDate, setFilterDate] = useState("");
  const [error, setError] = useState<string | null>(null);

  const buildQuery = () => {
    const p = new URLSearchParams({ limit: "200" });
    if (filterDept) p.set("department", filterDept);
    if (filterDate) p.set("shift_date", filterDate);
    return p.toString();
  };

  const load = () => {
    setLoading(true);
    fetch(`/api/v1/calendar/shifts?${buildQuery()}`)
      .then((r) => r.json())
      .then(setShifts)
      .catch((e) => setError(String(e)))
      .finally(() => setLoading(false));
  };

  useEffect(load, [filterDept, filterDate]);

  const handleTypeChange = (type: string) => {
    const preset = SHIFT_PRESETS[type];
    setForm((p) => ({
      ...p,
      shift_type: type,
      shift_start: preset.start || p.shift_start,
      shift_end: preset.end || p.shift_end,
    }));
  };

  const save = async () => {
    if (!form.user_id || !form.shift_date) return;
    setSaving(true);
    setError(null);
    try {
      const r = await fetch("/api/v1/calendar/shifts", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          user_id: form.user_id,
          user_name: form.user_name || undefined,
          department: form.department || undefined,
          shift_date: form.shift_date,
          shift_type: form.shift_type,
          shift_start: form.shift_start,
          shift_end: form.shift_end,
          location: form.location || undefined,
          notes: form.notes || undefined,
        }),
      });
      if (!r.ok) throw new Error(await r.text());
      setForm(EMPTY_FORM);
      load();
    } catch (e) {
      setError(String(e));
    } finally {
      setSaving(false);
    }
  };

  const approve = async (shiftId: string, approverName: string) => {
    await fetch(`/api/v1/calendar/shifts/${shiftId}/approve?approved_by=${encodeURIComponent(approverName)}`, {
      method: "PATCH",
    });
    load();
  };

  const del = async (shiftId: string) => {
    if (!confirm("Delete this shift?")) return;
    await fetch(`/api/v1/calendar/shifts/${shiftId}`, { method: "DELETE" });
    load();
  };

  // Group shifts by date
  const grouped = shifts.reduce<Record<string, Shift[]>>((acc, s) => {
    (acc[s.shift_date] = acc[s.shift_date] || []).push(s);
    return acc;
  }, {});

  return (
    <div className="p-6 space-y-6 max-w-5xl mx-auto">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Shift Scheduling</h1>
        <p className="text-sm text-gray-500 mt-0.5">Staff shift assignment, approval, and weekly view</p>
      </div>

      {error && <div className="bg-red-50 border border-red-200 rounded p-3 text-sm text-red-700">{error}</div>}

      {/* Add shift form */}
      <div className="bg-white border rounded-lg p-5 shadow-sm space-y-4">
        <h2 className="text-sm font-semibold text-gray-700">Schedule Shift</h2>
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {[
            { label: "User ID *", key: "user_id", placeholder: "user UUID or ID" },
            { label: "Name", key: "user_name", placeholder: "e.g. John Kamau" },
            { label: "Department", key: "department", placeholder: "e.g. Production" },
            { label: "Location", key: "location", placeholder: "e.g. Factory A" },
            { label: "Notes", key: "notes", placeholder: "Optional" },
          ].map(({ label, key, placeholder }) => (
            <div key={key}>
              <label className="text-xs text-gray-500 block mb-1">{label}</label>
              <input
                type="text"
                placeholder={placeholder}
                value={(form as unknown as Record<string, string>)[key]}
                onChange={(e) => setForm((p) => ({ ...p, [key]: e.target.value }))}
                className="w-full border border-gray-300 rounded px-3 py-1.5 text-sm focus:outline-none focus:ring-1 focus:ring-blue-500"
              />
            </div>
          ))}
          <div>
            <label className="text-xs text-gray-500 block mb-1">Date *</label>
            <input type="date" value={form.shift_date}
              onChange={(e) => setForm((p) => ({ ...p, shift_date: e.target.value }))}
              className="w-full border border-gray-300 rounded px-3 py-1.5 text-sm focus:outline-none focus:ring-1 focus:ring-blue-500" />
          </div>
        </div>

        {/* Shift type */}
        <div className="flex flex-wrap gap-2">
          {Object.entries(SHIFT_PRESETS).map(([type, { label }]) => (
            <button key={type} onClick={() => handleTypeChange(type)}
              className={`text-xs rounded-full border px-3 py-1.5 transition-colors ${
                form.shift_type === type
                  ? "bg-blue-600 text-white border-blue-600"
                  : "bg-gray-50 text-gray-600 border-gray-300 hover:bg-gray-100"
              }`}>
              {label}
            </button>
          ))}
        </div>

        {/* Time override */}
        <div className="flex gap-3">
          <div>
            <label className="text-xs text-gray-500 block mb-1">Start</label>
            <input type="time" value={form.shift_start}
              onChange={(e) => setForm((p) => ({ ...p, shift_start: e.target.value }))}
              className="border border-gray-300 rounded px-3 py-1.5 text-sm focus:outline-none" />
          </div>
          <div>
            <label className="text-xs text-gray-500 block mb-1">End</label>
            <input type="time" value={form.shift_end}
              onChange={(e) => setForm((p) => ({ ...p, shift_end: e.target.value }))}
              className="border border-gray-300 rounded px-3 py-1.5 text-sm focus:outline-none" />
          </div>
          <div className="flex items-end">
            <button onClick={save} disabled={saving || !form.user_id || !form.shift_date}
              className="bg-blue-600 hover:bg-blue-700 text-white text-sm font-medium px-5 py-1.5 rounded disabled:opacity-50">
              {saving ? "Saving…" : "Add Shift"}
            </button>
          </div>
        </div>
      </div>

      {/* Filters */}
      <div className="flex gap-3 flex-wrap bg-white border rounded-lg p-3 shadow-sm">
        <div>
          <label className="text-xs text-gray-500 block mb-1">Department</label>
          <input type="text" value={filterDept} onChange={(e) => setFilterDept(e.target.value)}
            placeholder="Filter by dept"
            className="border border-gray-300 rounded px-2 py-1 text-xs focus:outline-none" />
        </div>
        <div>
          <label className="text-xs text-gray-500 block mb-1">Date</label>
          <input type="date" value={filterDate} onChange={(e) => setFilterDate(e.target.value)}
            className="border border-gray-300 rounded px-2 py-1 text-xs focus:outline-none" />
        </div>
        <div className="flex items-end">
          <button onClick={() => { setFilterDept(""); setFilterDate(""); }}
            className="text-xs text-gray-500 hover:text-gray-700 underline">Clear</button>
        </div>
      </div>

      {/* Shifts grouped by date */}
      {loading ? (
        <p className="text-gray-400 text-sm">Loading…</p>
      ) : Object.keys(grouped).length === 0 ? (
        <div className="bg-white border rounded-lg p-6 text-center text-sm text-gray-400">
          No shifts scheduled. Add one above.
        </div>
      ) : (
        <div className="space-y-4">
          {Object.entries(grouped).sort(([a], [b]) => a.localeCompare(b)).map(([date, dayShifts]) => (
            <div key={date} className="bg-white border rounded-lg shadow-sm overflow-hidden">
              <div className="px-4 py-2.5 bg-gray-50 border-b">
                <p className="text-sm font-semibold text-gray-700">
                  {new Date(date + "T12:00:00").toLocaleDateString("en-GB", { weekday: "short", day: "2-digit", month: "short" })}
                  <span className="ml-2 font-normal text-gray-400">{dayShifts.length} shifts</span>
                </p>
              </div>
              <div className="divide-y">
                {dayShifts.map((s) => (
                  <div key={s.shift_id} className="px-4 py-3 flex items-center gap-4">
                    <span className={`text-xs rounded-full px-2 py-0.5 font-medium shrink-0 ${SHIFT_COLOR[s.shift_type] ?? "bg-gray-100 text-gray-600"}`}>
                      {s.shift_type}
                    </span>
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium text-gray-900">{s.user_name || s.user_id}</p>
                      <p className="text-xs text-gray-500">
                        {s.department && `${s.department} · `}{s.shift_start}–{s.shift_end}
                        {s.location && ` · ${s.location}`}
                      </p>
                    </div>
                    {s.approved_flag ? (
                      <span className="text-xs text-green-600 bg-green-100 rounded-full px-2 py-0.5 shrink-0">Approved</span>
                    ) : (
                      <button
                        onClick={() => approve(s.shift_id, "Manager")}
                        className="text-xs text-blue-600 hover:text-blue-800 shrink-0"
                      >
                        Approve
                      </button>
                    )}
                    <button onClick={() => del(s.shift_id)} className="text-xs text-red-500 hover:text-red-700 shrink-0">
                      Delete
                    </button>
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
