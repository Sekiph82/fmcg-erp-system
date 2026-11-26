"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { procurementApi, SupplierDashboardRow } from "@/lib/procurement";
import { qmsApi, CorrectiveAction, RiskLevel } from "@/lib/qms";
import { suppliersApi } from "@/lib/suppliers";
import { useAuth } from "@/context/AuthContext";
import { extractApiError } from "@/lib/inventory";
import { Table } from "@/components/ui/Table";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Modal } from "@/components/ui/Modal";
import { Input } from "@/components/ui/Input";
import { Select } from "@/components/ui/Select";
import { ToastContainer } from "@/components/ui/Toast";
import { useToast } from "@/hooks/useToast";
import { tx } from "@/lib/i18n/core";

function ScoreMeter({ value, suffix = "" }: { value?: number | null; suffix?: string }) {
  if (value == null) return <span className="text-gray-400 text-xs">—</span>;
  const pct = Math.min(Math.max(Number(value), 0), 100);
  const color = pct >= 80 ? "bg-green-500" : pct >= 60 ? "bg-amber-400" : "bg-red-400";
  return (
    <div className="flex items-center gap-2">
      <div className="w-20 h-2 rounded-full bg-gray-200">
        <div className={`h-2 rounded-full ${color}`} style={{ width: `${pct}%` }} />
      </div>
      <span className="text-xs font-medium">{pct.toFixed(1)}{suffix}</span>
    </div>
  );
}

export default function SupplierEvaluationPage() {
  const qc = useQueryClient();
  const router = useRouter();
  const { toasts, toast, dismiss } = useToast();
  const { hasAnyPermission } = useAuth();
  const [evalOpen, setEvalOpen] = useState(false);
  const [capaOpen, setCapaOpen] = useState(false);
  const [selectedSupplier, setSelectedSupplier] = useState<SupplierDashboardRow | null>(null);
  const [capaForm, setCapaForm] = useState({ title: "", description: "", severity: "MEDIUM" as RiskLevel, supplier_evaluation_id: "" });
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
      toast("success", tx("Evaluation saved"), tx("{supplier_name} scored.", { supplier_name: selectedSupplier?.supplier_name }));
    },
    onError: (e) => toast("error", tx("Failed"), extractApiError(e)),
  });

  const canViewCapa = hasAnyPermission(["quality.view", "quality.view_all"]);
  const canCreateCapa = hasAnyPermission(["quality.create", "quality.create_all"]);
  const supplierCapas = useQuery({
    queryKey: ["supplier-capas", selectedSupplier?.supplier_id],
    queryFn: () => qmsApi.listCAs({ supplier_id: selectedSupplier!.supplier_id }),
    enabled: capaOpen && !!selectedSupplier && canViewCapa,
  });
  const createCapa = useMutation({
    mutationFn: () => {
      if (!selectedSupplier) throw new Error(tx("Select a supplier first."));
      return qmsApi.createCA({
        title: capaForm.title.trim(),
        description: capaForm.description.trim(),
        severity: capaForm.severity,
        supplier_id: selectedSupplier.supplier_id,
        ...(capaForm.supplier_evaluation_id ? { supplier_evaluation_id: capaForm.supplier_evaluation_id } : {}),
      });
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["supplier-capas", selectedSupplier?.supplier_id] });
      qc.invalidateQueries({ queryKey: ["supplier-dashboard"] });
      setCapaForm({ title: "", description: "", severity: "MEDIUM", supplier_evaluation_id: "" });
      toast("success", tx("Corrective action created"), tx("{supplier_name} was linked to the action.", { supplier_name: selectedSupplier?.supplier_name }));
    },
    onError: (e) => toast("error", tx("Failed"), extractApiError(e)),
  });

  const openEval = (row: SupplierDashboardRow) => {
    setSelectedSupplier(row);
    setEvalForm({ evaluation_date: "", on_time_delivery_score: "", quality_score: "", price_competitiveness_score: "", responsiveness_score: "", notes: "" });
    setEvalOpen(true);
  };

  const openCapas = (row: SupplierDashboardRow) => {
    setSelectedSupplier(row);
    setCapaForm({ title: "", description: "", severity: "MEDIUM", supplier_evaluation_id: row.latest_evaluation_id ?? "" });
    setCapaOpen(true);
  };

  const preferred = dashboard.filter((r) => r.is_preferred);
  const overdue = dashboard.filter((r) => r.overdue_pos > 0);
  const uneval = dashboard.filter((r) => r.last_evaluation_date == null);

  return (
    <div className="space-y-6">
      <ToastContainer toasts={toasts} onDismiss={dismiss} />

      <div>
        <h1 className="text-2xl font-bold text-gray-900">{tx("Supplier Evaluation Dashboard")}</h1>
        <p className="text-sm text-gray-500 mt-1">
          {tx("Dimension scorecard: OTIF uses due ordered POs and posted GRNs from the rolling 365-day window; other procurement scores use recorded evaluations. ESG shows the latest active linked assessment and food safety shows the latest linked record per certificate type. No combined weighted rank is applied.")}
        </p>
      </div>

      {/* Summary cards */}
      <div className="grid grid-cols-4 gap-4">
        <div className="rounded-xl border border-gray-200 bg-white p-4 shadow-sm">
          <p className="text-xs text-gray-500">{tx("Active Suppliers")}</p>
          <p className="text-2xl font-bold">{dashboard.length}</p>
        </div>
        <div className="rounded-xl border border-gray-200 bg-white p-4 shadow-sm">
          <p className="text-xs text-gray-500">{tx("Preferred")}</p>
          <p className="text-2xl font-bold text-green-600">{preferred.length}</p>
        </div>
        <div className="rounded-xl border border-gray-200 bg-white p-4 shadow-sm">
          <p className="text-xs text-gray-500">{tx("With Overdue POs")}</p>
          <p className={`text-2xl font-bold ${overdue.length > 0 ? "text-red-600" : "text-gray-400"}`}>{overdue.length}</p>
        </div>
        <div className="rounded-xl border border-gray-200 bg-white p-4 shadow-sm">
          <p className="text-xs text-gray-500">{tx("Never Evaluated")}</p>
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
              header: tx("Supplier"),
              accessor: (r) => (
                <div>
                  <div className="flex items-center gap-2">
                    <span className="font-medium text-sm">{r.supplier_name}</span>
                    {r.is_preferred && <Badge label={tx("Preferred")} variant="green" />}
                  </div>
                  <span className="font-mono text-xs text-gray-400">{r.supplier_code}</span>
                </div>
              ),
            },
            {
              header: tx("Qualification"),
              accessor: (r) => {
                const value = r.qualification_status ?? "LEGACY / UNRECORDED";
                const variant = value === "APPROVED" ? "green" : ["SUSPENDED", "REJECTED"].includes(value) ? "red" : "yellow";
                return (
                  <div className="space-y-1">
                    <Badge label={value} variant={variant} />
                    {r.approved_until && <div className="text-[10px] text-gray-500">{tx("valid to")} {r.approved_until}</div>}
                  </div>
                );
              },
            },
            { header: tx("Lead Time"), accessor: (r) => `${r.lead_time_days}d` },
            {
              header: tx("POs"),
              accessor: (r) => (
                <div className="text-sm">
                  <span>{r.total_pos} {tx("total")}</span>
                  {r.open_pos > 0 && <span className="ml-1 text-blue-600">· {r.open_pos} {tx("open")}</span>}
                  {r.overdue_pos > 0 && <span className="ml-1 text-red-600 font-medium">· {r.overdue_pos} {tx("overdue")}</span>}
                </div>
              ),
            },
            {
              header: tx("Overall Score"),
              accessor: (r) => <ScoreMeter value={r.avg_overall} />,
            },
            {
              header: tx("OTIF (365d)"),
              accessor: (r) => (
                <div>
                  <ScoreMeter value={r.otif_rate} suffix="%" />
                  <span className="text-[11px] text-gray-400">
                    {r.otif_order_count === 0 ? tx("No due orders") : tx("{otif_met_order_count}/{otif_order_count} orders", { otif_met_order_count: r.otif_met_order_count, otif_order_count: r.otif_order_count })}
                  </span>
                </div>
              ),
            },
            {
              header: tx("Delivery Eval"),
              accessor: (r) => <ScoreMeter value={r.avg_on_time_delivery} />,
            },
            {
              header: tx("Quality Eval"),
              accessor: (r) => (
                <div>
                  <ScoreMeter value={r.avg_quality} />
                  <span className="text-[11px] text-gray-400">{r.evaluation_count} {tx("evals")}</span>
                </div>
              ),
            },
            {
              header: tx("Corrective Actions"),
              accessor: (r) => r.supplier_capa_signals_restricted ? (
                <span className="text-xs text-gray-400">{tx("Restricted")}</span>
              ) : (
                <Button variant="secondary" onClick={() => openCapas(r)}>
                  {r.supplier_open_capa_count ?? 0} {tx("open /")} {r.supplier_capa_count ?? 0} {tx("total")}
                </Button>
              ),
            },
            {
              header: tx("Price Eval"),
              accessor: (r) => (
                <div>
                  <ScoreMeter value={r.avg_price_competitiveness} />
                  <span className="text-[11px] text-gray-400">{r.evaluation_count} {tx("evals")}</span>
                </div>
              ),
            },
            {
              header: tx("Responsiveness Eval"),
              accessor: (r) => (
                <div>
                  <ScoreMeter value={r.avg_responsiveness} />
                  <span className="text-[11px] text-gray-400">{r.evaluation_count} {tx("evals")}</span>
                </div>
              ),
            },
            {
              header: "ESG",
              accessor: (r) => r.supplier_signals_restricted ? (
                <span className="text-xs text-gray-400">{tx("Restricted")}</span>
              ) : (
                <div>
                  <ScoreMeter value={r.esg_overall_score} />
                  <span className="text-[11px] text-gray-400">
                    {r.esg_assessment_period_end ? tx("Period end {esg_assessment_period_end}", { esg_assessment_period_end: r.esg_assessment_period_end }) : tx("Not assessed")}
                  </span>
                </div>
              ),
            },
            {
              header: tx("Food Safety"),
              accessor: (r) => r.supplier_signals_restricted ? (
                <span className="text-xs text-gray-400">{tx("Restricted")}</span>
              ) : r.food_safety_approvals.length === 0 ? (
                <span className="text-xs text-gray-400">{tx("Not assessed")}</span>
              ) : (
                <div className="space-y-1">
                  {r.food_safety_approvals.map((approval) => {
                    const isBlocked = approval.is_expired || ["REJECTED", "SUSPENDED"].includes(approval.status);
                    const statusClass = isBlocked
                      ? "text-red-700"
                      : approval.status === "APPROVED" && approval.is_current === true
                        ? "text-green-700"
                        : "text-amber-700";
                    return (
                      <div key={approval.approval_type} className={`text-[11px] ${statusClass}`}>
                        {approval.approval_type}: {approval.status}
                        {approval.is_expired ? tx(" · expired") : ""}
                        {approval.is_current == null ? tx(" · expiry not recorded") : ""}
                        {approval.audit_score != null ? tx(" · audit {audit_score}", { audit_score: Number(approval.audit_score).toFixed(1) }) : ""}
                        {approval.expiry_date ? tx(" · exp {expiry_date}", { expiry_date: approval.expiry_date }) : ""}
                      </div>
                    );
                  })}
                </div>
              ),
            },
            {
              header: tx("Last Evaluated"),
              accessor: (r) => r.last_evaluation_date
                ? new Date(r.last_evaluation_date).toLocaleDateString()
                : <span className="text-amber-600 text-xs">{tx("Never")}</span>,
            },
            {
              header: tx("Compliance"),
              accessor: (r) => r.compliance_notes
                ? <span className="text-xs text-gray-600 truncate max-w-[120px] block" title={r.compliance_notes}>{r.compliance_notes}</span>
                : <span className="text-gray-300 text-xs">—</span>,
            },
            {
              header: "",
              accessor: (r) => (
                <div className="flex gap-2">
                  <Button variant="secondary" onClick={() => openEval(r)}>{tx("Evaluate")}</Button>
                  {(canViewCapa || canCreateCapa) && (
                    <Button variant="secondary" onClick={() => openCapas(r)}>CAPA</Button>
                  )}
                </div>
              ),
            },
          ]}
        />
      )}

      {/* Evaluation Modal */}
      <Modal open={evalOpen} onClose={() => setEvalOpen(false)} title={tx("Evaluate: {supplier_name}", { supplier_name: selectedSupplier?.supplier_name })}>
        <form onSubmit={(e) => { e.preventDefault(); createEval.mutate(); }} className="space-y-4">
          <p className="text-xs text-gray-500">{tx("Score each dimension 0–100. Overall score is the average of all dimensions.")}</p>
          <Input label={tx("Evaluation Date *")} type="date" value={evalForm.evaluation_date} onChange={(e) => setEvalForm((f) => ({ ...f, evaluation_date: e.target.value }))} required />
          <div className="grid grid-cols-2 gap-4">
            <div>
              <Input label={tx("On-Time Delivery (0-100) *")} type="number" min="0" max="100" step="0.1"
                value={evalForm.on_time_delivery_score} onChange={(e) => setEvalForm((f) => ({ ...f, on_time_delivery_score: e.target.value }))} required />
              {selectedSupplier?.avg_on_time_delivery != null && (
                <p className="text-xs text-gray-400 mt-1">{tx("Avg:")} {Number(selectedSupplier.avg_on_time_delivery).toFixed(1)}</p>
              )}
            </div>
            <div>
              <Input label={tx("Quality (0-100) *")} type="number" min="0" max="100" step="0.1"
                value={evalForm.quality_score} onChange={(e) => setEvalForm((f) => ({ ...f, quality_score: e.target.value }))} required />
              {selectedSupplier?.avg_quality != null && (
                <p className="text-xs text-gray-400 mt-1">{tx("Avg:")} {Number(selectedSupplier.avg_quality).toFixed(1)}</p>
              )}
            </div>
            <Input label={tx("Price Competitiveness (0-100) *")} type="number" min="0" max="100" step="0.1"
              value={evalForm.price_competitiveness_score} onChange={(e) => setEvalForm((f) => ({ ...f, price_competitiveness_score: e.target.value }))} required />
            <Input label={tx("Responsiveness (0-100) *")} type="number" min="0" max="100" step="0.1"
              value={evalForm.responsiveness_score} onChange={(e) => setEvalForm((f) => ({ ...f, responsiveness_score: e.target.value }))} required />
          </div>
          <Input label={tx("Notes")} value={evalForm.notes} onChange={(e) => setEvalForm((f) => ({ ...f, notes: e.target.value }))} />
          {evalForm.on_time_delivery_score && evalForm.quality_score && evalForm.price_competitiveness_score && evalForm.responsiveness_score && (
            <div className="rounded-lg bg-gray-50 border border-gray-200 p-3 text-sm text-gray-600">
              {tx("Overall score preview:")}{" "}
              <strong>
                {((parseFloat(evalForm.on_time_delivery_score) + parseFloat(evalForm.quality_score) + parseFloat(evalForm.price_competitiveness_score) + parseFloat(evalForm.responsiveness_score)) / 4).toFixed(1)}
              </strong>
            </div>
          )}
          <div className="flex justify-end gap-3 pt-2">
            <Button variant="secondary" type="button" onClick={() => setEvalOpen(false)}>{tx("Cancel")}</Button>
            <Button type="submit" loading={createEval.isPending}
              disabled={!evalForm.evaluation_date || !evalForm.on_time_delivery_score || !evalForm.quality_score || !evalForm.price_competitiveness_score || !evalForm.responsiveness_score}>
              {tx("Save Evaluation")}
            </Button>
          </div>
        </form>
      </Modal>

      <Modal open={capaOpen} onClose={() => setCapaOpen(false)} title={tx("Corrective actions: {supplier_name}", { supplier_name: selectedSupplier?.supplier_name })}>
        <div className="space-y-5">
          <p className="text-xs text-gray-500">{tx("Actions are linked to this supplier. Linking an evaluation records the exact source; no score or automatic trigger is inferred.")}</p>
          {canViewCapa ? (
            <section className="space-y-2" aria-label={tx("Supplier corrective action history")}>
              <h2 className="text-sm font-semibold">{tx("History")}</h2>
              {supplierCapas.isLoading ? <p className="text-sm text-gray-500">{tx("Loading…")}</p> : null}
              {supplierCapas.isError ? <p className="text-sm text-red-600">{extractApiError(supplierCapas.error)}</p> : null}
              {!supplierCapas.isLoading && !supplierCapas.isError && (supplierCapas.data ?? []).length === 0 ? (
                <p className="text-sm text-gray-500">{tx("No corrective actions recorded.")}</p>
              ) : null}
              {(supplierCapas.data ?? []).map((action: CorrectiveAction) => (
                <div key={action.id} className="rounded border border-gray-200 p-3">
                  <div className="flex items-center justify-between gap-3">
                    <span className="font-medium text-sm">{action.ca_no} · {action.title}</span>
                    <Badge label={action.status} variant={action.status === "VERIFIED" ? "green" : action.status === "OVERDUE" ? "red" : "yellow"} />
                  </div>
                  <p className="mt-1 text-xs text-gray-600">{action.description}</p>
                  {action.supplier_evaluation_id && <p className="mt-1 text-[11px] text-gray-400">{tx("Linked evaluation:")} {action.supplier_evaluation_id}</p>}
                </div>
              ))}
            </section>
          ) : (
            <p className="text-sm text-gray-500">{tx("History is restricted to users with quality view permission.")}</p>
          )}
          {canCreateCapa && (
            <form onSubmit={(e) => { e.preventDefault(); createCapa.mutate(); }} className="space-y-3 border-t border-gray-200 pt-4">
              <h2 className="text-sm font-semibold">{tx("Record corrective action")}</h2>
              <Input label={tx("Title *")} value={capaForm.title} onChange={(e) => setCapaForm((f) => ({ ...f, title: e.target.value }))} required />
              <label className="block text-sm text-gray-700">
                {tx("Description *")}
                <textarea className="mt-1 w-full rounded border border-gray-300 p-2 text-sm" rows={3} value={capaForm.description} onChange={(e) => setCapaForm((f) => ({ ...f, description: e.target.value }))} required />
              </label>
              <label className="block text-sm text-gray-700">
                {tx("Severity")}
                <select className="mt-1 w-full rounded border border-gray-300 p-2 text-sm" value={capaForm.severity} onChange={(e) => setCapaForm((f) => ({ ...f, severity: e.target.value as RiskLevel }))}>
                  {["LOW", "MEDIUM", "HIGH", "CRITICAL"].map((severity) => <option key={severity} value={severity}>{severity}</option>)}
                </select>
              </label>
              {selectedSupplier?.latest_evaluation_id && (
                <label className="block text-sm text-gray-700">
                  {tx("Source evaluation")}
                  <select className="mt-1 w-full rounded border border-gray-300 p-2 text-sm" value={capaForm.supplier_evaluation_id} onChange={(e) => setCapaForm((f) => ({ ...f, supplier_evaluation_id: e.target.value }))}>
                    <option value="">{tx("Supplier only")}</option>
                    <option value={selectedSupplier.latest_evaluation_id}>{tx("Latest evaluation (")}{selectedSupplier.last_evaluation_date})</option>
                  </select>
                </label>
              )}
              <div className="flex justify-end">
                <Button type="submit" loading={createCapa.isPending} disabled={!capaForm.title.trim() || !capaForm.description.trim()}>{tx("Create linked action")}</Button>
              </div>
            </form>
          )}
        </div>
      </Modal>
    </div>
  );
}
