"use client";
import { useEffect, useState } from "react";
import {
  appraisalsApi, AppraisalPeriod, AppraisalPeriodStatus,
  PERIOD_STATUS_COLOR, PERIOD_TYPE_LABEL, AppraisalPeriodType,
} from "@/lib/appraisals";

const PERIOD_TYPES: AppraisalPeriodType[] = ["annual","semi_annual","quarterly","probation","project_based","custom"];

export default function AppraisalPeriodsPage() {
  const [periods, setPeriods] = useState<AppraisalPeriod[]>([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({
    period_code: "", period_name: "", period_type: "annual" as AppraisalPeriodType,
    start_date: "", end_date: "", review_start_date: "", review_end_date: "", notes: "",
  });

  const load = () => appraisalsApi.listPeriods().then(setPeriods).finally(() => setLoading(false));
  useEffect(() => { load(); }, []);

  const submit = async () => {
    await appraisalsApi.createPeriod({
      ...form,
      review_start_date: form.review_start_date || undefined,
      review_end_date: form.review_end_date || undefined,
      notes: form.notes || undefined,
    });
    setShowForm(false);
    load();
  };

  const activate = async (id: string) => {
    await appraisalsApi.updatePeriod(id, { status: "active" as AppraisalPeriodStatus });
    load();
  };

  const close = async (id: string) => {
    await appraisalsApi.updatePeriod(id, { status: "closed" as AppraisalPeriodStatus });
    load();
  };

  return (
    <div className="p-6 space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-bold text-gray-900">Appraisal Periods</h1>
        <button
          onClick={() => setShowForm(true)}
          className="rounded bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700"
        >
          + New Period
        </button>
      </div>

      {showForm && (
        <div className="bg-white border rounded-lg p-4 shadow-sm space-y-3">
          <h2 className="font-semibold text-gray-800">New Appraisal Period</h2>
          <div className="grid grid-cols-2 gap-3">
            {(["period_code","period_name"] as const).map((f) => (
              <div key={f}>
                <label className="text-xs text-gray-500 capitalize">{f.replace(/_/g," ")}</label>
                <input
                  className="w-full border rounded px-2 py-1 text-sm mt-1"
                  value={form[f]}
                  onChange={(e) => setForm({ ...form, [f]: e.target.value })}
                />
              </div>
            ))}
            <div>
              <label className="text-xs text-gray-500">Period Type</label>
              <select
                className="w-full border rounded px-2 py-1 text-sm mt-1"
                value={form.period_type}
                onChange={(e) => setForm({ ...form, period_type: e.target.value as AppraisalPeriodType })}
              >
                {PERIOD_TYPES.map((t) => (
                  <option key={t} value={t}>{PERIOD_TYPE_LABEL[t]}</option>
                ))}
              </select>
            </div>
            {(["start_date","end_date","review_start_date","review_end_date"] as const).map((f) => (
              <div key={f}>
                <label className="text-xs text-gray-500 capitalize">{f.replace(/_/g," ")}</label>
                <input
                  type="date"
                  className="w-full border rounded px-2 py-1 text-sm mt-1"
                  value={form[f]}
                  onChange={(e) => setForm({ ...form, [f]: e.target.value })}
                />
              </div>
            ))}
            <div className="col-span-2">
              <label className="text-xs text-gray-500">Notes</label>
              <textarea
                className="w-full border rounded px-2 py-1 text-sm mt-1"
                rows={2}
                value={form.notes}
                onChange={(e) => setForm({ ...form, notes: e.target.value })}
              />
            </div>
          </div>
          <div className="flex gap-2">
            <button onClick={submit} className="rounded bg-blue-600 px-4 py-1.5 text-sm text-white hover:bg-blue-700">Save</button>
            <button onClick={() => setShowForm(false)} className="rounded border px-4 py-1.5 text-sm text-gray-600 hover:bg-gray-50">Cancel</button>
          </div>
        </div>
      )}

      {loading ? (
        <p className="text-gray-500 text-sm">Loading…</p>
      ) : (
        <div className="bg-white border rounded-lg shadow-sm overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 border-b">
              <tr>
                {["Code","Name","Type","Start","End","Review Window","Status","Actions"].map((h) => (
                  <th key={h} className="px-4 py-2 text-left text-xs font-semibold text-gray-600">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y">
              {periods.map((p) => (
                <tr key={p.appraisal_period_id} className="hover:bg-gray-50">
                  <td className="px-4 py-2 font-mono text-xs">{p.period_code}</td>
                  <td className="px-4 py-2 font-medium text-gray-800">{p.period_name}</td>
                  <td className="px-4 py-2 text-gray-600">{PERIOD_TYPE_LABEL[p.period_type]}</td>
                  <td className="px-4 py-2 text-gray-600">{p.start_date}</td>
                  <td className="px-4 py-2 text-gray-600">{p.end_date}</td>
                  <td className="px-4 py-2 text-gray-500 text-xs">{p.review_start_date ?? "—"} → {p.review_end_date ?? "—"}</td>
                  <td className="px-4 py-2">
                    <span className={`inline-flex rounded-full px-2 py-0.5 text-xs font-medium ${PERIOD_STATUS_COLOR[p.status]}`}>
                      {p.status}
                    </span>
                  </td>
                  <td className="px-4 py-2">
                    {p.status === "draft" && (
                      <button onClick={() => activate(p.appraisal_period_id)} className="text-xs text-green-600 hover:underline mr-2">Activate</button>
                    )}
                    {p.status === "active" && (
                      <button onClick={() => close(p.appraisal_period_id)} className="text-xs text-gray-600 hover:underline">Close</button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          {periods.length === 0 && <p className="text-center text-gray-400 py-8 text-sm">No periods yet.</p>}
        </div>
      )}
    </div>
  );
}
