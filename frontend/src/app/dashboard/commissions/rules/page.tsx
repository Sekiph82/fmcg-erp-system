"use client";
import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { commissionsApi, RULE_STATUS_COLORS, RuleStatus } from "@/lib/commissions";

const APPLIES = ["SALES_REP", "DISTRIBUTOR", "TEAM"];
const SCOPES = ["GLOBAL", "CUSTOMER", "PRODUCT", "CATEGORY", "CHANNEL", "REGION", "BRAND"];

export default function RulesPage() {
  const qc = useQueryClient();
  const [filter, setFilter] = useState("");
  const [showNew, setShowNew] = useState(false);
  const [form, setForm] = useState({
    rule_code: "", rule_name: "", applies_to: "SALES_REP", applicable_scope: "GLOBAL",
    priority: "10", start_date: "", end_date: "",
    line_condition: "VALUE", line_type: "PERCENTAGE", line_value: "", notes: "",
  });

  const { data: rules = [], isLoading } = useQuery({
    queryKey: ["cm-rules", filter],
    queryFn: () => commissionsApi.listRules({ applies_to: filter || undefined }),
  });

  const createMut = useMutation({
    mutationFn: (data: any) => commissionsApi.createRule(data),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["cm-rules"] }); setShowNew(false); },
  });

  const activateMut = useMutation({
    mutationFn: (id: string) => commissionsApi.activateRule(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["cm-rules"] }),
  });

  const upd = (k: string, v: string) => setForm((f) => ({ ...f, [k]: v }));

  const handleCreate = (e: React.FormEvent) => {
    e.preventDefault();
    createMut.mutate({
      rule_code: form.rule_code,
      rule_name: form.rule_name,
      applies_to: form.applies_to,
      applicable_scope: form.applicable_scope,
      priority: parseInt(form.priority) || 10,
      start_date: form.start_date,
      end_date: form.end_date || undefined,
      notes: form.notes || undefined,
      lines: form.line_value ? [{
        condition_type: form.line_condition,
        commission_type: form.line_type,
        commission_value: parseFloat(form.line_value),
      }] : [],
    });
  };

  return (
    <div className="p-6 space-y-5 text-slate-200">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-white">Commission Rules</h1>
          <p className="text-slate-500 text-sm mt-0.5">{rules.length} rules</p>
        </div>
        <button onClick={() => setShowNew(true)}
          className="px-4 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white text-sm font-medium">
          + New Rule
        </button>
      </div>

      <div className="flex gap-2">
        {["", ...APPLIES].map((a) => (
          <button key={a} onClick={() => setFilter(a)}
            className={`px-3 py-1.5 rounded-lg text-xs font-medium border transition-colors ${filter === a ? "bg-indigo-600 border-indigo-500 text-white" : "border-white/[0.08] text-slate-400 hover:border-white/20"}`}>
            {a || "All"}
          </button>
        ))}
      </div>

      {/* New rule form */}
      {showNew && (
        <form onSubmit={handleCreate} className="glow-card p-5 space-y-4">
          <h2 className="text-sm font-semibold text-white">New Commission Rule</h2>
          <div className="grid grid-cols-2 gap-3">
            {[
              { k: "rule_code", label: "Rule Code *", placeholder: "CR-BASIC-001" },
              { k: "rule_name", label: "Rule Name *", placeholder: "Basic Sales Rep Commission" },
            ].map(({ k, label, placeholder }) => (
              <div key={k}>
                <label className="text-[10px] text-slate-400 mb-1 block">{label}</label>
                <input value={(form as any)[k]} onChange={(e) => upd(k, e.target.value)} required placeholder={placeholder}
                  className="w-full bg-white/[0.04] border border-white/[0.08] rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-indigo-500" />
              </div>
            ))}
            <div>
              <label className="text-[10px] text-slate-400 mb-1 block">Applies To</label>
              <select value={form.applies_to} onChange={(e) => upd("applies_to", e.target.value)}
                className="w-full bg-[#0d1829] border border-white/[0.08] rounded-lg px-3 py-2 text-sm text-white focus:outline-none">
                {APPLIES.map((a) => <option key={a} value={a}>{a.replace("_", " ")}</option>)}
              </select>
            </div>
            <div>
              <label className="text-[10px] text-slate-400 mb-1 block">Scope</label>
              <select value={form.applicable_scope} onChange={(e) => upd("applicable_scope", e.target.value)}
                className="w-full bg-[#0d1829] border border-white/[0.08] rounded-lg px-3 py-2 text-sm text-white focus:outline-none">
                {SCOPES.map((s) => <option key={s} value={s}>{s}</option>)}
              </select>
            </div>
            <div>
              <label className="text-[10px] text-slate-400 mb-1 block">Start Date *</label>
              <input type="date" value={form.start_date} onChange={(e) => upd("start_date", e.target.value)} required
                className="w-full bg-white/[0.04] border border-white/[0.08] rounded-lg px-3 py-2 text-sm text-white focus:outline-none" />
            </div>
            <div>
              <label className="text-[10px] text-slate-400 mb-1 block">Priority (lower = higher)</label>
              <input type="number" value={form.priority} onChange={(e) => upd("priority", e.target.value)}
                className="w-full bg-white/[0.04] border border-white/[0.08] rounded-lg px-3 py-2 text-sm text-white focus:outline-none" min={1} />
            </div>
          </div>
          <div className="border-t border-white/[0.07] pt-3">
            <p className="text-xs text-slate-400 mb-2">Default Rule Line</p>
            <div className="grid grid-cols-3 gap-3">
              <div>
                <label className="text-[10px] text-slate-500 mb-1 block">Condition</label>
                <select value={form.line_condition} onChange={(e) => upd("line_condition", e.target.value)}
                  className="w-full bg-[#0d1829] border border-white/[0.08] rounded px-2 py-1.5 text-xs text-white focus:outline-none">
                  {["VALUE","VOLUME","PRODUCT","CATEGORY","TARGET"].map((c) => <option key={c} value={c}>{c}</option>)}
                </select>
              </div>
              <div>
                <label className="text-[10px] text-slate-500 mb-1 block">Type</label>
                <select value={form.line_type} onChange={(e) => upd("line_type", e.target.value)}
                  className="w-full bg-[#0d1829] border border-white/[0.08] rounded px-2 py-1.5 text-xs text-white focus:outline-none">
                  {["PERCENTAGE","FIXED"].map((t) => <option key={t} value={t}>{t}</option>)}
                </select>
              </div>
              <div>
                <label className="text-[10px] text-slate-500 mb-1 block">Value (% or KES)</label>
                <input type="number" value={form.line_value} onChange={(e) => upd("line_value", e.target.value)}
                  className="w-full bg-white/[0.04] border border-white/[0.08] rounded px-2 py-1.5 text-xs text-white focus:outline-none" min={0} step={0.01} placeholder="e.g. 3.5" />
              </div>
            </div>
          </div>
          <div className="flex gap-2">
            <button type="submit" disabled={createMut.isPending}
              className="px-4 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white text-sm font-medium disabled:opacity-50">
              {createMut.isPending ? "Creating…" : "Create Rule"}
            </button>
            <button type="button" onClick={() => setShowNew(false)}
              className="px-4 py-2 rounded-lg border border-white/[0.08] text-slate-400 text-sm">Cancel</button>
          </div>
        </form>
      )}

      {/* Rules table */}
      <div className="rounded-xl border border-white/[0.07] overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-white/[0.03] text-slate-500 text-xs uppercase tracking-wider">
            <tr>
              <th className="px-4 py-3 text-left">Code</th>
              <th className="px-4 py-3 text-left">Name</th>
              <th className="px-4 py-3 text-left">Applies To</th>
              <th className="px-4 py-3 text-left">Scope</th>
              <th className="px-4 py-3 text-right">Priority</th>
              <th className="px-4 py-3 text-left">Lines</th>
              <th className="px-4 py-3 text-left">Status</th>
              <th className="px-4 py-3 text-left">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-white/[0.04]">
            {isLoading && <tr><td colSpan={8} className="text-center py-8 text-slate-600">Loading…</td></tr>}
            {!isLoading && rules.length === 0 && <tr><td colSpan={8} className="text-center py-8 text-slate-600">No rules</td></tr>}
            {rules.map((r) => (
              <tr key={r.id} className="hover:bg-white/[0.02]">
                <td className="px-4 py-3 font-mono text-xs text-indigo-300">{r.rule_code}</td>
                <td className="px-4 py-3 text-white">{r.rule_name}</td>
                <td className="px-4 py-3 text-slate-400 text-xs">{r.applies_to.replace("_", " ")}</td>
                <td className="px-4 py-3 text-slate-400 text-xs">{r.applicable_scope}</td>
                <td className="px-4 py-3 text-right text-slate-400">{r.priority}</td>
                <td className="px-4 py-3 text-slate-400">{r.lines.length}</td>
                <td className="px-4 py-3">
                  <span className={`text-[10px] px-2 py-0.5 rounded-full font-medium ${RULE_STATUS_COLORS[r.status]}`}>{r.status}</span>
                </td>
                <td className="px-4 py-3">
                  {r.status === "DRAFT" && (
                    <button onClick={() => activateMut.mutate(r.id)}
                      className="text-xs text-emerald-400 hover:text-emerald-300">Activate</button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
