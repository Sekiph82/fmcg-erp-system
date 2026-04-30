"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { recruitmentApi } from "@/lib/recruitment";

const inputCls = "w-full bg-white/[0.04] border border-white/[0.08] rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-indigo-500";
const selectCls = "w-full bg-[#0d1829] border border-white/[0.08] rounded-lg px-3 py-2 text-sm text-white focus:outline-none";
const labelCls = "block text-[10px] text-slate-400 mb-1";

export default function NewCandidatePage() {
  const router = useRouter();
  const [form, setForm] = useState({ full_name: "", email: "", phone: "", location: "", source: "manual", current_employer: "", current_title: "", years_experience: "", education_level: "", skills_tags: "", cv_attachment: "", notes: "" });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  const handleSubmit = async () => {
    setSaving(true); setError("");
    try {
      const c = await recruitmentApi.createCandidate({ ...form, years_experience: form.years_experience ? Number(form.years_experience) : undefined });
      router.push(`/dashboard/recruitment/candidates/${c.candidate_id}`);
    } catch (e: any) { setError(e.message); }
    finally { setSaving(false); }
  };

  const field = (label: string, key: keyof typeof form, type = "text") => (
    <div><label className={labelCls}>{label}</label>
      <input type={type} value={form[key]} onChange={(e) => setForm({ ...form, [key]: e.target.value })} className={inputCls} /></div>
  );

  return (
    <div className="p-6 space-y-6 min-h-screen bg-[#060d18] text-slate-200 max-w-2xl">
      <h1 className="text-xl font-bold text-white">Add Candidate</h1>
      <div className="rounded-xl border border-white/[0.07] bg-[#0d1829] p-5 space-y-4">
        <div className="grid grid-cols-2 gap-4">
          {field("Full Name *", "full_name")}
          {field("Email *", "email", "email")}
          {field("Phone", "phone", "tel")}
          {field("Location", "location")}
          <div><label className={labelCls}>Source</label>
            <select value={form.source} onChange={(e) => setForm({ ...form, source: e.target.value })} className={selectCls}>
              {["portal", "referral", "agency", "manual", "linkedin", "job_portal"].map((s) => <option key={s} value={s}>{s}</option>)}
            </select>
          </div>
          {field("Current Employer", "current_employer")}
          {field("Current Title", "current_title")}
          {field("Years Experience", "years_experience", "number")}
          {field("Education Level", "education_level")}
          {field("CV / Resume URL", "cv_attachment")}
        </div>
        <div><label className={labelCls}>Skills (comma-separated)</label>
          <input value={form.skills_tags} onChange={(e) => setForm({ ...form, skills_tags: e.target.value })} placeholder="React, Python, SQL…" className={inputCls} /></div>
        <div><label className={labelCls}>Notes</label>
          <textarea value={form.notes} onChange={(e) => setForm({ ...form, notes: e.target.value })} rows={2} className={inputCls} /></div>
      </div>
      {error && <p className="text-sm text-red-400">{error}</p>}
      <button onClick={handleSubmit} disabled={saving}
        className="px-6 py-2 rounded-lg bg-blue-600 hover:bg-blue-500 text-white text-sm font-medium disabled:opacity-50">
        {saving ? "Saving…" : "Add Candidate"}
      </button>
    </div>
  );
}
