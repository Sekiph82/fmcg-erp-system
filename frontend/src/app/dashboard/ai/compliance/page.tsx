"use client";

import Link from "next/link";

export default function CompliancePage() {
  return (
    <div className="p-6 space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Compliance & Documents</h1>
        <p className="text-sm text-gray-500 mt-0.5">Regulatory compliance, SDS sheets, and document management</p>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
        {[
          {
            title: "Safety Data Sheets",
            description: "AI-generated SDS for your formulations, compliant with GHS/UN standards",
            icon: "🛡️",
            href: "/dashboard/documents",
            badge: "Via Documents",
          },
          {
            title: "Regulatory Labels",
            description: "Generate compliant product labels for Kenya Bureau of Standards (KEBS) and regional markets",
            icon: "🏷️",
            href: "/dashboard/documents",
            badge: "Via Documents",
          },
          {
            title: "AI Formulations",
            description: "All approved formulations with safety notes and regulatory compliance guidance",
            icon: "🧪",
            href: "/dashboard/ai/formulations",
            badge: "Formulation Engine",
          },
          {
            title: "Tax & Regulatory",
            description: "Country-specific tax rules, excise duties, and import/export compliance",
            icon: "⚖️",
            href: "/dashboard/tax",
            badge: "Tax Module",
          },
          {
            title: "Quality Control",
            description: "QC parameters, inspection records, and CoA (Certificate of Analysis) management",
            icon: "✅",
            href: "/dashboard/production/quality",
            badge: "Quality Module",
          },
          {
            title: "Audit Logs",
            description: "Complete audit trail of all system actions for compliance reporting",
            icon: "📋",
            href: "/dashboard/ai/logs",
            badge: "AI Logs",
          },
        ].map((item) => (
          <Link
            key={item.title}
            href={item.href}
            className="bg-white rounded-xl border border-gray-200 shadow-sm p-5 hover:border-indigo-300 hover:shadow-md transition group"
          >
            <div className="flex items-start justify-between mb-3">
              <span className="text-3xl">{item.icon}</span>
              <span className="text-xs bg-gray-100 text-gray-500 px-2 py-0.5 rounded-full">{item.badge}</span>
            </div>
            <h3 className="font-semibold text-gray-800 group-hover:text-indigo-700">{item.title}</h3>
            <p className="text-sm text-gray-500 mt-1">{item.description}</p>
          </Link>
        ))}
      </div>

      <div className="bg-amber-50 border border-amber-200 rounded-xl p-5">
        <h3 className="font-semibold text-amber-800 mb-1">⚠️ Regulatory Context</h3>
        <p className="text-sm text-amber-700">
          This ERP is configured for the East African market (Kenya primary, with export to Uganda, Tanzania, Rwanda).
          AI formulations include KEBS compliance notes. For export to EU/US markets, additional regulatory review is required.
          Always verify AI-generated safety data against current regulatory databases before commercial use.
        </p>
      </div>
    </div>
  );
}
