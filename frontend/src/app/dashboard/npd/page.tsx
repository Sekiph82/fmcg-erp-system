"use client";
import { useEffect, useState } from "react";
import Link from "next/link";

interface NPDProject {
  id: string;
  project_code: string;
  name: string;
  category: string;
  stage: string;
  brand: string | null;
  target_launch_date: string | null;
  estimated_cogs: number | null;
  is_active: boolean;
  created_at: string;
}

interface NPDDash {
  total_active: number;
  by_stage: Record<string, number>;
  upcoming_launches: { name: string; stage: string; target_launch_date: string }[];
}

const STAGE_COLOR: Record<string, string> = {
  IDEA: "bg-gray-100 text-gray-600",
  CONCEPT: "bg-blue-100 text-blue-700",
  DEVELOPMENT: "bg-indigo-100 text-indigo-700",
  PILOT: "bg-amber-100 text-amber-700",
  LAUNCH: "bg-orange-100 text-orange-700",
  LAUNCHED: "bg-green-100 text-green-700",
  CANCELLED: "bg-red-100 text-red-600",
};

const STAGE_ORDER = ["IDEA", "CONCEPT", "DEVELOPMENT", "PILOT", "LAUNCH", "LAUNCHED", "CANCELLED"];

const CATEGORIES = ["NEW_PRODUCT", "LINE_EXTENSION", "REFORMULATION", "PACK_SIZE_CHANGE", "COST_REDUCTION"];

interface NewProjectForm {
  name: string;
  category: string;
  brand: string;
  target_market: string;
  target_launch_date: string;
  estimated_cogs: string;
  description: string;
}

export default function NPDPage() {
  const [projects, setProjects] = useState<NPDProject[]>([]);
  const [dash, setDash] = useState<NPDDash | null>(null);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState<NewProjectForm>({
    name: "", category: "NEW_PRODUCT", brand: "", target_market: "",
    target_launch_date: "", estimated_cogs: "", description: "",
  });
  const [saving, setSaving] = useState(false);
  const [filterStage, setFilterStage] = useState("");
  const [error, setError] = useState<string | null>(null);

  const load = () => {
    setLoading(true);
    const params = new URLSearchParams({ limit: "100" });
    if (filterStage) params.set("stage", filterStage);
    Promise.all([
      fetch(`/api/v1/npd-workflow/projects?${params}`).then((r) => r.json()),
      fetch("/api/v1/npd-workflow/dashboard").then((r) => r.json()),
    ]).then(([p, d]) => { setProjects(p); setDash(d); }).finally(() => setLoading(false));
  };

  useEffect(load, [filterStage]);

  const save = async () => {
    setSaving(true);
    setError(null);
    try {
      const r = await fetch("/api/v1/npd-workflow/projects", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          name: form.name,
          category: form.category,
          brand: form.brand || undefined,
          target_market: form.target_market || undefined,
          target_launch_date: form.target_launch_date || undefined,
          estimated_cogs: form.estimated_cogs ? Number(form.estimated_cogs) : undefined,
          description: form.description || undefined,
        }),
      });
      if (!r.ok) throw new Error(await r.text());
      setShowForm(false);
      setForm({ name: "", category: "NEW_PRODUCT", brand: "", target_market: "", target_launch_date: "", estimated_cogs: "", description: "" });
      load();
    } catch (e) { setError(String(e)); }
    setSaving(false);
  };

  return (
    <div className="p-6 space-y-6 max-w-6xl mx-auto">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">New Product Development</h1>
          <p className="text-sm text-gray-500 mt-0.5">Idea → Concept → Development → Pilot → Launch pipeline</p>
        </div>
        <button onClick={() => setShowForm(true)}
          className="bg-blue-600 hover:bg-blue-700 text-white text-sm font-medium px-4 py-2 rounded">
          + New Project
        </button>
      </div>

      {error && <div className="bg-red-50 border border-red-200 rounded p-3 text-sm text-red-700">{error}</div>}

      {/* Dashboard */}
      {dash && (
        <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
          <div className="bg-white border rounded-lg p-4 shadow-sm">
            <p className="text-xs text-gray-500">Total Active</p>
            <p className="text-2xl font-bold mt-1 text-gray-800">{dash.total_active}</p>
          </div>
          {["PILOT", "LAUNCH"].map((s) => (
            <div key={s} className="bg-white border rounded-lg p-4 shadow-sm">
              <p className="text-xs text-gray-500">{s}</p>
              <p className={`text-2xl font-bold mt-1 ${STAGE_COLOR[s]?.split(" ")[1] ?? "text-gray-800"}`}>{dash.by_stage[s] ?? 0}</p>
            </div>
          ))}
          <div className="bg-white border rounded-lg p-4 shadow-sm">
            <p className="text-xs text-gray-500">LAUNCHED</p>
            <p className="text-2xl font-bold mt-1 text-green-600">{dash.by_stage.LAUNCHED ?? 0}</p>
          </div>
        </div>
      )}

      {/* Stage pipeline bar */}
      <div className="flex gap-2 flex-wrap">
        <button onClick={() => setFilterStage("")}
          className={`text-xs rounded-full border px-3 py-1.5 ${!filterStage ? "bg-blue-600 text-white border-blue-600" : "bg-gray-50 text-gray-600 border-gray-300 hover:bg-gray-100"}`}>
          All
        </button>
        {STAGE_ORDER.map((s) => (
          <button key={s} onClick={() => setFilterStage(filterStage === s ? "" : s)}
            className={`text-xs rounded-full border px-3 py-1.5 ${filterStage === s ? "bg-blue-600 text-white border-blue-600" : "bg-gray-50 text-gray-600 border-gray-300 hover:bg-gray-100"}`}>
            {s} {dash?.by_stage[s] ? `(${dash.by_stage[s]})` : ""}
          </button>
        ))}
      </div>

      {/* New project form */}
      {showForm && (
        <div className="bg-white border rounded-lg p-5 shadow-sm space-y-3">
          <h2 className="text-sm font-semibold text-gray-700">New NPD Project</h2>
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
            <div className="sm:col-span-2">
              <label className="text-xs text-gray-500 block mb-1">Product Name *</label>
              <input type="text" value={form.name} onChange={(e) => setForm((p) => ({ ...p, name: e.target.value }))} placeholder="e.g. New Mango Juice 500ml"
                className="w-full border border-gray-300 rounded px-3 py-1.5 text-sm focus:outline-none focus:ring-1 focus:ring-blue-500" />
            </div>
            <div>
              <label className="text-xs text-gray-500 block mb-1">Category</label>
              <select value={form.category} onChange={(e) => setForm((p) => ({ ...p, category: e.target.value }))}
                className="w-full border border-gray-300 rounded px-3 py-1.5 text-sm focus:outline-none">
                {CATEGORIES.map((c) => <option key={c} value={c}>{c.replace(/_/g, " ")}</option>)}
              </select>
            </div>
            <div>
              <label className="text-xs text-gray-500 block mb-1">Brand</label>
              <input type="text" value={form.brand} onChange={(e) => setForm((p) => ({ ...p, brand: e.target.value }))} placeholder="e.g. POVU Naturals"
                className="w-full border border-gray-300 rounded px-3 py-1.5 text-sm focus:outline-none focus:ring-1 focus:ring-blue-500" />
            </div>
            <div>
              <label className="text-xs text-gray-500 block mb-1">Target Launch Date</label>
              <input type="date" value={form.target_launch_date} onChange={(e) => setForm((p) => ({ ...p, target_launch_date: e.target.value }))}
                className="w-full border border-gray-300 rounded px-3 py-1.5 text-sm focus:outline-none" />
            </div>
            <div>
              <label className="text-xs text-gray-500 block mb-1">Est. COGS/Unit (KES)</label>
              <input type="number" step="0.01" value={form.estimated_cogs} onChange={(e) => setForm((p) => ({ ...p, estimated_cogs: e.target.value }))} placeholder="e.g. 25.50"
                className="w-full border border-gray-300 rounded px-3 py-1.5 text-sm focus:outline-none" />
            </div>
            <div className="sm:col-span-2">
              <label className="text-xs text-gray-500 block mb-1">Description</label>
              <input type="text" value={form.description} onChange={(e) => setForm((p) => ({ ...p, description: e.target.value }))} placeholder="Brief description"
                className="w-full border border-gray-300 rounded px-3 py-1.5 text-sm focus:outline-none" />
            </div>
          </div>
          <div className="flex gap-2">
            <button onClick={save} disabled={saving || !form.name}
              className="bg-blue-600 text-white text-sm px-4 py-2 rounded disabled:opacity-50">{saving ? "Creating…" : "Create Project"}</button>
            <button onClick={() => setShowForm(false)} className="border border-gray-300 text-sm px-4 py-2 rounded hover:bg-gray-50">Cancel</button>
          </div>
        </div>
      )}

      {/* Project list */}
      {loading ? <p className="text-gray-400 text-sm">Loading…</p> : (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {projects.map((proj) => (
            <Link key={proj.id} href={`/dashboard/npd/${proj.id}`}
              className="bg-white border rounded-xl p-4 shadow-sm hover:shadow-md transition-shadow space-y-2 block">
              <div className="flex items-start justify-between gap-2">
                <div>
                  <p className="font-semibold text-gray-900 text-sm leading-snug">{proj.name}</p>
                  <p className="text-xs text-gray-400 font-mono">{proj.project_code}</p>
                </div>
                <span className={`text-xs rounded-full px-2 py-0.5 font-medium shrink-0 ${STAGE_COLOR[proj.stage] ?? "bg-gray-100 text-gray-600"}`}>
                  {proj.stage}
                </span>
              </div>
              <div className="flex flex-wrap gap-2 text-xs text-gray-500">
                {proj.brand && <span className="bg-gray-100 rounded px-2 py-0.5">{proj.brand}</span>}
                <span className="bg-gray-100 rounded px-2 py-0.5">{proj.category.replace(/_/g, " ")}</span>
              </div>
              {proj.target_launch_date && (
                <p className="text-xs text-gray-400">Target: {proj.target_launch_date}</p>
              )}
              {proj.estimated_cogs !== null && (
                <p className="text-xs text-gray-500">Est. COGS: KES {proj.estimated_cogs?.toFixed(2)}/unit</p>
              )}
            </Link>
          ))}
          {projects.length === 0 && (
            <div className="col-span-3 bg-gray-50 border rounded-lg p-8 text-center text-sm text-gray-400">
              No NPD projects yet. Create one above.
            </div>
          )}
        </div>
      )}
    </div>
  );
}
