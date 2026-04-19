"use client";

import { useState } from "react";
import { useParams } from "next/navigation";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { execApi } from "@/lib/productionExecution";

function GenealogyNodeCard({ node, depth = 0 }: { node: any; depth?: number }) {
  const [expanded, setExpanded] = useState(true);
  const hasChildren = node.children && node.children.length > 0;

  return (
    <div style={{ marginLeft: depth * 32 }}>
      <div className={`bg-white rounded-xl border shadow-sm p-4 mb-2 ${
        node.is_rework ? "border-orange-200" :
        node.is_split ? "border-blue-200" :
        depth === 0 ? "border-indigo-300" :
        "border-gray-100"
      }`}>
        <div className="flex items-start justify-between gap-4">
          <div className="flex items-start gap-3">
            {hasChildren && (
              <button onClick={() => setExpanded(!expanded)} className="text-gray-400 hover:text-gray-600 mt-0.5">
                {expanded ? "▼" : "▶"}
              </button>
            )}
            <div>
              <div className="flex items-center gap-2 mb-1">
                <span className="font-mono text-sm font-semibold text-gray-800">{node.order_no}</span>
                <span className={`text-xs px-1.5 py-0.5 rounded ${
                  node.status === "COMPLETED" ? "bg-green-100 text-green-700" :
                  node.status === "IN_PROGRESS" ? "bg-yellow-100 text-yellow-700" :
                  node.status === "CANCELLED" ? "bg-red-100 text-red-700" :
                  "bg-gray-100 text-gray-600"
                }`}>{node.status}</span>
                {node.is_rework && <span className="text-xs bg-orange-100 text-orange-700 px-1.5 rounded">REWORK</span>}
                {node.is_split && <span className="text-xs bg-blue-100 text-blue-700 px-1.5 rounded">SPLIT</span>}
              </div>
              {node.product_name && <p className="text-sm text-gray-600">{node.product_name}</p>}
              {node.batch_no && <p className="text-xs font-mono text-gray-400">Batch: {node.batch_no}</p>}
              <div className="flex items-center gap-4 mt-1 text-xs text-gray-400">
                <span>Planned: {Number(node.planned_qty).toLocaleString()}</span>
                <span>Done: {Number(node.completed_qty).toLocaleString()}</span>
              </div>
            </div>
          </div>
          <a href={`/dashboard/production-execution/${node.order_id}`} className="text-xs text-indigo-600 hover:underline shrink-0">View →</a>
        </div>

        {/* Input lots */}
        {node.input_lots && node.input_lots.length > 0 && (
          <div className="mt-3 border-t border-gray-50 pt-3">
            <p className="text-xs font-medium text-gray-400 mb-1">Input Lots</p>
            <div className="flex flex-wrap gap-2">
              {node.input_lots.map((lot: any, i: number) => (
                <span key={i} className="text-xs bg-amber-50 text-amber-700 px-2 py-0.5 rounded border border-amber-200">
                  📦 {lot.lot} {lot.item && `(${lot.item})`} {lot.qty > 0 && `— ${lot.qty.toFixed(2)} ${lot.uom || ""}`}
                </span>
              ))}
            </div>
          </div>
        )}

        {/* Output lots */}
        {node.output_lots && node.output_lots.length > 0 && (
          <div className="mt-2">
            <p className="text-xs font-medium text-gray-400 mb-1">Output Lots</p>
            <div className="flex flex-wrap gap-2">
              {node.output_lots.map((lot: any, i: number) => (
                <span key={i} className="text-xs bg-green-50 text-green-700 px-2 py-0.5 rounded border border-green-200">
                  ✓ {lot.lot} {lot.item && `(${lot.item})`}
                </span>
              ))}
            </div>
          </div>
        )}
      </div>

      {expanded && hasChildren && (
        <div className="ml-4 border-l-2 border-gray-200 pl-4">
          {node.children.map((child: any, i: number) => (
            <GenealogyNodeCard key={i} node={child} depth={0} />
          ))}
        </div>
      )}
    </div>
  );
}

export default function GenealogyPage() {
  const { id } = useParams<{ id: string }>();
  const qc = useQueryClient();
  const [showAddLink, setShowAddLink] = useState(false);
  const [linkForm, setLinkForm] = useState({
    input_lot_no: "", input_item_name: "", input_qty: "", input_uom: "KG", input_supplier: "",
    output_lot_no: "", output_item_name: "", output_qty: "", output_uom: "KG",
    link_type: "INPUT_OUTPUT",
  });

  const { data, isLoading } = useQuery({
    queryKey: ["exec-genealogy", id],
    queryFn: () => execApi.genealogy(id),
  });

  const addLink = useMutation({
    mutationFn: () => execApi.addGenealogyLink(id, {
      ...linkForm,
      input_qty: linkForm.input_qty ? Number(linkForm.input_qty) : undefined,
      output_qty: linkForm.output_qty ? Number(linkForm.output_qty) : undefined,
    } as any),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["exec-genealogy", id] });
      setShowAddLink(false);
      setLinkForm({ input_lot_no: "", input_item_name: "", input_qty: "", input_uom: "KG", input_supplier: "", output_lot_no: "", output_item_name: "", output_qty: "", output_uom: "KG", link_type: "INPUT_OUTPUT" });
    },
  });

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <a href={`/dashboard/production-execution/${id}`} className="text-sm text-gray-400 hover:text-gray-600">← Order Detail</a>
          <h1 className="text-xl font-bold text-gray-900">Batch Genealogy Tree</h1>
        </div>
        <button onClick={() => setShowAddLink(true)} className="px-3 py-1.5 text-xs bg-indigo-600 text-white rounded-lg hover:bg-indigo-700">
          + Add Traceability Link
        </button>
      </div>

      {isLoading && <div className="text-center text-gray-400 py-8">Building genealogy tree…</div>}

      {data && (
        <>
          {/* Summary */}
          <div className="flex flex-wrap gap-4 text-sm">
            <div className="bg-white rounded-xl border border-gray-100 shadow-sm px-4 py-3">
              <p className="text-xs text-gray-400">Tree Depth</p>
              <p className="text-xl font-bold text-gray-800">{data.depth} level{data.depth !== 1 ? "s" : ""}</p>
            </div>
            {data.all_input_lots?.length > 0 && (
              <div className="bg-amber-50 rounded-xl border border-amber-200 px-4 py-3 flex-1">
                <p className="text-xs text-amber-600 font-medium mb-1">Input Lots (Forward Traceability)</p>
                <div className="flex flex-wrap gap-1">
                  {data.all_input_lots.map((lot: string) => (
                    <span key={lot} className="text-xs bg-amber-100 text-amber-800 px-2 py-0.5 rounded">{lot}</span>
                  ))}
                </div>
              </div>
            )}
            {data.all_output_lots?.length > 0 && (
              <div className="bg-green-50 rounded-xl border border-green-200 px-4 py-3 flex-1">
                <p className="text-xs text-green-600 font-medium mb-1">Output Lots (Backward Traceability)</p>
                <div className="flex flex-wrap gap-1">
                  {data.all_output_lots.map((lot: string) => (
                    <span key={lot} className="text-xs bg-green-100 text-green-800 px-2 py-0.5 rounded">{lot}</span>
                  ))}
                </div>
              </div>
            )}
          </div>

          {/* Tree */}
          <div>
            <GenealogyNodeCard node={data.root} />
          </div>
        </>
      )}

      {/* Add Link Modal */}
      {showAddLink && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
          <div className="bg-white rounded-2xl shadow-xl w-full max-w-lg p-6 overflow-y-auto max-h-[90vh]">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-semibold">Add Traceability Link</h2>
              <button onClick={() => setShowAddLink(false)} className="text-gray-400 hover:text-gray-600 text-xl">×</button>
            </div>
            <div className="space-y-4">
              <div>
                <p className="text-xs font-medium text-amber-700 mb-2">Input (Raw Material Lot)</p>
                <div className="space-y-2">
                  <div className="grid grid-cols-2 gap-2">
                    <input className="border border-gray-200 rounded-lg px-3 py-2 text-sm" placeholder="Lot Number" value={linkForm.input_lot_no} onChange={(e) => setLinkForm({ ...linkForm, input_lot_no: e.target.value })} />
                    <input className="border border-gray-200 rounded-lg px-3 py-2 text-sm" placeholder="Item Name" value={linkForm.input_item_name} onChange={(e) => setLinkForm({ ...linkForm, input_item_name: e.target.value })} />
                  </div>
                  <div className="grid grid-cols-3 gap-2">
                    <input type="number" className="border border-gray-200 rounded-lg px-3 py-2 text-sm" placeholder="Qty" value={linkForm.input_qty} onChange={(e) => setLinkForm({ ...linkForm, input_qty: e.target.value })} />
                    <input className="border border-gray-200 rounded-lg px-3 py-2 text-sm" placeholder="UOM" value={linkForm.input_uom} onChange={(e) => setLinkForm({ ...linkForm, input_uom: e.target.value })} />
                    <input className="border border-gray-200 rounded-lg px-3 py-2 text-sm" placeholder="Supplier" value={linkForm.input_supplier} onChange={(e) => setLinkForm({ ...linkForm, input_supplier: e.target.value })} />
                  </div>
                </div>
              </div>
              <div>
                <p className="text-xs font-medium text-green-700 mb-2">Output (Finished/Intermediate Lot)</p>
                <div className="space-y-2">
                  <div className="grid grid-cols-2 gap-2">
                    <input className="border border-gray-200 rounded-lg px-3 py-2 text-sm" placeholder="Lot Number" value={linkForm.output_lot_no} onChange={(e) => setLinkForm({ ...linkForm, output_lot_no: e.target.value })} />
                    <input className="border border-gray-200 rounded-lg px-3 py-2 text-sm" placeholder="Item Name" value={linkForm.output_item_name} onChange={(e) => setLinkForm({ ...linkForm, output_item_name: e.target.value })} />
                  </div>
                  <div className="grid grid-cols-2 gap-2">
                    <input type="number" className="border border-gray-200 rounded-lg px-3 py-2 text-sm" placeholder="Qty" value={linkForm.output_qty} onChange={(e) => setLinkForm({ ...linkForm, output_qty: e.target.value })} />
                    <input className="border border-gray-200 rounded-lg px-3 py-2 text-sm" placeholder="UOM" value={linkForm.output_uom} onChange={(e) => setLinkForm({ ...linkForm, output_uom: e.target.value })} />
                  </div>
                </div>
              </div>
              <div>
                <label className="text-xs text-gray-500 mb-1 block">Link Type</label>
                <select className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm" value={linkForm.link_type} onChange={(e) => setLinkForm({ ...linkForm, link_type: e.target.value })}>
                  <option value="INPUT_OUTPUT">Input → Output</option>
                  <option value="REWORK">Rework</option>
                  <option value="SPLIT">Split</option>
                  <option value="MERGE">Merge</option>
                </select>
              </div>
            </div>
            <div className="flex gap-3 mt-4">
              <button onClick={() => addLink.mutate()} disabled={addLink.isPending} className="flex-1 bg-indigo-600 text-white py-2 rounded-lg text-sm font-medium hover:bg-indigo-700 disabled:opacity-40">
                {addLink.isPending ? "Adding…" : "Add Link"}
              </button>
              <button onClick={() => setShowAddLink(false)} className="px-4 py-2 border rounded-lg text-sm text-gray-600">Cancel</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
