"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { timesheetsApi, ActivityType, ACTIVITY_TYPES } from "@/lib/timesheets";

interface LineForm {
  work_date: string;
  project_name: string;
  task_name: string;
  activity_type: ActivityType;
  cost_center_name: string;
  hours_worked: string;
  overtime_flag: boolean;
  billable_flag: boolean;
  notes: string;
}

const emptyLine = (): LineForm => ({
  work_date: "", project_name: "", task_name: "",
  activity_type: "regular", cost_center_name: "",
  hours_worked: "", overtime_flag: false, billable_flag: false, notes: "",
});

function getMondayOfWeek(d: Date): string {
  const day = d.getDay();
  const diff = d.getDate() - day + (day === 0 ? -6 : 1);
  const mon = new Date(d.setDate(diff));
  return mon.toISOString().slice(0, 10);
}

function getSundayOfWeek(monStr: string): string {
  const d = new Date(monStr);
  d.setDate(d.getDate() + 6);
  return d.toISOString().slice(0, 10);
}

export default function TimeEntryPage() {
  const router = useRouter();
  const today = new Date();
  const defaultMon = getMondayOfWeek(new Date(today));
  const [header, setHeader] = useState({
    employee_id: "", employee_name: "", department_id: "", department_name: "",
    manager_id: "", manager_name: "",
    period_start: defaultMon,
    period_end: getSundayOfWeek(defaultMon),
    notes: "",
  });
  const [lines, setLines] = useState<LineForm[]>([emptyLine()]);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  const weekDays = Array.from({ length: 7 }, (_, i) => {
    const d = new Date(header.period_start);
    d.setDate(d.getDate() + i);
    return d.toISOString().slice(0, 10);
  });

  const totalHours = lines.reduce((s, l) => s + (Number(l.hours_worked) || 0), 0);
  const otHours = lines.filter(l => l.overtime_flag).reduce((s, l) => s + (Number(l.hours_worked) || 0), 0);

  const updateLine = (i: number, field: keyof LineForm, value: unknown) => {
    const n = [...lines];
    (n[i] as unknown as Record<string, unknown>)[field] = value;
    setLines(n);
  };

  const submit = async () => {
    if (!header.employee_id || !header.period_start) {
      setError("Employee ID and period start are required.");
      return;
    }
    setError("");
    setSaving(true);
    try {
      const ts = await timesheetsApi.create({
        employee_id: header.employee_id,
        employee_name: header.employee_name || undefined,
        department_id: header.department_id || undefined,
        department_name: header.department_name || undefined,
        manager_id: header.manager_id || undefined,
        manager_name: header.manager_name || undefined,
        period_start: header.period_start,
        period_end: header.period_end,
        notes: header.notes || undefined,
      });
      for (const l of lines.filter(l => l.work_date && l.hours_worked)) {
        await timesheetsApi.addLine(ts.timesheet_id, {
          work_date: l.work_date,
          project_name: l.project_name || undefined,
          task_name: l.task_name || undefined,
          activity_type: l.activity_type,
          cost_center_name: l.cost_center_name || undefined,
          hours_worked: Number(l.hours_worked),
          overtime_flag: l.overtime_flag,
          billable_flag: l.billable_flag,
          notes: l.notes || undefined,
        });
      }
      router.push("/dashboard/timesheets/my-timesheets");
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Error saving timesheet");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="p-6 space-y-6 max-w-5xl">
      <h1 className="text-xl font-bold text-gray-900">New Timesheet — Time Entry</h1>

      {error && <div className="bg-red-50 border border-red-200 text-red-700 rounded p-3 text-sm">{error}</div>}

      <div className="bg-white border rounded-lg p-4 shadow-sm space-y-3">
        <h2 className="font-semibold text-gray-800">Period & Employee</h2>
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
          <div>
            <label className="text-xs text-gray-500">Period Start (Monday) *</label>
            <input type="date" className="w-full border rounded px-2 py-1 text-sm mt-1"
              value={header.period_start}
              onChange={(e) => setHeader({ ...header, period_start: e.target.value, period_end: getSundayOfWeek(e.target.value) })} />
          </div>
          <div>
            <label className="text-xs text-gray-500">Period End (Sunday)</label>
            <input type="date" className="w-full border rounded px-2 py-1 text-sm mt-1 bg-gray-50"
              value={header.period_end} readOnly />
          </div>
          {(["employee_id","employee_name","department_id","department_name","manager_id","manager_name"] as const).map((f) => (
            <div key={f}>
              <label className="text-xs text-gray-500 capitalize">{f.replace(/_/g," ")}</label>
              <input className="w-full border rounded px-2 py-1 text-sm mt-1" value={header[f]}
                onChange={(e) => setHeader({ ...header, [f]: e.target.value })} />
            </div>
          ))}
          <div className="col-span-2 sm:col-span-3">
            <label className="text-xs text-gray-500">Notes</label>
            <textarea className="w-full border rounded px-2 py-1 text-sm mt-1" rows={2}
              value={header.notes} onChange={(e) => setHeader({ ...header, notes: e.target.value })} />
          </div>
        </div>
      </div>

      <div className="bg-white border rounded-lg p-4 shadow-sm space-y-3">
        <div className="flex justify-between items-center">
          <div>
            <h2 className="font-semibold text-gray-800">Time Lines</h2>
            <p className="text-xs text-gray-500 mt-0.5">Total: <strong>{totalHours.toFixed(1)}h</strong> · Overtime: <strong className="text-orange-600">{otHours.toFixed(1)}h</strong></p>
          </div>
          <div className="flex gap-2">
            {weekDays.map(d => (
              <button key={d} onClick={() => setLines([...lines, { ...emptyLine(), work_date: d }])}
                className="rounded border px-2 py-0.5 text-xs text-gray-600 hover:bg-gray-50">
                + {new Date(d + "T00:00:00").toLocaleDateString("en-GB", { weekday: "short" })} {d.slice(8)}
              </button>
            ))}
            <button onClick={() => setLines([...lines, emptyLine()])}
              className="rounded border border-blue-200 px-2 py-0.5 text-xs text-blue-600 hover:bg-blue-50">
              + Blank
            </button>
          </div>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 border-b text-xs">
              <tr>
                {["Date","Activity","Project","Task","Cost Center","Hours","OT","Billable","Notes",""].map(h=>(
                  <th key={h} className="px-2 py-1 text-left text-gray-600">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y">
              {lines.map((l, i) => (
                <tr key={i}>
                  <td className="px-1 py-1">
                    <input type="date" className="border rounded px-1 py-0.5 text-xs w-32"
                      value={l.work_date} onChange={(e) => updateLine(i, "work_date", e.target.value)} />
                  </td>
                  <td className="px-1 py-1">
                    <select className="border rounded px-1 py-0.5 text-xs w-24"
                      value={l.activity_type} onChange={(e) => updateLine(i, "activity_type", e.target.value as ActivityType)}>
                      {ACTIVITY_TYPES.map(t => <option key={t} value={t}>{t}</option>)}
                    </select>
                  </td>
                  <td className="px-1 py-1">
                    <input className="border rounded px-1 py-0.5 text-xs w-24"
                      placeholder="Project" value={l.project_name}
                      onChange={(e) => updateLine(i, "project_name", e.target.value)} />
                  </td>
                  <td className="px-1 py-1">
                    <input className="border rounded px-1 py-0.5 text-xs w-24"
                      placeholder="Task" value={l.task_name}
                      onChange={(e) => updateLine(i, "task_name", e.target.value)} />
                  </td>
                  <td className="px-1 py-1">
                    <input className="border rounded px-1 py-0.5 text-xs w-24"
                      placeholder="Cost Center" value={l.cost_center_name}
                      onChange={(e) => updateLine(i, "cost_center_name", e.target.value)} />
                  </td>
                  <td className="px-1 py-1">
                    <input type="number" min={0.5} max={16} step={0.5}
                      className="border rounded px-1 py-0.5 text-xs w-16"
                      value={l.hours_worked} onChange={(e) => updateLine(i, "hours_worked", e.target.value)} />
                  </td>
                  <td className="px-1 py-1 text-center">
                    <input type="checkbox" checked={l.overtime_flag}
                      onChange={(e) => updateLine(i, "overtime_flag", e.target.checked)} />
                  </td>
                  <td className="px-1 py-1 text-center">
                    <input type="checkbox" checked={l.billable_flag}
                      onChange={(e) => updateLine(i, "billable_flag", e.target.checked)} />
                  </td>
                  <td className="px-1 py-1">
                    <input className="border rounded px-1 py-0.5 text-xs w-24"
                      placeholder="Notes" value={l.notes}
                      onChange={(e) => updateLine(i, "notes", e.target.value)} />
                  </td>
                  <td className="px-1 py-1">
                    <button onClick={() => setLines(lines.filter((_, j) => j !== i))}
                      className="text-red-400 hover:text-red-600 text-xs">✕</button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      <div className="flex gap-2">
        <button onClick={submit} disabled={saving}
          className="rounded bg-blue-600 px-6 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50">
          {saving ? "Saving…" : "Save Timesheet"}
        </button>
        <button onClick={() => router.back()} className="rounded border px-6 py-2 text-sm text-gray-600 hover:bg-gray-50">
          Cancel
        </button>
      </div>
    </div>
  );
}
