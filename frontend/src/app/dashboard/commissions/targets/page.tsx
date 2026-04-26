"use client";
import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { commissionsApi } from "@/lib/commissions";

export default function TargetsPage() {
  const qc = useQueryClient();
  const today = new Date();
  const currentPeriod = `${today.getFullYear()}-${String(today.getMonth() + 1).padStart(2, "0")}`;
  const [form, setForm] = useState({ entity_id: "", applies_to: "SALES_REP", period: currentPeriod, target_value: "" });
  const upd = (k: string, v: string) => setForm((f) => ({ ...f, [k]: v }));

  const { data: targets = [], isLoading } = useQuery({
    queryKey: ["cm-targets"],
    queryFn: () => commissionsApi.listTargets(),
  });

  const mut = useMutation({
    mutationFn: (data: any) => commissionsApi.upsertTarget(data),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["cm-targets"] }); setForm((f) => ({ ...f, entity_id: "", target_value: "" })); },
  });

  return (
    <div className="p-6 space-y-5 min-h-screen bg-[#060d18] text-slate-200">
      <div>
        <h1 className="text-xl font-bold text-white">Sales Targets & Performance</h1>
        <p className="text-slate-500 text-sm mt-0.5">Track rep targets vs actuals and achievement</p>
      </div>

      {/* Set target */}
      <form onSubmit={(e) => { e.preventDefault(); mut.mutate({ entity_id: form.entity_id, applies_to: form.applies_to, period: form.period, target_value: parseFloat(form.target_value) }); }}
        className="rounded-xl border border-white/[0.07] bg-[#0d1829] p-5 space-y-3">
        <h2 className="text-sm font-semibold text-white">Set / Update Target</h2>
        <div className="grid grid-cols-4 gap-3">
          <div>
            <label className="text-[10px] text-slate-400 mb-1 block">Entity ID (UUID)</label>
            <input value={form.entity_id} onChange={(e) => upd("entity_id", e.target.value)} required
              className="w-full bg-white/[0.04] border border-white/[0.08] rounded px-3 py-2 text-sm text-white focus:outline-none font-mono" />
          </div>
          <div>
            <label className="text-[10px] text-slate-400 mb-1 block">Applies To</label>
            <select value={form.applies_to} onChange={(e) => upd("applies_to", e.target.value)}
              className="w-full bg-[#0d1829] border border-white/[0.08] rounded px-3 py-2 text-sm text-white focus:outline-none">
              {["SALES_REP", "DISTRIBUTOR", "TEAM"].map((a) => <option key={a} value={a}>{a.replace("_", " ")}</option>)}
            </select>
          </div>
          <div>
            <label className="text-[10px] text-slate-400 mb-1 block">Period</label>
            <input value={form.period} onChange={(e) => upd("period", e.target.value)} required
              className="w-full bg-white/[0.04] border border-white/[0.08] rounded px-3 py-2 text-sm text-white focus:outline-none" placeholder="YYYY-MM" />
          </div>
          <div>
            <label className="text-[10px] text-slate-400 mb-1 block">Target (KES)</label>
            <input type="number" value={form.target_value} onChange={(e) => upd("target_value", e.target.value)} required
              className="w-full bg-white/[0.04] border border-white/[0.08] rounded px-3 py-2 text-sm text-white focus:outline-none" />
          </div>
        </div>
        <button type="submit" disabled={mut.isPending}
          className="px-4 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white text-sm font-medium disabled:opacity-50">
          {mut.isPending ? "Saving…" : "Set Target"}
        </button>
      </form>

      {/* Targets table */}
      <div className="rounded-xl border border-white/[0.07] overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-white/[0.03] text-slate-500 text-xs uppercase tracking-wider">
            <tr>
              <th className="px-4 py-3 text-left">Entity</th>
              <th className="px-4 py-3 text-left">Period</th>
              <th className="px-4 py-3 text-left">Type</th>
              <th className="px-4 py-3 text-right">Target</th>
              <th className="px-4 py-3 text-right">Actual</th>
              <th className="px-4 py-3 text-right">Achievement</th>
              <th className="px-4 py-3 text-right">Bonus</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-white/[0.04]">
            {isLoading && <tr><td colSpan={7} className="text-center py-8 text-slate-600">Loading…</td></tr>}
            {targets.map((t) => {
              const ach = t.achievement_pct ?? 0;
              return (
                <tr key={t.id} className="hover:bg-white/[0.02]">
                  <td className="px-4 py-3 text-slate-400 font-mono text-xs">{t.entity_id.slice(0, 8)}…</td>
                  <td className="px-4 py-3 text-slate-300">{t.period}</td>
                  <td className="px-4 py-3 text-slate-400 text-xs">{t.applies_to.replace("_", " ")}</td>
                  <td className="px-4 py-3 text-right text-slate-300">KES {Number(t.target_value).toLocaleString()}</td>
                  <td className="px-4 py-3 text-right text-white font-medium">KES {Number(t.actual_value).toLocaleString()}</td>
                  <td className="px-4 py-3 text-right">
                    <div className="flex items-center justify-end gap-2">
                      <div className="w-16 h-1.5 bg-white/[0.07] rounded-full overflow-hidden">
                        <div className={`h-full rounded-full ${Number(ach) >= 100 ? "bg-emerald-500" : Number(ach) >= 60 ? "bg-amber-500" : "bg-red-500"}`}
                          style={{ width: `${Math.min(100, Number(ach))}%` }} />
                      </div>
                      <span className={`font-medium ${Number(ach) >= 100 ? "text-emerald-400" : Number(ach) >= 60 ? "text-amber-400" : "text-red-400"}`}>
                        {Number(ach).toFixed(1)}%
                      </span>
                    </div>
                  </td>
                  <td className="px-4 py-3 text-right text-emerald-400">{t.bonus_earned ? `KES ${Number(t.bonus_earned).toLocaleString()}` : "—"}</td>
                </tr>
              );
            })}
            {!isLoading && targets.length === 0 && <tr><td colSpan={7} className="text-center py-6 text-slate-600">No targets set</td></tr>}
          </tbody>
        </table>
      </div>
    </div>
  );
}
