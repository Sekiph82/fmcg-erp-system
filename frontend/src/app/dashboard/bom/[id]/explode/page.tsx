"use client";

import { useState } from "react";
import { useParams } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { bomApi, ExplosionResult, ExplosionNode } from "@/lib/bom";

function TreeNode({ node, depth = 0 }: { node: ExplosionNode; depth?: number }) {
  const [expanded, setExpanded] = useState(true);
  const hasChildren = node.children && node.children.length > 0;

  return (
    <div style={{ marginLeft: depth * 20 }} className="py-0.5">
      <div className={`flex items-center gap-2 px-2 py-1 rounded hover:bg-gray-50 text-sm ${depth === 0 ? "font-semibold" : ""}`}>
        {hasChildren ? (
          <button onClick={() => setExpanded(!expanded)} className="w-4 h-4 text-xs text-gray-400 hover:text-gray-600">
            {expanded ? "▼" : "▶"}
          </button>
        ) : <span className="w-4" />}
        <span className={`text-xs px-1 rounded ${
          node.component_type === "RAW" ? "bg-gray-100 text-gray-600" :
          node.component_type === "PACKAGING" ? "bg-teal-100 text-teal-700" :
          node.component_type === "INTERMEDIATE" ? "bg-purple-100 text-purple-700" :
          "bg-blue-100 text-blue-700"
        }`}>L{node.level}</span>
        <span className="font-medium text-gray-800">{node.item_name}</span>
        {node.item_code && <span className="text-xs text-gray-400 font-mono">[{node.item_code}]</span>}
        <span className="ml-auto text-xs text-gray-500 font-mono">
          {node.required_qty.toFixed(4)} → {node.adjusted_qty.toFixed(4)} {node.required_uom}
        </span>
        {node.allergen_flag && <span className="text-xs bg-red-100 text-red-700 px-1 rounded">Allergen</span>}
        {node.critical_component && <span className="text-xs bg-orange-100 text-orange-700 px-1 rounded">Critical</span>}
        {node.wastage_pct > 0 && <span className="text-xs text-orange-500">W:{node.wastage_pct}%</span>}
      </div>
      {expanded && hasChildren && node.children.map((child) => (
        <TreeNode key={child.line_id} node={child} depth={depth + 1} />
      ))}
    </div>
  );
}

export default function ExplodePage() {
  const { id } = useParams<{ id: string }>();
  const [targetQty, setTargetQty] = useState("");
  const [submitted, setSubmitted] = useState<number | undefined>(undefined);
  const [view, setView] = useState<"tree" | "flat">("tree");

  const { data, isLoading, refetch } = useQuery<ExplosionResult>({
    queryKey: ["bom-explode", id, submitted],
    queryFn: () => bomApi.explode(id, submitted),
    enabled: true,
  });

  return (
    <div className="p-6 space-y-5">
      <div className="flex items-center gap-3">
        <a href={`/dashboard/bom/${id}`} className="text-sm text-gray-400 hover:text-gray-600">← BOM Detail</a>
        <h1 className="text-xl font-bold text-gray-900">Multi-Level Explosion</h1>
      </div>

      <div className="flex items-center gap-3 flex-wrap">
        <input
          type="number"
          className="border border-gray-200 rounded-lg px-3 py-1.5 text-sm w-48"
          placeholder="Target qty (optional)"
          value={targetQty}
          onChange={(e) => setTargetQty(e.target.value)}
        />
        <button
          onClick={() => { setSubmitted(targetQty ? Number(targetQty) : undefined); refetch(); }}
          className="px-4 py-1.5 text-sm bg-indigo-600 text-white rounded-lg hover:bg-indigo-700"
        >
          Explode
        </button>
        <div className="flex rounded-lg border border-gray-200 overflow-hidden">
          <button onClick={() => setView("tree")} className={`px-3 py-1.5 text-xs ${view === "tree" ? "bg-indigo-600 text-white" : "text-gray-500 hover:bg-gray-50"}`}>Tree</button>
          <button onClick={() => setView("flat")} className={`px-3 py-1.5 text-xs ${view === "flat" ? "bg-indigo-600 text-white" : "text-gray-500 hover:bg-gray-50"}`}>Flat</button>
        </div>
      </div>

      {isLoading && <div className="text-center text-gray-400 py-8">Exploding BOM…</div>}

      {data && (
        <>
          <div className="flex items-center gap-4 text-sm text-gray-500">
            <span><strong className="text-gray-800">{data.bom_name}</strong></span>
            <span>Target: {data.target_qty.toLocaleString()} {data.target_uom}</span>
            <span>{data.total_levels} levels</span>
          </div>

          {view === "tree" && (
            <div className="bg-white rounded-xl border border-gray-100 shadow-sm p-4">
              {data.nodes.map((node) => <TreeNode key={node.line_id} node={node} />)}
            </div>
          )}

          {view === "flat" && (
            <div className="bg-white rounded-xl border border-gray-100 shadow-sm overflow-hidden">
              <table className="w-full text-sm">
                <thead className="bg-gray-50">
                  <tr>
                    {["Item", "Code", "Type", "Required", "Adjusted", "UOM", "Flags"].map((h) => (
                      <th key={h} className="px-4 py-3 text-left font-medium text-gray-400 text-xs">{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-50">
                  {data.flat_requirements.map((req, i) => (
                    <tr key={i} className="hover:bg-gray-50">
                      <td className="px-4 py-2 font-medium">{req.item_name}</td>
                      <td className="px-4 py-2 font-mono text-xs text-gray-400">{req.item_code || "—"}</td>
                      <td className="px-4 py-2">
                        <span className="text-xs bg-gray-100 text-gray-600 px-1.5 py-0.5 rounded">{req.component_type}</span>
                      </td>
                      <td className="px-4 py-2 text-right font-mono text-xs">{req.total_qty.toFixed(4)}</td>
                      <td className="px-4 py-2 text-right font-mono text-xs font-medium">{req.total_adjusted_qty.toFixed(4)}</td>
                      <td className="px-4 py-2 text-xs">{req.required_uom}</td>
                      <td className="px-4 py-2">
                        <div className="flex gap-1">
                          {req.allergen_flag && <span className="text-xs bg-red-100 text-red-700 px-1 rounded">A</span>}
                          {req.critical_component && <span className="text-xs bg-orange-100 text-orange-700 px-1 rounded">!</span>}
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </>
      )}
    </div>
  );
}
