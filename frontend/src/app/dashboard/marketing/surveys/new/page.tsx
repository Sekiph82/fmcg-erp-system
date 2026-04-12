"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useMutation } from "@tanstack/react-query";
import { marketingApi, SurveyType } from "@/lib/marketingApi";
import { RequirePermission } from "@/components/PermissionGuard";

const SURVEY_TYPES: SurveyType[] = [
  "CUSTOMER_FEEDBACK", "MARKET_AUDIT", "RETAILER_FEEDBACK",
  "BRAND_AWARENESS", "COMPETITOR_CHECK", "PRODUCT_FEEDBACK", "SHELF_AUDIT",
];

export default function NewSurveyPage() {
  const router = useRouter();
  const [form, setForm] = useState({
    survey_name: "",
    survey_type: "CUSTOMER_FEEDBACK" as SurveyType,
    region: "",
    survey_date: new Date().toISOString().split("T")[0],
    target_segment_id: "",
    summary: "",
    competitor_notes: "",
    questions_raw: "",
  });
  const [error, setError] = useState("");
  const [jsonError, setJsonError] = useState("");

  const createMut = useMutation({
    mutationFn: () => {
      let questions_json: Record<string, unknown> | null = null;
      if (form.questions_raw.trim()) {
        try {
          questions_json = JSON.parse(form.questions_raw);
        } catch {
          throw new Error("Questions JSON is invalid. Please check the format.");
        }
      }
      return marketingApi.surveys.create({
        survey_name: form.survey_name,
        survey_type: form.survey_type,
        region: form.region || null,
        survey_date: form.survey_date,
        target_segment_id: form.target_segment_id || null,
        summary: form.summary || null,
        competitor_notes: form.competitor_notes || null,
        questions_json,
      });
    },
    onSuccess: () => router.push("/dashboard/marketing/surveys"),
    onError: (e: unknown) => setError(String((e as { message?: string }).message ?? e)),
  });

  const set = (k: string, v: string) => setForm((f) => ({ ...f, [k]: v }));

  const validateJson = (v: string) => {
    set("questions_raw", v);
    if (!v.trim()) { setJsonError(""); return; }
    try { JSON.parse(v); setJsonError(""); } catch { setJsonError("Invalid JSON"); }
  };

  return (
    <RequirePermission permission="surveys.create">
      <div className="min-h-screen bg-[#0b1120] p-6 text-white max-w-2xl mx-auto">
        <div className="mb-6">
          <button onClick={() => router.back()} className="text-slate-400 hover:text-white text-sm mb-2">
            ← Back
          </button>
          <h1 className="text-2xl font-bold">New Survey</h1>
        </div>

        {error && (
          <div className="mb-4 p-3 rounded-lg bg-red-900/30 border border-red-700 text-red-300 text-sm">{error}</div>
        )}

        <div className="bg-[#131c2e] border border-slate-700/50 rounded-xl p-6 space-y-4">
          <div>
            <label className="block text-xs text-slate-400 mb-1">Survey Name *</label>
            <input type="text" value={form.survey_name}
              onChange={(e) => set("survey_name", e.target.value)}
              placeholder="e.g. Q2 Retailer Feedback — Nairobi"
              className="w-full bg-[#0b1120] border border-slate-700 rounded-lg px-3 py-2 text-sm text-white placeholder-slate-600" />
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-xs text-slate-400 mb-1">Survey Type *</label>
              <select value={form.survey_type} onChange={(e) => set("survey_type", e.target.value)}
                className="w-full bg-[#0b1120] border border-slate-700 rounded-lg px-3 py-2 text-sm text-white">
                {SURVEY_TYPES.map((t) => (
                  <option key={t} value={t}>{t.replace(/_/g, " ")}</option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-xs text-slate-400 mb-1">Survey Date *</label>
              <input type="date" value={form.survey_date}
                onChange={(e) => set("survey_date", e.target.value)}
                className="w-full bg-[#0b1120] border border-slate-700 rounded-lg px-3 py-2 text-sm text-white" />
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-xs text-slate-400 mb-1">Region</label>
              <input type="text" value={form.region}
                onChange={(e) => set("region", e.target.value)}
                placeholder="e.g. Nairobi, Western Kenya"
                className="w-full bg-[#0b1120] border border-slate-700 rounded-lg px-3 py-2 text-sm text-white placeholder-slate-600" />
            </div>

            <div>
              <label className="block text-xs text-slate-400 mb-1">Target Segment ID <span className="text-slate-600">(optional)</span></label>
              <input type="text" value={form.target_segment_id}
                onChange={(e) => set("target_segment_id", e.target.value)}
                placeholder="UUID"
                className="w-full bg-[#0b1120] border border-slate-700 rounded-lg px-3 py-2 text-sm text-white placeholder-slate-600" />
            </div>
          </div>

          <div>
            <label className="block text-xs text-slate-400 mb-1">
              Questions <span className="text-slate-500">(JSON format)</span>
            </label>
            <textarea
              value={form.questions_raw}
              onChange={(e) => validateJson(e.target.value)}
              rows={6}
              placeholder={`{\n  "q1": "How would you rate our product quality?",\n  "q2": "Would you recommend us to others?"\n}`}
              className={`w-full bg-[#0b1120] border rounded-lg px-3 py-2 text-sm text-white font-mono placeholder-slate-600 resize-y ${
                jsonError ? "border-red-600" : "border-slate-700"
              }`}
            />
            {jsonError && <p className="text-xs text-red-400 mt-1">{jsonError}</p>}
            <p className="text-xs text-slate-600 mt-1">Leave blank to add questions later. Must be valid JSON if filled.</p>
          </div>

          <div>
            <label className="block text-xs text-slate-400 mb-1">Summary / Objective</label>
            <textarea value={form.summary} onChange={(e) => set("summary", e.target.value)}
              rows={2} placeholder="What is this survey measuring?"
              className="w-full bg-[#0b1120] border border-slate-700 rounded-lg px-3 py-2 text-sm text-white placeholder-slate-600 resize-none" />
          </div>

          <div>
            <label className="block text-xs text-slate-400 mb-1">Competitor Notes</label>
            <textarea value={form.competitor_notes} onChange={(e) => set("competitor_notes", e.target.value)}
              rows={2} placeholder="Competitor observations to include..."
              className="w-full bg-[#0b1120] border border-slate-700 rounded-lg px-3 py-2 text-sm text-white placeholder-slate-600 resize-none" />
          </div>

          <div className="flex justify-end gap-3 pt-2">
            <button onClick={() => router.back()}
              className="px-4 py-2 rounded-lg border border-slate-600 text-slate-300 hover:bg-slate-800 text-sm">
              Cancel
            </button>
            <button
              onClick={() => createMut.mutate()}
              disabled={!form.survey_name || !form.survey_date || !!jsonError || createMut.isPending}
              className="px-5 py-2 rounded-lg bg-teal-600 hover:bg-teal-500 disabled:opacity-50 text-sm font-medium">
              {createMut.isPending ? "Creating..." : "Create Survey"}
            </button>
          </div>
        </div>
      </div>
    </RequirePermission>
  );
}
