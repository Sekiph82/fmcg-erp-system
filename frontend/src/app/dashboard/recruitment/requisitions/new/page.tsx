"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { recruitmentApi } from "@/lib/recruitment";

const inputCls = "w-full bg-white/[0.04] border border-white/[0.08] rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-indigo-500";
const selectCls = "w-full bg-[#0d1829] border border-white/[0.08] rounded-lg px-3 py-2 text-sm text-white focus:outline-none";
const labelCls = "block text-[10px] text-slate-400 mb-1";

export default function NewRequisitionPage() {
  const router = useRouter();
  const [form, setForm] = useState({
    job_title: "", location: "", employment_type: "full_time", headcount: "1",
    opening_date: "", closing_date: "", salary_min: "", salary_max: "",
    currency: "KES", job_description: "", requirements: "", notes: "",
  });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  const handleSubmit = async () => {
    setSaving(true); setError("");
    try {
      const r = await recruitmentApi.createRequisition({ ...form, headcount: Number(form.headcount), salary_min: form.salary_min ? Number(form.salary_min) : undefined, salary_max: form.salary_max ? Number(form.salary_max) : undefined, opening_date: form.opening_date || undefined, closing_date: form.closing_date || undefined });
      router.push(`/dashboard/recruitment/requisitions/${r.requisition_id}`);
    } catch (e: any) { setError(e.message); }
    finally { setSaving(false); }
  };

  const f = (label: string, key: keyof typeof form, type = "text", opts?: string[]) => (
    <div>
      <label className={labelCls}>{label}</label>
      {opts ? (
        <select value={form[key]} onChange={(e) => setForm({ ...form, [key]: e.target.value })} className={selectCls}>
          {opts.map((o) => <option key={o} value={o}>{o.replace("_", " ").toUpperCase()}</option>)}
        </select>
      ) : (
        <input type={type} value={form[key]} onChange={(e) => setForm({ ...form, [key]: e.target.value })} className={inputCls} />
      )}
    </div>
  );

  return (
    <div className="p-6 space-y-6 min-h-screen bg-[#060d18] text-slate-200 max-w-3xl">
      <h1 className="text-xl font-bold text-white">New Job Requisition</h1>

      <div className="rounded-xl border border-white/[0.07] bg-[#0d1829] p-5 space-y-4">
        <div className="grid grid-cols-2 gap-4">
          {f("Job Title *", "job_title")}
          {f("Location", "location")}
          {f("Employment Type", "employment_type", "text", ["full_time", "part_time", "contract", "intern"])}
          {f("Headcount", "headcount", "number")}
          {f("Opening Date", "opening_date", "date")}
          {f("Closing Date", "closing_date", "date")}
          {f("Salary Min (KES)", "salary_min", "number")}
          {f("Salary Max (KES)", "salary_max", "number")}
        </div>
        <div><label className={labelCls}>Job Description</label><textarea value={form.job_description} onChange={(e) => setForm({ ...form, job_description: e.target.value })} rows={4} className={inputCls} /></div>
        <div><label className={labelCls}>Requirements</label><textarea value={form.requirements} onChange={(e) => setForm({ ...form, requirements: e.target.value })} rows={3} className={inputCls} /></div>
        <div><label className={labelCls}>Notes</label><textarea value={form.notes} onChange={(e) => setForm({ ...form, notes: e.target.value })} rows={2} className={inputCls} /></div>
      </div>

      {error && <p className="text-sm text-red-400">{error}</p>}
      <button onClick={handleSubmit} disabled={saving}
        className="px-6 py-2 rounded-lg bg-blue-600 hover:bg-blue-500 text-white text-sm font-medium disabled:opacity-50">
        {saving ? "Saving…" : "Create Requisition"}
      </button>
    </div>
  );
}
