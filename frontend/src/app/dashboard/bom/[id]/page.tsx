"use client";

import { useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  bomApi, BOMOut, BOMLineOut, YieldConfigOut, BOMAIRecOut,
  ComponentType, BasisType, ItemLinkType, SubstitutionPolicy, LossCategory,
  LIFECYCLE_COLOR, BOM_TYPE_COLOR, COMPONENT_COLOR, AGENT_COLOR, AGENT_LABEL,
  LIFECYCLE_NEXT, fmtKES,
} from "@/lib/bom";

const TABS = ["Overview", "Formula", "Yield", "AI Recs"] as const;
type Tab = typeof TABS[number];

const COMPONENT_TYPES: ComponentType[] = ["RAW", "INTERMEDIATE", "PACKAGING", "SERVICE", "CO_PRODUCT", "BY_PRODUCT", "UTILITY", "REWORK"];
const BASIS_TYPES: BasisType[] = ["PER_BATCH", "PER_UNIT", "PER_100KG", "PER_1000L", "PERCENTAGE", "FIXED"];
const LOSS_CATEGORIES: LossCategory[] = ["PROCESS_LOSS", "EVAPORATION", "TRANSFER", "STARTUP", "SHUTDOWN", "FILLING", "PACKAGING_REJECT", "QC_REJECTION", "LINE_PURGE"];

const emptyLine: Partial<BOMLineOut> = {
  component_type: "RAW", item_type: "MATERIAL", required_qty: 1, required_uom: "KG",
  basis_type: "PER_BATCH", wastage_pct: 0, process_loss_pct: 0,
  fixed_consumption: false, is_optional: false, qc_required: false,
  allergen_flag: false, critical_component: false, substitution_policy: "NO_SUB",
};

export default function BOMDetailPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const qc = useQueryClient();
  const [tab, setTab] = useState<Tab>("Overview");
  const [showAddLine, setShowAddLine] = useState(false);
  const [editLineId, setEditLineId] = useState<string | null>(null);
  const [lineForm, setLineForm] = useState<Partial<BOMLineOut>>(emptyLine);
  const [showAddYield, setShowAddYield] = useState(false);
  const [yieldForm, setYieldForm] = useState<Partial<YieldConfigOut>>({
    loss_category: "PROCESS_LOSS", standard_pct: 1, cost_impact_flag: true,
  });
  const [showClone, setShowClone] = useState(false);
  const [cloneVersion, setCloneVersion] = useState("");
  const [scalingQty, setScalingQty] = useState("");
  const [scalingResult, setScalingResult] = useState<any>(null);

  const { data: bom, isLoading } = useQuery<BOMOut>({
    queryKey: ["bom", id],
    queryFn: () => bomApi.get(id),
  });

  const { data: aiRecs = [] } = useQuery<BOMAIRecOut[]>({
    queryKey: ["bom-ai", id],
    queryFn: () => bomApi.listAI(id),
    enabled: tab === "AI Recs",
  });

  const invalidate = () => {
    qc.invalidateQueries({ queryKey: ["bom", id] });
    qc.invalidateQueries({ queryKey: ["boms"] });
    qc.invalidateQueries({ queryKey: ["bom-dashboard"] });
  };

  const advance = useMutation({
    mutationFn: () => bomApi.advance(id),
    onSuccess: invalidate,
  });

  const archive = useMutation({
    mutationFn: () => bomApi.archive(id),
    onSuccess: invalidate,
  });

  const clone = useMutation({
    mutationFn: () => bomApi.clone(id, cloneVersion),
    onSuccess: (newBom) => {
      invalidate();
      setShowClone(false);
      router.push(`/dashboard/bom/${newBom.id}`);
    },
  });

  const runAI = useMutation({
    mutationFn: () => bomApi.runAI(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["bom-ai", id] }),
  });

  const addLine = useMutation({
    mutationFn: () => bomApi.addLine(id, lineForm),
    onSuccess: () => { invalidate(); setShowAddLine(false); setLineForm(emptyLine); },
  });

  const updateLine = useMutation({
    mutationFn: ({ lineId, body }: { lineId: string; body: Partial<BOMLineOut> }) =>
      bomApi.updateLine(lineId, body),
    onSuccess: () => { invalidate(); setEditLineId(null); },
  });

  const deleteLine = useMutation({
    mutationFn: (lineId: string) => bomApi.deleteLine(lineId),
    onSuccess: invalidate,
  });

  const addYield = useMutation({
    mutationFn: () => bomApi.addYield(id, yieldForm),
    onSuccess: () => { invalidate(); setShowAddYield(false); setYieldForm({ loss_category: "PROCESS_LOSS", standard_pct: 1, cost_impact_flag: true }); },
  });

  const actionAI = useMutation({
    mutationFn: ({ recId, status }: { recId: string; status: "ACCEPTED" | "REJECTED" }) =>
      bomApi.actionAI(recId, status),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["bom-ai", id] }),
  });

  const doScale = async () => {
    if (!scalingQty) return;
    const res = await bomApi.scale(id, Number(scalingQty));
    setScalingResult(res);
  };

  if (isLoading) return <div className="p-8 text-center text-gray-400">Loading BOM…</div>;
  if (!bom) return <div className="p-8 text-center text-red-400">BOM not found.</div>;

  const nextAction = LIFECYCLE_NEXT[bom.lifecycle];

  return (
    <div className="p-6 space-y-5">
      {/* Header */}
      <div className="flex items-start justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <button onClick={() => router.push("/dashboard/bom")} className="text-sm text-gray-400 hover:text-gray-600">← BOMs</button>
            <span className="text-gray-300">/</span>
            <span className="text-sm text-gray-600 font-mono">{bom.bom_code}</span>
          </div>
          <h1 className="text-2xl font-bold text-gray-900">{bom.bom_name}</h1>
          <div className="flex items-center gap-2 mt-1">
            <span className={`text-xs px-2 py-0.5 rounded ${BOM_TYPE_COLOR[bom.bom_type]}`}>{bom.bom_type}</span>
            <span className={`text-xs px-2 py-0.5 rounded ${LIFECYCLE_COLOR[bom.lifecycle]}`}>{bom.lifecycle}</span>
            {bom.is_default && <span className="text-xs bg-green-100 text-green-700 px-2 py-0.5 rounded">Default</span>}
            <span className="text-xs text-gray-400">v{bom.version_no}</span>
          </div>
        </div>
        <div className="flex items-center gap-2 flex-wrap justify-end">
          <a href={`/dashboard/bom/${id}/explode`} className="px-3 py-1.5 text-xs border rounded-lg text-gray-600 hover:bg-gray-50">Explode</a>
          <a href={`/dashboard/bom/${id}/costing`} className="px-3 py-1.5 text-xs border rounded-lg text-gray-600 hover:bg-gray-50">Costing</a>
          <a href={`/dashboard/bom/${id}/compliance`} className="px-3 py-1.5 text-xs border rounded-lg text-gray-600 hover:bg-gray-50">Compliance</a>
          <button onClick={() => { setCloneVersion(""); setShowClone(true); }} className="px-3 py-1.5 text-xs border rounded-lg text-gray-600 hover:bg-gray-50">Clone</button>
          <button onClick={() => runAI.mutate()} disabled={runAI.isPending} className="px-3 py-1.5 text-xs bg-purple-600 text-white rounded-lg hover:bg-purple-700 disabled:opacity-40">
            {runAI.isPending ? "Running AI…" : "Run AI"}
          </button>
          {nextAction && (
            <button onClick={() => advance.mutate()} disabled={advance.isPending} className="px-3 py-1.5 text-xs bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 disabled:opacity-40">
              {advance.isPending ? "…" : nextAction}
            </button>
          )}
          {!["ARCHIVED"].includes(bom.lifecycle) && (
            <button onClick={() => archive.mutate()} disabled={archive.isPending} className="px-3 py-1.5 text-xs border border-red-200 text-red-500 rounded-lg hover:bg-red-50">Archive</button>
          )}
        </div>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 border-b border-gray-200">
        {TABS.map((t) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={`px-4 py-2 text-sm font-medium border-b-2 -mb-px ${
              tab === t ? "border-indigo-600 text-indigo-600" : "border-transparent text-gray-500 hover:text-gray-700"
            }`}
          >
            {t}
            {t === "AI Recs" && aiRecs.filter((r) => r.status === "PENDING").length > 0 && (
              <span className="ml-1 text-xs bg-purple-100 text-purple-700 px-1.5 py-0.5 rounded-full">
                {aiRecs.filter((r) => r.status === "PENDING").length}
              </span>
            )}
          </button>
        ))}
      </div>

      {/* Overview Tab */}
      {tab === "Overview" && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <div className="bg-white rounded-xl border border-gray-100 shadow-sm p-5 space-y-3">
            <h3 className="font-semibold text-gray-800">BOM Details</h3>
            <dl className="grid grid-cols-2 gap-x-4 gap-y-2 text-sm">
              <dt className="text-gray-400">Code</dt><dd className="font-mono text-gray-700">{bom.bom_code}</dd>
              <dt className="text-gray-400">Product</dt><dd>{bom.product_name || "—"}</dd>
              <dt className="text-gray-400">Base Qty</dt><dd>{Number(bom.base_qty).toLocaleString()} {bom.base_uom}</dd>
              <dt className="text-gray-400">Version</dt><dd>v{bom.version_no} (rev {bom.revision_no})</dd>
              <dt className="text-gray-400">Effective From</dt><dd>{bom.effective_from ? new Date(bom.effective_from).toLocaleDateString() : "—"}</dd>
              <dt className="text-gray-400">Effective To</dt><dd>{bom.effective_to ? new Date(bom.effective_to).toLocaleDateString() : "—"}</dd>
              <dt className="text-gray-400">Std Batch Cost</dt><dd className="font-medium text-green-700">{bom.standard_batch_cost ? fmtKES(Number(bom.standard_batch_cost)) : "—"}</dd>
              <dt className="text-gray-400">Cost / UOM</dt><dd>{bom.standard_cost_per_uom ? fmtKES(Number(bom.standard_cost_per_uom)) : "—"}</dd>
            </dl>
            {bom.notes && <p className="text-sm text-gray-500 border-t pt-3">{bom.notes}</p>}
          </div>
          <div className="space-y-4">
            {bom.allergen_flags && Object.keys(bom.allergen_flags).length > 0 && (
              <div className="bg-white rounded-xl border border-gray-100 shadow-sm p-4">
                <h3 className="font-semibold text-gray-800 mb-2">Allergen Flags</h3>
                <div className="flex flex-wrap gap-2">
                  {Object.entries(bom.allergen_flags).filter(([, v]) => v).map(([k]) => (
                    <span key={k} className="text-xs bg-red-100 text-red-700 px-2 py-0.5 rounded-full capitalize">{k}</span>
                  ))}
                </div>
              </div>
            )}
            {bom.nutrition_per_100g && Object.keys(bom.nutrition_per_100g).length > 0 && (
              <div className="bg-white rounded-xl border border-gray-100 shadow-sm p-4">
                <h3 className="font-semibold text-gray-800 mb-2">Nutrition per 100g</h3>
                <div className="grid grid-cols-2 gap-x-4 gap-y-1 text-xs">
                  {Object.entries(bom.nutrition_per_100g).map(([k, v]) => (
                    <div key={k} className="flex justify-between"><span className="text-gray-400 capitalize">{k}</span><span className="font-medium">{Number(v).toFixed(1)}</span></div>
                  ))}
                </div>
              </div>
            )}
            {/* Batch Scaling */}
            <div className="bg-white rounded-xl border border-gray-100 shadow-sm p-4">
              <h3 className="font-semibold text-gray-800 mb-2">Batch Scaling Preview</h3>
              <div className="flex gap-2">
                <input
                  type="number"
                  className="flex-1 border border-gray-200 rounded-lg px-3 py-1.5 text-sm"
                  placeholder={`Target qty (base: ${Number(bom.base_qty).toLocaleString()} ${bom.base_uom})`}
                  value={scalingQty}
                  onChange={(e) => setScalingQty(e.target.value)}
                />
                <button onClick={doScale} disabled={!scalingQty} className="px-3 py-1.5 text-xs bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-40">Scale</button>
              </div>
              {scalingResult && (
                <div className="mt-3 overflow-x-auto">
                  <p className="text-xs text-gray-400 mb-1">Scale factor: ×{scalingResult.scale_factor?.toFixed(3)}</p>
                  <table className="w-full text-xs">
                    <thead><tr className="text-gray-400">{["#", "Item", "Original", "Scaled", "Adjusted", "UOM"].map((h) => <th key={h} className="text-left pb-1 pr-2">{h}</th>)}</tr></thead>
                    <tbody>
                      {scalingResult.lines?.map((l: any) => (
                        <tr key={l.line_no} className={l.warning ? "bg-yellow-50" : ""}>
                          <td className="pr-2">{l.line_no}</td>
                          <td className="pr-2">{l.item_name || "—"}</td>
                          <td className="pr-2 text-right">{l.original_qty?.toFixed(3)}</td>
                          <td className="pr-2 text-right">{l.scaled_qty?.toFixed(3)}</td>
                          <td className="pr-2 text-right font-medium">{l.adjusted_qty?.toFixed(3)}</td>
                          <td>{l.required_uom}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Formula Tab */}
      {tab === "Formula" && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <p className="text-sm text-gray-500">{bom.lines?.length ?? 0} component lines</p>
            <button onClick={() => { setLineForm(emptyLine); setShowAddLine(true); }} className="px-3 py-1.5 text-xs bg-indigo-600 text-white rounded-lg hover:bg-indigo-700">+ Add Line</button>
          </div>
          <div className="bg-white rounded-xl border border-gray-100 shadow-sm overflow-x-auto">
            <table className="w-full text-xs">
              <thead className="bg-gray-50">
                <tr>
                  {["#", "Type", "Item", "Qty", "UOM", "Basis", "Waste%", "Loss%", "Flags", "Cost", ""].map((h) => (
                    <th key={h} className="px-3 py-2.5 text-left font-medium text-gray-400">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-50">
                {(bom.lines ?? []).map((line) => (
                  editLineId === line.id ? (
                    <tr key={line.id} className="bg-indigo-50">
                      <td className="px-3 py-2">{line.line_no}</td>
                      <td className="px-3 py-2">
                        <select className="border rounded px-1 py-0.5 text-xs w-28" value={lineForm.component_type} onChange={(e) => setLineForm({ ...lineForm, component_type: e.target.value as ComponentType })}>
                          {COMPONENT_TYPES.map((t) => <option key={t} value={t}>{t}</option>)}
                        </select>
                      </td>
                      <td className="px-3 py-2"><input className="border rounded px-1 py-0.5 text-xs w-28" placeholder="Item name" value={lineForm.item_name ?? ""} onChange={(e) => setLineForm({ ...lineForm, item_name: e.target.value })} /></td>
                      <td className="px-3 py-2"><input type="number" className="border rounded px-1 py-0.5 text-xs w-16" value={lineForm.required_qty} onChange={(e) => setLineForm({ ...lineForm, required_qty: Number(e.target.value) })} /></td>
                      <td className="px-3 py-2"><input className="border rounded px-1 py-0.5 text-xs w-12" value={lineForm.required_uom} onChange={(e) => setLineForm({ ...lineForm, required_uom: e.target.value })} /></td>
                      <td className="px-3 py-2">
                        <select className="border rounded px-1 py-0.5 text-xs w-24" value={lineForm.basis_type} onChange={(e) => setLineForm({ ...lineForm, basis_type: e.target.value as BasisType })}>
                          {BASIS_TYPES.map((b) => <option key={b} value={b}>{b}</option>)}
                        </select>
                      </td>
                      <td className="px-3 py-2"><input type="number" className="border rounded px-1 py-0.5 text-xs w-12" value={lineForm.wastage_pct} onChange={(e) => setLineForm({ ...lineForm, wastage_pct: Number(e.target.value) })} /></td>
                      <td className="px-3 py-2"><input type="number" className="border rounded px-1 py-0.5 text-xs w-12" value={lineForm.process_loss_pct} onChange={(e) => setLineForm({ ...lineForm, process_loss_pct: Number(e.target.value) })} /></td>
                      <td className="px-3 py-2">
                        <div className="flex gap-1">
                          <label className="flex items-center gap-0.5 text-xs"><input type="checkbox" checked={lineForm.allergen_flag} onChange={(e) => setLineForm({ ...lineForm, allergen_flag: e.target.checked })} />Allg</label>
                          <label className="flex items-center gap-0.5 text-xs"><input type="checkbox" checked={lineForm.critical_component} onChange={(e) => setLineForm({ ...lineForm, critical_component: e.target.checked })} />Crit</label>
                        </div>
                      </td>
                      <td className="px-3 py-2 text-gray-400">—</td>
                      <td className="px-3 py-2">
                        <div className="flex gap-1">
                          <button onClick={() => updateLine.mutate({ lineId: line.id, body: lineForm })} className="text-xs text-green-600 hover:underline">Save</button>
                          <button onClick={() => setEditLineId(null)} className="text-xs text-gray-400 hover:underline">Cancel</button>
                        </div>
                      </td>
                    </tr>
                  ) : (
                    <tr key={line.id} className="hover:bg-gray-50">
                      <td className="px-3 py-2 text-gray-400">{line.line_no}</td>
                      <td className="px-3 py-2"><span className={`px-1.5 py-0.5 rounded text-xs ${COMPONENT_COLOR[line.component_type]}`}>{line.component_type}</span></td>
                      <td className="px-3 py-2 font-medium">{line.item_name || line.item_code || "—"}{line.is_optional && <span className="ml-1 text-gray-400">(opt)</span>}</td>
                      <td className="px-3 py-2 text-right font-mono">{Number(line.required_qty).toFixed(4)}</td>
                      <td className="px-3 py-2">{line.required_uom}</td>
                      <td className="px-3 py-2 text-gray-400">{line.basis_type}</td>
                      <td className="px-3 py-2 text-right">{line.wastage_pct}%</td>
                      <td className="px-3 py-2 text-right">{line.process_loss_pct}%</td>
                      <td className="px-3 py-2">
                        <div className="flex gap-1">
                          {line.allergen_flag && <span className="bg-red-100 text-red-700 px-1 rounded">A</span>}
                          {line.critical_component && <span className="bg-orange-100 text-orange-700 px-1 rounded">!</span>}
                          {line.qc_required && <span className="bg-blue-100 text-blue-700 px-1 rounded">QC</span>}
                        </div>
                      </td>
                      <td className="px-3 py-2 text-right">{line.extended_cost ? fmtKES(Number(line.extended_cost)) : "—"}</td>
                      <td className="px-3 py-2">
                        <div className="flex gap-2">
                          <button onClick={() => { setLineForm(line); setEditLineId(line.id); }} className="text-xs text-blue-600 hover:underline">Edit</button>
                          <button onClick={() => deleteLine.mutate(line.id)} className="text-xs text-red-400 hover:text-red-600 hover:underline">Del</button>
                        </div>
                      </td>
                    </tr>
                  )
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Yield Tab */}
      {tab === "Yield" && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <p className="text-sm text-gray-500">Yield & loss configuration</p>
            <button onClick={() => setShowAddYield(true)} className="px-3 py-1.5 text-xs bg-indigo-600 text-white rounded-lg hover:bg-indigo-700">+ Add Yield Config</button>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {(bom.yield_configs ?? []).map((yc) => (
              <div key={yc.id} className="bg-white rounded-xl border border-gray-100 shadow-sm p-4">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-xs font-medium text-gray-600 bg-gray-100 px-2 py-0.5 rounded">{yc.loss_category}</span>
                  {yc.cost_impact_flag && <span className="text-xs text-red-600">Cost Impact</span>}
                </div>
                <p className="text-2xl font-bold text-gray-800">{yc.standard_pct}%</p>
                <p className="text-xs text-gray-400 mt-0.5">Standard loss</p>
                {yc.max_allowable_pct && <p className="text-xs text-orange-600 mt-1">Max: {yc.max_allowable_pct}%</p>}
                {yc.description && <p className="text-xs text-gray-500 mt-2">{yc.description}</p>}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* AI Recs Tab */}
      {tab === "AI Recs" && (
        <div className="space-y-3">
          {aiRecs.length === 0 ? (
            <div className="bg-white rounded-xl border border-gray-100 shadow-sm p-8 text-center text-sm text-gray-400">
              No AI recommendations. Click "Run AI" to analyze this BOM.
            </div>
          ) : aiRecs.map((rec) => (
            <div key={rec.id} className="bg-white rounded-xl border border-gray-100 shadow-sm p-4">
              <div className="flex items-start justify-between gap-4">
                <div className="flex-1">
                  <div className="flex items-center gap-2 mb-1">
                    <span className={`text-xs px-2 py-0.5 rounded ${AGENT_COLOR[rec.agent_type]}`}>{AGENT_LABEL[rec.agent_type]}</span>
                    <span className={`text-xs px-1.5 py-0.5 rounded ${rec.status === "PENDING" ? "bg-yellow-100 text-yellow-700" : rec.status === "ACCEPTED" ? "bg-green-100 text-green-700" : "bg-gray-100 text-gray-500"}`}>{rec.status}</span>
                    {rec.confidence_score && <span className="text-xs text-gray-400">{Math.round(rec.confidence_score * 100)}% confidence</span>}
                  </div>
                  <p className="font-medium text-gray-800 text-sm">{rec.title}</p>
                  {rec.explanation && <p className="text-xs text-gray-500 mt-1">{rec.explanation}</p>}
                  {rec.impact_summary && <p className="text-xs text-indigo-600 mt-1">Impact: {rec.impact_summary}</p>}
                </div>
                {rec.status === "PENDING" && (
                  <div className="flex gap-2">
                    <button onClick={() => actionAI.mutate({ recId: rec.id, status: "ACCEPTED" })} className="px-2 py-1 text-xs bg-green-600 text-white rounded hover:bg-green-700">Accept</button>
                    <button onClick={() => actionAI.mutate({ recId: rec.id, status: "REJECTED" })} className="px-2 py-1 text-xs border text-gray-600 rounded hover:bg-gray-50">Reject</button>
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Add Line Modal */}
      {showAddLine && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
          <div className="bg-white rounded-2xl shadow-xl w-full max-w-lg p-6">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-semibold">Add BOM Line</h2>
              <button onClick={() => setShowAddLine(false)} className="text-gray-400 hover:text-gray-600 text-xl">×</button>
            </div>
            <div className="space-y-3">
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-xs text-gray-500 mb-1 block">Component Type</label>
                  <select className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm" value={lineForm.component_type} onChange={(e) => setLineForm({ ...lineForm, component_type: e.target.value as ComponentType })}>
                    {COMPONENT_TYPES.map((t) => <option key={t} value={t}>{t}</option>)}
                  </select>
                </div>
                <div>
                  <label className="text-xs text-gray-500 mb-1 block">Basis Type</label>
                  <select className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm" value={lineForm.basis_type} onChange={(e) => setLineForm({ ...lineForm, basis_type: e.target.value as BasisType })}>
                    {BASIS_TYPES.map((b) => <option key={b} value={b}>{b}</option>)}
                  </select>
                </div>
              </div>
              <input className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm" placeholder="Item Name" value={lineForm.item_name ?? ""} onChange={(e) => setLineForm({ ...lineForm, item_name: e.target.value })} />
              <input className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm" placeholder="Item Code (optional)" value={lineForm.item_code ?? ""} onChange={(e) => setLineForm({ ...lineForm, item_code: e.target.value })} />
              <div className="grid grid-cols-3 gap-3">
                <div>
                  <label className="text-xs text-gray-500 mb-1 block">Required Qty</label>
                  <input type="number" className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm" value={lineForm.required_qty} onChange={(e) => setLineForm({ ...lineForm, required_qty: Number(e.target.value) })} />
                </div>
                <div>
                  <label className="text-xs text-gray-500 mb-1 block">UOM</label>
                  <input className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm" value={lineForm.required_uom} onChange={(e) => setLineForm({ ...lineForm, required_uom: e.target.value })} />
                </div>
                <div>
                  <label className="text-xs text-gray-500 mb-1 block">Wastage %</label>
                  <input type="number" className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm" value={lineForm.wastage_pct} onChange={(e) => setLineForm({ ...lineForm, wastage_pct: Number(e.target.value) })} />
                </div>
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-xs text-gray-500 mb-1 block">Process Loss %</label>
                  <input type="number" className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm" value={lineForm.process_loss_pct} onChange={(e) => setLineForm({ ...lineForm, process_loss_pct: Number(e.target.value) })} />
                </div>
                <div>
                  <label className="text-xs text-gray-500 mb-1 block">Concentration %</label>
                  <input type="number" className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm" value={lineForm.concentration_pct ?? ""} onChange={(e) => setLineForm({ ...lineForm, concentration_pct: e.target.value ? Number(e.target.value) : null })} />
                </div>
              </div>
              <input className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm" placeholder="Consumption Stage (e.g. MIX, FILL)" value={lineForm.consumption_stage ?? ""} onChange={(e) => setLineForm({ ...lineForm, consumption_stage: e.target.value })} />
              <div className="flex flex-wrap gap-4 text-sm">
                {[
                  ["allergen_flag", "Allergen"],
                  ["critical_component", "Critical"],
                  ["qc_required", "QC Required"],
                  ["is_optional", "Optional"],
                  ["fixed_consumption", "Fixed"],
                ].map(([field, label]) => (
                  <label key={field} className="flex items-center gap-1.5">
                    <input type="checkbox" checked={!!(lineForm as any)[field]} onChange={(e) => setLineForm({ ...lineForm, [field]: e.target.checked })} />
                    {label}
                  </label>
                ))}
              </div>
              <textarea className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm" rows={2} placeholder="Notes (optional)" value={lineForm.notes ?? ""} onChange={(e) => setLineForm({ ...lineForm, notes: e.target.value })} />
            </div>
            <div className="flex gap-3 mt-4">
              <button onClick={() => addLine.mutate()} disabled={!lineForm.item_name || addLine.isPending} className="flex-1 bg-indigo-600 text-white py-2 rounded-lg text-sm font-medium hover:bg-indigo-700 disabled:opacity-40">
                {addLine.isPending ? "Adding…" : "Add Line"}
              </button>
              <button onClick={() => setShowAddLine(false)} className="px-4 py-2 border rounded-lg text-sm text-gray-600 hover:bg-gray-50">Cancel</button>
            </div>
          </div>
        </div>
      )}

      {/* Add Yield Modal */}
      {showAddYield && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
          <div className="bg-white rounded-2xl shadow-xl w-full max-w-md p-6">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-semibold">Add Yield Config</h2>
              <button onClick={() => setShowAddYield(false)} className="text-gray-400 hover:text-gray-600 text-xl">×</button>
            </div>
            <div className="space-y-3">
              <select className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm" value={yieldForm.loss_category} onChange={(e) => setYieldForm({ ...yieldForm, loss_category: e.target.value as LossCategory })}>
                {LOSS_CATEGORIES.map((c) => <option key={c} value={c}>{c}</option>)}
              </select>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-xs text-gray-500 mb-1 block">Standard %</label>
                  <input type="number" className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm" value={yieldForm.standard_pct} onChange={(e) => setYieldForm({ ...yieldForm, standard_pct: Number(e.target.value) })} />
                </div>
                <div>
                  <label className="text-xs text-gray-500 mb-1 block">Max Allowable %</label>
                  <input type="number" className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm" value={yieldForm.max_allowable_pct ?? ""} onChange={(e) => setYieldForm({ ...yieldForm, max_allowable_pct: e.target.value ? Number(e.target.value) : undefined })} />
                </div>
              </div>
              <input className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm" placeholder="Description" value={yieldForm.description ?? ""} onChange={(e) => setYieldForm({ ...yieldForm, description: e.target.value })} />
              <label className="flex items-center gap-2 text-sm">
                <input type="checkbox" checked={yieldForm.cost_impact_flag} onChange={(e) => setYieldForm({ ...yieldForm, cost_impact_flag: e.target.checked })} />
                Cost Impact Flag
              </label>
            </div>
            <div className="flex gap-3 mt-4">
              <button onClick={() => addYield.mutate()} disabled={addYield.isPending} className="flex-1 bg-indigo-600 text-white py-2 rounded-lg text-sm font-medium hover:bg-indigo-700 disabled:opacity-40">
                {addYield.isPending ? "Adding…" : "Add Config"}
              </button>
              <button onClick={() => setShowAddYield(false)} className="px-4 py-2 border rounded-lg text-sm text-gray-600 hover:bg-gray-50">Cancel</button>
            </div>
          </div>
        </div>
      )}

      {/* Clone Modal */}
      {showClone && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
          <div className="bg-white rounded-2xl shadow-xl w-full max-w-sm p-6">
            <h2 className="text-lg font-semibold mb-3">Clone BOM</h2>
            <p className="text-sm text-gray-500 mb-3">Creates a new DRAFT BOM with all lines and yield configs copied.</p>
            <input
              className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm"
              placeholder="New Version (e.g. 2.0)"
              value={cloneVersion}
              onChange={(e) => setCloneVersion(e.target.value)}
            />
            <div className="flex gap-3 mt-4">
              <button onClick={() => clone.mutate()} disabled={!cloneVersion || clone.isPending} className="flex-1 bg-indigo-600 text-white py-2 rounded-lg text-sm font-medium hover:bg-indigo-700 disabled:opacity-40">
                {clone.isPending ? "Cloning…" : "Clone"}
              </button>
              <button onClick={() => setShowClone(false)} className="px-4 py-2 border rounded-lg text-sm text-gray-600 hover:bg-gray-50">Cancel</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
