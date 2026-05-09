"use client";
import { useEffect, useState } from "react";
import Link from "next/link";

interface CarbonRecord { id: string; product_name: string | null; batch_ref: string | null; calculation_date: string; total_kg_co2e: number; co2e_per_unit: number | null; units_produced: number; uom: string; scope1: number; scope2: number; scope3: number; methodology: string | null; }
interface Summary { product_name: string | null; avg_co2e_per_unit: number; total_co2e: number; batches: number; }
interface CalcForm { product_name: string; batch_ref: string; calculation_date: string; units_produced: string; electricity_kwh: string; electricity_emission_factor: string; fuel_liters: string; raw_material_kg_co2e: string; packaging_kg_co2e: string; transport_kg_co2e: string; notes: string; }

const EMPTY: CalcForm = {
  product_name: "", batch_ref: "", calculation_date: new Date().toISOString().split("T")[0],
  units_produced: "", electricity_kwh: "", electricity_emission_factor: "0.4971",
  fuel_liters: "", raw_material_kg_co2e: "", packaging_kg_co2e: "", transport_kg_co2e: "", notes: "",
};

export default function CarbonFootprintPage() {
  const [records, setRecords] = useState<CarbonRecord[]>([]);
  const [summary, setSummary] = useState<Summary[]>([]);
  const [loading, setLoading] = useState(true);
  const [tab, setTab] = useState<"summary" | "records" | "calculate">("summary");
  const [form, setForm] = useState<CalcForm>(EMPTY);
  const [saving, setSaving] = useState(false);
  const [result, setResult] = useState<CarbonRecord | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = () => {
    setLoading(true);
    Promise.all([
      fetch("/api/v1/esg/carbon-footprints?limit=50").then(r => r.json()),
      fetch("/api/v1/esg/carbon-footprints/summary").then(r => r.json()),
    ]).then(([r, s]) => { setRecords(r); setSummary(s); }).finally(() => setLoading(false));
  };
  useEffect(load, []);

  const calculate = async () => {
    setSaving(true); setError(null); setResult(null);
    try {
      const r = await fetch("/api/v1/esg/carbon-footprints", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          product_name: form.product_name || undefined,
          batch_ref: form.batch_ref || undefined,
          calculation_date: form.calculation_date,
          units_produced: Number(form.units_produced),
          electricity_kwh: form.electricity_kwh ? Number(form.electricity_kwh) : undefined,
          electricity_emission_factor: Number(form.electricity_emission_factor),
          fuel_liters: form.fuel_liters ? Number(form.fuel_liters) : undefined,
          raw_material_kg_co2e: form.raw_material_kg_co2e ? Number(form.raw_material_kg_co2e) : undefined,
          packaging_kg_co2e: form.packaging_kg_co2e ? Number(form.packaging_kg_co2e) : undefined,
          transport_kg_co2e: form.transport_kg_co2e ? Number(form.transport_kg_co2e) : undefined,
          notes: form.notes || undefined,
        }),
      });
      if (!r.ok) throw new Error(await r.text());
      setResult(await r.json());
      setForm(EMPTY);
      load();
    } catch (e) { setError(String(e)); }
    setSaving(false);
  };

  const intensityColor = (v: number) => v < 1 ? "text-green-600" : v < 5 ? "text-amber-600" : "text-red-600";

  return (
    <div className="p-6 space-y-6 max-w-5xl mx-auto">
      <div className="flex items-center gap-3">
        <Link href="/dashboard/esg" className="text-sm text-blue-600 hover:text-blue-800">← ESG</Link>
      </div>
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Carbon Footprint Per Product</h1>
        <p className="text-sm text-gray-500 mt-0.5">Scope 1 (combustion) + Scope 2 (electricity) + Scope 3 (materials/transport) per production batch</p>
      </div>

      {error && <div className="bg-red-50 border border-red-200 rounded p-3 text-sm text-red-700">{error}</div>}

      {result && (
        <div className="bg-green-50 border border-green-200 rounded-lg p-4 space-y-1">
          <p className="text-green-700 font-semibold text-sm">Carbon footprint calculated</p>
          <div className="grid grid-cols-2 gap-2 sm:grid-cols-4 text-xs text-green-700">
            <span>Scope 1: {result.scope1.toFixed(3)} kg CO₂e</span>
            <span>Scope 2: {result.scope2.toFixed(3)} kg CO₂e</span>
            <span>Scope 3: {result.scope3.toFixed(3)} kg CO₂e</span>
            <span className="font-bold">Total: {result.total_kg_co2e.toFixed(3)} kg CO₂e</span>
          </div>
          {result.co2e_per_unit !== null && (
            <p className="text-xs text-green-600 font-semibold">
              Carbon intensity: {result.co2e_per_unit.toFixed(6)} kg CO₂e / {result.uom}
            </p>
          )}
          <button onClick={() => setResult(null)} className="text-xs underline text-green-600 mt-1">Dismiss</button>
        </div>
      )}

      <div className="flex gap-1 border-b">
        {(["summary","records","calculate"] as const).map(t => (
          <button key={t} onClick={() => setTab(t)}
            className={`px-4 py-2 text-sm font-medium border-b-2 -mb-px capitalize ${tab===t?"border-blue-600 text-blue-600":"border-transparent text-gray-500 hover:text-gray-700"}`}>{t}</button>
        ))}
      </div>

      {tab === "summary" && (
        <div className="bg-white border rounded-lg shadow-sm overflow-hidden">
          <div className="px-4 py-3 border-b bg-gray-50"><h2 className="text-sm font-semibold text-gray-700">Average CO₂e per unit by product</h2></div>
          {loading ? <div className="p-6 text-sm text-gray-400 text-center">Loading…</div> : summary.length === 0 ? (
            <div className="p-6 text-sm text-gray-400 text-center">No footprint calculations yet. Use Calculate tab.</div>
          ) : (
            <table className="w-full text-sm">
              <thead className="bg-gray-50 text-xs text-gray-500">
                <tr><th className="text-left px-4 py-2">Product</th><th className="text-left px-4 py-2">Avg CO₂e/unit</th><th className="text-left px-4 py-2">Total CO₂e (kg)</th><th className="text-left px-4 py-2">Batches</th></tr>
              </thead>
              <tbody className="divide-y">
                {summary.map((s, i) => (
                  <tr key={i}>
                    <td className="px-4 py-2.5 font-medium text-gray-900">{s.product_name ?? "Unknown"}</td>
                    <td className={`px-4 py-2.5 font-mono font-bold ${intensityColor(s.avg_co2e_per_unit)}`}>{s.avg_co2e_per_unit.toFixed(6)}</td>
                    <td className="px-4 py-2.5 text-gray-600">{s.total_co2e.toFixed(3)}</td>
                    <td className="px-4 py-2.5 text-gray-400">{s.batches}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      )}

      {tab === "records" && (
        <div className="bg-white border rounded-lg shadow-sm overflow-hidden">
          <div className="px-4 py-3 border-b bg-gray-50"><h2 className="text-sm font-semibold text-gray-700">All Footprint Records ({records.length})</h2></div>
          {records.length === 0 ? <div className="p-6 text-sm text-gray-400 text-center">No records.</div> : (
            <div className="divide-y">
              {records.map(r => (
                <div key={r.id} className="px-4 py-3 flex items-center gap-4">
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-gray-900">{r.product_name ?? "—"}{r.batch_ref && ` · ${r.batch_ref}`}</p>
                    <div className="text-xs text-gray-500 flex gap-3 flex-wrap mt-0.5">
                      <span>{r.calculation_date}</span>
                      <span>{r.units_produced} {r.uom}</span>
                      <span>S1: {r.scope1.toFixed(2)} · S2: {r.scope2.toFixed(2)} · S3: {r.scope3.toFixed(2)}</span>
                    </div>
                  </div>
                  <div className="text-right shrink-0">
                    <p className="text-sm font-bold text-gray-800">{r.total_kg_co2e.toFixed(3)} kg CO₂e</p>
                    {r.co2e_per_unit && <p className={`text-xs font-mono ${intensityColor(r.co2e_per_unit)}`}>{r.co2e_per_unit.toFixed(6)}/unit</p>}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {tab === "calculate" && (
        <div className="bg-white border rounded-lg p-5 shadow-sm space-y-4 max-w-2xl">
          <h2 className="text-sm font-semibold text-gray-700">Calculate Carbon Footprint</h2>
          <p className="text-xs text-gray-400">GHG Protocol. Kenya grid factor default: 0.4971 kg CO₂e/kWh. Diesel: 2.68 kg CO₂e/litre (fixed).</p>
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
            {([["Product Name","product_name","e.g. Mango Juice 500ml"],["Batch Ref","batch_ref","e.g. PO-2026-001"],["Units Produced *","units_produced","e.g. 10000"],["Electricity (kWh)","electricity_kwh","e.g. 450"],["Grid Factor (kg CO₂e/kWh)","electricity_emission_factor","0.4971"],["Diesel (litres)","fuel_liters","e.g. 20"],["Raw Material CO₂e (kg)","raw_material_kg_co2e","e.g. 150.5"],["Packaging CO₂e (kg)","packaging_kg_co2e","e.g. 12.3"],["Transport CO₂e (kg)","transport_kg_co2e","e.g. 8.7"],["Notes","notes","Optional"]] as const).map(([label,key,ph]) => (
              <div key={key}>
                <label className="text-xs text-gray-500 block mb-1">{label}</label>
                <input type="text" placeholder={ph} value={(form as unknown as Record<string,string>)[key]}
                  onChange={(e) => setForm((p) => ({ ...p, [key]: e.target.value }))}
                  className="w-full border border-gray-300 rounded px-3 py-1.5 text-sm focus:outline-none focus:ring-1 focus:ring-blue-500" />
              </div>
            ))}
            <div>
              <label className="text-xs text-gray-500 block mb-1">Date *</label>
              <input type="date" value={form.calculation_date} onChange={(e) => setForm(p => ({ ...p, calculation_date: e.target.value }))}
                className="w-full border border-gray-300 rounded px-3 py-1.5 text-sm focus:outline-none" />
            </div>
          </div>
          <button onClick={calculate} disabled={saving || !form.units_produced || !form.calculation_date}
            className="bg-blue-600 text-white text-sm px-4 py-2 rounded disabled:opacity-50">{saving ? "Calculating…" : "Calculate Footprint"}</button>
        </div>
      )}
    </div>
  );
}
