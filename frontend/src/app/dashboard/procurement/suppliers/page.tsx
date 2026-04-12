"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { procurementApi, SupplierDashboardRow } from "@/lib/procurement";
import { suppliersApi } from "@/lib/suppliers";
import { extractApiError } from "@/lib/inventory";
import { Table } from "@/components/ui/Table";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Modal } from "@/components/ui/Modal";
import { Input } from "@/components/ui/Input";
import { Select } from "@/components/ui/Select";
import { ToastContainer } from "@/components/ui/Toast";
import { useToast } from "@/hooks/useToast";

function ScoreMeter({ value }: { value?: number | null }) {
  if (value == null) return <span className="text-gray-400 text-xs">—</span>;
  const pct = Math.min(Math.max(Number(value), 0), 100);
  const color = pct >= 80 ? "bg-green-500" : pct >= 60 ? "bg-amber-400" : "bg-red-400";
  return (
    <div className="flex items-center gap-2">
      <div className="w-20 h-2 rounded-full bg-gray-200">
        <div className={`h-2 rounded-full ${color}`} style={{ width: `${pct}%` }} />
      </div>
      <span className="text-xs font-medium">{pct.toFixed(1)}</span>
    </div>
  );
}

export default function SupplierEvaluationPage() {
  const qc = useQueryClient();
  const router = useRouter();
  const { toasts, toast, dismiss } = useToast();
  const [evalOpen, setEvalOpen] = useState(false);
  const [selectedSupplier, setSelectedSupplier] = useState<SupplierDashboardRow | null>(null);
  const [evalForm, setEvalForm] = useState({
    evaluation_date: "", on_time_delivery_score: "", quality_score: "",
    price_competitiveness_score: "", responsiveness_score: "", notes: "",
  });

  const { data: dashboard = [], isLoading } = useQuery({
    queryKey: ["supplier-dashboard"],
    queryFn: () => procurementApi.supplierDashboard(),
  });

  const createEval = useMutation({
    mutationFn: () => procurementApi.createEvaluation({
      supplier_id: selectedSupplier!.supplier_id,
      ...evalForm,
      on_time_delivery_score: parseFloat(evalForm.on_time_delivery_score),
      quality_score: parseFloat(evalForm.quality_score),
      price_competitiveness_score: parseFloat(evalForm.price_competitiveness_score),
      responsiveness_score: parseFloat(evalForm.responsiveness_score),
    }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["supplier-dashboard"] });
      setEvalOpen(false);
      toast("success", "Evaluation saved", `${selectedSupplier?.supplier_name} scored.`);
    },
    onError: (e) => toast("error", "Failed", extractApiError(e)),
  });

  const openEval = (row: SupplierDashboardRow) => {
    setSelectedSupplier(row);
    setEvalForm({ evaluation_date: "", on_time_delivery_score: "", quality_score: "", price_competitiveness_score: "", responsiveness_score: "", notes: "" });
    setEvalOpen(true);
  };

  const preferred = dashboard.filter((r) => r.is_preferred);
  const overdue = dashboard.filter((r) => r.overdue_pos > 0);
  const uneval = dashboard.filter((r) => r.last_evaluation_date == null);

  return (
    <div className="space-y-6">
      <ToastContainer toasts={toasts} onDismiss={dismiss} />

      <div>
        <h1 className="text-2xl font-bold text-gray-900">Supplier Evaluation Dashboard</h1>
        <p className="text-sm text-gray-500 mt-1">Performance scoring, compliance, and KPI tracking</p>
      </div>

      {/* Summary cards */}
      <div className="grid grid-cols-4 gap-4">
        <div className="rounded-xl border border-gray-200 bg-white p-4 shadow-sm">
          <p className="text-xs text-gray-500">Active Suppliers</p>
          <p className="text-2xl font-bold">{dashboard.length}</p>
        </div>
        <div className="rounded-xl border border-gray-200 bg-white p-4 shadow-sm">
          <p className="text-xs text-gray-500">Preferred</p>
          <p className="text-2xl font-bold text-green-600">{preferred.length}</p>
        </div>
        <div className="rounded-xl border border-gray-200 bg-white p-4 shadow-sm">
          <p className="text-xs text-gray-500">With Overdue POs</p>
          <p className={`text-2xl font-bold ${overdue.length > 0 ? "text-red-600" : "text-gray-400"}`}>{overdue.length}</p>
        </div>
        <div className="rounded-xl border border-gray-200 bg-white p-4 shadow-sm">
          <p className="text-xs text-gray-500">Never Evaluated</p>
          <p className={`text-2xl font-bold ${uneval.length > 0 ? "text-amber-600" : "text-gray-400"}`}>{uneval.length}</p>
        </div>
      </div>

      {/* Dashboard table */}
      {isLoading ? (
        <div className="flex justify-center py-16"><div className="h-8 w-8 animate-spin rounded-full border-4 border-indigo-600 border-t-transparent" /></div>
      ) : (
        <Table
          keyField="supplier_id"
          data={dashboard}
          emptyMessage="No active suppliers."
          columns={[
            {
              header: "Supplier",
              accessor: (r) => (
                <div>
                  <div className="flex items-center gap-2">
                    <span className="font-medium text-sm">{r.supplier_name}</span>
                    {r.is_preferred && <Badge label="Preferred" variant="green" />}
                  </div>
                  <span className="font-mono text-xs text-gray-400">{r.supplier_code}</span>
                </div>
              ),
            },
            { header: "Lead Time", accessor: (r) => `${r.lead_time_days}d` },
            {
              header: "POs",
              accessor: (r) => (
                <div className="text-sm">
                  <span>{r.total_pos} total</span>
                  {r.open_pos > 0 && <span className="ml-1 text-blue-600">· {r.open_pos} open</span>}
                  {r.overdue_pos > 0 && <span className="ml-1 text-red-600 font-medium">· {r.overdue_pos} overdue</span>}
                </div>
              ),
            },
            {
              header: "Overall Score",
              accessor: (r) => <ScoreMeter value={r.avg_overall} />,
            },
            {
              header: "On-Time Delivery",
              accessor: (r) => <ScoreMeter value={r.avg_on_time_delivery} />,
            },
            {
              header: "Quality",
              accessor: (r) => <ScoreMeter value={r.avg_quality} />,
            },
            {
              header: "Last Evaluated",
              accessor: (r) => r.last_evaluation_date
                ? new Date(r.last_evaluation_date).toLocaleDateString()
                : <span className="text-amber-600 text-xs">Never</span>,
            },
            {
              header: "Compliance",
              accessor: (r) => r.compliance_notes
                ? <span className="text-xs text-gray-600 truncate max-w-[120px] block" title={r.compliance_notes}>{r.compliance_notes}</span>
                : <span className="text-gray-300 text-xs">—</span>,
            },
            {
              header: "",
              accessor: (r) => <Button variant="secondary" onClick={() => openEval(r)}>Evaluate</Button>,
            },
          ]}
        />
      )}

      {/* Evaluation Modal */}
      <Modal open={evalOpen} onClose={() => setEvalOpen(false)} title={`Evaluate: ${selectedSupplier?.supplier_name}`}>
        <form onSubmit={(e) => { e.preventDefault(); createEval.mutate(); }} className="space-y-4">
          <p className="text-xs text-gray-500">Score each dimension 0–100. Overall score is the average of all dimensions.</p>
          <Input label="Evaluation Date *" type="date" value={evalForm.evaluation_date} onChange={(e) => setEvalForm((f) => ({ ...f, evaluation_date: e.target.value }))} required />
          <div className="grid grid-cols-2 gap-4">
            <div>
              <Input label="On-Time Delivery (0-100) *" type="number" min="0" max="100" step="0.1"
                value={evalForm.on_time_delivery_score} onChange={(e) => setEvalForm((f) => ({ ...f, on_time_delivery_score: e.target.value }))} required />
              {selectedSupplier?.avg_on_time_delivery != null && (
                <p className="text-xs text-gray-400 mt-1">Avg: {Number(selectedSupplier.avg_on_time_delivery).toFixed(1)}</p>
              )}
            </div>
            <div>
              <Input label="Quality (0-100) *" type="number" min="0" max="100" step="0.1"
                value={evalForm.quality_score} onChange={(e) => setEvalForm((f) => ({ ...f, quality_score: e.target.value }))} required />
              {selectedSupplier?.avg_quality != null && (
                <p className="text-xs text-gray-400 mt-1">Avg: {Number(selectedSupplier.avg_quality).toFixed(1)}</p>
              )}
            </div>
            <Input label="Price Competitiveness (0-100) *" type="number" min="0" max="100" step="0.1"
              value={evalForm.price_competitiveness_score} onChange={(e) => setEvalForm((f) => ({ ...f, price_competitiveness_score: e.target.value }))} required />
            <Input label="Responsiveness (0-100) *" type="number" min="0" max="100" step="0.1"
              value={evalForm.responsiveness_score} onChange={(e) => setEvalForm((f) => ({ ...f, responsiveness_score: e.target.value }))} required />
          </div>
          <Input label="Notes" value={evalForm.notes} onChange={(e) => setEvalForm((f) => ({ ...f, notes: e.target.value }))} />
          {evalForm.on_time_delivery_score && evalForm.quality_score && evalForm.price_competitiveness_score && evalForm.responsiveness_score && (
            <div className="rounded-lg bg-gray-50 border border-gray-200 p-3 text-sm text-gray-600">
              Overall score preview:{" "}
              <strong>
                {((parseFloat(evalForm.on_time_delivery_score) + parseFloat(evalForm.quality_score) + parseFloat(evalForm.price_competitiveness_score) + parseFloat(evalForm.responsiveness_score)) / 4).toFixed(1)}
              </strong>
            </div>
          )}
          <div className="flex justify-end gap-3 pt-2">
            <Button variant="secondary" type="button" onClick={() => setEvalOpen(false)}>Cancel</Button>
            <Button type="submit" loading={createEval.isPending}
              disabled={!evalForm.evaluation_date || !evalForm.on_time_delivery_score || !evalForm.quality_score || !evalForm.price_competitiveness_score || !evalForm.responsiveness_score}>
              Save Evaluation
            </Button>
          </div>
        </form>
      </Modal>
    </div>
  );
}
