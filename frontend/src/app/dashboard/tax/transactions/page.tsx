"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { taxApi, CountryTaxConfig, TransactionTax, TaxType, TxTaxStatus } from "@/lib/tax_regulatory";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";

const STATUS_VARIANT: Record<string, "green" | "blue" | "yellow" | "gray"> = {
  DRAFT: "gray",
  CONFIRMED: "blue",
  POSTED: "green",
  REVERSED: "gray",
};

const TAX_TYPES: TaxType[] = [
  "VAT", "EXCISE", "CUSTOMS_DUTY", "WITHHOLDING_TAX",
  "RAILWAY_DEV_LEVY", "IDF_FEE", "STAMP_DUTY", "CORPORATE_TAX", "OTHER",
];

const ENTITY_TYPES = ["PURCHASE_ORDER", "SALES_ORDER", "INVOICE", "INTL_SHIPMENT"];

export default function TransactionTaxesPage() {
  const qc = useQueryClient();
  const [filterEntityType, setFilterEntityType] = useState("");
  const [filterCountry, setFilterCountry] = useState("");
  const [showNew, setShowNew] = useState(false);

  const { data: countries = [] } = useQuery({ queryKey: ["tax-countries"], queryFn: taxApi.listCountries });

  const { data: taxes = [], isLoading } = useQuery({
    queryKey: ["transaction-taxes", filterEntityType, filterCountry],
    queryFn: () => taxApi.listTransactionTaxes({
      entity_type: filterEntityType || undefined,
      country_code: filterCountry || undefined,
    }),
  });

  const createTax = useMutation({
    mutationFn: (d: object) => taxApi.createTransactionTax(d),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["transaction-taxes"] }); setShowNew(false); },
  });

  const updateStatus = useMutation({
    mutationFn: ({ id, status }: { id: string; status: TxTaxStatus }) => taxApi.updateTransactionTax(id, { status }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["transaction-taxes"] }),
  });

  const totalTax = taxes.reduce((s: number, t: TransactionTax) => s + Number(t.tax_amount), 0);
  const draftCount = taxes.filter((t: TransactionTax) => t.status === "DRAFT").length;
  const confirmedCount = taxes.filter((t: TransactionTax) => t.status === "CONFIRMED").length;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Transaction Taxes</h1>
          <p className="text-sm text-gray-500 mt-1">Tax lines applied on purchase orders, sales orders, invoices and shipments</p>
        </div>
        <Button onClick={() => setShowNew(true)}>Add Tax Line</Button>
      </div>

      {/* KPIs */}
      <div className="grid grid-cols-4 gap-4">
        <div className="bg-white rounded-lg border p-4">
          <p className="text-xs text-gray-500">Total Tax Amount</p>
          <p className="text-xl font-bold text-indigo-600 mt-1">{totalTax.toLocaleString(undefined, { maximumFractionDigits: 0 })}</p>
        </div>
        <div className="bg-white rounded-lg border p-4">
          <p className="text-xs text-gray-500">Total Lines</p>
          <p className="text-xl font-bold text-gray-800 mt-1">{taxes.length}</p>
        </div>
        <div className="bg-white rounded-lg border p-4">
          <p className="text-xs text-gray-500">Draft</p>
          <p className="text-xl font-bold text-yellow-600 mt-1">{draftCount}</p>
        </div>
        <div className="bg-white rounded-lg border p-4">
          <p className="text-xs text-gray-500">Confirmed</p>
          <p className="text-xl font-bold text-blue-600 mt-1">{confirmedCount}</p>
        </div>
      </div>

      {/* Filters */}
      <div className="flex flex-wrap gap-3">
        <select className="border rounded px-3 py-2 text-sm" value={filterEntityType} onChange={(e) => setFilterEntityType(e.target.value)}>
          <option value="">All entity types</option>
          {ENTITY_TYPES.map((t) => <option key={t} value={t}>{t.replace(/_/g, " ")}</option>)}
        </select>
        <select className="border rounded px-3 py-2 text-sm" value={filterCountry} onChange={(e) => setFilterCountry(e.target.value)}>
          <option value="">All countries</option>
          {countries.map((c: CountryTaxConfig) => <option key={c.country_code} value={c.country_code}>{c.country_code}</option>)}
        </select>
      </div>

      {/* Table */}
      <div className="bg-white rounded-lg border overflow-x-auto">
        {isLoading ? <p className="px-5 py-8 text-center text-gray-400">Loading…</p> : (
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b bg-gray-50 text-xs text-gray-500 uppercase">
                <th className="px-5 py-2 text-left">Entity Type</th>
                <th className="px-5 py-2 text-left">Entity ID</th>
                <th className="px-5 py-2 text-left">Country</th>
                <th className="px-5 py-2 text-left">Tax Type</th>
                <th className="px-5 py-2 text-right">Taxable Amt</th>
                <th className="px-5 py-2 text-right">Rate %</th>
                <th className="px-5 py-2 text-right">Tax Amt</th>
                <th className="px-5 py-2 text-left">Currency</th>
                <th className="px-5 py-2 text-left">Status</th>
                <th className="px-5 py-2" />
              </tr>
            </thead>
            <tbody className="divide-y">
              {taxes.map((t: TransactionTax) => (
                <tr key={t.id} className="hover:bg-gray-50">
                  <td className="px-5 py-3 text-xs font-semibold text-gray-700">{t.entity_type.replace(/_/g, " ")}</td>
                  <td className="px-5 py-3 font-mono text-xs text-gray-400">{t.entity_id.slice(0, 8)}…</td>
                  <td className="px-5 py-3 font-mono font-bold text-indigo-700">{t.country_code}</td>
                  <td className="px-5 py-3">{t.tax_type.replace(/_/g, " ")}</td>
                  <td className="px-5 py-3 text-right">{Number(t.taxable_amount).toLocaleString()}</td>
                  <td className="px-5 py-3 text-right">{t.rate}%</td>
                  <td className="px-5 py-3 text-right font-semibold">{Number(t.tax_amount).toLocaleString()}</td>
                  <td className="px-5 py-3">{t.currency}</td>
                  <td className="px-5 py-3"><Badge label={t.status} variant={STATUS_VARIANT[t.status]} /></td>
                  <td className="px-5 py-3">
                    {t.status === "DRAFT" && (
                      <button className="text-xs text-blue-600 hover:underline"
                        onClick={() => updateStatus.mutate({ id: t.id, status: "CONFIRMED" })}>
                        Confirm
                      </button>
                    )}
                    {t.status === "CONFIRMED" && (
                      <button className="text-xs text-green-600 hover:underline"
                        onClick={() => updateStatus.mutate({ id: t.id, status: "POSTED" })}>
                        Post
                      </button>
                    )}
                  </td>
                </tr>
              ))}
              {taxes.length === 0 && <tr><td colSpan={10} className="px-5 py-8 text-center text-gray-400">No transaction taxes</td></tr>}
            </tbody>
          </table>
        )}
      </div>

      {showNew && (
        <TaxLineModal countries={countries.map((c: CountryTaxConfig) => ({ code: c.country_code, currency: c.currency }))}
          onClose={() => setShowNew(false)} onSubmit={(d) => createTax.mutate(d)} loading={createTax.isPending} />
      )}
    </div>
  );
}

function TaxLineModal({ countries, onClose, onSubmit, loading }: {
  countries: { code: string; currency: string }[];
  onClose: () => void; onSubmit: (d: object) => void; loading: boolean;
}) {
  const [form, setForm] = useState({
    entity_type: "PURCHASE_ORDER",
    entity_id: "",
    country_code: "",
    tax_type: "VAT" as TaxType,
    description: "",
    taxable_amount: "",
    rate: "",
    tax_amount: "",
    currency: "KES",
    notes: "",
  });
  const set = (k: string, v: string) => {
    setForm((f) => {
      const next = { ...f, [k]: v };
      // Auto-calc tax_amount when taxable_amount or rate changes
      if (k === "taxable_amount" || k === "rate") {
        const base = parseFloat(k === "taxable_amount" ? v : next.taxable_amount);
        const rate = parseFloat(k === "rate" ? v : next.rate);
        if (!isNaN(base) && !isNaN(rate)) {
          next.tax_amount = ((base * rate) / 100).toFixed(4);
        }
      }
      if (k === "country_code") {
        const c = countries.find((x) => x.code === v);
        if (c) next.currency = c.currency;
      }
      return next;
    });
  };

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
      <div className="bg-white rounded-xl shadow-xl w-full max-w-lg p-6 space-y-4">
        <h2 className="font-semibold text-lg">Add Tax Line</h2>
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Entity Type</label>
            <select className="w-full border rounded px-3 py-2 text-sm" value={form.entity_type} onChange={(e) => set("entity_type", e.target.value)}>
              {ENTITY_TYPES.map((t) => <option key={t} value={t}>{t.replace(/_/g, " ")}</option>)}
            </select>
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Entity ID (UUID)</label>
            <input className="w-full border rounded px-3 py-2 text-sm font-mono" value={form.entity_id} onChange={(e) => set("entity_id", e.target.value)} placeholder="UUID of PO/SO/Invoice" />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Country</label>
            <select className="w-full border rounded px-3 py-2 text-sm" value={form.country_code} onChange={(e) => set("country_code", e.target.value)}>
              <option value="">Select…</option>
              {countries.map((c) => <option key={c.code} value={c.code}>{c.code}</option>)}
            </select>
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Tax Type</label>
            <select className="w-full border rounded px-3 py-2 text-sm" value={form.tax_type} onChange={(e) => set("tax_type", e.target.value)}>
              {TAX_TYPES.map((t) => <option key={t} value={t}>{t.replace(/_/g, " ")}</option>)}
            </select>
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Taxable Amount</label>
            <input type="number" step="0.01" className="w-full border rounded px-3 py-2 text-sm" value={form.taxable_amount} onChange={(e) => set("taxable_amount", e.target.value)} />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Rate %</label>
            <input type="number" step="0.0001" className="w-full border rounded px-3 py-2 text-sm" value={form.rate} onChange={(e) => set("rate", e.target.value)} />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Tax Amount (auto)</label>
            <input type="number" step="0.0001" className="w-full border rounded px-3 py-2 text-sm bg-gray-50" value={form.tax_amount} onChange={(e) => set("tax_amount", e.target.value)} />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Currency</label>
            <input className="w-full border rounded px-3 py-2 text-sm font-mono" value={form.currency} onChange={(e) => set("currency", e.target.value)} />
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
            taxable_amount: parseFloat(form.taxable_amount),
            rate: parseFloat(form.rate),
            tax_amount: parseFloat(form.tax_amount),
          })}>Save</Button>
        </div>
      </div>
    </div>
  );
}
