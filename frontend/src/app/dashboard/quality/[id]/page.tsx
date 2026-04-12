"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useParams, useRouter } from "next/navigation";
import { qualityApi, QCDecision, ParameterType } from "@/lib/quality";
import { qualityApi as qApi } from "@/lib/quality";
import { extractApiError } from "@/lib/inventory";
import { Table } from "@/components/ui/Table";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Modal } from "@/components/ui/Modal";
import { Input } from "@/components/ui/Input";
import { Select } from "@/components/ui/Select";
import { ToastContainer } from "@/components/ui/Toast";
import { useToast } from "@/hooks/useToast";

const statusVariant = (s: string) =>
  s === "PASSED" ? "green"
  : s === "FAILED" ? "red"
  : s === "CONDITIONAL_RELEASE" ? "blue"
  : s === "CANCELLED" ? "red"
  : "blue";

const PARAM_TYPE_OPTS = [
  { value: "NUMERIC", label: "Numeric" },
  { value: "TEXT", label: "Text" },
  { value: "BOOLEAN", label: "Yes/No" },
  { value: "PASS_FAIL", label: "Pass/Fail" },
];

type TestForm = {
  parameter_name: string;
  parameter_type: ParameterType;
  unit: string;
  numeric_value: string;
  text_value: string;
  boolean_value: string;
  min_spec: string;
  max_spec: string;
  expected_text: string;
  is_passed: string;
  is_critical: boolean;
  notes: string;
};

const emptyTestForm = (): TestForm => ({
  parameter_name: "", parameter_type: "NUMERIC", unit: "",
  numeric_value: "", text_value: "", boolean_value: "",
  min_spec: "", max_spec: "", expected_text: "",
  is_passed: "", is_critical: false, notes: "",
});

export default function QCInspectionDetailPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const qc = useQueryClient();
  const { toasts, toast, dismiss } = useToast();
  const [testOpen, setTestOpen] = useState(false);
  const [decideOpen, setDecideOpen] = useState(false);
  const [coaOpen, setCoaOpen] = useState(false);
  const [testForm, setTestForm] = useState<TestForm>(emptyTestForm());
  const [decideForm, setDecideForm] = useState({
    decision: "" as QCDecision | "",
    decision_notes: "",
    rework_candidate: false,
    apply_quarantine: false,
  });

  const { data: inspection, isLoading } = useQuery({
    queryKey: ["qc-inspection", id],
    queryFn: () => qualityApi.getInspection(id),
    enabled: !!id,
  });

  const { data: coa } = useQuery({
    queryKey: ["qc-coa", id],
    queryFn: () => qualityApi.getCOA(id),
    enabled: coaOpen && !!id,
  });

  const { data: parameters = [] } = useQuery({
    queryKey: ["qc-parameters", inspection?.qc_type],
    queryFn: () => qualityApi.listParameters({ qc_type: inspection?.qc_type }),
    enabled: testOpen && !!inspection,
  });

  const invalidate = () => {
    qc.invalidateQueries({ queryKey: ["qc-inspection", id] });
    qc.invalidateQueries({ queryKey: ["qc-inspections"] });
  };

  const addResult = useMutation({
    mutationFn: () => {
      const ptype = testForm.parameter_type;
      return qualityApi.addTestResult(id, {
        parameter_name: testForm.parameter_name,
        parameter_type: ptype,
        unit: testForm.unit || undefined,
        numeric_value: ptype === "NUMERIC" && testForm.numeric_value ? parseFloat(testForm.numeric_value) : undefined,
        text_value: ptype === "TEXT" ? testForm.text_value || undefined : undefined,
        boolean_value: ptype === "BOOLEAN" ? testForm.boolean_value === "true" : undefined,
        min_spec: ptype === "NUMERIC" && testForm.min_spec ? parseFloat(testForm.min_spec) : undefined,
        max_spec: ptype === "NUMERIC" && testForm.max_spec ? parseFloat(testForm.max_spec) : undefined,
        expected_text: (ptype === "TEXT" || ptype === "BOOLEAN") ? testForm.expected_text || undefined : undefined,
        is_passed: ptype === "PASS_FAIL" ? testForm.is_passed === "pass" : undefined,
        is_critical: testForm.is_critical,
        notes: testForm.notes || undefined,
      });
    },
    onSuccess: () => {
      invalidate();
      setTestOpen(false);
      setTestForm(emptyTestForm());
      toast("success", "Result added", "");
    },
    onError: (e) => toast("error", "Failed", extractApiError(e)),
  });

  const deleteResult = useMutation({
    mutationFn: (resultId: string) => qualityApi.deleteTestResult(id, resultId),
    onSuccess: () => { invalidate(); toast("success", "Removed", ""); },
    onError: (e) => toast("error", "Failed", extractApiError(e)),
  });

  const decide = useMutation({
    mutationFn: () => qualityApi.decide(id, { ...decideForm }),
    onSuccess: () => { invalidate(); setDecideOpen(false); toast("success", "Decision recorded", ""); },
    onError: (e) => toast("error", "Failed", extractApiError(e)),
  });

  const releaseQuar = useMutation({
    mutationFn: () => qualityApi.releaseQuarantine(id),
    onSuccess: () => { invalidate(); toast("success", "Quarantine released", "Stock available again."); },
    onError: (e) => toast("error", "Failed", extractApiError(e)),
  });

  const fillFromParam = (paramName: string) => {
    const p = parameters.find((x) => x.name === paramName);
    if (!p) return;
    setTestForm((f) => ({
      ...f,
      parameter_name: p.name,
      parameter_type: p.parameter_type,
      unit: p.unit || "",
      min_spec: p.min_value != null ? String(p.min_value) : "",
      max_spec: p.max_value != null ? String(p.max_value) : "",
      expected_text: p.expected_value || "",
      is_critical: p.is_critical,
    }));
  };

  if (isLoading) return <div className="flex justify-center py-24"><div className="h-8 w-8 animate-spin rounded-full border-4 border-indigo-600 border-t-transparent" /></div>;
  if (!inspection) return <div className="text-center py-16 text-gray-500">Inspection not found.</div>;

  const isOpen = inspection.status === "PENDING" || inspection.status === "IN_PROGRESS";
  const isDecided = !!inspection.decision;

  return (
    <div className="space-y-6">
      <ToastContainer toasts={toasts} onDismiss={dismiss} />

      {/* Header */}
      <div className="rounded-xl border border-gray-200 bg-white p-6 shadow-sm">
        <div className="flex items-start justify-between flex-wrap gap-4">
          <div>
            <button className="text-sm text-indigo-600 hover:underline mb-2 block" onClick={() => router.push("/dashboard/quality")}>
              ← Back to QC Inspections
            </button>
            <h1 className="text-2xl font-bold text-gray-900 font-mono">{inspection.inspection_no}</h1>
            <p className="text-sm text-gray-500 mt-1">
              {inspection.qc_type.replace(/_/g, " ")}
              {inspection.material_name && ` · ${inspection.material_code ? `${inspection.material_code} ` : ""}${inspection.material_name}`}
              {inspection.product_name && ` · ${inspection.product_sku ? `${inspection.product_sku} ` : ""}${inspection.product_name}`}
              {inspection.supplier_name && ` · ${inspection.supplier_name}`}
            </p>
            {(inspection.lot_number || inspection.batch_no) && (
              <p className="text-xs text-gray-400 mt-1">
                {inspection.lot_number && `Lot: ${inspection.lot_number}`}
                {inspection.lot_number && inspection.batch_no && " · "}
                {inspection.batch_no && `Batch: ${inspection.batch_no}`}
              </p>
            )}
            {inspection.decision && (
              <p className="text-sm mt-2">
                Decision: <span className={`font-semibold ${inspection.decision === "ACCEPT" ? "text-green-600" : inspection.decision === "REJECT" ? "text-red-600" : "text-amber-600"}`}>
                  {inspection.decision.replace(/_/g, " ")}
                </span>
                {inspection.decision_notes && <span className="text-gray-500 ml-1">— {inspection.decision_notes}</span>}
              </p>
            )}
          </div>
          <div className="flex flex-col items-end gap-3">
            <div className="flex items-center gap-2">
              <Badge label={inspection.status.replace(/_/g, " ")} variant={statusVariant(inspection.status)} />
              {inspection.quarantine_applied && <Badge label="QUARANTINED" variant="red" />}
              {inspection.rework_candidate && <Badge label="REWORK" variant="blue" />}
              {inspection.critical_fail && <Badge label="CRITICAL FAIL" variant="red" />}
            </div>
            <div className="flex gap-2 flex-wrap justify-end">
              {isOpen && (
                <>
                  <Button onClick={() => setTestOpen(true)}>+ Add Test Result</Button>
                  <Button variant="secondary" onClick={() => setDecideOpen(true)}>Record Decision</Button>
                </>
              )}
              {inspection.quarantine_applied && (
                <Button variant="secondary" onClick={() => releaseQuar.mutate()} loading={releaseQuar.isPending}>Release Quarantine</Button>
              )}
              <Button variant="secondary" onClick={() => setCoaOpen(true)}>View COA</Button>
            </div>
          </div>
        </div>

        {/* Stats row */}
        <div className="mt-4 grid grid-cols-4 gap-4 pt-4 border-t border-gray-100">
          <div><p className="text-xs text-gray-500">Total Tests</p><p className="text-xl font-bold">{inspection.test_count}</p></div>
          <div><p className="text-xs text-gray-500">Passed</p><p className="text-xl font-bold text-green-600">{inspection.pass_count}</p></div>
          <div><p className="text-xs text-gray-500">Failed</p><p className={`text-xl font-bold ${inspection.fail_count > 0 ? "text-red-600" : "text-gray-400"}`}>{inspection.fail_count}</p></div>
          <div>
            <p className="text-xs text-gray-500">Pass Rate</p>
            <p className={`text-xl font-bold ${inspection.test_count > 0 && inspection.pass_count === inspection.test_count ? "text-green-600" : inspection.fail_count > 0 ? "text-red-600" : "text-gray-400"}`}>
              {inspection.test_count > 0 ? `${Math.round(inspection.pass_count / inspection.test_count * 100)}%` : "—"}
            </p>
          </div>
        </div>
      </div>

      {/* Test Results */}
      <div>
        <h2 className="text-lg font-semibold text-gray-800 mb-3">Test Results</h2>
        {inspection.test_results.length === 0 ? (
          <div className="rounded-xl border border-dashed border-gray-300 p-8 text-center text-gray-500 text-sm">
            No test results recorded yet. Click "Add Test Result" to start.
          </div>
        ) : (
          <Table
            keyField="id"
            data={inspection.test_results}
            emptyMessage=""
            columns={[
              {
                header: "Parameter",
                accessor: (t) => (
                  <span className="flex items-center gap-2">
                    {t.parameter_name}
                    {t.is_critical && <Badge label="Critical" variant="red" />}
                  </span>
                ),
              },
              { header: "Type", accessor: (t) => <span className="text-xs text-gray-500">{t.parameter_type}</span> },
              { header: "Spec", accessor: (t) => t.spec_range ?? "—" },
              { header: "Result", accessor: (t) => <span className="font-medium">{t.display_value}</span> },
              {
                header: "Status",
                accessor: (t) => t.is_passed == null ? (
                  <span className="text-gray-400 text-xs">Pending</span>
                ) : t.is_passed ? (
                  <Badge label="PASS" variant="green" />
                ) : (
                  <Badge label="FAIL" variant="red" />
                ),
              },
              { header: "Tested By", accessor: (t) => t.tested_by_name ?? "—" },
              { header: "Notes", accessor: (t) => t.notes ?? "—" },
              {
                header: "",
                accessor: (t) => isOpen ? (
                  <button className="text-xs text-red-400 hover:text-red-600" onClick={() => deleteResult.mutate(t.id)}>Remove</button>
                ) : null,
              },
            ]}
          />
        )}
      </div>

      {/* Add Test Result Modal */}
      <Modal open={testOpen} onClose={() => setTestOpen(false)} title="Add Test Result">
        <div className="space-y-4">
          {parameters.length > 0 && (
            <div>
              <p className="text-xs text-gray-500 mb-1">Quick fill from template:</p>
              <div className="flex flex-wrap gap-2">
                {parameters.map((p) => (
                  <button key={p.id} className="text-xs bg-gray-100 hover:bg-gray-200 rounded px-2 py-1" onClick={() => fillFromParam(p.name)}>
                    {p.name}
                  </button>
                ))}
              </div>
            </div>
          )}
          <div className="grid grid-cols-2 gap-4">
            <Input label="Parameter Name *" value={testForm.parameter_name} onChange={(e) => setTestForm((f) => ({ ...f, parameter_name: e.target.value }))} required />
            <Select label="Type *" options={PARAM_TYPE_OPTS} value={testForm.parameter_type} onChange={(e) => setTestForm((f) => ({ ...f, parameter_type: e.target.value as ParameterType }))} />
          </div>
          <Input label="Unit" value={testForm.unit} onChange={(e) => setTestForm((f) => ({ ...f, unit: e.target.value }))} placeholder="e.g. cP, °C, pH" />

          {testForm.parameter_type === "NUMERIC" && (
            <>
              <Input label="Result Value *" type="number" step="any" value={testForm.numeric_value} onChange={(e) => setTestForm((f) => ({ ...f, numeric_value: e.target.value }))} />
              <div className="grid grid-cols-2 gap-4">
                <Input label="Min Spec" type="number" step="any" value={testForm.min_spec} onChange={(e) => setTestForm((f) => ({ ...f, min_spec: e.target.value }))} />
                <Input label="Max Spec" type="number" step="any" value={testForm.max_spec} onChange={(e) => setTestForm((f) => ({ ...f, max_spec: e.target.value }))} />
              </div>
            </>
          )}
          {testForm.parameter_type === "TEXT" && (
            <>
              <Input label="Result *" value={testForm.text_value} onChange={(e) => setTestForm((f) => ({ ...f, text_value: e.target.value }))} />
              <Input label="Expected Value (optional)" value={testForm.expected_text} onChange={(e) => setTestForm((f) => ({ ...f, expected_text: e.target.value }))} />
            </>
          )}
          {testForm.parameter_type === "BOOLEAN" && (
            <>
              <Select label="Result *" options={[{ value: "", label: "Select…" }, { value: "true", label: "Yes" }, { value: "false", label: "No" }]}
                value={testForm.boolean_value} onChange={(e) => setTestForm((f) => ({ ...f, boolean_value: e.target.value }))} />
              <Input label="Expected Value (true/false)" value={testForm.expected_text} onChange={(e) => setTestForm((f) => ({ ...f, expected_text: e.target.value }))} />
            </>
          )}
          {testForm.parameter_type === "PASS_FAIL" && (
            <Select label="Result *" options={[{ value: "", label: "Select…" }, { value: "pass", label: "PASS" }, { value: "fail", label: "FAIL" }]}
              value={testForm.is_passed} onChange={(e) => setTestForm((f) => ({ ...f, is_passed: e.target.value }))} />
          )}

          <div className="flex items-center gap-2">
            <input type="checkbox" id="is_critical" checked={testForm.is_critical} onChange={(e) => setTestForm((f) => ({ ...f, is_critical: e.target.checked }))} />
            <label htmlFor="is_critical" className="text-sm text-gray-700">Critical parameter (failure = overall fail)</label>
          </div>
          <Input label="Notes" value={testForm.notes} onChange={(e) => setTestForm((f) => ({ ...f, notes: e.target.value }))} />
          <div className="flex justify-end gap-3 pt-2">
            <Button variant="secondary" type="button" onClick={() => setTestOpen(false)}>Cancel</Button>
            <Button onClick={() => addResult.mutate()} loading={addResult.isPending} disabled={!testForm.parameter_name}>Add Result</Button>
          </div>
        </div>
      </Modal>

      {/* Decision Modal */}
      <Modal open={decideOpen} onClose={() => setDecideOpen(false)} title="Record QC Decision">
        <form onSubmit={(e) => { e.preventDefault(); decide.mutate(); }} className="space-y-4">
          <Select
            label="Decision *"
            options={[
              { value: "", label: "Select…" },
              { value: "ACCEPT", label: "Accept — Release for use" },
              { value: "REJECT", label: "Reject — Non-conforming" },
              { value: "CONDITIONAL_RELEASE", label: "Conditional Release — Use with caution" },
              { value: "REWORK", label: "Rework Required" },
            ]}
            value={decideForm.decision}
            onChange={(e) => setDecideForm((f) => ({ ...f, decision: e.target.value as QCDecision | "" }))}
          />
          <Input label="Decision Notes" value={decideForm.decision_notes} onChange={(e) => setDecideForm((f) => ({ ...f, decision_notes: e.target.value }))} />
          <div className="space-y-2">
            <label className="flex items-center gap-2 text-sm text-gray-700">
              <input type="checkbox" checked={decideForm.rework_candidate} onChange={(e) => setDecideForm((f) => ({ ...f, rework_candidate: e.target.checked }))} />
              Flag as rework candidate
            </label>
            {inspection.lot_id && inspection.warehouse_id && (decideForm.decision === "REJECT" || decideForm.decision === "CONDITIONAL_RELEASE") && (
              <label className="flex items-center gap-2 text-sm text-gray-700">
                <input type="checkbox" checked={decideForm.apply_quarantine} onChange={(e) => setDecideForm((f) => ({ ...f, apply_quarantine: e.target.checked }))} />
                Apply quarantine to stock (block from use)
              </label>
            )}
          </div>
          {decideForm.decision === "REJECT" && (
            <div className="rounded-lg bg-red-50 border border-red-200 p-3 text-xs text-red-700">
              Rejected stock will be flagged. If quarantine is selected, all matching stock will be blocked from issue and transfer.
            </div>
          )}
          <div className="flex justify-end gap-3 pt-2">
            <Button variant="secondary" type="button" onClick={() => setDecideOpen(false)}>Cancel</Button>
            <Button type="submit" loading={decide.isPending} disabled={!decideForm.decision}>Record Decision</Button>
          </div>
        </form>
      </Modal>

      {/* COA Modal */}
      <Modal open={coaOpen} onClose={() => setCoaOpen(false)} title="Certificate of Analysis">
        {coa ? (
          <div className="space-y-4">
            <div className="grid grid-cols-2 gap-4 text-sm">
              <div><p className="text-xs text-gray-400">Inspection No</p><p className="font-mono font-medium">{coa.inspection_no}</p></div>
              <div><p className="text-xs text-gray-400">Type</p><p>{coa.qc_type.replace(/_/g, " ")}</p></div>
              <div><p className="text-xs text-gray-400">Date</p><p>{new Date(coa.inspection_date).toLocaleDateString()}</p></div>
              <div><p className="text-xs text-gray-400">Inspector</p><p>{coa.inspector_name ?? "—"}</p></div>
              {coa.product_name && <div><p className="text-xs text-gray-400">Product</p><p>{coa.product_sku && `${coa.product_sku} · `}{coa.product_name}</p></div>}
              {coa.material_name && <div><p className="text-xs text-gray-400">Material</p><p>{coa.material_name}</p></div>}
              {coa.supplier_name && <div><p className="text-xs text-gray-400">Supplier</p><p>{coa.supplier_name}</p></div>}
              {coa.lot_number && <div><p className="text-xs text-gray-400">Lot No</p><p className="font-mono">{coa.lot_number}</p></div>}
              {coa.batch_no && <div><p className="text-xs text-gray-400">Batch No</p><p className="font-mono">{coa.batch_no}</p></div>}
            </div>

            <div className="rounded-lg p-3 border text-center text-sm font-semibold
              ${coa.overall_result === 'PASS' ? 'bg-green-50 border-green-200 text-green-700' : coa.overall_result === 'FAIL' ? 'bg-red-50 border-red-200 text-red-700' : 'bg-amber-50 border-amber-200 text-amber-700'}">
              Overall: {coa.overall_result}
              {coa.decision_notes && <span className="font-normal ml-1">— {coa.decision_notes}</span>}
            </div>

            {coa.test_lines.length > 0 && (
              <table className="w-full text-xs border-collapse">
                <thead>
                  <tr className="border-b border-gray-200 text-left text-gray-500">
                    <th className="py-1 pr-3">Parameter</th>
                    <th className="py-1 pr-3">Specification</th>
                    <th className="py-1 pr-3">Result</th>
                    <th className="py-1">Status</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100">
                  {coa.test_lines.map((l, i) => (
                    <tr key={i} className={l.is_critical && l.is_passed === false ? "bg-red-50" : ""}>
                      <td className="py-1.5 pr-3 font-medium">
                        {l.parameter_name}
                        {l.is_critical && <span className="ml-1 text-red-500">*</span>}
                      </td>
                      <td className="py-1.5 pr-3 text-gray-500">{l.spec_range ?? "—"}</td>
                      <td className="py-1.5 pr-3 font-mono">{l.result_value}</td>
                      <td className="py-1.5">
                        {l.is_passed == null ? "—" : l.is_passed
                          ? <span className="text-green-600 font-medium">PASS</span>
                          : <span className="text-red-600 font-medium">FAIL</span>}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
            {coa.test_lines.some((l) => l.is_critical) && (
              <p className="text-xs text-gray-400">* Critical parameter</p>
            )}
          </div>
        ) : (
          <div className="flex justify-center py-8"><div className="h-6 w-6 animate-spin rounded-full border-4 border-indigo-600 border-t-transparent" /></div>
        )}
      </Modal>
    </div>
  );
}
