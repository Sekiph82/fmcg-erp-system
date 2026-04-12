"use client";

import { useQuery } from "@tanstack/react-query";
import { taxApi, RegulatoryStatusRow, TaxSummaryRow } from "@/lib/tax_regulatory";
import { Badge } from "@/components/ui/Badge";
import Link from "next/link";

const STATUS_VARIANT: Record<string, "green" | "red" | "yellow" | "gray" | "blue"> = {
  COMPLIANT: "green",
  NON_COMPLIANT: "red",
  EXPIRED: "red",
  PENDING: "yellow",
  NOT_APPLICABLE: "gray",
};

export default function TaxDashboardPage() {
  const { data: taxSummary = [] } = useQuery<TaxSummaryRow[]>({
    queryKey: ["tax-summary"],
    queryFn: () => taxApi.getTaxSummary(),
  });

  const { data: regStatus = [] } = useQuery<RegulatoryStatusRow[]>({
    queryKey: ["regulatory-status"],
    queryFn: () => taxApi.getRegulatoryStatus(),
  });

  const { data: expiringFlags = [] } = useQuery({
    queryKey: ["expiring-flags"],
    queryFn: () => taxApi.getExpiringFlags(30),
  });

  const totalTax = taxSummary.reduce((s: number, r: TaxSummaryRow) => s + Number(r.total_tax_amount), 0);
  const nonCompliant = regStatus.filter((r: RegulatoryStatusRow) => r.status === "NON_COMPLIANT" || r.status === "EXPIRED")
    .reduce((s: number, r: RegulatoryStatusRow) => s + r.count, 0);
  const pendingCount = regStatus.filter((r: RegulatoryStatusRow) => r.status === "PENDING").reduce((s: number, r: RegulatoryStatusRow) => s + r.count, 0);

  const kpis = [
    { label: "Total Tax Posted (KES)", value: totalTax.toLocaleString(undefined, { maximumFractionDigits: 0 }), color: "text-indigo-600" },
    { label: "Non-Compliant Flags", value: nonCompliant, color: nonCompliant > 0 ? "text-red-600" : "text-green-600" },
    { label: "Pending Flags", value: pendingCount, color: "text-yellow-600" },
    { label: "Expiring (30 days)", value: expiringFlags.length, color: expiringFlags.length > 0 ? "text-orange-600" : "text-green-600" },
  ];

  const quickLinks = [
    { href: "/dashboard/tax/rules", label: "Tax Rules & Categories", desc: "Country VAT, excise, WHT rules" },
    { href: "/dashboard/tax/regulatory", label: "Regulatory Flags", desc: "Compliance, licenses, certifications" },
    { href: "/dashboard/tax/transactions", label: "Transaction Taxes", desc: "Applied taxes on POs/SOs/invoices" },
    { href: "/dashboard/tax/reports", label: "Tax Reports", desc: "Summary by country and type" },
  ];

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Tax & Regulatory</h1>
        <p className="text-sm text-gray-500 mt-1">Kenya & Turkey tax rules, compliance flags, and transaction tax tracking</p>
      </div>

      {/* KPI tiles */}
      <div className="grid grid-cols-4 gap-4">
        {kpis.map((k) => (
          <div key={k.label} className="bg-white rounded-lg border p-4">
            <p className="text-xs text-gray-500">{k.label}</p>
            <p className={`text-2xl font-bold mt-1 ${k.color}`}>{k.value}</p>
          </div>
        ))}
      </div>

      {/* Expiring flags alert */}
      {expiringFlags.length > 0 && (
        <div className="bg-orange-50 border border-orange-200 rounded-lg p-4">
          <p className="font-semibold text-orange-800 text-sm mb-2">
            {expiringFlags.length} regulatory certificate(s) expiring within 30 days
          </p>
          <div className="space-y-1">
            {expiringFlags.slice(0, 5).map((f) => (
              <div key={f.id} className="flex items-center gap-3 text-sm text-orange-700">
                <span className="font-mono text-xs">{f.country_code}</span>
                <span>{f.flag_type.replace(/_/g, " ")}</span>
                {f.license_no && <span className="text-orange-500">{f.license_no}</span>}
                <span className="ml-auto text-xs">Expires: {f.expiry_date}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Tax summary */}
      {taxSummary.length > 0 && (
        <div className="bg-white rounded-lg border">
          <div className="px-5 py-3 border-b font-semibold text-gray-800">Tax Summary (Confirmed + Posted)</div>
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b bg-gray-50 text-xs text-gray-500 uppercase">
                <th className="px-5 py-2 text-left">Country</th>
                <th className="px-5 py-2 text-left">Tax Type</th>
                <th className="px-5 py-2 text-left">Currency</th>
                <th className="px-5 py-2 text-right">Taxable Amount</th>
                <th className="px-5 py-2 text-right">Tax Amount</th>
                <th className="px-5 py-2 text-right">Transactions</th>
              </tr>
            </thead>
            <tbody className="divide-y">
              {taxSummary.map((r, i) => (
                <tr key={i} className="hover:bg-gray-50">
                  <td className="px-5 py-3 font-semibold text-indigo-700">{r.country_code}</td>
                  <td className="px-5 py-3">{r.tax_type.replace(/_/g, " ")}</td>
                  <td className="px-5 py-3">{r.currency}</td>
                  <td className="px-5 py-3 text-right">{Number(r.total_taxable_amount).toLocaleString()}</td>
                  <td className="px-5 py-3 text-right font-semibold">{Number(r.total_tax_amount).toLocaleString()}</td>
                  <td className="px-5 py-3 text-right">{r.transaction_count}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Regulatory status */}
      {regStatus.length > 0 && (
        <div className="bg-white rounded-lg border">
          <div className="px-5 py-3 border-b font-semibold text-gray-800">Regulatory Compliance Status</div>
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b bg-gray-50 text-xs text-gray-500 uppercase">
                <th className="px-5 py-2 text-left">Country</th>
                <th className="px-5 py-2 text-left">Flag Type</th>
                <th className="px-5 py-2 text-left">Status</th>
                <th className="px-5 py-2 text-right">Count</th>
                <th className="px-5 py-2 text-right">Expiring Soon</th>
              </tr>
            </thead>
            <tbody className="divide-y">
              {regStatus.map((r, i) => (
                <tr key={i} className="hover:bg-gray-50">
                  <td className="px-5 py-3 font-semibold">{r.country_code}</td>
                  <td className="px-5 py-3">{r.flag_type.replace(/_/g, " ")}</td>
                  <td className="px-5 py-3">
                    <Badge label={r.status} variant={STATUS_VARIANT[r.status] ?? "gray"} />
                  </td>
                  <td className="px-5 py-3 text-right">{r.count}</td>
                  <td className="px-5 py-3 text-right">
                    {r.expiring_soon > 0 ? (
                      <span className="text-orange-600 font-semibold">{r.expiring_soon}</span>
                    ) : "—"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Quick links */}
      <div className="grid grid-cols-4 gap-4">
        {quickLinks.map((l) => (
          <Link key={l.href} href={l.href}
            className="bg-white rounded-lg border p-4 hover:border-indigo-300 hover:shadow-sm transition-all">
            <p className="font-semibold text-gray-800 text-sm">{l.label}</p>
            <p className="text-xs text-gray-500 mt-1">{l.desc}</p>
          </Link>
        ))}
      </div>
    </div>
  );
}
