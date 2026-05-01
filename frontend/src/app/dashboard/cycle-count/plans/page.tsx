"use client";

import { useEffect, useState } from "react";
import { listPlans, createPlan, updatePlan, generateTasks, CycleCountPlan, PlanStatus, PlanType, PLAN_STATUS_BADGE } from "@/lib/cycleCount";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";

const PLAN_TYPES: PlanType[] = ["abc", "random", "location", "item", "frequency"];

export default function PlansPage() {
  const [plans, setPlans] = useState<CycleCountPlan[]>([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [saving, setSaving] = useState(false);
  const [generating, setGenerating] = useState<string | null>(null);
  const [msg, setMsg] = useState("");
  const [error, setError] = useState("");
  const [form, setForm] = useState<Record<string, string>>({
    plan_type: "abc",
    abc_classes: "ABC",
    variance_tolerance_pct: "2.0",
  });

  useEffect(() => { load(); }, []);
  async function load() {
    setLoading(true);
    try { setPlans(await listPlans()); } catch {}
    setLoading(false);
  }

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault(); setError(""); setSaving(true);
    try {
      await createPlan({ ...form });
      setShowForm(false); setForm({ plan_type: "abc", abc_classes: "ABC", variance_tolerance_pct: "2.0" });
      await load();
    } catch (err: unknown) {
      const e2 = err as { response?: { data?: { detail?: string } } };
      setError(e2?.response?.data?.detail || "Failed to create plan");
    }
    setSaving(false);
  }

  async function handleGenerate(id: string) {
    setGenerating(id);
    try {
      const r = await generateTasks(id);
      setMsg(`Generated ${r.generated} task(s)`);
      await load();
    } catch { setMsg("Generate failed"); }
    setGenerating(null);
  }

  async function handleStatusChange(id: string, status: PlanStatus) {
    await updatePlan(id, { status });
    await load();
  }

  return (
    <div className="max-w-5xl mx-auto py-8 px-4 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Count Plans</h1>
          <p className="text-sm text-gray-500 mt-1">{plans.length} plan(s)</p>
        </div>
        <Button onClick={() => setShowForm(!showForm)}>{showForm ? "Cancel" : "New Plan"}</Button>
      </div>

      {msg && <div className="bg-blue-50 border border-blue-200 text-blue-700 text-sm rounded-lg px-4 py-2">{msg}</div>}

      {showForm && (
        <div className="bg-white rounded-2xl border border-gray-200 p-6">
          <form onSubmit={handleCreate} className="grid grid-cols-2 gap-4">
            <Input id="code" label="Plan Code" value={form.plan_code || ""} onChange={(e) => setForm({ ...form, plan_code: e.target.value })} placeholder="Auto-generated if blank" />
            <Input id="name" label="Plan Name" value={form.name || ""} onChange={(e) => setForm({ ...form, name: e.target.value })} required />
            <Input id="wh" label="Warehouse ID" value={form.warehouse_id || ""} onChange={(e) => setForm({ ...form, warehouse_id: e.target.value })} required placeholder="UUID" />
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Plan Type</label>
              <select className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm capitalize" value={form.plan_type} onChange={(e) => setForm({ ...form, plan_type: e.target.value })}>
                {PLAN_TYPES.map((t) => <option key={t} value={t}>{t}</option>)}
              </select>
            </div>
            {(form.plan_type === "abc" || form.plan_type === "frequency") && (
              <Input id="abc" label="ABC Classes (e.g. AB)" value={form.abc_classes} onChange={(e) => setForm({ ...form, abc_classes: e.target.value })} />
            )}
            <Input id="tol" label="Variance Tolerance %" type="number" step="0.1" value={form.variance_tolerance_pct} onChange={(e) => setForm({ ...form, variance_tolerance_pct: e.target.value })} />
            <Input id="freq" label="Frequency (days)" type="number" value={form.frequency_days || ""} onChange={(e) => setForm({ ...form, frequency_days: e.target.value })} />
            {error && <div className="col-span-2 text-sm text-red-600 bg-red-50 border border-red-200 rounded px-3 py-2">{error}</div>}
            <div className="col-span-2 flex justify-end gap-3">
              <Button variant="secondary" type="button" onClick={() => setShowForm(false)}>Cancel</Button>
              <Button type="submit" loading={saving}>Create Plan</Button>
            </div>
          </form>
        </div>
      )}

      {loading ? <div className="text-gray-500 py-8 text-center">Loading...</div> : (
        <div className="space-y-3">
          {plans.map((p) => (
            <div key={p.id} className="bg-white rounded-xl border border-gray-200 p-5">
              <div className="flex items-start justify-between">
                <div className="space-y-1">
                  <div className="flex items-center gap-2">
                    <span className="font-mono text-xs text-indigo-700">{p.plan_code}</span>
                    <span className="font-semibold text-gray-900">{p.name}</span>
                    <span className={`text-xs px-2 py-0.5 rounded font-medium capitalize ${PLAN_STATUS_BADGE[p.status]}`}>{p.status}</span>
                  </div>
                  <div className="flex gap-4 text-xs text-gray-500">
                    <span className="capitalize">Type: {p.plan_type}</span>
                    {p.abc_classes && <span>ABC: {p.abc_classes}</span>}
                    {p.frequency_days && <span>Every {p.frequency_days}d</span>}
                    <span>Tolerance: {p.variance_tolerance_pct}%</span>
                    {p.auto_approve_within_tolerance && <span className="text-green-600">Auto-approve</span>}
                  </div>
                </div>
                <div className="flex gap-2 items-center">
                  <select className="text-xs border border-gray-200 rounded px-2 py-1 capitalize" value={p.status} onChange={(e) => handleStatusChange(p.id, e.target.value as PlanStatus)}>
                    {["draft", "active", "paused", "completed"].map((s) => <option key={s} value={s}>{s}</option>)}
                  </select>
                  <Button variant="secondary" onClick={() => handleGenerate(p.id)} loading={generating === p.id}>
                    Generate Tasks
                  </Button>
                </div>
              </div>
            </div>
          ))}
          {plans.length === 0 && <div className="text-center py-12 text-gray-400">No plans yet. Create one to start cycle counting.</div>}
        </div>
      )}
    </div>
  );
}
