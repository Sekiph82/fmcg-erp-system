"use client";

import dynamic from "next/dynamic";
import { ModuleWorkspace } from "@/components/workspace";
import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  bomApi, BOMDashboard, BOMSummary, BOMType, BOMLifecycle,
  LIFECYCLE_COLOR, BOM_TYPE_COLOR, fmtKES,
} from "@/lib/bom";
import { PermissionGuard, RequirePermission } from "@/components/PermissionGuard";

const BOM_TYPES: BOMType[] = ["FORMULA", "INTERMEDIATE", "PACKAGING", "MULTILEVEL", "PHANTOM", "REWORK", "COPRODUCT"];

function BOMListTab() {
  const qc = useQueryClient();
  const [showCreate, setShowCreate] = useState(false);
  const [filterType, setFilterType] = useState<string>("");
  const [filterLifecycle, setFilterLifecycle] = useState<string>("");
  const [form, setForm] = useState({ bom_name: "", bom_type: "FORMULA" as BOMType, base_qty: "1000", base_uom: "KG", version_no: "1.0" });

  const { data: dashboard } = useQuery<BOMDashboard>({
    queryKey: ["bom-dashboard"],
    queryFn: () => bomApi.dashboard(),
  });

  const { data: boms = [], isLoading } = useQuery<BOMSummary[]>({
    queryKey: ["boms", filterType, filterLifecycle],
    queryFn: () => bomApi.list({ bom_type: filterType || undefined, lifecycle: filterLifecycle || undefined }),
  });

  const create = useMutation({
    mutationFn: () => bomApi.create({ ...form, base_qty: Number(form.base_qty) } as any),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["boms"] });
      qc.invalidateQueries({ queryKey: ["bom-dashboard"] });
      setShowCreate(false);
      setForm({ bom_name: "", bom_type: "FORMULA", base_qty: "1000", base_uom: "KG", version_no: "1.0" });
    },
  });

  return (
    <RequirePermission permission="bom.view">
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">BOM Master</h1>
          <p className="text-sm text-gray-500 mt-0.5">Formula · Packaging · Multi-Level · Co-Product · Rework BOMs</p>
        </div>
        <PermissionGuard permission="bom.create">
          <button onClick={() => setShowCreate(true)} className="px-4 py-2 bg-indigo-600 text-white text-sm font-medium rounded-lg hover:bg-indigo-700">
            + New BOM
          </button>
        </PermissionGuard>
      </div>

      {/* KPIs */}
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
        {[
          { label: "Total BOMs",      value: dashboard?.total_boms ?? 0 },
          { label: "Released",        value: dashboard?.released_boms ?? 0,  color: "text-green-600" },
          { label: "Drafts",          value: dashboard?.draft_boms ?? 0,      color: "text-gray-500" },
          { label: "Pending Review",  value: dashboard?.pending_review ?? 0,  color: "text-yellow-600" },
          { label: "With Allergens",  value: dashboard?.boms_with_allergens ?? 0, color: "text-red-600" },
          { label: "AI Recs Pending", value: dashboard?.pending_ai_recs ?? 0, color: "text-purple-600" },
        ].map((k) => (
          <div key={k.label} className="bg-white rounded-xl border border-gray-100 shadow-sm p-4">
            <p className="text-xs text-gray-400 font-medium">{k.label}</p>
            <p className={`text-2xl font-bold mt-1 ${k.color || "text-gray-900"}`}>{k.value}</p>
          </div>
        ))}
      </div>

      {/* By-type breakdown */}
      {dashboard?.by_type && Object.keys(dashboard.by_type).length > 0 && (
        <div className="bg-white rounded-xl border border-gray-100 shadow-sm p-4 flex flex-wrap gap-3">
          {Object.entries(dashboard.by_type).map(([type, count]) => (
            <div key={type} className={`px-3 py-1.5 rounded-lg text-xs font-medium ${BOM_TYPE_COLOR[type as BOMType] || "bg-gray-100 text-gray-600"}`}>
              {type}: {count}
            </div>
          ))}
        </div>
      )}

      {/* Filters */}
      <div className="flex flex-wrap items-center gap-3">
        <select
          className="border border-gray-200 rounded-lg px-3 py-1.5 text-sm"
          value={filterType}
          onChange={(e) => setFilterType(e.target.value)}
        >
          <option value="">All Types</option>
          {BOM_TYPES.map((t) => <option key={t} value={t}>{t}</option>)}
        </select>
        <select
          className="border border-gray-200 rounded-lg px-3 py-1.5 text-sm"
          value={filterLifecycle}
          onChange={(e) => setFilterLifecycle(e.target.value)}
        >
          <option value="">All Statuses</option>
          {["DRAFT", "UNDER_REVIEW", "APPROVED", "RELEASED", "SUPERSEDED", "ARCHIVED"].map((s) => (
            <option key={s} value={s}>{s}</option>
          ))}
        </select>
      </div>

      {/* BOM List */}
      {isLoading ? (
        <div className="text-center text-gray-400 py-8">Loading…</div>
      ) : boms.length === 0 ? (
        <div className="bg-white rounded-xl border border-gray-100 shadow-sm p-8 text-center text-sm text-gray-400">
          No BOMs found. Create your first BOM to get started.
        </div>
      ) : (
        <div className="bg-white rounded-xl border border-gray-100 shadow-sm overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-gray-50">
              <tr>
                {["Code", "Name", "Type", "Product", "Base Qty", "Version", "Status", "Std Cost", "Actions"].map((h) => (
                  <th key={h} className="px-4 py-3 text-left font-medium text-gray-400 text-xs">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-50">
              {boms.map((bom) => (
                <tr key={bom.id} className="hover:bg-gray-50">
                  <td className="px-4 py-2 font-mono text-xs text-gray-500">{bom.bom_code}</td>
                  <td className="px-4 py-2">
                    <a href={`/dashboard/bom/${bom.id}`} className="font-medium text-indigo-600 hover:underline">
                      {bom.bom_name}
                    </a>
                    {bom.is_default && (
                      <span className="ml-1 text-xs bg-green-100 text-green-700 px-1 rounded">default</span>
                    )}
                  </td>
                  <td className="px-4 py-2">
                    <span className={`text-xs px-1.5 py-0.5 rounded ${BOM_TYPE_COLOR[bom.bom_type]}`}>{bom.bom_type}</span>
                  </td>
                  <td className="px-4 py-2 text-xs text-gray-500">{bom.product_name || "—"}</td>
                  <td className="px-4 py-2 text-xs text-right font-medium">{Number(bom.base_qty).toLocaleString()} {bom.base_uom}</td>
                  <td className="px-4 py-2 text-xs text-gray-500">v{bom.version_no}</td>
                  <td className="px-4 py-2">
                    <span className={`text-xs px-1.5 py-0.5 rounded ${LIFECYCLE_COLOR[bom.lifecycle]}`}>{bom.lifecycle}</span>
                  </td>
                  <td className="px-4 py-2 text-xs text-right">
                    {bom.standard_batch_cost ? fmtKES(Number(bom.standard_batch_cost)) : "—"}
                  </td>
                  <td className="px-4 py-2">
                    <div className="flex items-center gap-2">
                      <a href={`/dashboard/bom/${bom.id}`} className="text-xs text-blue-600 hover:underline">View</a>
                      <a href={`/dashboard/bom/${bom.id}?tab=formula`} className="text-xs text-gray-500 hover:text-gray-700">Formula</a>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Create Modal */}
      {showCreate && (
        <PermissionGuard permission="bom.create">
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
          <div className="bg-white rounded-2xl shadow-xl w-full max-w-md p-6">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-semibold">New BOM</h2>
              <button onClick={() => setShowCreate(false)} className="text-gray-400 hover:text-gray-600 text-xl">×</button>
            </div>
            <div className="space-y-3">
              <input
                className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm"
                placeholder="BOM Name *"
                value={form.bom_name}
                onChange={(e) => setForm({ ...form, bom_name: e.target.value })}
              />
              <select
                className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm"
                value={form.bom_type}
                onChange={(e) => setForm({ ...form, bom_type: e.target.value as BOMType })}
              >
                {BOM_TYPES.map((t) => <option key={t} value={t}>{t}</option>)}
              </select>
              <div className="grid grid-cols-2 gap-3">
                <input
                  type="number"
                  className="border border-gray-200 rounded-lg px-3 py-2 text-sm"
                  placeholder="Base Qty"
                  value={form.base_qty}
                  onChange={(e) => setForm({ ...form, base_qty: e.target.value })}
                />
                <select
                  className="border border-gray-200 rounded-lg px-3 py-2 text-sm"
                  value={form.base_uom}
                  onChange={(e) => setForm({ ...form, base_uom: e.target.value })}
                >
                  {["KG", "L", "UNIT", "MT", "G", "ML"].map((u) => <option key={u} value={u}>{u}</option>)}
                </select>
              </div>
              <input
                className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm"
                placeholder="Version (e.g. 1.0)"
                value={form.version_no}
                onChange={(e) => setForm({ ...form, version_no: e.target.value })}
              />
            </div>
            <div className="flex gap-3 mt-4">
              <button
                onClick={() => create.mutate()}
                disabled={!form.bom_name || create.isPending}
                className="flex-1 bg-indigo-600 text-white py-2 rounded-lg text-sm font-medium hover:bg-indigo-700 disabled:opacity-40"
              >
                {create.isPending ? "Creating…" : "Create BOM"}
              </button>
              <button onClick={() => setShowCreate(false)} className="px-4 py-2 border rounded-lg text-sm text-gray-600 hover:bg-gray-50">
                Cancel
              </button>
            </div>
          </div>
        </div>
        </PermissionGuard>
      )}
    </div>
    </RequirePermission>
  );
}

const BOMComparePage    = dynamic(() => import("@/app/dashboard/bom/compare/page"),    { ssr: false });
const BOMSubstitutesPage= dynamic(() => import("@/app/dashboard/bom/substitutes/page"),{ ssr: false });
const BOMConversionPage = dynamic(() => import("@/app/dashboard/bom/conversion/page"), { ssr: false });

export default function BOMPage() {
  const tabs = [
    { key: "list",        label: "BOM / Formula", permission: "bom.view", content: <BOMListTab /> },
    { key: "substitutes", label: "Substitutes",   permission: "bom.view", content: <BOMSubstitutesPage /> },
    { key: "compare",     label: "Compare",       permission: "bom.view", content: <BOMComparePage /> },
    { key: "conversion",  label: "Conversion",    permission: "bom.view", content: <BOMConversionPage /> },
  ];
  return (
    <ModuleWorkspace
      title="BOM & Formula"
      description="Bill of materials, formula versions, substitutes, cost explosion"
      permission="bom.view"
      tabs={tabs}
      defaultTab="list"
    />
  );
}
