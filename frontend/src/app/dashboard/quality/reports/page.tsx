"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { qualityApi, QCType } from "@/lib/quality";
import { Table } from "@/components/ui/Table";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Select } from "@/components/ui/Select";

type Tab = "overview" | "rejections" | "incoming" | "in-process" | "finished-goods";

const TABS: { key: Tab; label: string }[] = [
  { key: "overview", label: "Overview" },
  { key: "rejections", label: "Rejection Summary" },
  { key: "incoming", label: "Incoming QC" },
  { key: "in-process", label: "In-Process" },
  { key: "finished-goods", label: "Finished Goods" },
];

const QC_TYPE_MAP: Record<string, QCType> = {
  "incoming": "INCOMING",
  "in-process": "IN_PROCESS",
  "finished-goods": "FINISHED_GOODS",
};

function PassBar({ pass, total }: { pass: number; total: number }) {
  if (total === 0) return <span className="text-gray-400 text-xs">—</span>;
  const pct = Math.round(pass / total * 100);
  const color = pct >= 90 ? "bg-green-500" : pct >= 70 ? "bg-amber-400" : "bg-red-400";
  return (
    <div className="flex items-center gap-2">
      <div className="w-24 h-2 rounded-full bg-gray-200">
        <div className={`h-2 rounded-full ${color}`} style={{ width: `${pct}%` }} />
      </div>
      <span className="text-xs font-medium">{pct}%</span>
    </div>
  );
}

export default function QCReportsPage() {
  const router = useRouter();
  const [tab, setTab] = useState<Tab>("overview");

  const { data: allInspections = [], isFetching: loadingAll } = useQuery({
    queryKey: ["qc-inspections-all"],
    queryFn: () => qualityApi.listInspections({}),
    enabled: tab === "overview",
  });

  const currentQCType = QC_TYPE_MAP[tab];
  const { data: typeInspections = [], isFetching: loadingType } = useQuery({
    queryKey: ["qc-inspections", tab],
    queryFn: () => qualityApi.listInspections({ qc_type: currentQCType }),
    enabled: !!currentQCType,
  });

  const { data: rejections = [], isFetching: loadingRej } = useQuery({
    queryKey: ["qc-rejections"],
    queryFn: () => qualityApi.rejectionSummary(),
    enabled: tab === "rejections",
  });

  const inspections = currentQCType ? typeInspections : allInspections;
  const Spinner = () => (
    <div className="flex justify-center py-16"><div className="h-8 w-8 animate-spin rounded-full border-4 border-indigo-600 border-t-transparent" /></div>
  );

  // Overview stats
  const total = allInspections.length;
  const passed = allInspections.filter((i) => i.status === "PASSED").length;
  const failed = allInspections.filter((i) => i.status === "FAILED").length;
  const conditional = allInspections.filter((i) => i.status === "CONDITIONAL_RELEASE").length;
  const quarantined = allInspections.filter((i) => i.quarantine_applied).length;
  const reworkCandidates = allInspections.filter((i) => i.rework_candidate).length;
  const criticalFails = allInspections.filter((i) => i.critical_fail).length;

  const byType = (type: QCType) => ({
    total: allInspections.filter((i) => i.qc_type === type).length,
    passed: allInspections.filter((i) => i.qc_type === type && i.status === "PASSED").length,
  });

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">QC Reports</h1>
        <p className="text-sm text-gray-500 mt-1">Inspection outcomes, rejection analysis, and compliance overview</p>
      </div>

      {/* Tab bar */}
      <div className="flex gap-1 rounded-lg bg-gray-100 p-1 w-fit">
        {TABS.map((t) => (
          <button key={t.key} onClick={() => setTab(t.key)}
            className={`rounded-md px-4 py-1.5 text-sm font-medium transition-colors ${tab === t.key ? "bg-white shadow-sm text-gray-900" : "text-gray-500 hover:text-gray-700"}`}>
            {t.label}
          </button>
        ))}
      </div>

      {/* ── Overview ── */}
      {tab === "overview" && (
        loadingAll ? <Spinner /> : (
          <div className="space-y-6">
            <div className="grid grid-cols-4 gap-4">
              {[
                { label: "Total Inspections", value: total, color: "text-gray-900" },
                { label: "Passed", value: passed, color: "text-green-600" },
                { label: "Failed", value: failed, color: failed > 0 ? "text-red-600" : "text-gray-400" },
                { label: "Conditional", value: conditional, color: conditional > 0 ? "text-amber-600" : "text-gray-400" },
                { label: "Quarantined", value: quarantined, color: quarantined > 0 ? "text-red-700" : "text-gray-400" },
                { label: "Rework Candidates", value: reworkCandidates, color: reworkCandidates > 0 ? "text-amber-600" : "text-gray-400" },
                { label: "Critical Failures", value: criticalFails, color: criticalFails > 0 ? "text-red-700 font-extrabold" : "text-gray-400" },
                { label: "Pass Rate", value: total > 0 ? `${Math.round(passed / total * 100)}%` : "—", color: "text-indigo-600" },
              ].map((c) => (
                <div key={c.label} className="rounded-xl border border-gray-200 bg-white p-4 shadow-sm">
                  <p className="text-xs text-gray-500">{c.label}</p>
                  <p className={`text-2xl font-bold ${c.color}`}>{c.value}</p>
                </div>
              ))}
            </div>

            <div className="grid grid-cols-3 gap-4">
              {[
                { type: "INCOMING" as QCType, label: "Incoming QC" },
                { type: "IN_PROCESS" as QCType, label: "In-Process QC" },
                { type: "FINISHED_GOODS" as QCType, label: "Finished Goods QC" },
              ].map(({ type, label }) => {
                const s = byType(type);
                return (
                  <div key={type} className="rounded-xl border border-gray-200 bg-white p-4 shadow-sm">
                    <p className="text-sm font-semibold text-gray-700 mb-2">{label}</p>
                    <p className="text-3xl font-bold text-gray-900">{s.total}</p>
                    <div className="mt-2"><PassBar pass={s.passed} total={s.total} /></div>
                    <p className="text-xs text-gray-400 mt-1">{s.passed} passed of {s.total}</p>
                  </div>
                );
              })}
            </div>
          </div>
        )
      )}

      {/* ── Rejection Summary ── */}
      {tab === "rejections" && (
        loadingRej ? <Spinner /> :
        rejections.length === 0 ? (
          <div className="rounded-xl border border-dashed border-gray-300 p-12 text-center text-gray-500">
            No rejection data yet.
          </div>
        ) : (
          <Table
            keyField={(r) => `${r.material_name}-${r.supplier_name}`}
            data={rejections}
            emptyMessage="No rejections."
            columns={[
              {
                header: "Item",
                accessor: (r) => <span className="font-medium">{r.material_name || r.product_name || "—"}</span>,
              },
              { header: "Supplier", accessor: (r) => r.supplier_name ?? "—" },
              { header: "Total Inspections", accessor: "total_inspections" },
              { header: "Rejected", accessor: (r) => <span className={r.total_rejected > 0 ? "text-red-600 font-semibold" : "text-gray-400"}>{r.total_rejected}</span> },
              {
                header: "Rejection Rate",
                accessor: (r) => (
                  <div className="flex items-center gap-2">
                    <div className="w-20 h-2 rounded-full bg-gray-200">
                      <div className={`h-2 rounded-full ${r.rejection_rate >= 20 ? "bg-red-500" : r.rejection_rate >= 10 ? "bg-amber-400" : "bg-green-500"}`}
                        style={{ width: `${Math.min(r.rejection_rate, 100)}%` }} />
                    </div>
                    <span className={`text-xs font-medium ${r.rejection_rate >= 20 ? "text-red-600" : ""}`}>{r.rejection_rate.toFixed(1)}%</span>
                  </div>
                ),
              },
              {
                header: "Last Rejection",
                accessor: (r) => r.last_rejection_date ? new Date(r.last_rejection_date).toLocaleDateString() : "—",
              },
            ]}
          />
        )
      )}

      {/* ── Type-specific inspection list ── */}
      {(tab === "incoming" || tab === "in-process" || tab === "finished-goods") && (
        loadingType ? <Spinner /> : (
          <Table
            keyField="id"
            data={typeInspections}
            emptyMessage={`No ${currentQCType?.replace(/_/g, " ")} inspections.`}
            columns={[
              {
                header: "Inspection No",
                accessor: (i) => (
                  <button className="font-mono text-xs font-medium text-indigo-600 hover:underline" onClick={() => router.push(`/dashboard/quality/${i.id}`)}>
                    {i.inspection_no}
                  </button>
                ),
              },
              {
                header: "Item",
                accessor: (i) => (
                  <span>
                    {i.material_code && <span className="font-mono text-xs text-gray-400 mr-1">{i.material_code}</span>}
                    {i.material_name || i.product_name || "—"}
                  </span>
                ),
              },
              { header: "Supplier / Batch", accessor: (i) => i.supplier_name || i.batch_no || "—" },
              { header: "Lot", accessor: (i) => i.lot_number ? <span className="font-mono text-xs">{i.lot_number}</span> : "—" },
              { header: "Date", accessor: (i) => new Date(i.inspection_date).toLocaleDateString() },
              {
                header: "Tests",
                accessor: (i) => i.test_count > 0
                  ? <PassBar pass={i.pass_count} total={i.test_count} />
                  : <span className="text-gray-400 text-xs">—</span>,
              },
              {
                header: "Status",
                accessor: (i) => (
                  <div className="flex items-center gap-1">
                    <Badge
                      label={i.status.replace(/_/g, " ")}
                      variant={i.status === "PASSED" ? "green" : i.status === "FAILED" ? "red" : i.status === "CONDITIONAL_RELEASE" ? "blue" : "blue"}
                    />
                    {i.quarantine_applied && <Badge label="Q" variant="red" />}
                  </div>
                ),
              },
              {
                header: "",
                accessor: (i) => <Button variant="secondary" onClick={() => router.push(`/dashboard/quality/${i.id}`)}>View</Button>,
              },
            ]}
          />
        )
      )}
    </div>
  );
}
