"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { taxApi, CountryTaxConfig, TaxCategory, TaxRule, TaxType, TaxAppliesTo } from "@/lib/tax_regulatory";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";

const TAX_TYPES: TaxType[] = ["VAT", "EXCISE", "CUSTOMS_DUTY", "WITHHOLDING_TAX", "RAILWAY_DEV_LEVY", "IDF_FEE", "STAMP_DUTY", "CORPORATE_TAX", "OTHER"];
const APPLIES_TO: TaxAppliesTo[] = ["PURCHASE", "SALE", "IMPORT", "EXPORT", "ALL"];

export default function TaxRulesPage() {
  const qc = useQueryClient();
  const [tab, setTab] = useState<"countries" | "categories" | "rules">("countries");
  const [filterCountry, setFilterCountry] = useState("");
  const [showCountryModal, setShowCountryModal] = useState(false);
  const [editCountry, setEditCountry] = useState<CountryTaxConfig | null>(null);
  const [showCategoryModal, setShowCategoryModal] = useState(false);
  const [showRuleModal, setShowRuleModal] = useState(false);

  const { data: countries = [] } = useQuery({ queryKey: ["tax-countries"], queryFn: taxApi.listCountries });
  const { data: categories = [] } = useQuery({ queryKey: ["tax-categories"], queryFn: taxApi.listCategories });
  const { data: rules = [] } = useQuery({
    queryKey: ["tax-rules", filterCountry],
    queryFn: () => taxApi.listRules(filterCountry || undefined),
  });

  const createCountry = useMutation({
    mutationFn: (d: object) => taxApi.createCountry(d),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["tax-countries"] }); setShowCountryModal(false); },
  });
  const updateCountry = useMutation({
    mutationFn: ({ code, data }: { code: string; data: object }) => taxApi.updateCountry(code, data),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["tax-countries"] }); setEditCountry(null); },
  });
  const createCategory = useMutation({
    mutationFn: (d: object) => taxApi.createCategory(d),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["tax-categories"] }); setShowCategoryModal(false); },
  });
  const createRule = useMutation({
    mutationFn: (d: object) => taxApi.createRule(d),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["tax-rules"] }); setShowRuleModal(false); },
  });

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Tax Rules & Categories</h1>
          <p className="text-sm text-gray-500 mt-1">Country-specific tax configurations, categories, and rate rules</p>
        </div>
        <div className="flex gap-2">
          {tab === "countries" && <Button onClick={() => setShowCountryModal(true)}>Add Country</Button>}
          {tab === "categories" && <Button onClick={() => setShowCategoryModal(true)}>Add Category</Button>}
          {tab === "rules" && <Button onClick={() => setShowRuleModal(true)}>Add Rule</Button>}
        </div>
      </div>

      {/* Tabs */}
      <div className="flex border-b">
        {(["countries", "categories", "rules"] as const).map((t) => (
          <button key={t} onClick={() => setTab(t)}
            className={`px-4 py-2 text-sm font-medium capitalize border-b-2 -mb-px transition-colors ${tab === t ? "border-indigo-600 text-indigo-600" : "border-transparent text-gray-500 hover:text-gray-700"}`}>
            {t}
          </button>
        ))}
      </div>

      {/* Countries Tab */}
      {tab === "countries" && (
        <div className="bg-white rounded-lg border">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b bg-gray-50 text-xs text-gray-500 uppercase">
                <th className="px-5 py-2 text-left">Code</th>
                <th className="px-5 py-2 text-left">Country</th>
                <th className="px-5 py-2 text-left">Currency</th>
                <th className="px-5 py-2 text-right">VAT Rate %</th>
                <th className="px-5 py-2 text-right">WHT Rate %</th>
                <th className="px-5 py-2 text-right">Corp Tax %</th>
                <th className="px-5 py-2 text-right">Import Duty %</th>
                <th className="px-5 py-2 text-left">Tax Authority</th>
                <th className="px-5 py-2 text-left">Status</th>
                <th className="px-5 py-2" />
              </tr>
            </thead>
            <tbody className="divide-y">
              {countries.map((c) => (
                <tr key={c.id} className="hover:bg-gray-50">
                  <td className="px-5 py-3 font-mono font-bold text-indigo-700">{c.country_code}</td>
                  <td className="px-5 py-3 font-medium">{c.country_name}</td>
                  <td className="px-5 py-3">{c.currency}</td>
                  <td className="px-5 py-3 text-right">{c.standard_vat_rate != null ? `${c.standard_vat_rate}%` : "—"}</td>
                  <td className="px-5 py-3 text-right">{c.standard_wht_rate != null ? `${c.standard_wht_rate}%` : "—"}</td>
                  <td className="px-5 py-3 text-right">{c.corporate_tax_rate != null ? `${c.corporate_tax_rate}%` : "—"}</td>
                  <td className="px-5 py-3 text-right">{c.import_duty_default_rate != null ? `${c.import_duty_default_rate}%` : "—"}</td>
                  <td className="px-5 py-3 text-gray-600">{c.tax_authority || "—"}</td>
                  <td className="px-5 py-3"><Badge label={c.is_active ? "Active" : "Inactive"} variant={c.is_active ? "green" : "gray"} /></td>
                  <td className="px-5 py-3">
                    <button className="text-xs text-indigo-600 hover:underline" onClick={() => setEditCountry(c)}>Edit</button>
                  </td>
                </tr>
              ))}
              {countries.length === 0 && <tr><td colSpan={10} className="px-5 py-8 text-center text-gray-400">No country configs</td></tr>}
            </tbody>
          </table>
        </div>
      )}

      {/* Categories Tab */}
      {tab === "categories" && (
        <div className="bg-white rounded-lg border">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b bg-gray-50 text-xs text-gray-500 uppercase">
                <th className="px-5 py-2 text-left">Code</th>
                <th className="px-5 py-2 text-left">Name</th>
                <th className="px-5 py-2 text-left">Description</th>
                <th className="px-5 py-2 text-left">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y">
              {categories.map((c) => (
                <tr key={c.id} className="hover:bg-gray-50">
                  <td className="px-5 py-3 font-mono font-semibold text-indigo-700">{c.code}</td>
                  <td className="px-5 py-3 font-medium">{c.name}</td>
                  <td className="px-5 py-3 text-gray-500">{c.description || "—"}</td>
                  <td className="px-5 py-3"><Badge label={c.is_active ? "Active" : "Inactive"} variant={c.is_active ? "green" : "gray"} /></td>
                </tr>
              ))}
              {categories.length === 0 && <tr><td colSpan={4} className="px-5 py-8 text-center text-gray-400">No categories</td></tr>}
            </tbody>
          </table>
        </div>
      )}

      {/* Rules Tab */}
      {tab === "rules" && (
        <div className="space-y-4">
          <div className="flex items-center gap-3">
            <label className="text-sm text-gray-600">Filter by country:</label>
            <select className="border rounded px-3 py-2 text-sm" value={filterCountry} onChange={(e) => setFilterCountry(e.target.value)}>
              <option value="">All countries</option>
              {countries.map((c) => <option key={c.country_code} value={c.country_code}>{c.country_code} — {c.country_name}</option>)}
            </select>
          </div>
          <div className="bg-white rounded-lg border">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b bg-gray-50 text-xs text-gray-500 uppercase">
                  <th className="px-5 py-2 text-left">Country</th>
                  <th className="px-5 py-2 text-left">Category</th>
                  <th className="px-5 py-2 text-left">Tax Type</th>
                  <th className="px-5 py-2 text-left">Applies To</th>
                  <th className="px-5 py-2 text-right">Rate %</th>
                  <th className="px-5 py-2 text-left">Compound</th>
                  <th className="px-5 py-2 text-left">Effective From</th>
                  <th className="px-5 py-2 text-left">Effective To</th>
                  <th className="px-5 py-2 text-left">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y">
                {rules.map((r) => (
                  <tr key={r.id} className="hover:bg-gray-50">
                    <td className="px-5 py-3 font-mono font-bold text-indigo-700">{r.country_code}</td>
                    <td className="px-5 py-3 font-medium">{r.category?.name || r.tax_category_id.slice(0, 8)}</td>
                    <td className="px-5 py-3">{r.tax_type.replace(/_/g, " ")}</td>
                    <td className="px-5 py-3">{r.applies_to}</td>
                    <td className="px-5 py-3 text-right font-semibold">{r.rate}%</td>
                    <td className="px-5 py-3">{r.is_compound ? <Badge label="Yes" variant="yellow" /> : "—"}</td>
                    <td className="px-5 py-3 text-gray-500">{r.effective_from || "—"}</td>
                    <td className="px-5 py-3 text-gray-500">{r.effective_to || "—"}</td>
                    <td className="px-5 py-3"><Badge label={r.is_active ? "Active" : "Inactive"} variant={r.is_active ? "green" : "gray"} /></td>
                  </tr>
                ))}
                {rules.length === 0 && <tr><td colSpan={9} className="px-5 py-8 text-center text-gray-400">No tax rules</td></tr>}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Modals */}
      {showCountryModal && (
        <CountryModal onClose={() => setShowCountryModal(false)}
          onSubmit={(d) => createCountry.mutate(d)} loading={createCountry.isPending} />
      )}
      {editCountry && (
        <CountryModal initial={editCountry} onClose={() => setEditCountry(null)}
          onSubmit={(d) => updateCountry.mutate({ code: editCountry.country_code, data: d })} loading={updateCountry.isPending} />
      )}
      {showCategoryModal && (
        <CategoryModal onClose={() => setShowCategoryModal(false)}
          onSubmit={(d) => createCategory.mutate(d)} loading={createCategory.isPending} />
      )}
      {showRuleModal && (
        <RuleModal categories={categories} countries={countries}
          onClose={() => setShowRuleModal(false)}
          onSubmit={(d) => createRule.mutate(d)} loading={createRule.isPending} />
      )}
    </div>
  );
}

function CountryModal({ initial, onClose, onSubmit, loading }: {
  initial?: CountryTaxConfig; onClose: () => void; onSubmit: (d: object) => void; loading: boolean;
}) {
  const [form, setForm] = useState({
    country_code: initial?.country_code ?? "",
    country_name: initial?.country_name ?? "",
    currency: initial?.currency ?? "KES",
    standard_vat_rate: initial?.standard_vat_rate?.toString() ?? "",
    reduced_vat_rate: initial?.reduced_vat_rate?.toString() ?? "",
    standard_wht_rate: initial?.standard_wht_rate?.toString() ?? "",
    corporate_tax_rate: initial?.corporate_tax_rate?.toString() ?? "",
    import_duty_default_rate: initial?.import_duty_default_rate?.toString() ?? "",
    fiscal_year_start_month: initial?.fiscal_year_start_month?.toString() ?? "1",
    tax_authority: initial?.tax_authority ?? "",
    notes: initial?.notes ?? "",
    is_active: initial?.is_active ?? true,
  });
  const set = (k: string, v: string | boolean) => setForm((f) => ({ ...f, [k]: v }));
  const num = (v: string) => v ? parseFloat(v) : null;

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
      <div className="bg-white rounded-xl shadow-xl w-full max-w-lg p-6 space-y-4 max-h-[90vh] overflow-y-auto">
        <h2 className="font-semibold text-lg">{initial ? "Edit Country Config" : "Add Country Config"}</h2>
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Country Code</label>
            <input className="w-full border rounded px-3 py-2 text-sm font-mono disabled:bg-gray-50" value={form.country_code}
              onChange={(e) => set("country_code", e.target.value)} disabled={!!initial} placeholder="e.g. KE" />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Country Name</label>
            <input className="w-full border rounded px-3 py-2 text-sm" value={form.country_name} onChange={(e) => set("country_name", e.target.value)} />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Currency</label>
            <input className="w-full border rounded px-3 py-2 text-sm font-mono" value={form.currency} onChange={(e) => set("currency", e.target.value)} />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Tax Authority</label>
            <input className="w-full border rounded px-3 py-2 text-sm" value={form.tax_authority} onChange={(e) => set("tax_authority", e.target.value)} placeholder="e.g. KRA, GİB" />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Standard VAT %</label>
            <input type="number" step="0.01" className="w-full border rounded px-3 py-2 text-sm" value={form.standard_vat_rate} onChange={(e) => set("standard_vat_rate", e.target.value)} />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Reduced VAT %</label>
            <input type="number" step="0.01" className="w-full border rounded px-3 py-2 text-sm" value={form.reduced_vat_rate} onChange={(e) => set("reduced_vat_rate", e.target.value)} />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">WHT Rate %</label>
            <input type="number" step="0.01" className="w-full border rounded px-3 py-2 text-sm" value={form.standard_wht_rate} onChange={(e) => set("standard_wht_rate", e.target.value)} />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Corporate Tax %</label>
            <input type="number" step="0.01" className="w-full border rounded px-3 py-2 text-sm" value={form.corporate_tax_rate} onChange={(e) => set("corporate_tax_rate", e.target.value)} />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Default Import Duty %</label>
            <input type="number" step="0.01" className="w-full border rounded px-3 py-2 text-sm" value={form.import_duty_default_rate} onChange={(e) => set("import_duty_default_rate", e.target.value)} />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Fiscal Year Start (month)</label>
            <input type="number" min="1" max="12" className="w-full border rounded px-3 py-2 text-sm" value={form.fiscal_year_start_month} onChange={(e) => set("fiscal_year_start_month", e.target.value)} />
          </div>
          <div className="col-span-2">
            <label className="block text-xs font-medium text-gray-600 mb-1">Notes</label>
            <textarea className="w-full border rounded px-3 py-2 text-sm" rows={2} value={form.notes} onChange={(e) => set("notes", e.target.value)} />
          </div>
        </div>
        <div className="flex gap-2 justify-end">
          <Button variant="secondary" onClick={onClose}>Cancel</Button>
          <Button loading={loading} onClick={() => onSubmit({
            ...form,
            standard_vat_rate: num(form.standard_vat_rate),
            reduced_vat_rate: num(form.reduced_vat_rate),
            standard_wht_rate: num(form.standard_wht_rate),
            corporate_tax_rate: num(form.corporate_tax_rate),
            import_duty_default_rate: num(form.import_duty_default_rate),
            fiscal_year_start_month: parseInt(form.fiscal_year_start_month),
          })}>Save</Button>
        </div>
      </div>
    </div>
  );
}

function CategoryModal({ onClose, onSubmit, loading }: {
  onClose: () => void; onSubmit: (d: object) => void; loading: boolean;
}) {
  const [form, setForm] = useState({ code: "", name: "", description: "" });
  const set = (k: string, v: string) => setForm((f) => ({ ...f, [k]: v }));
  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
      <div className="bg-white rounded-xl shadow-xl w-full max-w-md p-6 space-y-4">
        <h2 className="font-semibold text-lg">Add Tax Category</h2>
        <div className="space-y-3">
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Code</label>
            <input className="w-full border rounded px-3 py-2 text-sm font-mono" value={form.code} onChange={(e) => set("code", e.target.value)} placeholder="e.g. VAT_STANDARD_KE" />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Name</label>
            <input className="w-full border rounded px-3 py-2 text-sm" value={form.name} onChange={(e) => set("name", e.target.value)} placeholder="e.g. VAT Standard Rate Kenya" />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Description</label>
            <textarea className="w-full border rounded px-3 py-2 text-sm" rows={2} value={form.description} onChange={(e) => set("description", e.target.value)} />
          </div>
        </div>
        <div className="flex gap-2 justify-end">
          <Button variant="secondary" onClick={onClose}>Cancel</Button>
          <Button loading={loading} onClick={() => onSubmit(form)}>Save</Button>
        </div>
      </div>
    </div>
  );
}

function RuleModal({ categories, countries, onClose, onSubmit, loading }: {
  categories: TaxCategory[]; countries: CountryTaxConfig[];
  onClose: () => void; onSubmit: (d: object) => void; loading: boolean;
}) {
  const [form, setForm] = useState({
    country_code: "",
    tax_category_id: "",
    tax_type: "VAT" as TaxType,
    applies_to: "ALL" as TaxAppliesTo,
    rate: "",
    is_compound: false,
    effective_from: "",
    effective_to: "",
    description: "",
  });
  const set = (k: string, v: string | boolean) => setForm((f) => ({ ...f, [k]: v }));
  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
      <div className="bg-white rounded-xl shadow-xl w-full max-w-md p-6 space-y-4">
        <h2 className="font-semibold text-lg">Add Tax Rule</h2>
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Country</label>
            <select className="w-full border rounded px-3 py-2 text-sm" value={form.country_code} onChange={(e) => set("country_code", e.target.value)}>
              <option value="">Select…</option>
              {countries.map((c) => <option key={c.country_code} value={c.country_code}>{c.country_code} — {c.country_name}</option>)}
            </select>
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Tax Category</label>
            <select className="w-full border rounded px-3 py-2 text-sm" value={form.tax_category_id} onChange={(e) => set("tax_category_id", e.target.value)}>
              <option value="">Select…</option>
              {categories.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
            </select>
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Tax Type</label>
            <select className="w-full border rounded px-3 py-2 text-sm" value={form.tax_type} onChange={(e) => set("tax_type", e.target.value)}>
              {TAX_TYPES.map((t) => <option key={t} value={t}>{t.replace(/_/g, " ")}</option>)}
            </select>
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Applies To</label>
            <select className="w-full border rounded px-3 py-2 text-sm" value={form.applies_to} onChange={(e) => set("applies_to", e.target.value)}>
              {APPLIES_TO.map((t) => <option key={t} value={t}>{t}</option>)}
            </select>
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Rate %</label>
            <input type="number" step="0.0001" className="w-full border rounded px-3 py-2 text-sm" value={form.rate} onChange={(e) => set("rate", e.target.value)} />
          </div>
          <div className="flex items-center gap-2 pt-5">
            <input type="checkbox" id="compound" checked={form.is_compound} onChange={(e) => set("is_compound", e.target.checked)} />
            <label htmlFor="compound" className="text-sm">Compound tax</label>
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Effective From</label>
            <input type="date" className="w-full border rounded px-3 py-2 text-sm" value={form.effective_from} onChange={(e) => set("effective_from", e.target.value)} />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Effective To</label>
            <input type="date" className="w-full border rounded px-3 py-2 text-sm" value={form.effective_to} onChange={(e) => set("effective_to", e.target.value)} />
          </div>
          <div className="col-span-2">
            <label className="block text-xs font-medium text-gray-600 mb-1">Description</label>
            <input className="w-full border rounded px-3 py-2 text-sm" value={form.description} onChange={(e) => set("description", e.target.value)} />
          </div>
        </div>
        <div className="flex gap-2 justify-end">
          <Button variant="secondary" onClick={onClose}>Cancel</Button>
          <Button loading={loading} onClick={() => onSubmit({
            ...form,
            rate: parseFloat(form.rate),
            effective_from: form.effective_from || null,
            effective_to: form.effective_to || null,
          })}>Save</Button>
        </div>
      </div>
    </div>
  );
}
