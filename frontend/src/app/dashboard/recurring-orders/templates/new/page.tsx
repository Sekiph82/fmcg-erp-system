"use client";
import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { subscriptionApi } from "@/lib/subscription";
import { useRouter } from "next/navigation";

const RECURRENCE_TYPES = [
  { value: "WEEKLY", label: "Weekly" },
  { value: "BIWEEKLY", label: "Every 2 weeks" },
  { value: "MONTHLY_DATE", label: "Monthly (fixed date)" },
  { value: "MONTHLY_DAY", label: "Monthly (weekday)" },
  { value: "CUSTOM_DAYS", label: "Custom interval (days)" },
  { value: "ROUTE_BASED", label: "Route-based" },
];

const GENERATION_MODES = [
  { value: "DRAFT_ONLY", label: "Draft only (manual review)" },
  { value: "APPROVAL_REQUIRED", label: "Pending approval" },
  { value: "AUTO_CONFIRM", label: "Auto-confirm" },
];

export default function NewTemplatePage() {
  const router = useRouter();
  const qc = useQueryClient();
  const [form, setForm] = useState({
    template_code: "",
    template_name: "",
    customer_id: "",
    currency: "KES",
    recurrence_type: "WEEKLY",
    recurrence_interval: "",
    recurrence_day_of_month: "",
    start_date: "",
    end_date: "",
    generation_mode: "DRAFT_ONLY",
    notes: "",
  });
  const [error, setError] = useState("");

  const mut = useMutation({
    mutationFn: (data: any) => subscriptionApi.createTemplate(data),
    onSuccess: (t) => {
      qc.invalidateQueries({ queryKey: ["sub-templates"] });
      router.push(`/dashboard/recurring-orders/templates/${t.id}`);
    },
    onError: (e: any) => setError(e?.message ?? "Failed to create"),
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    const data: any = {
      template_code: form.template_code,
      template_name: form.template_name,
      customer_id: form.customer_id,
      currency: form.currency,
      recurrence_type: form.recurrence_type,
      start_date: form.start_date,
      generation_mode: form.generation_mode,
      notes: form.notes || undefined,
      lines: [],
    };
    if (form.recurrence_interval) data.recurrence_interval = parseInt(form.recurrence_interval);
    if (form.recurrence_day_of_month) data.recurrence_day_of_month = parseInt(form.recurrence_day_of_month);
    if (form.end_date) data.end_date = form.end_date;
    mut.mutate(data);
  };

  const upd = (k: string, v: string) => setForm((f) => ({ ...f, [k]: v }));

  return (
    <div className="p-6 max-w-2xl mx-auto space-y-6 text-slate-200">
      <div>
        <h1 className="text-xl font-bold text-white">New Recurring Template</h1>
        <p className="text-slate-500 text-sm mt-0.5">Create a recurring order contract</p>
      </div>

      <form onSubmit={handleSubmit} className="space-y-5">
        <div className="glow-card p-5 space-y-4">
          <h2 className="text-sm font-semibold text-white">Template Info</h2>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="text-xs text-slate-400 mb-1 block">Template Code *</label>
              <input value={form.template_code} onChange={(e) => upd("template_code", e.target.value)} required
                className="w-full bg-white/[0.04] border border-white/[0.08] rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-indigo-500"
                placeholder="SUB-001" />
            </div>
            <div>
              <label className="text-xs text-slate-400 mb-1 block">Currency</label>
              <input value={form.currency} onChange={(e) => upd("currency", e.target.value)}
                className="w-full bg-white/[0.04] border border-white/[0.08] rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-indigo-500"
                placeholder="KES" maxLength={3} />
            </div>
          </div>

          <div>
            <label className="text-xs text-slate-400 mb-1 block">Template Name *</label>
            <input value={form.template_name} onChange={(e) => upd("template_name", e.target.value)} required
              className="w-full bg-white/[0.04] border border-white/[0.08] rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-indigo-500"
              placeholder="Weekly delivery for Nairobi branch" />
          </div>

          <div>
            <label className="text-xs text-slate-400 mb-1 block">Customer ID *</label>
            <input value={form.customer_id} onChange={(e) => upd("customer_id", e.target.value)} required
              className="w-full bg-white/[0.04] border border-white/[0.08] rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-indigo-500 font-mono"
              placeholder="UUID" />
          </div>
        </div>

        <div className="glow-card p-5 space-y-4">
          <h2 className="text-sm font-semibold text-white">Recurrence Settings</h2>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="text-xs text-slate-400 mb-1 block">Recurrence Type *</label>
              <select value={form.recurrence_type} onChange={(e) => upd("recurrence_type", e.target.value)}
                className="w-full bg-[#0d1829] border border-white/[0.08] rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-indigo-500">
                {RECURRENCE_TYPES.map((r) => (
                  <option key={r.value} value={r.value}>{r.label}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="text-xs text-slate-400 mb-1 block">Interval (days, for custom)</label>
              <input type="number" value={form.recurrence_interval} onChange={(e) => upd("recurrence_interval", e.target.value)}
                className="w-full bg-white/[0.04] border border-white/[0.08] rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-indigo-500"
                min={1} placeholder="e.g. 14" />
            </div>
          </div>

          {form.recurrence_type === "MONTHLY_DATE" && (
            <div>
              <label className="text-xs text-slate-400 mb-1 block">Day of month</label>
              <input type="number" value={form.recurrence_day_of_month} onChange={(e) => upd("recurrence_day_of_month", e.target.value)}
                className="w-full bg-white/[0.04] border border-white/[0.08] rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-indigo-500"
                min={1} max={31} />
            </div>
          )}

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="text-xs text-slate-400 mb-1 block">Start Date *</label>
              <input type="date" value={form.start_date} onChange={(e) => upd("start_date", e.target.value)} required
                className="w-full bg-white/[0.04] border border-white/[0.08] rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-indigo-500" />
            </div>
            <div>
              <label className="text-xs text-slate-400 mb-1 block">End Date (optional)</label>
              <input type="date" value={form.end_date} onChange={(e) => upd("end_date", e.target.value)}
                className="w-full bg-white/[0.04] border border-white/[0.08] rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-indigo-500" />
            </div>
          </div>
        </div>

        <div className="glow-card p-5 space-y-4">
          <h2 className="text-sm font-semibold text-white">Generation Settings</h2>
          <div>
            <label className="text-xs text-slate-400 mb-1 block">Generation Mode</label>
            <select value={form.generation_mode} onChange={(e) => upd("generation_mode", e.target.value)}
              className="w-full bg-[#0d1829] border border-white/[0.08] rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-indigo-500">
              {GENERATION_MODES.map((m) => (
                <option key={m.value} value={m.value}>{m.label}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="text-xs text-slate-400 mb-1 block">Notes</label>
            <textarea value={form.notes} onChange={(e) => upd("notes", e.target.value)} rows={3}
              className="w-full bg-white/[0.04] border border-white/[0.08] rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-indigo-500 resize-none" />
          </div>
        </div>

        {error && (
          <div className="rounded-lg border border-red-500/30 bg-red-500/10 p-3 text-sm text-red-300">{error}</div>
        )}

        <div className="flex justify-end gap-3">
          <button type="button" onClick={() => router.back()}
            className="px-4 py-2 rounded-lg border border-white/[0.08] text-slate-400 text-sm hover:border-white/20">
            Cancel
          </button>
          <button type="submit" disabled={mut.isPending}
            className="px-5 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white text-sm font-medium disabled:opacity-50">
            {mut.isPending ? "Creating..." : "Create Template"}
          </button>
        </div>
      </form>
    </div>
  );
}
