"use client";
import { useEffect, useState } from "react";

interface Stats { active_contracts: number; total_production_runs: number; active_customer_tools: number; tools_near_end_of_life: number; }
interface Contract { id: string; contract_ref: string; contract_type: string; customer_name: string; brand_name: string | null; status: string; start_date: string; end_date: string | null; processing_fee_per_unit: number | null; currency: string; }
interface Tool { id: string; tool_ref: string; customer_name: string; tool_name: string; tool_type: string | null; status: string; units_produced: number; max_units_life: number | null; life_used_pct: number | null; storage_location: string | null; }
interface Run { id: string; run_ref: string; run_date: string; qty_produced: number | null; uom: string; processing_fee_total: number | null; quality_passed: boolean | null; }

const STATUS_COLOR: Record<string, string> = {
  DRAFT: "bg-gray-100 text-gray-600", ACTIVE: "bg-green-100 text-green-700",
  SUSPENDED: "bg-amber-100 text-amber-600", EXPIRED: "bg-red-100 text-red-600",
  TERMINATED: "bg-gray-100 text-gray-400",
};
const TOOL_STATUS_COLOR: Record<string, string> = {
  ACTIVE: "bg-green-100 text-green-700", IN_REPAIR: "bg-amber-100 text-amber-600",
  RETIRED: "bg-red-100 text-red-600", RETURNED: "bg-gray-100 text-gray-400",
};
const CONTRACT_TYPES = ["COPACKING", "TOLL_MFG", "PRIVATE_LABEL"];

interface ContractForm { customer_name: string; contract_type: string; brand_name: string; product_description: string; start_date: string; end_date: string; minimum_order_qty: string; moq_uom: string; processing_fee_per_unit: string; quality_standards: string; }
interface ToolForm { customer_name: string; tool_name: string; tool_type: string; serial_number: string; max_units_life: string; storage_location: string; }

export default function CoPackingPage() {
  const [stats, setStats] = useState<Stats | null>(null);
  const [contracts, setContracts] = useState<Contract[]>([]);
  const [tools, setTools] = useState<Tool[]>([]);
  const [runs, setRuns] = useState<Run[]>([]);
  const [loading, setLoading] = useState(true);
  const [tab, setTab] = useState<"contracts" | "tools" | "runs" | "newcontract" | "newtool">("contracts");
  const [cForm, setCForm] = useState<ContractForm>({ customer_name: "", contract_type: "COPACKING", brand_name: "", product_description: "", start_date: new Date().toISOString().split("T")[0], end_date: "", minimum_order_qty: "", moq_uom: "KG", processing_fee_per_unit: "", quality_standards: "" });
  const [tForm, setTForm] = useState<ToolForm>({ customer_name: "", tool_name: "", tool_type: "", serial_number: "", max_units_life: "", storage_location: "" });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = async () => {
    setLoading(true);
    try {
      const [s, c, t, r] = await Promise.all([
        fetch("/api/v1/copacking/stats").then(x => x.json()),
        fetch("/api/v1/copacking/contracts?limit=50").then(x => x.json()),
        fetch("/api/v1/copacking/tools?limit=50").then(x => x.json()),
        fetch("/api/v1/copacking/runs?limit=30").then(x => x.json()),
      ]);
      setStats(s); setContracts(c); setTools(t); setRuns(r);
    } finally { setLoading(false); }
  };

  useEffect(() => { load(); }, []);

  const saveContract = async () => {
    setSaving(true); setError(null);
    try {
      const r = await fetch("/api/v1/copacking/contracts", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          customer_name: cForm.customer_name, contract_type: cForm.contract_type,
          brand_name: cForm.brand_name || undefined, product_description: cForm.product_description || undefined,
          start_date: cForm.start_date, end_date: cForm.end_date || undefined,
          minimum_order_qty: cForm.minimum_order_qty ? Number(cForm.minimum_order_qty) : undefined,
          moq_uom: cForm.moq_uom,
          processing_fee_per_unit: cForm.processing_fee_per_unit ? Number(cForm.processing_fee_per_unit) : undefined,
          quality_standards: cForm.quality_standards || undefined,
        }),
      });
      if (!r.ok) throw new Error(await r.text());
      setTab("contracts"); load();
    } catch (e) { setError(String(e)); }
    setSaving(false);
  };

  const saveTool = async () => {
    setSaving(true); setError(null);
    try {
      const r = await fetch("/api/v1/copacking/tools", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          customer_name: tForm.customer_name, tool_name: tForm.tool_name,
          tool_type: tForm.tool_type || undefined, serial_number: tForm.serial_number || undefined,
          max_units_life: tForm.max_units_life ? Number(tForm.max_units_life) : undefined,
          storage_location: tForm.storage_location || undefined,
        }),
      });
      if (!r.ok) throw new Error(await r.text());
      setTab("tools"); load();
    } catch (e) { setError(String(e)); }
    setSaving(false);
  };

  return (
    <div className="p-6 space-y-6 max-w-6xl mx-auto">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Co-Packing / Toll Manufacturing</h1>
        <p className="text-sm text-gray-500 mt-0.5">Contract management, production runs, and customer tool register</p>
      </div>

      {error && <div className="bg-red-50 border border-red-200 rounded p-3 text-sm text-red-700">{error}</div>}

      {/* KPI strip */}
      {stats && (
        <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
          {[
            { label: "Active Contracts", value: stats.active_contracts, color: "text-green-600" },
            { label: "Production Runs", value: stats.total_production_runs, color: "text-blue-600" },
            { label: "Customer Tools", value: stats.active_customer_tools, color: "text-gray-800" },
            { label: "Tools Near EOL", value: stats.tools_near_end_of_life, color: "text-red-600" },
          ].map((k) => (
            <div key={k.label} className={`bg-white border rounded-lg p-4 shadow-sm ${k.label === "Tools Near EOL" && k.value > 0 ? "border-red-300 bg-red-50" : ""}`}>
              <p className="text-xs text-gray-500">{k.label}</p>
              <p className={`text-2xl font-bold mt-1 ${k.color}`}>{k.value}</p>
            </div>
          ))}
        </div>
      )}

      {/* Tabs */}
      <div className="flex gap-1 border-b flex-wrap">
        {([["contracts","Contracts"],["tools","Customer Tools"],["runs","Production Runs"],["newcontract","+ Contract"],["newtool","+ Tool"]] as const).map(([t,l]) => (
          <button key={t} onClick={() => setTab(t)}
            className={`px-4 py-2 text-sm font-medium border-b-2 -mb-px ${tab===t?"border-blue-600 text-blue-600":"border-transparent text-gray-500 hover:text-gray-700"}`}>{l}</button>
        ))}
      </div>

      {/* Contracts */}
      {tab === "contracts" && (
        <div className="bg-white border rounded-lg shadow-sm overflow-hidden">
          <div className="px-4 py-3 border-b bg-gray-50"><h2 className="text-sm font-semibold text-gray-700">Co-Packing Contracts ({contracts.length})</h2></div>
          {contracts.length === 0 ? <div className="p-6 text-sm text-gray-400 text-center">No contracts. Create one above.</div> : (
            <div className="divide-y">
              {contracts.map((c) => (
                <div key={c.id} className="px-4 py-3 flex items-center gap-4">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className="font-mono text-xs text-blue-600">{c.contract_ref}</span>
                      <span className={`text-xs rounded-full px-2 py-0.5 ${STATUS_COLOR[c.status] ?? "bg-gray-100"}`}>{c.status}</span>
                      <span className="text-xs bg-gray-100 text-gray-600 rounded px-2 py-0.5">{c.contract_type.replace(/_/g, " ")}</span>
                    </div>
                    <p className="text-sm font-medium text-gray-900 mt-0.5">{c.customer_name}{c.brand_name && ` — ${c.brand_name}`}</p>
                    <div className="text-xs text-gray-400 mt-0.5 flex gap-3">
                      <span>{c.start_date} → {c.end_date ?? "Open"}</span>
                      {c.processing_fee_per_unit && <span>{c.currency} {c.processing_fee_per_unit}/unit</span>}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Tools */}
      {tab === "tools" && (
        <div className="bg-white border rounded-lg shadow-sm overflow-hidden">
          <div className="px-4 py-3 border-b bg-gray-50"><h2 className="text-sm font-semibold text-gray-700">Customer Tools ({tools.length})</h2></div>
          {tools.length === 0 ? <div className="p-6 text-sm text-gray-400 text-center">No tools registered.</div> : (
            <table className="w-full text-sm">
              <thead className="bg-gray-50 text-xs text-gray-500">
                <tr>
                  <th className="text-left px-4 py-2">Tool</th>
                  <th className="text-left px-4 py-2">Customer</th>
                  <th className="text-left px-4 py-2">Type</th>
                  <th className="text-left px-4 py-2">Status</th>
                  <th className="text-left px-4 py-2">Life Used</th>
                  <th className="text-left px-4 py-2">Location</th>
                </tr>
              </thead>
              <tbody className="divide-y">
                {tools.map((t) => (
                  <tr key={t.id} className={t.life_used_pct !== null && t.life_used_pct >= 90 ? "bg-red-50" : ""}>
                    <td className="px-4 py-2.5">
                      <p className="font-medium text-gray-900">{t.tool_name}</p>
                      <p className="text-xs text-gray-400 font-mono">{t.tool_ref}</p>
                    </td>
                    <td className="px-4 py-2.5 text-gray-600">{t.customer_name}</td>
                    <td className="px-4 py-2.5 text-gray-500 text-xs">{t.tool_type ?? "—"}</td>
                    <td className="px-4 py-2.5">
                      <span className={`text-xs rounded-full px-2 py-0.5 ${TOOL_STATUS_COLOR[t.status] ?? "bg-gray-100"}`}>{t.status}</span>
                    </td>
                    <td className="px-4 py-2.5">
                      {t.life_used_pct !== null ? (
                        <div className="flex items-center gap-2">
                          <span className={`text-xs font-semibold ${t.life_used_pct >= 90 ? "text-red-600" : t.life_used_pct >= 70 ? "text-amber-500" : "text-gray-600"}`}>{t.life_used_pct}%</span>
                          <span className="text-xs text-gray-400">{t.units_produced}/{t.max_units_life}</span>
                        </div>
                      ) : `${t.units_produced} units`}
                    </td>
                    <td className="px-4 py-2.5 text-gray-400 text-xs">{t.storage_location ?? "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      )}

      {/* Runs */}
      {tab === "runs" && (
        <div className="bg-white border rounded-lg shadow-sm overflow-hidden">
          <div className="px-4 py-3 border-b bg-gray-50"><h2 className="text-sm font-semibold text-gray-700">Production Runs ({runs.length})</h2></div>
          {runs.length === 0 ? <div className="p-6 text-sm text-gray-400 text-center">No production runs.</div> : (
            <div className="divide-y">
              {runs.map((r) => (
                <div key={r.id} className="px-4 py-3 flex items-center gap-4">
                  <span className="font-mono text-xs text-blue-600">{r.run_ref}</span>
                  <div className="flex-1">
                    <div className="flex gap-3 text-xs text-gray-500 flex-wrap">
                      <span>{r.run_date}</span>
                      {r.qty_produced && <span className="font-semibold text-gray-700">{r.qty_produced} {r.uom}</span>}
                      {r.processing_fee_total && <span>Fee: KES {r.processing_fee_total.toLocaleString()}</span>}
                    </div>
                  </div>
                  {r.quality_passed !== null && (
                    <span className={`text-xs rounded-full px-2 py-0.5 ${r.quality_passed ? "bg-green-100 text-green-700" : "bg-red-100 text-red-600"}`}>
                      {r.quality_passed ? "QC Pass" : "QC Fail"}
                    </span>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* New contract form */}
      {tab === "newcontract" && (
        <div className="bg-white border rounded-lg p-5 shadow-sm space-y-3 max-w-2xl">
          <h2 className="text-sm font-semibold text-gray-700">New Co-Packing Contract</h2>
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
            {([["Customer Name *","customer_name","e.g. Fresh Corp Ltd"],["Brand Name","brand_name","e.g. FreshJuice"],["Product Description","product_description","e.g. Fruit juices 250ml-1L"],["Min Order Qty","minimum_order_qty","e.g. 5000"],["Processing Fee/Unit (KES)","processing_fee_per_unit","e.g. 12.50"],["Quality Standards","quality_standards","e.g. ISO 22000, KEBS"]] as const).map(([label,key,ph]) => (
              <div key={key}>
                <label className="text-xs text-gray-500 block mb-1">{label}</label>
                <input type="text" placeholder={ph} value={(cForm as unknown as Record<string,string>)[key]}
                  onChange={(e) => setCForm((p) => ({ ...p, [key]: e.target.value }))}
                  className="w-full border border-gray-300 rounded px-3 py-1.5 text-sm focus:outline-none focus:ring-1 focus:ring-blue-500" />
              </div>
            ))}
            <div>
              <label className="text-xs text-gray-500 block mb-1">Contract Type</label>
              <select value={cForm.contract_type} onChange={(e) => setCForm((p) => ({ ...p, contract_type: e.target.value }))}
                className="w-full border border-gray-300 rounded px-3 py-1.5 text-sm focus:outline-none">
                {CONTRACT_TYPES.map((t) => <option key={t} value={t}>{t.replace(/_/g, " ")}</option>)}
              </select>
            </div>
            <div>
              <label className="text-xs text-gray-500 block mb-1">Start Date *</label>
              <input type="date" value={cForm.start_date} onChange={(e) => setCForm((p) => ({ ...p, start_date: e.target.value }))}
                className="w-full border border-gray-300 rounded px-3 py-1.5 text-sm focus:outline-none" />
            </div>
            <div>
              <label className="text-xs text-gray-500 block mb-1">End Date</label>
              <input type="date" value={cForm.end_date} onChange={(e) => setCForm((p) => ({ ...p, end_date: e.target.value }))}
                className="w-full border border-gray-300 rounded px-3 py-1.5 text-sm focus:outline-none" />
            </div>
          </div>
          <button onClick={saveContract} disabled={saving || !cForm.customer_name || !cForm.start_date}
            className="bg-blue-600 text-white text-sm px-4 py-2 rounded disabled:opacity-50">{saving ? "Creating…" : "Create Contract"}</button>
        </div>
      )}

      {/* New tool form */}
      {tab === "newtool" && (
        <div className="bg-white border rounded-lg p-5 shadow-sm space-y-3 max-w-xl">
          <h2 className="text-sm font-semibold text-gray-700">Register Customer Tool</h2>
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
            {([["Customer Name *","customer_name","e.g. Fresh Corp Ltd"],["Tool Name *","tool_name","e.g. 500ml Blow Mould #1"],["Tool Type","tool_type","mould | die | jig | fixture"],["Serial Number","serial_number","e.g. BM-2024-001"],["Max Units Life","max_units_life","e.g. 500000"],["Storage Location","storage_location","e.g. Store B, Shelf 3"]] as const).map(([label,key,ph]) => (
              <div key={key}>
                <label className="text-xs text-gray-500 block mb-1">{label}</label>
                <input type="text" placeholder={ph} value={(tForm as unknown as Record<string,string>)[key]}
                  onChange={(e) => setTForm((p) => ({ ...p, [key]: e.target.value }))}
                  className="w-full border border-gray-300 rounded px-3 py-1.5 text-sm focus:outline-none focus:ring-1 focus:ring-blue-500" />
              </div>
            ))}
          </div>
          <button onClick={saveTool} disabled={saving || !tForm.customer_name || !tForm.tool_name}
            className="bg-blue-600 text-white text-sm px-4 py-2 rounded disabled:opacity-50">{saving ? "Registering…" : "Register Tool"}</button>
        </div>
      )}
    </div>
  );
}
