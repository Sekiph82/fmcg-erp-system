"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { recruitmentApi } from "@/lib/recruitment";

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
    setSaving(true);
    setError("");
    try {
      const r = await recruitmentApi.createRequisition({
        ...form,
        headcount: Number(form.headcount),
        salary_min: form.salary_min ? Number(form.salary_min) : undefined,
        salary_max: form.salary_max ? Number(form.salary_max) : undefined,
        opening_date: form.opening_date || undefined,
        closing_date: form.closing_date || undefined,
      });
      router.push(`/dashboard/recruitment/requisitions/${r.requisition_id}`);
    } catch (e: any) { setError(e.message); }
    finally { setSaving(false); }
  };

  const f = (label: string, key: keyof typeof form, type = "text", opts?: string[]) => (
    <div>
      <label className="block text-xs text-gray-500 mb-1">{label}</label>
      {opts ? (
        <select value={form[key]} onChange={(e) => setForm({ ...form, [key]: e.target.value })}
          className="w-full border rounded p-2 text-sm">
          {opts.map((o) => <option key={o} value={o}>{o.replace("_", " ").toUpperCase()}</option>)}
        </select>
      ) : (
        <input type={type} value={form[key]} onChange={(e) => setForm({ ...form, [key]: e.target.value })}
          className="w-full border rounded p-2 text-sm" />
      )}
    </div>
  );

  return (
    <div className="p-6 space-y-6 max-w-3xl">
      <h1 className="text-xl font-bold">New Job Requisition</h1>
      <div className="bg-white border rounded-xl p-5 space-y-4">
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
        <div>
          <label className="block text-xs text-gray-500 mb-1">Job Description</label>
          <textarea value={form.job_description} onChange={(e) => setForm({ ...form, job_description: e.target.value })}
            rows={4} className="w-full border rounded p-2 text-sm" />
        </div>
        <div>
          <label className="block text-xs text-gray-500 mb-1">Requirements</label>
          <textarea value={form.requirements} onChange={(e) => setForm({ ...form, requirements: e.target.value })}
            rows={3} className="w-full border rounded p-2 text-sm" />
        </div>
        <div>
          <label className="block text-xs text-gray-500 mb-1">Notes</label>
          <textarea value={form.notes} onChange={(e) => setForm({ ...form, notes: e.target.value })}
            rows={2} className="w-full border rounded p-2 text-sm" />
        </div>
      </div>
      {error && <p className="text-sm text-red-600">{error}</p>}
      <button onClick={handleSubmit} disabled={saving}
        className="bg-blue-600 text-white px-6 py-2 rounded-lg hover:bg-blue-700 disabled:opacity-50 text-sm">
        {saving ? "Saving…" : "Create Requisition"}
      </button>
    </div>
  );
}
