"use client";
// M43.S01.T014: lead routing rules, stage approval rules + pending approvals, won-deal handoffs.
import { useCallback, useEffect, useState } from "react";
import { apiClient } from "@/lib/api";
import { EntityPicker } from "@/components/EntityPicker";
import { tx } from "@/lib/i18n/core";

interface Rule { id: string; name: string; priority: number; method: string; conditions: Record<string, string>; user_ids: string[] }
interface Approval { id: string; record_id: string; stage_id: string; requested_at: string }
interface Handoff { id: string; record_id: string; status: string; created_at: string;
  brief: { customer: string; value: string; contacts: string[]; promises: string[]; open_tasks: string[] } }

const err = (e: unknown, fb: string) => {
  const d = (e as { response?: { data?: { detail?: unknown } } }).response?.data?.detail;
  return typeof d === "string" ? d : fb;
};

export default function CRMRoutingPage() {
  const [rules, setRules] = useState<Rule[]>([]);
  const [approvals, setApprovals] = useState<Approval[]>([]);
  const [handoffs, setHandoffs] = useState<Handoff[]>([]);
  const [msg, setMsg] = useState<string | null>(null);
  const [rule, setRule] = useState({ name: "", priority: 100, method: "ROUND_ROBIN", source_type: "", sales_region_id: "", users: [] as string[] });
  const [pick, setPick] = useState("");
  const [ap, setAp] = useState({ name: "", stage_id: "", min_expected_revenue: "" });
  const load = useCallback(() => {
    apiClient.get("/api/v1/crm-routing/rules").then((r) => setRules(r.data)).catch(() => setRules([]));
    apiClient.get("/api/v1/crm-routing/approvals").then((r) => setApprovals(r.data)).catch(() => setApprovals([]));
    apiClient.get("/api/v1/crm-routing/handoffs").then((r) => setHandoffs(r.data)).catch(() => setHandoffs([]));
  }, []);
  useEffect(() => { load(); }, [load]);
  const act = async (fn: () => Promise<unknown>, ok: string) => { try { await fn(); setMsg(ok); load(); } catch (e) { setMsg(err(e, "Not allowed.")); } };

  return (
    <div className="p-4 grid lg:grid-cols-3 gap-4 text-xs">
      {msg && <p role="status" className="lg:col-span-3 text-sm">{msg}</p>}
      <section className="border rounded bg-white p-3 space-y-2">
        <h3 className="text-sm font-semibold">{tx("Lead routing")}</h3>
        {rules.map((r) => <div key={r.id} className="border-b py-1">{r.priority}. {r.name} · {r.method.replace("_", " ").toLowerCase()} · {r.user_ids.length} {tx("people")}
          {Object.entries(r.conditions).filter(([, v]) => v).map(([k, v]) => <span key={k} className="text-gray-500"> · {k}={v}</span>)}
          <button className="ml-2 text-red-600" onClick={() => act(() => apiClient.delete(`/api/v1/crm-routing/rules/${r.id}`), "Rule removed.")}>×</button></div>)}
        <form className="space-y-1" onSubmit={(e) => { e.preventDefault();
          act(() => apiClient.post("/api/v1/crm-routing/rules", { name: rule.name, priority: rule.priority, method: rule.method, user_ids: rule.users,
            conditions: { source_type: rule.source_type || null, sales_region_id: rule.sales_region_id || null } }), "Rule added."); }}>
          <input required className="border rounded px-2 py-1 w-full" placeholder={tx("Rule name")} value={rule.name} onChange={(e) => setRule({ ...rule, name: e.target.value })} />
          <div className="flex gap-1">
            <select className="border rounded px-1" value={rule.method} onChange={(e) => setRule({ ...rule, method: e.target.value })}>
              <option value="ROUND_ROBIN">{tx("Round robin")}</option><option value="WEIGHTED">{tx("Weighted")}</option><option value="FIXED">{tx("Fixed")}</option></select>
            <input type="number" className="border rounded px-1 w-16" aria-label={tx("Priority")} value={rule.priority} onChange={(e) => setRule({ ...rule, priority: +e.target.value })} />
          </div>
          <input className="border rounded px-2 py-1 w-full" placeholder={tx("Only source (e.g. WEBSITE)")} value={rule.source_type} onChange={(e) => setRule({ ...rule, source_type: e.target.value })} />
          <input className="border rounded px-2 py-1 w-full" placeholder={tx("Only region")} value={rule.sales_region_id} onChange={(e) => setRule({ ...rule, sales_region_id: e.target.value })} />
          <div>{rule.users.length} {tx("people")} <button type="button" className="text-red-600" onClick={() => setRule({ ...rule, users: [] })}>{tx("clear")}</button></div>
          <EntityPicker kind="user" value={pick} onChange={(id) => { if (id && !rule.users.includes(id)) setRule({ ...rule, users: [...rule.users, id] }); setPick(""); }} placeholder={tx("Add a person…")} />
          <button className="bg-indigo-600 text-white rounded px-3 py-1" disabled={!rule.users.length}>{tx("Add rule")}</button>
        </form>
      </section>
      <section className="border rounded bg-white p-3 space-y-2">
        <h3 className="text-sm font-semibold">{tx("Stage approvals")}</h3>
        {approvals.length === 0 && <p className="text-gray-500">{tx("Nothing waiting.")}</p>}
        {approvals.map((a) => (
          <div key={a.id} className="border-b py-1 flex flex-wrap gap-2 items-center">{tx("Deal")} {a.record_id.slice(0, 8)} {tx("→ stage")} {a.stage_id.slice(0, 8)} · {new Date(a.requested_at).toLocaleString()}
            <button className="text-green-700 underline" onClick={() => act(() => apiClient.post(`/api/v1/crm-routing/approvals/${a.id}/decision`, { approve: true }), "Approved.")}>{tx("Approve")}</button>
            <button className="underline" onClick={() => { const reason = prompt(tx("Reason?")) ?? ""; act(() => apiClient.post(`/api/v1/crm-routing/approvals/${a.id}/decision`, { approve: false, reason }), "Rejected."); }}>{tx("Reject")}</button>
          </div>))}
        <form className="space-y-1 pt-2 border-t" onSubmit={(e) => { e.preventDefault();
          act(() => apiClient.post("/api/v1/crm-routing/approval-rules", { name: ap.name, stage_id: ap.stage_id, min_expected_revenue: ap.min_expected_revenue ? +ap.min_expected_revenue : null }), "Approval rule added."); }}>
          <input required className="border rounded px-2 py-1 w-full" placeholder={tx("Rule name, e.g. Large deal sign-off")} value={ap.name} onChange={(e) => setAp({ ...ap, name: e.target.value })} />
          <input required className="border rounded px-2 py-1 w-full" placeholder={tx("Stage id that needs approval to enter")} value={ap.stage_id} onChange={(e) => setAp({ ...ap, stage_id: e.target.value })} />
          <input type="number" className="border rounded px-2 py-1 w-full" placeholder={tx("Only above expected value")} value={ap.min_expected_revenue} onChange={(e) => setAp({ ...ap, min_expected_revenue: e.target.value })} />
          <button className="border rounded px-2 py-1">{tx("Add approval rule")}</button>
        </form>
      </section>
      <section className="border rounded bg-white p-3 space-y-2">
        <h3 className="text-sm font-semibold">{tx("Won-deal handoffs")}</h3>
        {handoffs.length === 0 && <p className="text-gray-500">{tx("No open handoffs.")}</p>}
        {handoffs.map((h) => (
          <div key={h.id} className="border rounded p-2 space-y-1">
            <div className="font-medium">{h.brief.customer} · {h.brief.value}</div>
            {h.brief.contacts.length > 0 && <div>{tx("Contacts:")} {h.brief.contacts.join("; ")}</div>}
            {h.brief.promises.length > 0 && <div>{tx("Promised by us:")} {h.brief.promises.join("; ")}</div>}
            {h.brief.open_tasks.length > 0 && <div>{tx("Open tasks:")} {h.brief.open_tasks.join("; ")}</div>}
            <button className="underline" onClick={() => act(() => apiClient.post(`/api/v1/crm-routing/handoffs/${h.id}/acknowledge`), "Handoff taken over.")}>{tx("Take over")}</button>
          </div>))}
      </section>
    </div>
  );
}
