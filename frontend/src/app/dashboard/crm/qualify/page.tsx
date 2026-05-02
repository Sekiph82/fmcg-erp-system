"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import { crmApi, CRMRecord, fmtCurrency, TEMPERATURE_COLORS } from "@/lib/crm_pipeline";

interface QualForm {
  budget_fit: boolean;
  need_fit: boolean;
  timeline_fit: boolean;
  authority_fit: boolean;
  product_fit: boolean;
  geo_fit: boolean;
  notes: string;
}

export default function LeadQualificationPage() {
  const [leads, setLeads] = useState<CRMRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [selected, setSelected] = useState<CRMRecord | null>(null);
  const [form, setForm] = useState<QualForm>({
    budget_fit: false, need_fit: false, timeline_fit: false,
    authority_fit: false, product_fit: false, geo_fit: false, notes: "",
  });
  const [saving, setSaving] = useState(false);

  const load = () => {
    setLoading(true);
    crmApi.getLeads({ status: "OPEN", limit: 100 }).then(setLeads).catch(console.error).finally(() => setLoading(false));
  };

  useEffect(() => { load(); }, []);

  const score = Object.entries(form).filter(([k, v]) => k !== "notes" && v === true).length;

  const handleQualify = async () => {
    if (!selected) return;
    setSaving(true);
    try {
      await crmApi.qualify(selected.id, form as unknown as Record<string, unknown>);
      setSelected(null);
      setForm({ budget_fit: false, need_fit: false, timeline_fit: false, authority_fit: false, product_fit: false, geo_fit: false, notes: "" });
      load();
    } catch (e) { console.error(e); }
    setSaving(false);
  };

  const fitCriteria = [
    { key: "budget_fit", label: "Budget Fit", desc: "Prospect has the budget for our solution" },
    { key: "need_fit", label: "Need Fit", desc: "Clear need that our product/service addresses" },
    { key: "timeline_fit", label: "Timeline Fit", desc: "Ready to buy within a reasonable timeframe" },
    { key: "authority_fit", label: "Authority / Contact Quality", desc: "Speaking to a decision maker or key influencer" },
    { key: "product_fit", label: "Product Fit", desc: "Our product is suitable for their requirements" },
    { key: "geo_fit", label: "Geographic Fit", desc: "Within our service/delivery coverage area" },
  ];

  const qualifiedLeads = leads.filter(l => l.qualified_flag);
  const unqualifiedLeads = leads.filter(l => !l.qualified_flag);

  return (
    <div className="p-6 space-y-6">
      <h1 className="text-xl font-bold text-gray-900">Lead Qualification Panel</h1>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Unqualified Leads */}
        <div>
          <h2 className="font-semibold text-gray-700 mb-3 text-sm">Unqualified Leads ({unqualifiedLeads.length})</h2>
          <div className="space-y-2">
            {loading && <div className="text-gray-400 text-sm">Loading…</div>}
            {!loading && unqualifiedLeads.length === 0 && (
              <p className="text-sm text-gray-400">No unqualified leads</p>
            )}
            {unqualifiedLeads.map(lead => (
              <button key={lead.id} onClick={() => setSelected(lead)}
                className={`w-full text-left bg-white rounded-xl border shadow-sm p-3 hover:border-blue-400 transition-colors ${selected?.id === lead.id ? "border-blue-500 ring-1 ring-blue-200" : ""}`}>
                <div className="flex items-center justify-between">
                  <div className="font-medium text-gray-800 text-sm">{lead.company_name}</div>
                  <div className="w-2 h-2 rounded-full" style={{ background: TEMPERATURE_COLORS[lead.temperature] }} />
                </div>
                <div className="text-xs text-gray-400 mt-0.5">
                  {lead.lead_code} · Score: {lead.lead_score} · {fmtCurrency(lead.expected_revenue, lead.currency)}
                </div>
              </button>
            ))}
          </div>
        </div>

        {/* Qualification Panel */}
        <div>
          {selected ? (
            <div className="bg-white rounded-xl border shadow-sm p-4 space-y-4">
              <div>
                <h2 className="font-semibold text-gray-800">{selected.company_name}</h2>
                <div className="text-xs text-gray-500">{selected.lead_code}</div>
              </div>

              {/* Score Meter */}
              <div className="flex items-center gap-3">
                <div className="text-2xl font-bold text-indigo-700">{score}/6</div>
                <div className="flex-1 h-3 bg-gray-100 rounded-full overflow-hidden">
                  <div className="h-full rounded-full transition-all"
                    style={{
                      width: `${(score / 6) * 100}%`,
                      background: score >= 5 ? "#10B981" : score >= 3 ? "#F59E0B" : "#EF4444"
                    }} />
                </div>
                <div className="text-xs text-gray-500">
                  {score >= 5 ? "Qualify" : score >= 3 ? "Marginal" : "Disqualify"}
                </div>
              </div>

              {/* Fit Criteria */}
              <div className="space-y-2">
                {fitCriteria.map(c => (
                  <label key={c.key} className="flex items-start gap-3 cursor-pointer">
                    <input type="checkbox"
                      checked={form[c.key as keyof QualForm] as boolean}
                      onChange={e => setForm(f => ({ ...f, [c.key]: e.target.checked }))}
                      className="mt-0.5 rounded" />
                    <div>
                      <div className="text-sm font-medium text-gray-800">{c.label}</div>
                      <div className="text-xs text-gray-400">{c.desc}</div>
                    </div>
                  </label>
                ))}
              </div>

              <textarea placeholder="Qualification notes…" value={form.notes}
                onChange={e => setForm(f => ({ ...f, notes: e.target.value }))}
                className="w-full border rounded-lg px-3 py-2 text-sm" rows={2} />

              <div className="flex gap-2">
                <button onClick={handleQualify} disabled={saving}
                  className="flex-1 bg-blue-600 text-white py-2 rounded-lg text-sm disabled:opacity-50">
                  {saving ? "Qualifying…" : "Qualify Lead"}
                </button>
                <button onClick={() => setSelected(null)}
                  className="flex-1 border rounded-lg py-2 text-sm">Clear</button>
              </div>
            </div>
          ) : (
            <div className="bg-gray-50 rounded-xl border-2 border-dashed p-8 text-center text-gray-400 text-sm">
              Select a lead from the left to qualify it
            </div>
          )}
        </div>
      </div>

      {/* Recently Qualified */}
      {qualifiedLeads.length > 0 && (
        <div>
          <h2 className="font-semibold text-gray-700 mb-3 text-sm">Qualified Leads ({qualifiedLeads.length})</h2>
          <div className="space-y-2">
            {qualifiedLeads.map(lead => (
              <div key={lead.id} className="bg-white rounded-xl border shadow-sm p-3 flex items-center gap-3">
                <div className="flex-1">
                  <div className="font-medium text-gray-800 text-sm">{lead.company_name}</div>
                  <div className="text-xs text-gray-400">{lead.lead_code} · Qualified {lead.qualified_date}</div>
                </div>
                <span className="text-xs bg-green-100 text-green-700 px-2 py-0.5 rounded-full">Qualified</span>
                <Link href={`/dashboard/crm/records/${lead.id}`}
                  className="text-xs text-blue-600 hover:underline">View</Link>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
