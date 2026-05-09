"use client";

import { useEffect, useMemo, useState } from "react";
import type { FormEvent } from "react";
import Link from "next/link";
import {
  esgApi,
  ESGIntelligenceDashboard,
  SupplierSustainabilityRisk,
  SupplierSustainabilityScore,
} from "@/lib/esg";

const riskClasses: Record<SupplierSustainabilityRisk, string> = {
  LOW: "bg-green-100 text-green-700",
  MEDIUM: "bg-yellow-100 text-yellow-700",
  HIGH: "bg-orange-100 text-orange-700",
  CRITICAL: "bg-red-100 text-red-700",
};

const qualityClasses: Record<string, string> = {
  GOOD: "bg-green-100 text-green-700",
  PARTIAL: "bg-yellow-100 text-yellow-700",
  MISSING_PRODUCTION_VOLUME: "bg-orange-100 text-orange-700",
  NO_KWH_QUANTITY: "bg-red-100 text-red-700",
};

const initialForm = {
  supplier_name: "",
  assessment_period_start: "",
  assessment_period_end: "",
  overall_score: "75",
  risk_level: "MEDIUM" as SupplierSustainabilityRisk,
  emissions_score: "",
  energy_score: "",
  water_score: "",
  waste_score: "",
  compliance_score: "",
  labor_score: "",
  renewable_energy_pct: "",
  has_ghg_disclosure: false,
  has_science_based_target: false,
  iso14001_certified: false,
  wastewater_policy_verified: false,
  audit_findings: "",
  improvement_plan: "",
};

function fmt(value?: number, digits = 1) {
  if (value === undefined || value === null) return "-";
  return Number(value).toLocaleString(undefined, { maximumFractionDigits: digits });
}

function toNumber(value: string) {
  return value === "" ? undefined : Number(value);
}

export default function ESGIntelligencePage() {
  const [dashboard, setDashboard] = useState<ESGIntelligenceDashboard | null>(null);
  const [scores, setScores] = useState<SupplierSustainabilityScore[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");
  const [form, setForm] = useState(initialForm);

  const params = useMemo(() => ({
    date_from: dateFrom || undefined,
    date_to: dateTo || undefined,
  }), [dateFrom, dateTo]);

  const load = async () => {
    setLoading(true);
    try {
      const [dash, supplierScores] = await Promise.all([
        esgApi.intelligenceDashboard(params),
        esgApi.listSupplierScores({ limit: 20 }),
      ]);
      setDashboard(dash);
      setScores(supplierScores);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, [params]);

  const submitScore = async (event: FormEvent) => {
    event.preventDefault();
    setSaving(true);
    try {
      await esgApi.createSupplierScore({
        supplier_name: form.supplier_name,
        assessment_period_start: form.assessment_period_start,
        assessment_period_end: form.assessment_period_end,
        overall_score: Number(form.overall_score),
        risk_level: form.risk_level,
        status: "ACTIVE",
        emissions_score: toNumber(form.emissions_score),
        energy_score: toNumber(form.energy_score),
        water_score: toNumber(form.water_score),
        waste_score: toNumber(form.waste_score),
        compliance_score: toNumber(form.compliance_score),
        labor_score: toNumber(form.labor_score),
        renewable_energy_pct: toNumber(form.renewable_energy_pct),
        has_ghg_disclosure: form.has_ghg_disclosure,
        has_science_based_target: form.has_science_based_target,
        iso14001_certified: form.iso14001_certified,
        wastewater_policy_verified: form.wastewater_policy_verified,
        audit_findings: form.audit_findings || undefined,
        improvement_plan: form.improvement_plan || undefined,
      });
      setForm(initialForm);
      await load();
    } finally {
      setSaving(false);
    }
  };

  const wastewater = dashboard?.wastewater_compliance;
  const kpis = [
    { label: "Supplier Scorecards", value: fmt(dashboard?.supplier_score_count, 0), sub: `${fmt(dashboard?.average_supplier_score)} avg score` },
    { label: "High Risk Suppliers", value: fmt(dashboard?.high_risk_supplier_count, 0), sub: "High and critical risk" },
    { label: "Wastewater Compliance", value: wastewater?.compliance_rate_pct != null ? `${fmt(wastewater.compliance_rate_pct)}%` : "-", sub: `${fmt(wastewater?.total_records, 0)} records` },
    { label: "WWTP Energy", value: `${fmt(wastewater?.total_power_kwh)} kWh`, sub: "Treatment power" },
  ];

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">ESG Intelligence</h1>
          <p className="text-sm text-gray-500 mt-1">Supplier sustainability, energy intensity, and wastewater compliance</p>
        </div>
        <div className="flex gap-2 flex-wrap">
          <Link href="/dashboard/esg" className="px-3 py-2 text-sm border rounded-lg hover:bg-gray-50">Dashboard</Link>
          <Link href="/dashboard/esg/reports" className="px-3 py-2 text-sm border rounded-lg hover:bg-gray-50">Reports</Link>
        </div>
      </div>

      <div className="bg-white rounded-lg border p-4 flex flex-wrap items-end gap-3">
        <div>
          <label className="block text-xs text-gray-500 mb-1">From</label>
          <input type="date" value={dateFrom} onChange={(e) => setDateFrom(e.target.value)} className="border rounded-lg px-3 py-2 text-sm" />
        </div>
        <div>
          <label className="block text-xs text-gray-500 mb-1">To</label>
          <input type="date" value={dateTo} onChange={(e) => setDateTo(e.target.value)} className="border rounded-lg px-3 py-2 text-sm" />
        </div>
        <button onClick={load} disabled={loading} className="px-4 py-2 text-sm bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:opacity-50">
          {loading ? "Loading..." : "Refresh"}
        </button>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {kpis.map((kpi) => (
          <div key={kpi.label} className="bg-white rounded-lg border p-4">
            <p className="text-xs text-gray-500">{kpi.label}</p>
            <p className="text-xl font-bold text-gray-900 mt-1">{kpi.value}</p>
            <p className="text-xs text-gray-400 mt-0.5">{kpi.sub}</p>
          </div>
        ))}
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
        <form onSubmit={submitScore} className="bg-white rounded-lg border p-4 space-y-3">
          <h2 className="font-semibold text-gray-800">Supplier Scorecard</h2>
          <input required value={form.supplier_name} onChange={(e) => setForm({ ...form, supplier_name: e.target.value })} placeholder="Supplier name" className="w-full border rounded-lg px-3 py-2 text-sm" />
          <div className="grid grid-cols-2 gap-3">
            <input required type="date" value={form.assessment_period_start} onChange={(e) => setForm({ ...form, assessment_period_start: e.target.value })} className="border rounded-lg px-3 py-2 text-sm" />
            <input required type="date" value={form.assessment_period_end} onChange={(e) => setForm({ ...form, assessment_period_end: e.target.value })} className="border rounded-lg px-3 py-2 text-sm" />
            <input required type="number" min="0" max="100" value={form.overall_score} onChange={(e) => setForm({ ...form, overall_score: e.target.value })} placeholder="Overall score" className="border rounded-lg px-3 py-2 text-sm" />
            <select value={form.risk_level} onChange={(e) => setForm({ ...form, risk_level: e.target.value as SupplierSustainabilityRisk })} className="border rounded-lg px-3 py-2 text-sm">
              {(["LOW", "MEDIUM", "HIGH", "CRITICAL"] as SupplierSustainabilityRisk[]).map((risk) => <option key={risk}>{risk}</option>)}
            </select>
          </div>
          <div className="grid grid-cols-2 gap-3">
            {[
              ["emissions_score", "Emissions score"],
              ["energy_score", "Energy score"],
              ["water_score", "Water score"],
              ["waste_score", "Waste score"],
              ["compliance_score", "Compliance score"],
              ["labor_score", "Labor score"],
              ["renewable_energy_pct", "Renewable %"],
            ].map(([key, label]) => (
              <input key={key} type="number" min="0" max={key === "renewable_energy_pct" ? "100" : undefined} value={(form as any)[key]} onChange={(e) => setForm({ ...form, [key]: e.target.value })} placeholder={label} className="border rounded-lg px-3 py-2 text-sm" />
            ))}
          </div>
          {[
            ["has_ghg_disclosure", "GHG disclosure"],
            ["has_science_based_target", "Science-based target"],
            ["iso14001_certified", "ISO 14001"],
            ["wastewater_policy_verified", "Wastewater policy"],
          ].map(([key, label]) => (
            <label key={key} className="flex items-center gap-2 text-sm text-gray-700">
              <input type="checkbox" checked={(form as any)[key]} onChange={(e) => setForm({ ...form, [key]: e.target.checked })} />
              {label}
            </label>
          ))}
          <textarea value={form.audit_findings} onChange={(e) => setForm({ ...form, audit_findings: e.target.value })} placeholder="Audit findings" className="w-full border rounded-lg px-3 py-2 text-sm min-h-[70px]" />
          <textarea value={form.improvement_plan} onChange={(e) => setForm({ ...form, improvement_plan: e.target.value })} placeholder="Improvement plan" className="w-full border rounded-lg px-3 py-2 text-sm min-h-[70px]" />
          <button disabled={saving} className="w-full px-4 py-2 text-sm bg-gray-900 text-white rounded-lg hover:bg-gray-800 disabled:opacity-50">
            {saving ? "Saving..." : "Save Scorecard"}
          </button>
        </form>

        <div className="xl:col-span-2 bg-white rounded-lg border overflow-hidden">
          <div className="px-4 py-3 border-b">
            <h2 className="font-semibold text-gray-800">Energy Intensity per SKU</h2>
          </div>
          <table className="w-full text-sm">
            <thead className="bg-gray-50 text-gray-600 uppercase text-xs">
              <tr>
                <th className="px-4 py-3 text-left">SKU</th>
                <th className="px-4 py-3 text-right">kWh</th>
                <th className="px-4 py-3 text-right">Volume kg</th>
                <th className="px-4 py-3 text-right">kWh/kg</th>
                <th className="px-4 py-3 text-right">Quality</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {(dashboard?.energy_intensity_rows ?? []).map((row) => (
                <tr key={`${row.product_id}-${row.product_name}`} className="hover:bg-gray-50">
                  <td className="px-4 py-3">
                    <p className="font-medium text-gray-900">{row.product_sku || "No SKU"}</p>
                    <p className="text-xs text-gray-500">{row.product_name}</p>
                  </td>
                  <td className="px-4 py-3 text-right">{fmt(row.total_energy_kwh)}</td>
                  <td className="px-4 py-3 text-right">{fmt(row.production_volume_kg)}</td>
                  <td className="px-4 py-3 text-right font-semibold">{fmt(row.kwh_per_kg, 4)}</td>
                  <td className="px-4 py-3 text-right">
                    <span className={`px-2 py-0.5 rounded-full text-xs ${qualityClasses[row.data_quality] ?? "bg-gray-100 text-gray-700"}`}>
                      {row.data_quality.replaceAll("_", " ")}
                    </span>
                  </td>
                </tr>
              ))}
              {!loading && (dashboard?.energy_intensity_rows ?? []).length === 0 && (
                <tr><td colSpan={5} className="px-4 py-8 text-center text-gray-500">No product-linked utility allocations found.</td></tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
        <div className="bg-white rounded-lg border overflow-hidden">
          <div className="px-4 py-3 border-b">
            <h2 className="font-semibold text-gray-800">Recent Supplier Sustainability Scores</h2>
          </div>
          <table className="w-full text-sm">
            <thead className="bg-gray-50 text-gray-600 uppercase text-xs">
              <tr>
                <th className="px-4 py-3 text-left">Supplier</th>
                <th className="px-4 py-3 text-right">Score</th>
                <th className="px-4 py-3 text-right">Risk</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {scores.map((score) => (
                <tr key={score.id} className="hover:bg-gray-50">
                  <td className="px-4 py-3">
                    <p className="font-medium text-gray-900">{score.supplier_name}</p>
                    <p className="text-xs text-gray-500">{score.assessment_period_start} to {score.assessment_period_end}</p>
                  </td>
                  <td className="px-4 py-3 text-right font-semibold">{fmt(score.overall_score)}</td>
                  <td className="px-4 py-3 text-right">
                    <span className={`px-2 py-0.5 rounded-full text-xs ${riskClasses[score.risk_level]}`}>
                      {score.risk_level}
                    </span>
                  </td>
                </tr>
              ))}
              {!loading && scores.length === 0 && (
                <tr><td colSpan={3} className="px-4 py-8 text-center text-gray-500">No supplier scorecards yet.</td></tr>
              )}
            </tbody>
          </table>
        </div>

        <div className="bg-white rounded-lg border p-4 space-y-4">
          <div>
            <h2 className="font-semibold text-gray-800">Wastewater Compliance</h2>
            <p className="text-sm text-gray-500 mt-1">
              COD {fmt(wastewater?.avg_effluent_cod_mgl)} mg/L, BOD {fmt(wastewater?.avg_effluent_bod_mgl)} mg/L,
              TSS {fmt(wastewater?.avg_effluent_tss_mgl)} mg/L, pH {fmt(wastewater?.avg_effluent_ph, 2)}
            </p>
          </div>
          <div className="grid grid-cols-4 gap-3">
            {[
              ["Compliant", wastewater?.compliant_records, "text-green-600"],
              ["Borderline", wastewater?.borderline_records, "text-yellow-600"],
              ["Non-compliant", wastewater?.non_compliant_records, "text-red-600"],
              ["Not tested", wastewater?.not_tested_records, "text-gray-600"],
            ].map(([label, value, color]) => (
              <div key={label as string} className="border rounded-lg p-3">
                <p className="text-xs text-gray-500">{label}</p>
                <p className={`text-lg font-bold ${color}`}>{fmt(value as number | undefined, 0)}</p>
              </div>
            ))}
          </div>
          <div className="space-y-2">
            {(wastewater?.latest_deviations ?? []).map((dev) => (
              <div key={dev.id} className="border rounded-lg p-3">
                <div className="flex items-center justify-between gap-3">
                  <p className="text-sm font-medium text-gray-900">{dev.record_no}</p>
                  <span className="text-xs text-red-700 bg-red-100 rounded-full px-2 py-0.5">{dev.status}</span>
                </div>
                <p className="text-xs text-gray-500 mt-1">{dev.record_datetime}</p>
                {(dev.deviation_reason || dev.corrective_action) && (
                  <p className="text-xs text-gray-600 mt-2">{dev.deviation_reason || dev.corrective_action}</p>
                )}
              </div>
            ))}
            {!loading && (wastewater?.latest_deviations ?? []).length === 0 && (
              <p className="text-sm text-gray-500 border rounded-lg p-4">No wastewater deviations in the selected period.</p>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
