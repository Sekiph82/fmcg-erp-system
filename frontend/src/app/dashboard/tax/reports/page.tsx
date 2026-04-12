"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { taxApi, TaxSummaryRow, RegulatoryStatusRow } from "@/lib/tax_regulatory";
import { Badge } from "@/components/ui/Badge";

const STATUS_VARIANT: Record<string, "green" | "red" | "yellow" | "gray"> = {
  COMPLIANT: "green",
  NON_COMPLIANT: "red",
  EXPIRED: "red",
  PENDING: "yellow",
  NOT_APPLICABLE: "gray",
};

export default function TaxReportsPage() {
  const [filterCountry, setFilterCountry] = useState("");

  const { data: countries = [] } = useQuery({ queryKey: ["tax-countries"], queryFn: taxApi.listCountries });

  const { data: taxSummary = [], isLoading: loadingTax } = useQuery<TaxSummaryRow[]>({
    queryKey: ["tax-summary-report", filterCountry],
    queryFn: () => taxApi.getTaxSummary(filterCountry || undefined),
  });

  const { data: regStatus = [], isLoading: loadingReg } = useQuery<RegulatoryStatusRow[]>({
    queryKey: ["regulatory-status-report", filterCountry],
    queryFn: () => taxApi.getRegulatoryStatus(filterCountry || undefined),
  });

  // Group tax summary by country
  const byCountry = taxSummary.reduce<Record<string, TaxSummaryRow[]>>((acc, r) => {
    (acc[r.country_code] = acc[r.country_code] || []).push(r);
    return acc;
  }, {});

  const countryTotals = Object.entries(byCountry).map(([code, rows]) => ({
    country_code: code,
    currency: rows[0]?.currency ?? "",
    total_tax: rows.reduce((s, r) => s + Number(r.total_tax_amount), 0),
    total_taxable: rows.reduce((s, r) => s + Number(r.total_taxable_amount), 0),
    tx_count: rows.reduce((s, r) => s + r.transaction_count, 0),
    rows,
  }));

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Tax Reports</h1>
          <p className="text-sm text-gray-500 mt-1">Tax summary by country and type, regulatory compliance overview</p>
        </div>
        <select className="border rounded px-3 py-2 text-sm" value={filterCountry} onChange={(e) => setFilterCountry(e.target.value)}>
          <option value="">All countries</option>
          {countries.map((c) => <option key={c.country_code} value={c.country_code}>{c.country_code} — {c.country_name}</option>)}
        </select>
      </div>

      {/* Country summary tiles */}
      {countryTotals.length > 0 && (
        <div className="grid grid-cols-3 gap-4">
          {countryTotals.map((c) => (
            <div key={c.country_code} className="bg-white rounded-lg border p-4">
              <div className="flex items-center justify-between mb-3">
                <span className="text-lg font-bold text-indigo-700">{c.country_code}</span>
                <span className="text-xs text-gray-500">{c.currency}</span>
              </div>
              <div className="space-y-1">
                <div className="flex justify-between text-sm">
                  <span className="text-gray-500">Taxable Amount</span>
                  <span className="font-medium">{c.total_taxable.toLocaleString(undefined, { maximumFractionDigits: 0 })}</span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-gray-500">Total Tax</span>
                  <span className="font-bold text-indigo-600">{c.total_tax.toLocaleString(undefined, { maximumFractionDigits: 0 })}</span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-gray-500">Effective Rate</span>
                  <span>{c.total_taxable > 0 ? ((c.total_tax / c.total_taxable) * 100).toFixed(2) : "0.00"}%</span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-gray-500">Transactions</span>
                  <span>{c.tx_count}</span>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Tax breakdown table */}
      {taxSummary.length > 0 && (
        <div className="bg-white rounded-lg border">
          <div className="px-5 py-3 border-b font-semibold text-gray-800">Tax Breakdown by Country & Type</div>
          {loadingTax ? <p className="px-5 py-8 text-center text-gray-400">Loading…</p> : (
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b bg-gray-50 text-xs text-gray-500 uppercase">
                  <th className="px-5 py-2 text-left">Country</th>
                  <th className="px-5 py-2 text-left">Tax Type</th>
                  <th className="px-5 py-2 text-left">Currency</th>
                  <th className="px-5 py-2 text-right">Taxable Amount</th>
                  <th className="px-5 py-2 text-right">Tax Amount</th>
                  <th className="px-5 py-2 text-right">Effective %</th>
                  <th className="px-5 py-2 text-right">Transactions</th>
                </tr>
              </thead>
              <tbody className="divide-y">
                {taxSummary.map((r, i) => (
                  <tr key={i} className="hover:bg-gray-50">
                    <td className="px-5 py-3 font-mono font-bold text-indigo-700">{r.country_code}</td>
                    <td className="px-5 py-3">{r.tax_type.replace(/_/g, " ")}</td>
                    <td className="px-5 py-3">{r.currency}</td>
                    <td className="px-5 py-3 text-right">{Number(r.total_taxable_amount).toLocaleString()}</td>
                    <td className="px-5 py-3 text-right font-semibold">{Number(r.total_tax_amount).toLocaleString()}</td>
                    <td className="px-5 py-3 text-right">
                      {Number(r.total_taxable_amount) > 0
                        ? ((Number(r.total_tax_amount) / Number(r.total_taxable_amount)) * 100).toFixed(2)
                        : "0.00"}%
                    </td>
                    <td className="px-5 py-3 text-right">{r.transaction_count}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      )}

      {taxSummary.length === 0 && !loadingTax && (
        <div className="bg-white rounded-lg border p-12 text-center text-gray-400">
          No confirmed or posted tax transactions found
        </div>
      )}

      {/* Regulatory compliance table */}
      <div className="bg-white rounded-lg border">
        <div className="px-5 py-3 border-b font-semibold text-gray-800">Regulatory Compliance Status</div>
        {loadingReg ? <p className="px-5 py-8 text-center text-gray-400">Loading…</p> : (
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b bg-gray-50 text-xs text-gray-500 uppercase">
                <th className="px-5 py-2 text-left">Country</th>
                <th className="px-5 py-2 text-left">Flag Type</th>
                <th className="px-5 py-2 text-left">Status</th>
                <th className="px-5 py-2 text-right">Count</th>
                <th className="px-5 py-2 text-right">Expiring (30d)</th>
              </tr>
            </thead>
            <tbody className="divide-y">
              {regStatus.map((r, i) => (
                <tr key={i} className="hover:bg-gray-50">
                  <td className="px-5 py-3 font-mono font-bold text-indigo-700">{r.country_code}</td>
                  <td className="px-5 py-3">{r.flag_type.replace(/_/g, " ")}</td>
                  <td className="px-5 py-3">
                    <Badge label={r.status.replace(/_/g, " ")} variant={STATUS_VARIANT[r.status] ?? "gray"} />
                  </td>
                  <td className="px-5 py-3 text-right">{r.count}</td>
                  <td className="px-5 py-3 text-right">
                    {r.expiring_soon > 0 ? (
                      <span className="text-orange-600 font-semibold">{r.expiring_soon}</span>
                    ) : "—"}
                  </td>
                </tr>
              ))}
              {regStatus.length === 0 && (
                <tr><td colSpan={5} className="px-5 py-8 text-center text-gray-400">No regulatory data</td></tr>
              )}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
