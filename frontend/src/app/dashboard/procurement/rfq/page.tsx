"use client";
import { useCallback, useEffect, useState } from "react";
import {
  procurementApi, RFQRead, RFQDetail, RFQStatus,
  RFQEvaluationCriterionRead, RFQEvaluationDimension, RFQResponseRead,
} from "@/lib/procurement";
import { suppliersApi, Supplier } from "@/lib/suppliers";

const STATUS_COLORS: Record<RFQStatus, string> = {
  DRAFT: "bg-gray-100 text-gray-600",
  SENT: "bg-blue-100 text-blue-700",
  RESPONSES_RECEIVED: "bg-amber-100 text-amber-700",
  AWARDED: "bg-green-100 text-green-700",
  CANCELLED: "bg-red-100 text-red-500",
};

export default function RFQPage() {
  const [rfqs, setRFQs] = useState<RFQRead[]>([]);
  const [loading, setLoading] = useState(true);
  const [filterStatus, setFilterStatus] = useState<RFQStatus | "">("");
  const [showCreate, setShowCreate] = useState(false);
  const [selected, setSelected] = useState<RFQDetail | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [form, setForm] = useState({
    rfq_no: "", title: "", quantity: "", unit: "KG",
    description: "", required_by: "", response_deadline: "", notes: "",
  });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [suppliers, setSuppliers] = useState<Supplier[]>([]);
  const [selectedSupplierIds, setSelectedSupplierIds] = useState<string[]>([]);
  const [criteriaDraft, setCriteriaDraft] = useState([
    { code: "TECHNICAL_FIT", name: "Technical fit", dimension: "TECHNICAL" as RFQEvaluationDimension, weight_percent: "50", is_mandatory: true },
    { code: "COMMERCIAL_VALUE", name: "Commercial value", dimension: "COMMERCIAL" as RFQEvaluationDimension, weight_percent: "50", is_mandatory: false },
  ]);
  const [activeEvaluationResponseId, setActiveEvaluationResponseId] = useState<string | null>(null);
  const [evaluationDraft, setEvaluationDraft] = useState<Record<string, { score: string; passes_gate: boolean | null; comments: string }>>({});

  // Response form
  const [showResponse, setShowResponse] = useState(false);
  const [respForm, setRespForm] = useState({
    supplier_id: "", quoted_unit_price: "", quoted_currency: "KES",
    lead_time_days: "", valid_until: "", payment_terms: "", notes: "",
  });

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const data = await procurementApi.listRFQs(filterStatus ? { status: filterStatus as RFQStatus } : undefined);
      setRFQs(data);
    } finally {
      setLoading(false);
    }
  }, [filterStatus]);

  useEffect(() => { load(); }, [load]);

  useEffect(() => {
    suppliersApi.list(0, 200)
      .then((rows) => setSuppliers(rows.filter((supplier) => supplier.is_active)))
      .catch(() => setSuppliers([]));
  }, []);

  const openDetail = async (id: string) => {
    setDetailLoading(true);
    setSelected(null);
    setActiveEvaluationResponseId(null);
    try {
      const detail = await procurementApi.getRFQ(id);
      if (detail.evaluation_criteria.length === 0) {
        setCriteriaDraft([
          { code: "TECHNICAL_FIT", name: "Technical fit", dimension: "TECHNICAL", weight_percent: "50", is_mandatory: true },
          { code: "COMMERCIAL_VALUE", name: "Commercial value", dimension: "COMMERCIAL", weight_percent: "50", is_mandatory: false },
        ]);
      }
      setSelected(detail);
    } finally {
      setDetailLoading(false);
    }
  };

  const create = async () => {
    if (!form.rfq_no.trim() || !form.title.trim() || !form.quantity || selectedSupplierIds.length === 0) {
      setError("RFQ No., Title, Quantity, and at least one invited supplier are required"); return;
    }
    setSaving(true); setError("");
    try {
      await procurementApi.createRFQ({
        ...form,
        quantity: parseFloat(form.quantity),
        supplier_ids: selectedSupplierIds,
      });
      setShowCreate(false);
      setForm({ rfq_no: "", title: "", quantity: "", unit: "KG", description: "", required_by: "", response_deadline: "", notes: "" });
      setSelectedSupplierIds([]);
      await load();
    } catch {
      setError("Failed to create RFQ");
    } finally {
      setSaving(false);
    }
  };

  const sendRFQ = async (id: string) => {
    setError("");
    try {
      const updated = await procurementApi.issueRFQInvitations(id);
      await load();
      if (selected?.id === id) setSelected(updated);
    } catch {
      setError("Could not issue invitations. Confirm that the RFQ has active suppliers and remains a draft.");
    }
  };

  const awardRFQ = async (id: string, supplierId: string) => {
    await procurementApi.updateRFQ(id, { status: "AWARDED", awarded_supplier_id: supplierId });
    await load();
    const updated = await procurementApi.getRFQ(id);
    setSelected(updated);
  };

  const submitResponse = async () => {
    if (!selected || !respForm.supplier_id) { setError("Supplier ID required"); return; }
    setSaving(true); setError("");
    try {
      await procurementApi.addRFQResponse(selected.id, {
        supplier_id: respForm.supplier_id,
        quoted_unit_price: respForm.quoted_unit_price ? parseFloat(respForm.quoted_unit_price) : null,
        quoted_currency: respForm.quoted_currency,
        lead_time_days: respForm.lead_time_days ? parseInt(respForm.lead_time_days) : null,
        valid_until: respForm.valid_until || null,
        payment_terms: respForm.payment_terms || null,
        notes: respForm.notes || null,
      });
      setShowResponse(false);
      const updated = await procurementApi.getRFQ(selected.id);
      setSelected(updated);
      await load();
    } catch {
      setError("Failed to submit response");
    } finally {
      setSaving(false);
    }
  };

  const saveEvaluationMatrix = async () => {
    if (!selected) return;
    setSaving(true); setError("");
    try {
      await procurementApi.createRFQEvaluationMatrix(selected.id, {
        criteria: criteriaDraft.map((criterion) => ({
          ...criterion,
          weight_percent: parseFloat(criterion.weight_percent),
        })),
      });
      setSelected(await procurementApi.getRFQ(selected.id));
    } catch {
      setError("Could not save the matrix. Use unique codes, include both dimensions, and make weights total exactly 100%.");
    } finally {
      setSaving(false);
    }
  };

  const startEvaluation = (response: RFQResponseRead, criteria: RFQEvaluationCriterionRead[]) => {
    setActiveEvaluationResponseId(response.id);
    setEvaluationDraft(Object.fromEntries(criteria.map((criterion) => {
      const existing = response.evaluations.find((item) => item.criterion_id === criterion.id);
      return [criterion.id, {
        score: existing ? String(existing.score) : "",
        passes_gate: criterion.is_mandatory ? (existing?.passes_gate ?? null) : null,
        comments: existing?.comments ?? "",
      }];
    })));
  };

  const submitEvaluation = async (responseId: string) => {
    if (!selected) return;
    setSaving(true); setError("");
    try {
      await procurementApi.submitRFQResponseEvaluations(selected.id, responseId, {
        evaluations: selected.evaluation_criteria.map((criterion) => ({
          criterion_id: criterion.id,
          score: Number(evaluationDraft[criterion.id]?.score),
          passes_gate: criterion.is_mandatory ? evaluationDraft[criterion.id]?.passes_gate : null,
          comments: evaluationDraft[criterion.id]?.comments || null,
        })),
      });
      setSelected(await procurementApi.getRFQ(selected.id));
      setActiveEvaluationResponseId(null);
    } catch {
      setError("Could not record evaluation. Enter a 0–100 score for every criterion and pass/fail for mandatory gates.");
    } finally {
      setSaving(false);
    }
  };

  const criteriaWeightTotal = criteriaDraft.reduce((sum, criterion) => sum + (Number(criterion.weight_percent) || 0), 0);
  const evaluationMatrixReady = criteriaDraft.length >= 2
    && Math.abs(criteriaWeightTotal - 100) < 0.001
    && new Set(criteriaDraft.map((criterion) => criterion.dimension)).size === 2
    && new Set(criteriaDraft.map((criterion) => criterion.code.trim().toUpperCase())).size === criteriaDraft.length
    && criteriaDraft.every((criterion) => criterion.code.trim().length >= 2 && criterion.name.trim().length >= 2);

  return (
    <div className="p-6 space-y-5">
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div>
          <h1 className="text-xl font-bold text-gray-900">Request for Quotation (RFQ)</h1>
          <p className="text-xs text-gray-500 mt-0.5">Issue RFQs to suppliers, collect quotes, compare, and award.</p>
        </div>
        <button onClick={() => { setShowCreate(true); setError(""); }}
          className="rounded bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700">
          + New RFQ
        </button>
      </div>

      <div className="flex gap-3 flex-wrap items-center">
        <select className="border rounded px-2 py-1.5 text-sm" value={filterStatus}
          onChange={e => setFilterStatus(e.target.value as RFQStatus | "")}>
          <option value="">All Status</option>
          {(["DRAFT","SENT","RESPONSES_RECEIVED","AWARDED","CANCELLED"] as RFQStatus[]).map(s => (
            <option key={s} value={s}>{s.replace("_", " ")}</option>
          ))}
        </select>
        <span className="text-xs text-gray-500 self-center">{rfqs.length} RFQs</span>
        {error && <span role="alert" className="text-xs text-red-600">{error}</span>}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
        {/* RFQ List */}
        <div className="lg:col-span-2">
          {loading ? (
            <p className="text-sm text-gray-500">Loading…</p>
          ) : rfqs.length === 0 ? (
            <div className="bg-white border rounded-lg p-10 text-center text-gray-400">
              <p className="text-2xl mb-2">📋</p>
              <p className="text-sm">No RFQs found.</p>
            </div>
          ) : (
            <div className="bg-white border rounded-lg shadow-sm overflow-x-auto">
              <table className="w-full text-sm">
                <thead className="bg-gray-50 border-b">
                  <tr>
                    {["RFQ No.", "Title", "Qty", "Deadline", "Responses", "Status", ""].map(h => (
                      <th key={h} className="px-4 py-2 text-left text-xs font-semibold text-gray-600">{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody className="divide-y">
                  {rfqs.map(r => (
                    <tr key={r.id} className="hover:bg-gray-50">
                      <td className="px-4 py-3 font-mono text-xs text-gray-600">{r.rfq_no}</td>
                      <td className="px-4 py-3 font-medium text-gray-800">
                        <button onClick={() => openDetail(r.id)} className="hover:text-blue-600 text-left">
                          {r.title}
                        </button>
                      </td>
                      <td className="px-4 py-3 text-xs text-gray-600">{r.quantity != null ? `${r.quantity} ${r.unit}` : `${r.line_count} lines`}</td>
                      <td className="px-4 py-3 text-xs text-gray-600">{r.response_deadline ?? "—"}</td>
                      <td className="px-4 py-3 text-xs font-semibold text-blue-600">{r.response_count}/{r.invited_count}</td>
                      <td className="px-4 py-3">
                        <span className={`text-xs rounded-full px-2 py-0.5 ${STATUS_COLORS[r.status]}`}>
                          {r.status.replace("_", " ")}
                        </span>
                      </td>
                      <td className="px-4 py-3">
                        {r.status === "DRAFT" && (
                          <button onClick={() => sendRFQ(r.id)} className="text-xs text-blue-600 hover:underline">
                            Issue invitations
                          </button>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>

        {/* Detail Panel */}
        <div className="bg-white border rounded-lg p-5">
          {detailLoading ? (
            <p className="text-sm text-gray-500">Loading…</p>
          ) : selected ? (
            <div className="space-y-4">
              <div>
                <div className="flex items-center justify-between mb-1">
                  <h3 className="text-sm font-semibold text-gray-800">{selected.rfq_no}</h3>
                  <span className={`text-xs rounded-full px-2 py-0.5 ${STATUS_COLORS[selected.status]}`}>
                    {selected.status.replace("_", " ")}
                  </span>
                </div>
                <p className="text-xs text-gray-600">{selected.title}</p>
                <p className="text-xs text-gray-500 mt-1">{selected.quantity != null ? `${selected.quantity} ${selected.unit}` : `${selected.lines.length} event lines`}</p>
                {selected.lines.length > 0 && (
                  <ul className="mt-2 space-y-1 text-xs text-gray-500">
                    {selected.lines.map((line) => (
                      <li key={line.id}>
                        {line.line_no}. {line.description || line.material_id || line.product_id || "Requirement"}: {line.quantity} {line.unit}
                      </li>
                    ))}
                  </ul>
                )}
                {selected.description && <p className="text-xs text-gray-500 mt-1">{selected.description}</p>}
              </div>

              <div className="border-t pt-3">
                {selected.status === "SENT" || selected.status === "RESPONSES_RECEIVED" ? (
                  <p className="mb-2 text-xs text-amber-700">Invitation recorded in the ERP. This local workflow does not send external email.</p>
                ) : null}
                <div className="flex items-center justify-between mb-2">
                  <p className="text-xs font-semibold text-gray-600">Bids ({selected.response_count}) · Invited ({selected.invited_count})</p>
                  {(selected.status === "SENT" || selected.status === "RESPONSES_RECEIVED") && (
                    <button onClick={() => { setShowResponse(true); setError(""); }}
                      className="text-xs text-blue-600 hover:underline">
                      + Record Bid
                    </button>
                  )}
                </div>
                {selected.responses.length === 0 ? (
                  <p className="text-xs text-gray-400">No responses yet.</p>
                ) : (
                  <div className="space-y-2">
                    {selected.responses.map(resp => (
                      <div key={resp.id} className="border rounded p-3 bg-gray-50">
                        <div className="flex items-center justify-between">
                          <p className="text-xs font-medium text-gray-700">{resp.supplier_name ?? resp.supplier_id.slice(0,8)}</p>
                          <span className="text-xs text-gray-500">{resp.status} · {resp.invitation_status === "ISSUED" ? "Invitation issued" : "Not issued"}</span>
                        </div>
                        {resp.invitation_issued_at && <p className="text-xs text-gray-500 mt-1">Issued in ERP: {new Date(resp.invitation_issued_at).toLocaleString()}</p>}
                        {resp.submitted_at && <p className="text-xs text-gray-500 mt-1">Bid recorded: {new Date(resp.submitted_at).toLocaleString()}</p>}
                        {resp.quoted_unit_price != null && (
                          <p className="text-xs text-gray-600 mt-1">
                            {resp.quoted_currency} {Number(resp.quoted_unit_price).toLocaleString()} /unit
                            {resp.lead_time_days != null && ` · ${resp.lead_time_days}d lead`}
                          </p>
                        )}
                        {selected.status === "RESPONSES_RECEIVED" && (
                          <button
                            onClick={() => awardRFQ(selected.id, resp.supplier_id)}
                            className="mt-2 text-xs bg-green-600 text-white rounded px-2 py-0.5 hover:bg-green-700"
                          >
                            Award
                          </button>
                        )}
                      </div>
                    ))}
                  </div>
                )}
              </div>

              {(selected.status === "SENT" || selected.status === "RESPONSES_RECEIVED") && (
                <div className="border-t pt-3 space-y-3">
                  <div>
                    <p className="text-xs font-semibold text-gray-700">Bid evaluation</p>
                    <p className="text-[11px] text-gray-500 mt-1">Set a separate, buyer-configured matrix for this RFQ. Example values are editable and are not organization-wide policy.</p>
                  </div>
                  {selected.evaluation_criteria.length === 0 ? (
                    selected.access?.can_edit ? <div className="space-y-2">
                      {criteriaDraft.map((criterion, index) => (
                        <div key={`${criterion.code}-${index}`} className="grid grid-cols-2 gap-2 rounded border p-2">
                          <input aria-label={`Criterion ${index + 1} code`} value={criterion.code}
                            onChange={(event) => setCriteriaDraft((rows) => rows.map((row, rowIndex) => rowIndex === index ? { ...row, code: event.target.value } : row))}
                            className="border rounded px-2 py-1 text-xs" placeholder="Code" />
                          <input aria-label={`Criterion ${index + 1} name`} value={criterion.name}
                            onChange={(event) => setCriteriaDraft((rows) => rows.map((row, rowIndex) => rowIndex === index ? { ...row, name: event.target.value } : row))}
                            className="border rounded px-2 py-1 text-xs" placeholder="Criterion name" />
                          <select aria-label={`Criterion ${index + 1} dimension`} value={criterion.dimension}
                            onChange={(event) => setCriteriaDraft((rows) => rows.map((row, rowIndex) => rowIndex === index ? { ...row, dimension: event.target.value as RFQEvaluationDimension } : row))}
                            className="border rounded px-2 py-1 text-xs">
                            <option value="TECHNICAL">Technical</option>
                            <option value="COMMERCIAL">Commercial</option>
                          </select>
                          <label className="flex items-center gap-2 text-xs text-gray-600">
                            Weight %
                            <input aria-label={`Criterion ${index + 1} weight`} type="number" min="0.01" max="100" step="0.01" value={criterion.weight_percent}
                              onChange={(event) => setCriteriaDraft((rows) => rows.map((row, rowIndex) => rowIndex === index ? { ...row, weight_percent: event.target.value } : row))}
                              className="w-20 border rounded px-2 py-1" />
                          </label>
                          <label className="col-span-2 flex items-center gap-2 text-xs text-gray-600">
                            <input type="checkbox" checked={criterion.is_mandatory}
                              onChange={(event) => setCriteriaDraft((rows) => rows.map((row, rowIndex) => rowIndex === index ? { ...row, is_mandatory: event.target.checked } : row))} />
                            Mandatory pass/fail gate
                          </label>
                        </div>
                      ))}
                      <div className="flex items-center justify-between text-xs">
                        <button type="button" onClick={() => setCriteriaDraft((rows) => [...rows, {
                          code: `CRITERION_${rows.length + 1}`, name: "New criterion", dimension: "COMMERCIAL", weight_percent: "10", is_mandatory: false,
                        }])} className="text-blue-600 hover:underline">+ Add criterion</button>
                        <span className={evaluationMatrixReady ? "text-green-700" : "text-amber-700"}>
                          Total: {criteriaWeightTotal.toFixed(2)}%
                        </span>
                      </div>
                      <button type="button" onClick={saveEvaluationMatrix} disabled={saving || !evaluationMatrixReady}
                        className="w-full rounded bg-indigo-600 px-3 py-2 text-xs font-medium text-white disabled:opacity-50">
                        {saving ? "Saving…" : "Save RFQ evaluation matrix"}
                      </button>
                    </div> : <p className="text-xs text-gray-500">An evaluation matrix has not been configured for this RFQ.</p>
                  ) : (
                    <div className="space-y-3">
                      <ul className="space-y-1">
                        {selected.evaluation_criteria.map((criterion) => (
                          <li key={criterion.id} className="text-[11px] text-gray-600">
                            {criterion.dimension}: {criterion.name} · {Number(criterion.weight_percent).toFixed(2)}%{criterion.is_mandatory ? " · mandatory gate" : ""}
                          </li>
                        ))}
                      </ul>
                      {selected.responses.filter((response) => response.status === "SUBMITTED").map((response) => (
                        <div key={response.id} className="rounded border bg-gray-50 p-2 space-y-2">
                          <div className="flex items-center justify-between gap-2">
                            <span className="text-xs font-medium text-gray-700">{response.supplier_name ?? response.supplier_id}</span>
                            <span className={`text-[11px] ${response.evaluation_status === "DISQUALIFIED" ? "text-red-700" : response.evaluation_status === "QUALIFIED" ? "text-green-700" : "text-gray-500"}`}>
                              {response.evaluation_status.replace("_", " ")}{response.score != null ? ` · ${Number(response.score).toFixed(2)}/100` : ""}
                            </span>
                          </div>
                          {activeEvaluationResponseId === response.id ? (
                            <div className="space-y-2">
                              {selected.evaluation_criteria.map((criterion) => {
                                const previous = response.evaluations.find((item) => item.criterion_id === criterion.id);
                                const draft = evaluationDraft[criterion.id] ?? { score: "", passes_gate: null, comments: "" };
                                return (
                                  <div key={criterion.id} className="grid grid-cols-2 gap-2 border-t pt-2">
                                    <label className="text-[11px] text-gray-600">
                                      {criterion.name} score (0–100)
                                      <input type="number" min="0" max="100" step="0.01" value={draft.score}
                                        onChange={(event) => setEvaluationDraft((current) => ({ ...current, [criterion.id]: { ...draft, score: event.target.value } }))}
                                        className="mt-1 w-full border rounded px-2 py-1 text-xs" />
                                    </label>
                                    {criterion.is_mandatory ? (
                                      <label className="text-[11px] text-gray-600">Mandatory gate decision
                                        <select value={draft.passes_gate === null ? "" : String(draft.passes_gate)}
                                          onChange={(event) => setEvaluationDraft((current) => ({ ...current, [criterion.id]: { ...draft, passes_gate: event.target.value === "" ? null : event.target.value === "true" } }))}
                                          className="mt-1 w-full border rounded px-2 py-1 text-xs">
                                          <option value="">Select pass/fail</option><option value="true">Pass</option><option value="false">Fail</option>
                                        </select>
                                      </label>
                                    ) : <div className="text-[11px] text-gray-500 self-center">{previous ? `Previous revision ${previous.revision_no}` : "No prior score"}</div>}
                                    <input aria-label={`${criterion.name} evaluation comments`} value={draft.comments}
                                      onChange={(event) => setEvaluationDraft((current) => ({ ...current, [criterion.id]: { ...draft, comments: event.target.value } }))}
                                      className="col-span-2 border rounded px-2 py-1 text-xs" placeholder="Evaluation notes (optional)" />
                                  </div>
                                );
                              })}
                              <div className="flex gap-2">
                              <button type="button" onClick={() => submitEvaluation(response.id)}
                                disabled={saving || selected.evaluation_criteria.some((criterion) => {
                                  const draft = evaluationDraft[criterion.id];
                                  const score = Number(draft?.score);
                                  return !draft?.score.trim() || !Number.isFinite(score) || score < 0 || score > 100 || (criterion.is_mandatory && draft.passes_gate === null);
                                })}
                                  className="flex-1 rounded bg-indigo-600 px-2 py-1.5 text-xs text-white disabled:opacity-50">Save evaluation revision</button>
                                <button type="button" onClick={() => setActiveEvaluationResponseId(null)} className="rounded border px-2 py-1.5 text-xs">Cancel</button>
                              </div>
                            </div>
                          ) : (
                            <div className="space-y-1">
                              {response.evaluation_history.map((evaluation) => (
                                <p key={`${evaluation.criterion_id}-${evaluation.revision_no}`} className="text-[11px] text-gray-500">
                                  {evaluation.criterion_name ?? evaluation.criterion_code}: {Number(evaluation.score).toFixed(2)} · revision {evaluation.revision_no}{evaluation.passes_gate === null || evaluation.passes_gate === undefined ? "" : evaluation.passes_gate ? " · gate passed" : " · gate failed"} · {evaluation.evaluator_id ? `evaluator ${evaluation.evaluator_id.slice(0, 8)}` : "unattributed"} · {new Date(evaluation.evaluated_at).toLocaleString()}{evaluation.comments ? ` · ${evaluation.comments}` : ""}
                                </p>
                              ))}
                              {selected.access?.can_edit && <button type="button" onClick={() => startEvaluation(response, selected.evaluation_criteria)} className="text-xs text-indigo-700 hover:underline">
                                {response.evaluations.length > 0 ? "Record new evaluation revision" : "Evaluate bid"}
                              </button>}
                            </div>
                          )}
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}

              {selected.awarded_supplier_name && (
                <div className="bg-green-50 border border-green-200 rounded p-3">
                  <p className="text-xs font-semibold text-green-700">Awarded to: {selected.awarded_supplier_name}</p>
                </div>
              )}
            </div>
          ) : (
            <div className="text-center py-8 text-gray-400">
              <p className="text-2xl mb-2">📋</p>
              <p className="text-sm">Click an RFQ to view details.</p>
            </div>
          )}
        </div>
      </div>

      {/* Create Modal */}
      {showCreate && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-xl shadow-2xl w-full max-w-md max-h-[90vh] overflow-y-auto">
            <div className="px-6 py-4 border-b flex items-center justify-between">
              <h2 className="text-base font-semibold">New RFQ</h2>
              <button onClick={() => setShowCreate(false)} className="text-gray-400 hover:text-gray-600 text-xl">×</button>
            </div>
            <div className="p-6 space-y-4">
              {error && <p className="text-xs text-red-500 bg-red-50 border border-red-200 rounded px-3 py-2">{error}</p>}
              {[
                { label: "RFQ No. *", key: "rfq_no", placeholder: "RFQ-2026-001" },
                { label: "Title *", key: "title", placeholder: "Raw material procurement Q3" },
                { label: "Description", key: "description", placeholder: "Details…" },
                { label: "Quantity *", key: "quantity", placeholder: "100", type: "number" },
              ].map(f => (
                <div key={f.key}>
                  <label className="block text-xs font-medium text-gray-600 mb-1">{f.label}</label>
                  <input type={f.type ?? "text"} placeholder={f.placeholder}
                    value={(form as Record<string, string>)[f.key]}
                    onChange={e => setForm(prev => ({ ...prev, [f.key]: e.target.value }))}
                    className="w-full border rounded px-3 py-2 text-sm focus:ring-1 focus:ring-blue-500 outline-none"
                  />
                </div>
              ))}
              <fieldset className="space-y-2">
                <legend className="block text-xs font-medium text-gray-600">Suppliers to invite *</legend>
                {suppliers.length === 0 ? (
                  <p className="text-xs text-amber-700">No active suppliers are available.</p>
                ) : suppliers.map((supplier) => (
                  <label key={supplier.id} className="flex items-center gap-2 text-xs text-gray-700">
                    <input
                      type="checkbox"
                      checked={selectedSupplierIds.includes(supplier.id)}
                      onChange={(event) => setSelectedSupplierIds((current) => event.target.checked
                        ? [...current, supplier.id]
                        : current.filter((id) => id !== supplier.id))}
                    />
                    <span>{supplier.name}{supplier.email ? ` · ${supplier.email}` : ""}</span>
                  </label>
                ))}
                <p className="text-[11px] text-gray-500">Issuing records invitations in the ERP; external email delivery is not configured here.</p>
              </fieldset>
              <div className="grid grid-cols-2 gap-3">
                {[
                  { label: "Unit", key: "unit" },
                  { label: "Required By", key: "required_by", type: "date" },
                  { label: "Response Deadline", key: "response_deadline", type: "date" },
                ].map(f => (
                  <div key={f.key}>
                    <label className="block text-xs font-medium text-gray-600 mb-1">{f.label}</label>
                    <input type={f.type ?? "text"}
                      value={(form as Record<string, string>)[f.key]}
                      onChange={e => setForm(prev => ({ ...prev, [f.key]: e.target.value }))}
                      className="w-full border rounded px-3 py-2 text-sm focus:ring-1 focus:ring-blue-500 outline-none"
                    />
                  </div>
                ))}
              </div>
            </div>
            <div className="px-6 pb-5 flex gap-3">
              <button onClick={create} disabled={saving}
                className="flex-1 rounded bg-blue-600 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50">
                {saving ? "Creating…" : "Create RFQ"}
              </button>
              <button onClick={() => setShowCreate(false)}
                className="flex-1 rounded border py-2 text-sm text-gray-600 hover:bg-gray-50">
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Add Response Modal */}
      {showResponse && selected && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-xl shadow-2xl w-full max-w-md">
            <div className="px-6 py-4 border-b flex items-center justify-between">
              <h2 className="text-base font-semibold">Add Supplier Response</h2>
              <button onClick={() => setShowResponse(false)} className="text-gray-400 hover:text-gray-600 text-xl">×</button>
            </div>
            <div className="p-6 space-y-3">
              {error && <p className="text-xs text-red-500 bg-red-50 border border-red-200 rounded px-3 py-2">{error}</p>}
              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1">Invited supplier *</label>
                <select
                  value={respForm.supplier_id}
                  onChange={(event) => setRespForm((prev) => ({ ...prev, supplier_id: event.target.value }))}
                  className="w-full border rounded px-3 py-2 text-sm"
                >
                  <option value="">Select invited supplier</option>
                  {selected.responses.filter((response) => response.invitation_status === "ISSUED" && response.status === "PENDING").map((response) => (
                    <option key={response.id} value={response.supplier_id}>{response.supplier_name ?? response.supplier_id}</option>
                  ))}
                </select>
                <p className="mt-1 text-[11px] text-gray-500">Internal procurement users record a quote supplied through the approved business channel.</p>
              </div>
              {[
                { label: "Quoted Unit Price", key: "quoted_unit_price", type: "number", placeholder: "0.00" },
                { label: "Currency", key: "quoted_currency", placeholder: "KES" },
                { label: "Lead Time (days)", key: "lead_time_days", type: "number", placeholder: "7" },
                { label: "Valid Until", key: "valid_until", type: "date" },
                { label: "Payment Terms", key: "payment_terms", placeholder: "e.g. Net 30" },
                { label: "Notes", key: "notes", placeholder: "" },
              ].map(f => (
                <div key={f.key}>
                  <label className="block text-xs font-medium text-gray-600 mb-1">{f.label}</label>
                  <input type={f.type ?? "text"} placeholder={f.placeholder}
                    value={(respForm as Record<string, string>)[f.key]}
                    onChange={e => setRespForm(prev => ({ ...prev, [f.key]: e.target.value }))}
                    className="w-full border rounded px-3 py-2 text-sm focus:ring-1 focus:ring-blue-500 outline-none"
                  />
                </div>
              ))}
            </div>
            <div className="px-6 pb-5 flex gap-3">
              <button onClick={submitResponse} disabled={saving}
                className="flex-1 rounded bg-blue-600 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50">
                {saving ? "Saving…" : "Submit Response"}
              </button>
              <button onClick={() => setShowResponse(false)}
                className="flex-1 rounded border py-2 text-sm text-gray-600 hover:bg-gray-50">
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
