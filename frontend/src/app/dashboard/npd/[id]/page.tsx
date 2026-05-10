"use client";
import { useCallback, useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";

interface Gate { id: string; stage: string; department: string; approved_flag: boolean; approved_by: string | null; approved_at: string | null; notes: string | null; }
interface PilotBatch { id: string; batch_ref: string; batch_no: number; qty_produced: number | null; uom: string; outcome: string; actual_cogs: number | null; started_at: string | null; completed_at: string | null; notes: string | null; }

interface Project {
  id: string; project_code: string; name: string; category: string; stage: string;
  description: string | null; target_launch_date: string | null; estimated_cogs: number | null;
  estimated_selling_price: number | null; bom_recipe_id: string | null; brand: string | null;
  regulatory_checklist: Record<string, boolean> | null;
  launch_readiness_checklist: Record<string, boolean> | null;
  stage_gates: Gate[]; pilot_batches: PilotBatch[];
  notes: string | null; created_at: string;
}

const STAGE_COLOR: Record<string, string> = { IDEA: "bg-gray-100 text-gray-600", CONCEPT: "bg-blue-100 text-blue-700", DEVELOPMENT: "bg-indigo-100 text-indigo-700", PILOT: "bg-amber-100 text-amber-700", LAUNCH: "bg-orange-100 text-orange-700", LAUNCHED: "bg-green-100 text-green-700", CANCELLED: "bg-red-100 text-red-600" };
const OUTCOME_COLOR: Record<string, string> = { PASS: "text-green-600", FAIL: "text-red-600", CONDITIONAL: "text-amber-600", IN_PROGRESS: "text-blue-500" };

export default function NPDProjectDetailPage() {
  const { id } = useParams() as { id: string };
  const [proj, setProj] = useState<Project | null>(null);
  const [loading, setLoading] = useState(true);
  const [advancing, setAdvancing] = useState(false);
  const [approving, setApproving] = useState<string | null>(null);
  const [approver, setApprover] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [batchForm, setBatchForm] = useState({ batch_ref: "", qty_produced: "", outcome: "IN_PROGRESS", notes: "" });
  const [addingBatch, setAddingBatch] = useState(false);

  const load = useCallback(() => {
    setLoading(true);
    fetch(`/api/v1/npd-workflow/projects/${id}`).then((r) => r.json()).then(setProj).finally(() => setLoading(false));
  }, [id]);
  useEffect(() => { if (id) load(); }, [id, load]);

  const advance = async () => {
    setAdvancing(true);
    setError(null);
    try {
      const r = await fetch(`/api/v1/npd-workflow/projects/${id}/advance-stage`, { method: "POST" });
      const data = await r.json();
      if (!r.ok) throw new Error(data.detail || JSON.stringify(data));
      load();
    } catch (e) { setError(String(e)); }
    setAdvancing(false);
  };

  const approveGate = async (gateId: string) => {
    if (!approver.trim()) { setError("Enter approver name first."); return; }
    setApproving(gateId);
    try {
      await fetch(`/api/v1/npd-workflow/projects/${id}/gates/${gateId}/approve`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ approved_by: approver }),
      });
      load();
    } catch (e) { setError(String(e)); }
    setApproving(null);
  };

  const toggleChecklist = async (type: string, key: string, val: boolean) => {
    await fetch(`/api/v1/npd-workflow/projects/${id}/checklist`, {
      method: "PATCH", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ checklist_type: type, key, value: val }),
    });
    load();
  };

  const addBatch = async () => {
    setAddingBatch(true);
    try {
      await fetch(`/api/v1/npd-workflow/projects/${id}/pilot-batches`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ batch_ref: batchForm.batch_ref, qty_produced: batchForm.qty_produced ? Number(batchForm.qty_produced) : undefined, outcome: batchForm.outcome, notes: batchForm.notes || undefined }),
      });
      setBatchForm({ batch_ref: "", qty_produced: "", outcome: "IN_PROGRESS", notes: "" });
      load();
    } catch (e) { setError(String(e)); }
    setAddingBatch(false);
  };

  if (loading) return <div className="p-6 text-gray-400 text-sm">Loading…</div>;
  if (!proj) return <div className="p-6 text-red-500 text-sm">Project not found.</div>;

  const currentGates = proj.stage_gates.filter((g) => g.stage === proj.stage);
  const allGatesApproved = currentGates.length > 0 && currentGates.every((g) => g.approved_flag);

  return (
    <div className="p-6 space-y-6 max-w-5xl mx-auto">
      <div className="flex items-center gap-3">
        <Link href="/dashboard/npd" className="text-sm text-blue-600 hover:text-blue-800">← NPD Projects</Link>
        <span className="text-gray-300">/</span>
        <span className="text-sm text-gray-500">{proj.project_code}</span>
      </div>

      {error && <div className="bg-red-50 border border-red-200 rounded p-3 text-sm text-red-700">{error}</div>}

      {/* Header */}
      <div className="bg-white border rounded-xl p-5 shadow-sm space-y-3">
        <div className="flex items-start justify-between gap-4 flex-wrap">
          <div>
            <h1 className="text-xl font-bold text-gray-900">{proj.name}</h1>
            <p className="text-sm text-gray-500 mt-0.5">{proj.category.replace(/_/g, " ")} {proj.brand ? `· ${proj.brand}` : ""}</p>
          </div>
          <div className="flex items-center gap-3">
            <span className={`text-sm font-semibold rounded-full px-3 py-1 ${STAGE_COLOR[proj.stage] ?? "bg-gray-100 text-gray-600"}`}>{proj.stage}</span>
            <button onClick={advance} disabled={advancing || !allGatesApproved}
              className="bg-blue-600 hover:bg-blue-700 text-white text-sm px-4 py-2 rounded disabled:opacity-40">
              {advancing ? "Advancing…" : "Advance Stage →"}
            </button>
          </div>
        </div>
        {!allGatesApproved && currentGates.length > 0 && (
          <p className="text-xs text-amber-700 bg-amber-50 border border-amber-200 rounded px-3 py-1.5">
            Approve all current stage gates before advancing. Unapproved: {currentGates.filter((g) => !g.approved_flag).map((g) => g.department).join(", ")}
          </p>
        )}
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-4 text-sm">
          {proj.target_launch_date && <div><p className="text-xs text-gray-400">Target Launch</p><p className="font-medium">{proj.target_launch_date}</p></div>}
          {proj.estimated_cogs !== null && <div><p className="text-xs text-gray-400">Est. COGS/unit</p><p className="font-medium">KES {proj.estimated_cogs?.toFixed(2)}</p></div>}
          {proj.estimated_selling_price !== null && <div><p className="text-xs text-gray-400">Est. Price</p><p className="font-medium">KES {proj.estimated_selling_price?.toFixed(2)}</p></div>}
          {proj.bom_recipe_id && <div><p className="text-xs text-gray-400">BOM/Recipe</p><p className="font-mono text-xs">{proj.bom_recipe_id}</p></div>}
        </div>
      </div>

      {/* Approver input */}
      <div className="flex items-center gap-3">
        <label className="text-xs text-gray-500">Approver Name:</label>
        <input type="text" value={approver} onChange={(e) => setApprover(e.target.value)} placeholder="Your name"
          className="border border-gray-300 rounded px-3 py-1 text-sm focus:outline-none focus:ring-1 focus:ring-blue-500 w-48" />
      </div>

      {/* Stage Gates */}
      <div className="bg-white border rounded-lg shadow-sm overflow-hidden">
        <div className="px-4 py-3 border-b bg-gray-50">
          <h2 className="text-sm font-semibold text-gray-700">Stage Gates — {proj.stage}</h2>
        </div>
        <div className="divide-y">
          {currentGates.map((g) => (
            <div key={g.id} className="px-4 py-3 flex items-center gap-4">
              <div className="flex-1">
                <p className="text-sm font-medium text-gray-900">{g.department}</p>
                {g.approved_by && <p className="text-xs text-gray-400">Approved by {g.approved_by} · {g.approved_at?.slice(0, 10)}</p>}
              </div>
              {g.approved_flag ? (
                <span className="text-xs text-green-600 bg-green-100 rounded-full px-3 py-1 font-medium">✓ Approved</span>
              ) : (
                <button onClick={() => approveGate(g.id)} disabled={approving === g.id || !approver.trim()}
                  className="text-xs bg-blue-600 hover:bg-blue-700 text-white rounded px-3 py-1 disabled:opacity-50">
                  {approving === g.id ? "…" : "Approve"}
                </button>
              )}
            </div>
          ))}
          {currentGates.length === 0 && <div className="px-4 py-4 text-sm text-gray-400">No gates configured for this stage.</div>}
        </div>
      </div>

      {/* Checklists */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        {[
          { title: "Regulatory Checklist", type: "regulatory", data: proj.regulatory_checklist },
          { title: "Launch Readiness", type: "launch", data: proj.launch_readiness_checklist },
        ].map(({ title, type, data }) => (
          <div key={type} className="bg-white border rounded-lg shadow-sm overflow-hidden">
            <div className="px-4 py-3 border-b bg-gray-50"><h2 className="text-sm font-semibold text-gray-700">{title}</h2></div>
            <div className="px-4 py-3 space-y-2">
              {Object.entries(data ?? {}).map(([key, val]) => (
                <label key={key} className="flex items-center gap-2 cursor-pointer">
                  <input type="checkbox" checked={val} onChange={(e) => toggleChecklist(type, key, e.target.checked)} className="h-4 w-4" />
                  <span className="text-sm text-gray-700 capitalize">{key.replace(/_/g, " ")}</span>
                </label>
              ))}
            </div>
          </div>
        ))}
      </div>

      {/* Pilot Batches */}
      <div className="bg-white border rounded-lg shadow-sm overflow-hidden">
        <div className="px-4 py-3 border-b bg-gray-50 flex items-center justify-between">
          <h2 className="text-sm font-semibold text-gray-700">Pilot Batches</h2>
        </div>
        <div className="divide-y">
          {proj.pilot_batches.map((b) => (
            <div key={b.id} className="px-4 py-3 flex items-center gap-4">
              <span className="font-mono text-xs text-blue-600">Batch #{b.batch_no}</span>
              <div className="flex-1">
                <p className="text-sm font-medium text-gray-900">{b.batch_ref}</p>
                {b.qty_produced && <p className="text-xs text-gray-400">{b.qty_produced} {b.uom}{b.actual_cogs ? ` · COGS: KES ${b.actual_cogs.toFixed(2)}/unit` : ""}</p>}
              </div>
              <span className={`text-xs font-medium ${OUTCOME_COLOR[b.outcome] ?? "text-gray-500"}`}>{b.outcome}</span>
            </div>
          ))}
          {proj.pilot_batches.length === 0 && <div className="px-4 py-4 text-sm text-gray-400">No pilot batches yet.</div>}
        </div>
        {/* Add batch */}
        <div className="px-4 py-3 border-t bg-gray-50 flex items-end gap-3 flex-wrap">
          <div>
            <label className="text-xs text-gray-500 block mb-1">Batch Ref</label>
            <input type="text" value={batchForm.batch_ref} onChange={(e) => setBatchForm((p) => ({ ...p, batch_ref: e.target.value }))} placeholder="e.g. PILOT-001"
              className="border border-gray-300 rounded px-2 py-1 text-sm w-32 focus:outline-none" />
          </div>
          <div>
            <label className="text-xs text-gray-500 block mb-1">Qty</label>
            <input type="number" value={batchForm.qty_produced} onChange={(e) => setBatchForm((p) => ({ ...p, qty_produced: e.target.value }))} placeholder="kg"
              className="border border-gray-300 rounded px-2 py-1 text-sm w-20 focus:outline-none" />
          </div>
          <div>
            <label className="text-xs text-gray-500 block mb-1">Outcome</label>
            <select value={batchForm.outcome} onChange={(e) => setBatchForm((p) => ({ ...p, outcome: e.target.value }))}
              className="border border-gray-300 rounded px-2 py-1 text-sm focus:outline-none">
              <option value="IN_PROGRESS">In Progress</option>
              <option value="PASS">Pass</option>
              <option value="FAIL">Fail</option>
              <option value="CONDITIONAL">Conditional</option>
            </select>
          </div>
          <button onClick={addBatch} disabled={addingBatch || !batchForm.batch_ref}
            className="bg-green-600 text-white text-xs px-3 py-2 rounded disabled:opacity-50">
            {addingBatch ? "Adding…" : "Add Batch"}
          </button>
        </div>
      </div>
    </div>
  );
}
