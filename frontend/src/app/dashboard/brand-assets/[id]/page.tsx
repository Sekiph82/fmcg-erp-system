"use client";
import { useCallback, useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";

interface Stage { id: string; stage_name: string; stage_order: number; status: string; approved_by: string | null; approved_at: string | null; notes: string | null; }
interface Asset {
  id: string; asset_ref: string; name: string; asset_type: string; brand: string | null;
  product_name: string | null; product_sku: string | null; version: number;
  bom_version: string | null; bom_change_flag: boolean; file_url: string | null;
  file_format: string | null; status: string;
  compliance_checklist: Record<string, boolean> | null;
  approval_stages: Stage[]; notes: string | null; created_at: string;
}

const STAGE_COLOR: Record<string, string> = {
  PENDING: "bg-gray-100 text-gray-500",
  APPROVED: "bg-green-100 text-green-700",
  REJECTED: "bg-red-100 text-red-600",
  SKIPPED: "bg-gray-50 text-gray-400",
};

export default function BrandAssetDetailPage() {
  const { id } = useParams() as { id: string };
  const [asset, setAsset] = useState<Asset | null>(null);
  const [loading, setLoading] = useState(true);
  const [approver, setApprover] = useState("");
  const [approving, setApproving] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(() => {
    setLoading(true);
    fetch(`/api/v1/brand-assets/${id}`).then((r) => r.json()).then(setAsset).finally(() => setLoading(false));
  }, [id]);
  useEffect(() => { if (id) load(); }, [id, load]);

  const approveStage = async (stageId: string, action: "approve" | "reject") => {
    if (!approver.trim()) { setError("Enter approver name first."); return; }
    setApproving(stageId);
    try {
      await fetch(`/api/v1/brand-assets/${id}/stages/${stageId}/${action}`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ approved_by: approver }),
      });
      load();
    } catch (e) { setError(String(e)); }
    setApproving(null);
  };

  const toggleCompliance = async (key: string, val: boolean) => {
    await fetch(`/api/v1/brand-assets/${id}/compliance`, {
      method: "PATCH", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ key, value: val }),
    });
    load();
  };

  const flagBomChange = async () => {
    await fetch(`/api/v1/brand-assets/${id}/flag-bom-change`, { method: "POST" });
    load();
  };

  if (loading) return <div className="p-6 text-gray-400 text-sm">Loading…</div>;
  if (!asset) return <div className="p-6 text-red-500 text-sm">Asset not found.</div>;

  const allApproved = asset.approval_stages.length > 0 && asset.approval_stages.every((s) => s.status === "APPROVED");
  const compliancePct = asset.compliance_checklist
    ? Math.round(Object.values(asset.compliance_checklist).filter(Boolean).length / Object.values(asset.compliance_checklist).length * 100)
    : 0;

  return (
    <div className="p-6 space-y-6 max-w-5xl mx-auto">
      <div className="flex items-center gap-3">
        <Link href="/dashboard/brand-assets" className="text-sm text-blue-600 hover:text-blue-800">← Brand Assets</Link>
        <span className="text-gray-300">/</span>
        <span className="text-sm text-gray-500">{asset.asset_ref}</span>
      </div>

      {error && <div className="bg-red-50 border border-red-200 rounded p-3 text-sm text-red-700">{error}</div>}

      {/* Header */}
      <div className="bg-white border rounded-xl p-5 shadow-sm space-y-3">
        <div className="flex items-start justify-between gap-4 flex-wrap">
          <div>
            <h1 className="text-xl font-bold text-gray-900">{asset.name}</h1>
            <p className="text-sm text-gray-500 mt-0.5">
              {asset.asset_type.replace(/_/g, " ")}
              {asset.brand && ` · ${asset.brand}`}
              {asset.product_sku && ` · ${asset.product_sku}`}
              {` · v${asset.version}`}
            </p>
          </div>
          <div className="flex items-center gap-3 flex-wrap">
            {asset.bom_change_flag && (
              <span className="text-xs bg-red-100 text-red-700 border border-red-200 rounded-full px-3 py-1 font-medium">BOM Changed — Review Required</span>
            )}
            <span className={`text-sm font-semibold rounded-full px-3 py-1 ${asset.status === "PRINT_READY" ? "bg-emerald-100 text-emerald-700" : asset.status === "APPROVED" ? "bg-green-100 text-green-700" : "bg-gray-100 text-gray-600"}`}>
              {asset.status.replace(/_/g, " ")}
            </span>
          </div>
        </div>
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-4 text-sm">
          {asset.bom_version && <div><p className="text-xs text-gray-400">BOM Version</p><p className="font-medium">{asset.bom_version}</p></div>}
          {asset.file_format && <div><p className="text-xs text-gray-400">Format</p><p className="font-medium">{asset.file_format}</p></div>}
          <div><p className="text-xs text-gray-400">Label Compliance</p><p className={`font-bold ${compliancePct === 100 ? "text-green-600" : "text-amber-600"}`}>{compliancePct}%</p></div>
        </div>
        <div className="flex gap-3 flex-wrap">
          {asset.file_url && (
            <a href={asset.file_url} target="_blank" rel="noopener noreferrer"
              className="text-xs border border-blue-300 bg-blue-50 text-blue-700 rounded px-3 py-1.5 hover:bg-blue-100">
              Open File ↗
            </a>
          )}
          {!asset.bom_change_flag && (
            <button onClick={flagBomChange}
              className="text-xs border border-orange-300 bg-orange-50 text-orange-700 rounded px-3 py-1.5 hover:bg-orange-100">
              Flag BOM Change
            </button>
          )}
          <Link href={`/dashboard/brand-assets`}
            className="text-xs border border-gray-300 text-gray-600 rounded px-3 py-1.5 hover:bg-gray-50">
            + New Version
          </Link>
        </div>
      </div>

      {/* Approver input */}
      <div className="flex items-center gap-3">
        <label className="text-xs text-gray-500">Your Name (for approvals):</label>
        <input type="text" value={approver} onChange={(e) => setApprover(e.target.value)} placeholder="e.g. QA Manager"
          className="border border-gray-300 rounded px-3 py-1 text-sm focus:outline-none focus:ring-1 focus:ring-blue-500 w-48" />
      </div>

      {/* Approval pipeline */}
      <div className="bg-white border rounded-lg shadow-sm overflow-hidden">
        <div className="px-4 py-3 border-b bg-gray-50 flex items-center justify-between">
          <h2 className="text-sm font-semibold text-gray-700">Approval Workflow</h2>
          {allApproved && <span className="text-xs text-emerald-600 bg-emerald-100 rounded-full px-3 py-1 font-medium">All Approved — Print Ready</span>}
        </div>
        <div className="divide-y">
          {asset.approval_stages.map((s) => (
            <div key={s.id} className="px-4 py-3 flex items-center gap-4">
              <span className="text-sm font-bold text-gray-400 w-5">{s.stage_order}</span>
              <div className="flex-1">
                <p className="text-sm font-medium text-gray-900">{s.stage_name}</p>
                {s.approved_by && <p className="text-xs text-gray-400">By {s.approved_by} · {s.approved_at?.slice(0, 10)}</p>}
                {s.notes && <p className="text-xs text-gray-400 italic">{s.notes}</p>}
              </div>
              <span className={`text-xs rounded-full px-2 py-0.5 font-medium ${STAGE_COLOR[s.status] ?? "bg-gray-100 text-gray-500"}`}>{s.status}</span>
              {s.status === "PENDING" && (
                <div className="flex gap-2">
                  <button onClick={() => approveStage(s.id, "approve")} disabled={approving === s.id || !approver.trim()}
                    className="text-xs bg-green-600 hover:bg-green-700 text-white px-3 py-1 rounded disabled:opacity-50">
                    {approving === s.id ? "…" : "Approve"}
                  </button>
                  <button onClick={() => approveStage(s.id, "reject")} disabled={approving === s.id || !approver.trim()}
                    className="text-xs border border-red-300 text-red-600 px-3 py-1 rounded hover:bg-red-50 disabled:opacity-50">
                    Reject
                  </button>
                </div>
              )}
            </div>
          ))}
        </div>
      </div>

      {/* Compliance checklist */}
      {asset.compliance_checklist && (
        <div className="bg-white border rounded-lg shadow-sm overflow-hidden">
          <div className="px-4 py-3 border-b bg-gray-50">
            <h2 className="text-sm font-semibold text-gray-700">
              Label Compliance Checklist
              <span className={`ml-2 text-xs font-normal ${compliancePct === 100 ? "text-green-600" : "text-amber-600"}`}>
                {compliancePct}% complete
              </span>
            </h2>
          </div>
          <div className="px-4 py-4 grid grid-cols-1 gap-2 sm:grid-cols-2">
            {Object.entries(asset.compliance_checklist).map(([key, val]) => (
              <label key={key} className="flex items-center gap-2 cursor-pointer">
                <input type="checkbox" checked={val} onChange={(e) => toggleCompliance(key, e.target.checked)} className="h-4 w-4" />
                <span className={`text-sm capitalize ${val ? "text-gray-700" : "text-gray-400"}`}>
                  {key.replace(/_/g, " ")}
                </span>
              </label>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
