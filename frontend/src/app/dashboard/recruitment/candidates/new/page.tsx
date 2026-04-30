"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { recruitmentApi } from "@/lib/recruitment";

export default function NewCandidatePage() {
  const router = useRouter();
  const [form, setForm] = useState({
    full_name: "", email: "", phone: "", location: "",
    source: "manual", current_employer: "", current_title: "",
    years_experience: "", education_level: "", skills_tags: "",
    cv_attachment: "", notes: "",
  });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  const handleSubmit = async () => {
    setSaving(true);
    setError("");
    try {
      const c = await recruitmentApi.createCandidate({
        ...form,
        years_experience: form.years_experience ? Number(form.years_experience) : undefined,
      });
      router.push(`/dashboard/recruitment/candidates/${c.candidate_id}`);
    } catch (e: any) { setError(e.message); }
    finally { setSaving(false); }
  };

  const field = (label: string, key: keyof typeof form, type = "text") => (
    <div>
      <label className="block text-xs text-gray-500 mb-1">{label}</label>
      <input type={type} value={form[key]} onChange={(e) => setForm({ ...form, [key]: e.target.value })}
        className="w-full border rounded p-2 text-sm" />
    </div>
  );

  return (
    <div className="p-6 space-y-6 max-w-2xl">
      <h1 className="text-xl font-bold">Add Candidate</h1>
      <div className="bg-white border rounded-xl p-5 space-y-4">
        <div className="grid grid-cols-2 gap-4">
          {field("Full Name *", "full_name")}
          {field("Email *", "email", "email")}
          {field("Phone", "phone", "tel")}
          {field("Location", "location")}
          <div>
            <label className="block text-xs text-gray-500 mb-1">Source</label>
            <select value={form.source} onChange={(e) => setForm({ ...form, source: e.target.value })}
              className="w-full border rounded p-2 text-sm">
              {["portal", "referral", "agency", "manual", "linkedin", "job_portal"].map((s) => (
                <option key={s} value={s}>{s}</option>
              ))}
            </select>
          </div>
          {field("Current Employer", "current_employer")}
          {field("Current Title", "current_title")}
          {field("Years Experience", "years_experience", "number")}
          {field("Education Level", "education_level")}
          {field("CV / Resume URL", "cv_attachment")}
        </div>
        <div>
          <label className="block text-xs text-gray-500 mb-1">Skills (comma-separated)</label>
          <input value={form.skills_tags} onChange={(e) => setForm({ ...form, skills_tags: e.target.value })}
            className="w-full border rounded p-2 text-sm" placeholder="React, Python, SQL…" />
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
        {saving ? "Saving…" : "Add Candidate"}
      </button>
    </div>
  );
}
