"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import { reportBuilderApi, Report, DataSource } from "@/lib/report_builder";

export default function ReportBuilderHome() {
  const [reports, setReports] = useState<Report[]>([]);
  const [catalog, setCatalog] = useState<Record<string, DataSource>>({});
  const [loading, setLoading] = useState(true);
  const [seeding, setSeeding] = useState(false);

  useEffect(() => {
    Promise.all([reportBuilderApi.listReports(), reportBuilderApi.getCatalog()])
      .then(([r, c]) => { setReports(r); setCatalog(c); })
      .finally(() => setLoading(false));
  }, []);

  const seed = async () => {
    setSeeding(true);
    const r = await reportBuilderApi.seedTemplates();
    setSeeding(false);
    alert(`Seeded ${r.created} template reports.`);
    reportBuilderApi.listReports().then(setReports);
  };

  const totalRuns = reports.reduce((s, r) => s + r.run_count, 0);
  const templates = reports.filter(r => r.is_template).length;
  const scheduled = reports.filter(r => r.schedules.length > 0).length;

  const links = [
    { href: "/dashboard/report-builder/catalog", label: "Data Catalog" },
    { href: "/dashboard/report-builder/builder", label: "Build Report" },
    { href: "/dashboard/report-builder/saved", label: "Saved Reports" },
    { href: "/dashboard/report-builder/viewer", label: "Report Viewer" },
    { href: "/dashboard/report-builder/dashboards", label: "Dashboards" },
    { href: "/dashboard/report-builder/schedules", label: "Schedules" },
    { href: "/dashboard/report-builder/ai", label: "AI Insights" },
  ];

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-900">Custom Report Builder</h1>
        <button onClick={seed} disabled={seeding}
          className="rounded border border-gray-300 px-3 py-1.5 text-sm text-gray-600 hover:bg-gray-50 disabled:opacity-50">
          {seeding ? "Seeding…" : "Seed Template Reports"}
        </button>
      </div>

      {!loading && (
        <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
          {[
            { label: "Total Reports", value: reports.length },
            { label: "Templates", value: templates, color: "text-blue-600" },
            { label: "Scheduled", value: scheduled, color: "text-green-600" },
            { label: "Total Runs", value: totalRuns, color: "text-purple-600" },
          ].map(k => (
            <div key={k.label} className="bg-white rounded-lg border p-4 shadow-sm">
              <p className="text-xs text-gray-500">{k.label}</p>
              <p className={`text-2xl font-bold mt-1 ${k.color ?? "text-gray-900"}`}>{k.value}</p>
            </div>
          ))}
        </div>
      )}

      <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
        {Object.entries(catalog).slice(0, 6).map(([key, ds]) => (
          <div key={key} className="bg-white border rounded-lg p-3 shadow-sm">
            <p className="font-semibold text-gray-800 text-sm">{ds.label}</p>
            <p className="text-xs text-gray-400">{ds.module} · {ds.field_count} fields</p>
          </div>
        ))}
      </div>

      <div className="bg-white border rounded-lg p-4 shadow-sm">
        <h2 className="text-sm font-semibold text-gray-700 mb-3">Quick Navigation</h2>
        <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
          {links.map(l => (
            <Link key={l.href} href={l.href}
              className="block rounded border border-blue-200 bg-blue-50 px-3 py-2 text-sm text-blue-700 hover:bg-blue-100 text-center">
              {l.label}
            </Link>
          ))}
        </div>
      </div>
    </div>
  );
}
